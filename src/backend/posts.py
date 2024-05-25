import requests
import time
from datetime import datetime
import backend.crypto_helper as crypto

from backend import (db, self_domain, fix_url, parse_id, build_id, from_timestamp, to_timestamp, generate_id, )
from backend.instances import get_instance, get_pubkey_of_instance

def get_posts(instance=None):
    if not instance:
        instance = self_domain
    instance = fix_url(instance)

    if instance == self_domain:
        result = db.query("SELECT * FROM posts JOIN instances ON posts.instance_domain = instances.domain WHERE posts.is_self=true")
        posts = [format_post(post) for post in result]
        return {"posts": posts}, None
    
    posts, _ = get_posts_from_instance(instance)
    if posts:
        return {"posts": posts}, None

    result = db.query("SELECT * FROM posts JOIN instances ON posts.instance_domain = instances.domain WHERE instance_domain=%s", (instance,))
    posts = [format_post(post) for post in result]
    return {
        "is_cached": True, 
        "posts": posts
    }, None

def get_posts_from_instance(instance):
    domain = fix_url(instance)

    url = f"{domain}/api/posts/"
    
    try:
        data = requests.get(url)

        if not data:
            post_exists = data.status_code != 404 
            return None, {"error": f"{url} returned {data.status_code}", "post_exists": post_exists}

        # post found, need to verify signature
        posts = data.json()["posts"]
    except:
        # invalid json or bad request might be server error with an existing post
        return None, {"error": f"http req to {url} didn't work", "post_exists": True}

    results = db.query("SELECT * FROM posts WHERE instance_domain=%s", (instance,))
    ids = [result["id"] for result in results]

    verified_posts = []

    for post in posts:
        post["is_self"] = False
        
        if post["id"] in ids:
            # already in db, already verified
            verified_posts.append(post)
        else:
            # verify it and then add it
            verify_result = verify_and_add_post(post, domain)
            if verify_result["verified"]:
                verified_posts.append(post)

    return verified_posts, None

def get_post(post_id, *, load_comments=True, use_cached_global=False, allow_cached_global_as_fallback=True, allow_requests=True):
    post_id, instance = parse_id(post_id)

    local_search = not bool(instance)
    if local_search or use_cached_global:
        post, error = get_post_from_db(post_id, use_cached_global, load_comments)
        if post:
            # if use_cached_global but not if its a local search
            # bc a local search is the newwest data of a local post
            if not local_search:
                post["is_cached"] = True
            return post, error
    
    # local search and no post found, continue
    if allow_requests and instance:
        post, error = get_post_from_instance(instance, post_id, load_comments=load_comments)
        if post:
            return post, error
        # if the post (might) exist it we shouldnt error yet and 
        # try to search for it locally again, the error could just
        # be some http and internet magic
        if error and not error["post_exists"]:
            return post, error

    # local wasnt allowed before and global didnt work
    if allow_cached_global_as_fallback:
        post, error = get_post_from_db(post_id, True, load_comments)
        if post:
            post["is_cached"] = True
        return post, error
    return None, {"error": "post not found", "code": 404}

def get_post_from_db(post_id, allow_global, load_comments):
    post_id, _ = parse_id(post_id)

    if allow_global:
        query = "SELECT * FROM posts JOIN instances ON posts.instance_domain = instances.domain WHERE id=%s"
    else:
        query = "SELECT * FROM posts JOIN instances ON posts.instance_domain = instances.domain WHERE id=%s AND posts.is_self=true"

    result = db.query(query, (post_id,))

    if len(result) == 0:
        return None, {"error": "post not found", "code": 404}
    post = format_post(result[0])

    if load_comments:
        comments_result = db.query("""
SELECT * FROM comments JOIN instances ON comments.instance_domain = instances.domain WHERE parent_post_id=%s""", (post_id,))
        post["comments"] = [format_comment(comment) for comment in comments_result if comment["signature_verified"]]
    
    return post, None

