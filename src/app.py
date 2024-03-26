import os
import requests
from datetime import datetime, timezone
from urllib.parse import urlparse
from dotenv import load_dotenv
from flask import Flask, request, jsonify

from database_helper import DatabaseHelper

# setup
load_dotenv(".env")

# db stuff
db = DatabaseHelper()
db.connect()
db.setup()

# web server
app = Flask(__name__)

@app.route('/api/posts/')
def get_posts():
    result = db.query("SELECT * FROM posts WHERE is_self=true")
    
    return jsonify([format_post(post) for post in result])

@app.route('/api/posts/<post_id>')
def get_post(post_id):
    result = db.query("SELECT * FROM posts WHERE id=%s and is_self=true", (post_id,))

    if len(result) == 0:
        return "post not found", 404
    
    post = result[0]
    return jsonify(format_post(post))

@app.route('/api/createpost/', methods=['POST'])
def createpost():
    json_data = request.json
    text = json_data["text"]

    db.execute("""
INSERT INTO posts (id, is_self, text)
VALUES (
    UUID(),
    true,
    %s
)
""", (text,))

    return "posted"

@app.route('/api/comments/')
def get_comments():
    result = db.query("SELECT * FROM comments")
    
    return jsonify([format_comment(comment) for comment in result])

@app.route('/api/comments/<comments_id>')
def get_comment(comments_id):
    result = db.query("SELECT * FROM comments WHERE id=%s", (comments_id,))

    if len(result) == 0:
        return "comment not found", 404
    
    comment = result[0]
    return jsonify(format_comment(comment))

@app.route('/api/createcomment/', methods=['POST'])
def createcomment():
    json_data = request.json
    text = json_data["text"]
    parent = json_data["parent"]

    error, parent_post_id, parent_comment_id = get_parent(parent)
    
    if error:
        return error, 400

    db.execute("""
INSERT INTO comments (id, is_self, parent_post_id, parent_comment_id, text) 
VALUES (
    UUID(),
    true,
    %s,
    %s,
    %s
)
""", (parent_post_id, parent_comment_id, text))

    return "posted", 200

@app.route('/api/sharepost/', methods=['POST'])
def sharepost():
    json_data = request.json
    post_id = json_data["id"]

    domain, error = fix_url(json_data["domain"])
    if error:
        return error, 400

    result = db.query("SELECT * FROM posts WHERE id=%s", (post_id,))
    if len(result) != 0:
        return "post already exists", 400
    
    url = f"{domain}/api/posts/{post_id}"

    data = requests.get(url)

    if not data:
        return f"{url} returned {data.status_code}", 500

    post = data.json()
    db.execute("""
INSERT INTO posts (id, is_self, user, text, posted_at)
VALUES (%s, %s, %s, %s, %s)""",
(post["id"], False, domain, post["text"], datetime.fromtimestamp(post["posted_at"], tz=timezone.utc)))

    return "posted", 200

@app.route('/api/sharecomment/', methods=['POST'])
def sharecomment():
    json_data = request.json
    comment_id = json_data["id"]

    domain, error = fix_url(json_data["domain"])
    if error:
        return error, 400

    result = db.query("SELECT * FROM comments WHERE id=%s", (comment_id,))
    if len(result) != 0:
        return "post already exists", 400
    
    url = f"{domain}/api/comments/{comment_id}"

    data = requests.get(url)

    if not data:
        return f"{url} returned {data.status_code}", 500
    
    comment = data.json()
    parent = comment["parent"]
    error, parent_post_id, parent_comment_id = get_parent(parent)
    
    if error:
        return "parent not found", 400

    db.execute("""
INSERT INTO comments (id, is_self, parent_post_id, parent_comment_id, user, text, posted_at)
VALUES (%s, %s, %s, %s, %s, %s, %s)""",
(comment["id"], False, parent_post_id, parent_comment_id, domain, comment["text"], datetime.fromtimestamp(comment["posted_at"], tz=timezone.utc)))

    return "posted", 200

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
        parent_post_id = parent_id
    elif parent_type == "comment":
        result = db.query("SELECT * FROM comments WHERE id=%s", (parent_id,))
        parent_comment_id = parent_id
    else:
        return "invalid parent type", None, None
    if len(result) == 0:
        return "parent not found", None, None
    return False, parent_post_id, parent_comment_id

def validate_url(parsed_url):
    if not parsed_url.scheme:
        return False, "needs scheme"
    return True, None

def fix_url(given_domain):
    parsed_url = urlparse(given_domain)
    valid, reason = validate_url(parsed_url)
    if not valid:
        return None, reason
    domain = parsed_url.scheme+"://"+parsed_url.hostname
    if parsed_url.port:
        domain+=":"+str(parsed_url.port)
    return domain, None

if __name__ == '__main__':
    app.run(host=os.getenv("HOST"), port=os.getenv("PORT"))