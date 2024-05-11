from threading import Thread
import os
from dotenv import load_dotenv
from flask import Flask, request, jsonify, send_from_directory

# setup
load_dotenv(".env")

import backend

# web server
app = Flask(__name__)

# front end
@app.route("/")
def index():
    return send_from_directory('static', 'index.html')

@app.route("/posts/<path:_>")
def post(_):
    return send_from_directory('static', 'posts/posts.html')

@app.route("/writepost/")
def writepost():
    return send_from_directory('static', 'writepost/writepost.html')

@app.route("/writereply/")
def writereply():
    return send_from_directory('static', 'writereply/writereply.html')

# api
@app.route("/api/")
def api_index():
    return jsonify(backend.get_index())

@app.route("/api/posts/")
def api_get_posts():
    return jsonify(backend.get_posts())

@app.route("/api/posts/<path:post_id>")
def api_get_post(post_id):
    res, status_code = backend.get_post(post_id)
    return jsonify(res), status_code

@app.route("/api/comments/")
def api_get_comments():
    return jsonify(backend.get_comments())

@app.route("/api/comments/<path:comment_id>")
def api_get_comment(comment_id):
    res, status_code = backend.get_comment(comment_id)
    return jsonify(res), status_code

@app.route("/api/preview/posts/<path:post_id>")
def api_get_post_preview(post_id):
    res, status_code = backend.get_post(post_id, False)
    return jsonify(res), status_code

@app.route("/api/preview/comments/<path:comment_id>")
def api_get_comment_preview(comment_id):
    print(comment_id)
    res, status_code = backend.get_comment(comment_id)
    return jsonify(res), status_code

@app.route("/api/createpost/", methods=["POST"])
def api_createpost():
    json_data = request.json
    text = json_data["text"]

    res, status_code = backend.create_post(text)

    return jsonify(res), status_code

@app.route("/api/createcomment/", methods=["POST"])
def api_createcomment():
    json_data = request.json
    text = json_data["text"]
    parent = json_data["parent"]

    res, status_code = backend.create_comment(text, parent)

    return jsonify(res), status_code

@app.route("/api/sharecomment/", methods=["POST"])
def api_sharecomment():
    json_data = request.json
    comment = json_data["comment"]
    domain = json_data["domain"]
    
    res, status_code = backend.share_comment(comment, domain)
    return jsonify(res), status_code

if __name__ == "__main__":
    t=Thread(target=backend.process_task_queue)
    t.daemon = True
    t.start()
    app.run(host=os.getenv("HOST"), port=os.getenv("PORT"))