def get_post_from_instance(instance, post_id, *, load_comments=True):
    post_id, _ = parse_id(post_id)
    domain = fix_url(instance)
    url = f"{domain}/api/posts/{post_id}"
    
    try:
        data = requests.get(url)

        if not data:
            post_exists = data.status_code != 404 
            return None, {"error": f"{url} returned {data.status_code}", "post_exists": post_exists}

        # post found, need to verify signature
        post = data.json()
    except:
        # invalid json or bad request might be server error with an existing post
        return None, {"error": f"http req to {url} didn't work", "post_exists": True}

    post["is_self"] = False
    result = db.query("SELECT * FROM posts JOIN instances ON posts.instance_domain = instances.domain WHERE id=%s", (post["id"],))

    if len(result) == 0:
        verify_result = verify_and_add_post(post, domain)
        if not verify_result["verified"]:
            res, err = verify_result["res"]
            if err:
                err["post_exists"] = False
            return res, err
        
    if not load_comments:
        post.pop("comments")
    else:
        # try to find known comments locally
        # together with their instances data
        comments_result = db.query("""
SELECT * FROM comments JOIN instances ON comments.instance_domain = instances.domain WHERE parent_post_id=%s""", (post_id,))
        
        # make a list of all local comments and their
        # instances info, we can use this later to not duplicate
        # comments from other instances and to not have to ask sql
        # about each new comment from other instances
        instance_lookup = {}
        local_comments = {}
        for comment in comments_result:
            formatted = format_comment(comment)
            instance_lookup[formatted["instance"]] = formatted["author"]
            local_comments[formatted["id"]] = formatted

        found_all_instances = True

        for i, comment in enumerate(post["comments"]):
            comment.pop("author") # dont trust what the other instance says
            if comment["id"] in local_comments:
                post["comments"][i] = local_comments.pop(comment["id"])
                # remove comment from `comments` such that all remaining elements
                # will be comments which the other instance doesnt know about
                continue
            comment["signature_verified"] = verify_and_add_comment(comment, True)["verified"]

            if comment["instance"] in instance_lookup:
                comment["author"] = instance_lookup[comment["instance"]]
            else:
                if comment["signature_verified"]:
                    # real comment without instance data known
                    found_all_instances = False

        if found_all_instances:
            for comment in local_comments.values():
                if not comment["signature_verified"]:
                    continue
                post["comments"].append(comment)
        else:
            comments_result = db.query("""
SELECT * FROM comments JOIN instances ON comments.instance_domain = instances.domain WHERE parent_post_id=%s""", (post_id,))
            post["comments"] = [format_comment(comment) for comment in comments_result if comment["signature_verified"]]

    return post, None

def verify_and_add_post(post, domain):
    signature = crypto.signature_from_string(post["signature"])

    pubkey = get_pubkey_of_instance(domain)

    if not pubkey:
        return {
            "verified": False,
            "res": (None, {"error": f"cant get pubkey", "code": 404})
        }

    if not crypto.verify_signature(crypto.stringify_post({
        "id": post["id"],
        "posted_at": post["posted_at"],
        "text": post["text"],
        "instance": domain
    }), signature, pubkey):
        return {
            "verified": False,
            "res": (None, {"error": f"couldnt verify signature", "code": 400})
        }

    post["is_self"] = False
    db.execute("""
INSERT INTO posts (id, is_self, instance_domain, text, posted_at, signature)
VALUES (%s, %s, %s, %s, %s, %s)
""", (post["id"], False, domain, post["text"], from_timestamp(post["posted_at"]), signature))
    
    return {
        "verified": True,
        "res": (post, None)
    }

