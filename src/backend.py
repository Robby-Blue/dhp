import os
import requests
import time
import uuid
from datetime import datetime, timezone
from urllib.parse import urlparse

from database_helper import DatabaseHelper
import crypto_helper as crypto

# db stuff
db = DatabaseHelper()
db.connect()
db.setup()

def get_index():
    return {
        "public_key": crypto.get_public_pem(),
        "domain": self_domain
    }

def get_posts():
    result = db.query("SELECT * FROM posts WHERE is_self=true")
    return [format_post(post) for post in result]

def get_post(post_id):
    global_search = "@" in post_id
    if global_search:
        id_segments = post_id.split("@")
        post_id = id_segments[0]

    result = db.query("SELECT * FROM posts WHERE id=%s", (post_id,))

    if len(result) > 0: # post found
        post = result[0]
        return format_post(post), 200

    if not global_search: # was local search and no post
        return {"error": "post not found"}, 404

    # global search and no post found, continue
    post_id = id_segments[0]
    domain = fix_url(id_segments[1])
    url = f"{domain}/api/posts/{post_id}"

    data = requests.get(url)

    if not data:
        return {"error": f"{url} returned {data.status_code}"}, data.status_code

    # post found, need to verify signature
    post = data.json()
    signature = crypto.signature_from_string(post["signature"])

    pubkey = get_pubkey_of_instance(domain)

    if not pubkey:
        return {"error": f"cant get pubkey"}, 404

    if not crypto.verify_signature(crypto.stringify_post({
        "id": post["id"],
        "posted_at": post["posted_at"],
        "text": post["text"],
        "user": domain
    }), signature, pubkey):
        return {"error": f"couldnt verify signature"}, 400

    post["is_self"] = False
    post["user"] = domain
    db.execute("""
INSERT INTO posts (id, is_self, user, text, posted_at, signature)
VALUES (%s, %s, %s, %s, %s, %s)
""", (post["id"], False, domain, post["text"], from_timestamp(post["posted_at"]), signature))
    return post, 200

def create_post(text):
    uuid = generate_id()
    timestamp = to_timestamp(datetime.now())

    signature = crypto.sign_string(crypto.stringify_post({
        "id": uuid,
        "posted_at": timestamp,
        "text": text,
        "user": self_domain
    }))

    db.execute("""
INSERT INTO posts (id, is_self, user, text, posted_at, signature)
VALUES (%s, %s, %s, %s, %s, %s);
""", (uuid, True, self_domain, text, from_timestamp(timestamp), signature))

def get_comments():
    result = db.query("SELECT * FROM comments")
    return [format_comment(comment) for comment in result]

def get_comment(comment_id):
    result = db.query("SELECT * FROM comments WHERE id=%s", (comment_id,))

    if len(result) == 0:
        return {"error": "comment not found"}, 404
    
    comment = result[0]
    return format_comment(comment), 200

def create_comment(text, parent):
    error, parent_post, parent_comment = get_parent(parent)
    
    if error:
        return {"error": error}, 400
    
    parent_comment_id = parent_comment.get("id", None)

    # write comment to db
    uuid = generate_id()
    timestamp = to_timestamp(datetime.now())

    signature = crypto.sign_string(crypto.stringify_comment({
        "id": uuid,
        "parent_post_id": parent_post["id"],
        "parent_comment_id": parent_comment_id if parent_comment else None,
        "parent_post_signature": parent_post["signature"],
        "parent_comment_signature": parent_comment["signature"] if parent_comment else None,
        "posted_at": timestamp,
        "text": text,
        "user": self_domain
    }))

    # need the uuid for later
    db.execute("""
INSERT INTO comments (id, is_self, parent_post_id, parent_comment_id, user, text, posted_at, signature) 
VALUES (%s, %s, %s, %s, %s, %s, %s, %s);
""", (uuid, True, parent_post["id"], parent_comment_id, self_domain, text, from_timestamp(timestamp), signature))

    # now need to share the comment with other instances
    # first, figure out which instances to share to
    # instance of post and all comments
    post, _ = get_post(parent_post["id"])
    instances = [post["user"]]

    result = db.query("""
WITH RECURSIVE comment_tree AS (
    SELECT
        id, user
    FROM comments WHERE
        parent_post_id = %s AND parent_comment_id is NULL
    
    UNION ALL
    
    SELECT
        c.id, c.user
    FROM comments c
    INNER JOIN
        comment_tree ct ON c.parent_comment_id = ct.id
)
SELECT * FROM comment_tree;""", (parent_post["id"],))
    
    for row in result:
        user = row["user"]
        if user == self_domain:
            continue
        if user not in instances:
            instances.append(user)

    db.execute_many("""
INSERT INTO task_queue (type, domain, comment_id) VALUES (%s, %s, %s) 
""", [("share_comment", instance, uuid) for instance in instances])

    return {"success": True}, 200

