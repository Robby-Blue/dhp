import os
import requests
from datetime import datetime, timezone
from urllib.parse import urlparse

from database_helper import DatabaseHelper

# db stuff
db = DatabaseHelper()
db.connect()
db.setup()

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

    post = data.json()
    post["is_self"] = False
    post["user"] = domain
    db.execute("""
INSERT INTO posts (id, is_self, user, text, posted_at)
VALUES (%s, %s, %s, %s, %s)
""", (post["id"], False, domain, post["text"], datetime.fromtimestamp(post["posted_at"], tz=timezone.utc)))
    return post, 200

def create_post(text):
    db.execute("""
INSERT INTO posts (id, is_self, text)
VALUES (
    UUID(),
    true,
    %s
)
""", (text,))

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
    error, parent_post_id, parent_comment_id = get_parent(parent)
    
    if error:
        return {"error": error}, 400

    # write comment to db
    uuid = db.query("SELECT UUID();")[0]["UUID()"]
    # need the uuid for later
    db.execute("""
INSERT INTO comments (id, is_self, parent_post_id, parent_comment_id, text) 
VALUES (
    %s,
    true,
    %s,
    %s,
    %s
);
""", (uuid, parent_post_id, parent_comment_id, text))

    # now need to share the comment with other instances
    # first, figure out which instances to share to
    # instance of post and all comments
    post, _ = get_post(parent_post_id)
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
SELECT * FROM comment_tree;""", (parent_post_id,))
    
    for row in result:
        user = row["user"]
        if user not in instances:
            instances.append(user)

    fails = []

    for instance in instances:
        if not instance:
            continue
        success = False
        try:
            r = requests.post(f"{instance}/api/sharecomment/", 
                json={"domain": "localhost:3000", "id": uuid})
            if r.status_code == 200:
                success = True
        except:
            pass
        if not success:
            fails.append(instance)

    if fails:
        db.execute_many("""
INSERT INTO failed_shares (user, comment_id) VALUES (%s, %s) 
""", [(instance, uuid) for instance in fails])

    return {"success": True}, 200

def share_comment(comment_id, domain):
    domain = fix_url(domain)

    result = db.query("SELECT * FROM comments WHERE id=%s", (comment_id,))
    if len(result) != 0:
        return {"error": "post already exists"}, 400
    
    url = f"{domain}/api/comments/{comment_id}"

    data = requests.get(url)

    if not data:
        return {"error": f"{url} returned {data.status_code}"}, data.status_code
    
    comment = data.json()
    parent = comment["parent"]
    error, parent_post_id, parent_comment_id = get_parent(parent)
    
    if error:
        return {"error": "parent not found"}, 400

    db.execute("""
INSERT INTO comments (id, is_self, parent_post_id, parent_comment_id, user, text, posted_at)
VALUES (%s, %s, %s, %s, %s, %s, %s)""",
(comment["id"], False, parent_post_id, parent_comment_id, domain, comment["text"], datetime.fromtimestamp(comment["posted_at"], tz=timezone.utc)))

    return {"success": True}, 200

def format_post(sql_post):
    return {
        "id": sql_post["id"],
        "is_self": bool(sql_post["is_self"]),
        "posted_at": int(sql_post["posted_at"].replace(tzinfo=timezone.utc).timestamp()),
        "text": sql_post["text"],
        "user": sql_post["user"],
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
        "posted_at": int(sql_comment["posted_at"].replace(tzinfo=timezone.utc).timestamp()),
        "text": sql_comment["text"],
        "user": sql_comment["user"],
    }

def get_parent(parent):
    parent_id = parent["id"]
    parent_type = parent["type"]

    parent_post_id = None
    parent_comment_id = None

    if parent_type == "post":
        result = db.query("SELECT * FROM posts WHERE id=%s", (parent_id,))
        if len(result) == 0:
            return "parent not found", None, None
        parent_post_id = parent_id
    elif parent_type == "comment":
        result = db.query("SELECT * FROM comments WHERE id=%s", (parent_id,))
        if len(result) == 0:
            return "parent not found", None, None
        parent_comment_id = parent_id
        parent_post_id = result["parent_post_id"]
    else:
        return "invalid parent type", None, None
    return False, parent_post_id, parent_comment_id

def fix_url(given_domain):
    if not given_domain.startswith("http"):
        default_scheme = os.getenv("DEFAULT_SCHEME")
        given_domain=f"{default_scheme}://{given_domain}"
    parsed_url = urlparse(given_domain)
    domain = parsed_url.scheme+"://"+parsed_url.hostname
    if parsed_url.port:
        domain+=":"+str(parsed_url.port)
    return domain