def verify_and_add_comment(comment, verify_now):
    parent = comment["parent"]
    parent_post, parent_comment, error = get_parent(parent)
    
    parent_comment_id = parent_comment["id"] if parent_comment else None

    if error:
        return {
            "verified": False,
            "res": (None, {"error": "unknown dependent id", "code": 404})
        }

    if not get_instance(comment["instance"]):
        return {
            "verified": False,
            "res": (None, {"error": "instance not found", "code": 400})
        }

    signature = crypto.signature_from_string(comment["signature"])

    db.execute("""
INSERT INTO comments (id, is_self, parent_post_id, parent_comment_id, instance_domain, text, posted_at, signature, signature_verified)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
(comment["id"], False, parent_post["id"], parent_comment_id, comment["instance"], comment["text"], from_timestamp(comment["posted_at"]), signature, False))

    verified = False

    if verify_now:
        res = process_verify_comment_task({"comment_id": comment["id"]})
        verified = res["verified"]
    
    if not verified:
        db.execute("""
INSERT INTO task_queue (type, instance_domain, comment_id) VALUES (%s, %s, %s) 
""", ("verify_comment", comment["instance"], comment["id"]))
    
    return {
        "verified": verified,
        "res": ({"success": True}, None)
    }

def create_post(text):
    uuid = generate_id()
    timestamp = to_timestamp(datetime.now())

    signature = crypto.sign_string(crypto.stringify_post({
        "id": uuid,
        "posted_at": timestamp,
        "text": text,
        "instance": self_domain
    }))

    db.execute("""
INSERT INTO posts (id, is_self, instance_domain, text, posted_at, signature)
VALUES (%s, %s, %s, %s, %s, %s);
""", (uuid, True, self_domain, text, from_timestamp(timestamp), signature))
    
    return {"id": uuid}, None

def get_comments():
    result = db.query("SELECT * FROM comments JOIN instances ON comments.instance_domain = instances.domain")
    return [format_comment(comment) for comment in result], None

def get_comment(comment_id):
    comment_id, instance = parse_id(comment_id)

    if instance:
        result = db.query("SELECT * FROM comments JOIN instances ON comments.instance_domain = instances.domain WHERE id=%s AND instance_domain=%s", (comment_id, instance))
    else:
        result = db.query("SELECT * FROM comments JOIN instances ON comments.instance_domain = instances.domain WHERE id=%s AND comments.is_self=true", (comment_id,))

    if len(result) == 0:
        return None, {"error": "comment not found", "code": 404}
    
    comment = result[0]
    return format_comment(comment), None

def create_comment(text, parent):
    parent_post, parent_comment, error = get_parent(parent)
    
    if error:
        return None, {"error": error, "code": 400}
    
    parent_comment_id = parent_comment["id"] if parent_comment else None

    # write comment to db
    uuid = generate_id()
    timestamp = to_timestamp(datetime.now())

    signature = crypto.sign_string(crypto.stringify_comment({
        "id": uuid,
        "parent_post_id": parent_post["id"],
        "parent_comment_id": parent_comment_id,
        "parent_post_signature": parent_post["signature"],
        "parent_comment_signature": parent_comment["signature"] if parent_comment else None,
        "posted_at": timestamp,
        "text": text,
        "instance": self_domain
    }))

    # need the uuid for later
    db.execute("""
INSERT INTO comments (id, is_self, parent_post_id, parent_comment_id, instance_domain, text, posted_at, signature, signature_verified) 
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s);
""", (uuid, True, parent_post["id"], parent_comment_id, self_domain, text, from_timestamp(timestamp), signature, True))

    # share comment to post host
    post, _ = get_post(parent_post["id"], use_cached_global=True)
    instance = post["instance"]

    if instance != self_domain:
        db.execute("""
