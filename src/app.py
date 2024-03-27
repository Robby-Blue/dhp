import os
from dotenv import load_dotenv
from flask import Flask, request, jsonify

import backend

# setup
load_dotenv(".env")

# web server
app = Flask(__name__)

@app.route('/api/posts/')
def get_posts():
    return jsonify(backend.get_posts())

@app.route('/api/posts/<post_id>')
def get_post(post_id):
    res, status_code = backend.get_post(post_id)
    return jsonify(res), status_code

@app.route('/api/createpost/', methods=['POST'])
def createpost():
    json_data = request.json
    text = json_data["text"]

    backend.create_post(text)

    return "posted"

@app.route('/api/comments/')
def get_comments():
    return jsonify(backend.get_comments())

@app.route('/api/comments/<comment_id>')
def get_comment(comment_id):
    res, status_code = backend.get_comment(comment_id)
    return jsonify(res), status_code

@app.route('/api/createcomment/', methods=['POST'])
def createcomment():
    json_data = request.json
    text = json_data["text"]
    parent = json_data["parent"]

    backend.create_comment(text, parent)

    return {"success": True}, 200

@app.route('/api/sharecomment/', methods=['POST'])
def sharecomment():
    json_data = request.json
    comment_id = json_data["id"]
    domain = json_data["domain"]
    
    res, status_code = backend.share_comment(comment_id, domain)
    return jsonify(res), status_code

if __name__ == '__main__':
    app.run(host=os.getenv("HOST"), port=os.getenv("PORT"))