def share_comment(comment, domain):
    domain = fix_url(domain)
    comment_id = comment["id"]

    result = db.query("SELECT * FROM comments WHERE id=%s", (comment_id,))
    if len(result) != 0:
        return {"error": "already exists"}, 400
    
    parent = comment["parent"]
    error, parent_post, parent_comment = get_parent(parent)
    
    parent_comment_id = parent_comment["id"] if parent_comment else None

    if error:
        return {"error": "unknown dependent id"}, 404

    signature = crypto.signature_from_string(comment["signature"])

    db.execute("""
INSERT INTO comments (id, is_self, parent_post_id, parent_comment_id, user, text, posted_at, signature)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
(comment_id, False, parent_post["id"], parent_comment_id, domain, comment["text"], from_timestamp(comment["posted_at"]), signature))

    db.execute("""
INSERT INTO task_queue (type, domain, comment_id) VALUES (%s, %s, %s) 
""", ("verify_comment",domain, comment_id))

    return {"success": True}, 200

def format_post(sql_post):
    return {
        "id": sql_post["id"],
        "is_self": bool(sql_post["is_self"]),
        "posted_at": to_timestamp(sql_post["posted_at"]),
        "text": sql_post["text"],
        "user": sql_post["user"],
        "signature": crypto.signature_to_string(sql_post["signature"])
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
        "user": sql_comment["user"],
        "signature": crypto.signature_to_string(sql_comment["signature"])
    }

def get_pubkey_of_instance(domain):
    try:
        result = db.query("SELECT * FROM users WHERE domain=%s;", (domain,))

        if len(result) == 1:
            return crypto.public_key_from_string(result[0]["public_key"])
        
        r = requests.get(f"{domain}/api")
        key_string = r.json()["public_key"]

        db.execute("INSERT INTO users (domain, public_key) VALUES (%s, %s)",
                (domain, key_string))
        
        return crypto.public_key_from_string(key_string)
    except:
        return None

def get_parent(parent):
    parent_id = parent["id"]
    parent_type = parent["type"]

    parent_post = None
    parent_comment = None

    if parent_type == "post":
        result = db.query("SELECT * FROM posts WHERE id=%s", (parent_id,))
        if len(result) == 0:
            return "parent not found", None, None
        parent_post = result[0]
    elif parent_type == "comment":
        result = db.query("SELECT * FROM comments WHERE id=%s", (parent_id,))
        if len(result) == 0:
            return "parent not found", None, None
        parent_comment = result[0]
        result = db.query("SELECT * FROM posts WHERE id=%s", (parent_comment["parent_post_id"],))
        parent_post = result[0]
    else:
        return "invalid parent type", None, None
    return False, parent_post, parent_comment

def fix_url(given_domain):
    if not given_domain.startswith("http"):
        default_scheme = os.getenv("DEFAULT_SCHEME")
        given_domain=f"{default_scheme}://{given_domain}"
    parsed_url = urlparse(given_domain)
    domain = parsed_url.scheme+"://"+parsed_url.hostname
    if parsed_url.port:
        domain+=":"+str(parsed_url.port)
    return domain

def process_task_queue():
    while True:
        tasks = db.query("SELECT * FROM task_queue;")
        for task in tasks:
            should_delete = process_task(task)
            if should_delete:
                db.execute("DELETE FROM task_queue WHERE id=%s",
                    (task["id"],))

        time.sleep(6)

def process_task(task):
    task_type = task["type"]
    if task_type == "share_comment":
        return process_share_comment_task(task)
    if task_type == "verify_comment":
        return process_verify_comment_task(task)
    return False # idk what to do

def process_share_comment_task(task):
    instance = task["domain"]
    uuid = task["comment_id"]

    try:
        r = requests.post(f"{instance}/api/sharecomment/", 
            json={
                "domain": self_domain,
                "comment": get_comment(uuid)[0]
            })
        if r.status_code == 200:
            return True
        
        # stop resending comments it already knows about
        if r.json()["error"] == "already exists":
            return True
    except:
        return False
    
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
    pubkey = get_pubkey_of_instance(comment["user"])

    if not pubkey:
        return False

    verified = crypto.verify_signature(crypto.stringify_comment({
        "id": comment["id"],
        "parent_post_id": comment["parent_post_id"],
        "parent_comment_id": comment["parent_comment_id"],
        "parent_post_signature": comment["parent_post_signature"],
        "parent_comment_signature": comment["parent_comment_signature"],
        "posted_at": to_timestamp(comment["posted_at"]),
        "text": comment["text"],
        "user": comment["user"]
    }), signature, pubkey)

    if verified:
        db.execute("""
UPDATE comments SET signature_verified=1 WHERE id=%s;
""", (comment["id"],))

    # either its verified and done
    # or its unverifieable, no need to retry later
    return True

def to_timestamp(datetime):
    return int(datetime.replace(tzinfo=timezone.utc).timestamp())

def from_timestamp(timestamp):
    return datetime.fromtimestamp(timestamp, tz=timezone.utc)

def generate_id():
    generated_uuid = uuid.uuid4()
    return str(generated_uuid)

self_domain = fix_url(os.getenv("DOMAIN"))