INSERT INTO task_queue (type, instance_domain, comment_id) VALUES (%s, %s, %s) 
""", ("share_comment", instance, uuid))

    parent_id = build_id(post["id"], post["instance"])
    return {"parent_post_id": parent_id}, None

def share_comment(comment, domain):
    domain = fix_url(domain)

    result = db.query("SELECT * FROM comments JOIN instances ON comments.instance_domain = instances.domain WHERE id=%s", (comment["id"],))
    if len(result) != 0:
        return None, {"error": "already exists", "code": 400}

    res, err = verify_and_add_comment(comment, False)["res"]

    return res, err

def get_post_or_comment(id):
    post, err = get_post(id, load_comments=False, use_cached_global=True)
    if post:
        return {"type": "post", "submission": post}, err
    comment, err = get_comment(id)
    if comment:
        return {"type": "comment", "submission": comment}, err
    return None, {"error": "post or comment not found", "code": 404}

def format_post(sql_post):
    return {
        "id": sql_post["id"],
        "is_self": bool(sql_post["is_self"]),
        "posted_at": to_timestamp(sql_post["posted_at"]),
        "text": sql_post["text"],
        "instance": sql_post["instance_domain"],
        "signature": crypto.signature_to_string(sql_post["signature"]),
        "author": {
            "nickname": sql_post["nickname"],
            "pronouns": sql_post["pronouns"]
        }
    }

def format_comment(sql_comment):
    if sql_comment["parent_post_id"]:
        parent_id = sql_comment["parent_post_id"]
        parent_type = "post"
    if sql_comment["parent_comment_id"]:
        parent_id = sql_comment["parent_comment_id"]
        parent_type = "comment"
    
    return {
        "id": sql_comment["id"],
        "is_self": bool(sql_comment["is_self"]),
        "parent": {
            "id": parent_id,
            "type": parent_type
        },
        "posted_at": to_timestamp(sql_comment["posted_at"]),
        "text": sql_comment["text"],
        "instance": sql_comment["instance_domain"],
        "signature": crypto.signature_to_string(sql_comment["signature"]),
        "signature_verified": bool(sql_comment["signature_verified"]),
        "author": {
            "nickname": sql_comment["nickname"],
            "pronouns": sql_comment["pronouns"]
        }
    }

def get_parent(parent):
    parent_id = parent["id"]
    parent_type = parent["type"]

    parent_post = None
    parent_comment = None

    if parent_type == "post":
        result = db.query("SELECT * FROM posts JOIN instances ON posts.instance_domain = instances.domain WHERE id=%s", (parent_id,))
        if len(result) == 0:
            return None, None, "parent not found"
        parent_post = result[0]
    elif parent_type == "comment":
        result = db.query("SELECT * FROM comments JOIN instances ON comments.instance_domain = instances.domain WHERE id=%s", (parent_id,))
        if len(result) == 0:
            return None, None, "parent not found"
        parent_comment = result[0]
        result = db.query("SELECT * FROM posts JOIN instances ON posts.instance_domain = instances.domain WHERE id=%s", (parent_comment["parent_post_id"],))
        parent_post = result[0]
    else:
        return None, None, "invalid parent type"
    return parent_post, parent_comment, False

def process_task_queue():
    while True:
        tasks = db.query("SELECT * FROM task_queue;")
        for task in tasks:
            should_delete = process_task(task)["task_done"]
            if should_delete:
                db.execute("DELETE FROM task_queue WHERE id=%s",
                    (task["id"],))

        time.sleep(600)

def process_task(task):
    task_type = task["type"]
    if task_type == "share_comment":
        return process_share_comment_task(task)
    if task_type == "verify_comment":
        return process_verify_comment_task(task)
    return {"task_done": False} # idk what to do

def process_share_comment_task(task):
    instance = task["instance_domain"]
    uuid = task["comment_id"]

    try:
        r = requests.post(f"{instance}/api/sharecomment/", 
            json={
                "domain": self_domain,
                "comment": get_comment(uuid)[0]
            })
        if r.status_code == 200:
            return {"task_done": True}
        
        # stop resending comments it already knows about
        if r.json()["error"] == "already exists":
            return {"task_done": True}
    except:
        return {"task_done": False}
    
def process_verify_comment_task(task):
    result = db.query("""
SELECT
    comments.*, parent_post.signature AS parent_post_signature, parent_comment.signature AS parent_comment_signature
FROM
    comments
LEFT JOIN
    posts AS parent_post ON parent_post.id=comments.parent_post_id
LEFT JOIN
    comments as parent_comment on parent_comment.id=comments.parent_comment_id
WHERE
    comments.id=%s;""",
        (task["comment_id"],))
    comment = result[0]

    signature = comment["signature"]
    pubkey = get_pubkey_of_instance(comment["instance_domain"])

    if not pubkey:
        return {"task_done": False, "verified": False}

    verified = crypto.verify_signature(crypto.stringify_comment({
        "id": comment["id"],
        "parent_post_id": comment["parent_post_id"],
        "parent_comment_id": comment["parent_comment_id"],
        "parent_post_signature": comment["parent_post_signature"],
        "parent_comment_signature": comment["parent_comment_signature"],
        "posted_at": to_timestamp(comment["posted_at"]),
        "text": comment["text"],
        "instance": comment["instance_domain"]
    }), signature, pubkey)

    if verified:
        db.execute("""
UPDATE comments SET signature_verified=1 WHERE id=%s;
""", (comment["id"],))

    # either its verified and done
    # or its unverifieable, no need to retry later
    return {"task_done": True, "verified": verified}