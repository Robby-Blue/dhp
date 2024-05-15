from threading import Thread
import os
from dotenv import load_dotenv
from flask import Flask, request, jsonify, redirect

from frontend import sites

# setup
load_dotenv(".env")

import backend

# web server
app = Flask(__name__)

# front end
@app.route("/posts/<path:post_id>/")
def post(post_id):
    data, err = backend.get_post(post_id)
    return sites.get_post_site(data, err)

@app.route("/writepost/", methods=['GET'])
def writepost():
    return sites.get_writepost_site()

@app.route("/writepost/", methods=['POST'])
def writepost_post():
    form = request.form
    if not "text" in form:
        return format_err({"error": "text not given", "code": 400}), 400
    text = form["text"]

    res, err = backend.create_post(text)
    if err:
        return format_err(err)
    
    id = res["id"]
    return redirect(f"/posts/{id}")

@app.route("/<path:id>/writereply/", methods=['GET'])
def writereply(id):
    data, err = backend.get_post_or_comment(id)
    return sites.get_writereply_site(data, err)

@app.route("/<path:id>/writereply/", methods=['POST'])
def writereply_post(id):
    form = request.form
    if not "text" in form:
        return format_err({"error": "text not given", "code": 400}), 400
    
    text = form["text"]

    data, err = backend.get_post_or_comment(id)
    if err:
        return format_err(err)
    
    parent = {
        "type": data["type"],
        "id": data["submission"]["id"]
    }

    res, err = backend.create_comment(text, parent)
    if err:
        return format_err(err)
    
    id = res["parent_post_id"]
    return redirect(f"/posts/{id}")

# api
@app.route("/api/")
def api_index():
    return format_res(backend.get_index())

@app.route("/api/posts/")
def api_get_posts():
    return format_res(backend.get_posts())

@app.route("/api/posts/<path:post_id>")
def api_get_post(post_id):
    res = backend.get_post(post_id)
    return format_res(res)

@app.route("/api/sharecomment/", methods=["POST"])
def api_sharecomment():
    json_data = request.json
    comment = json_data["comment"]
    domain = json_data["domain"]
    
    res = backend.share_comment(comment, domain)
    return format_res(res)

def format_res(res):
    data, err = res
    if err:
        status_code = err["code"]
        return format_err(err), status_code
    return jsonify(data)

def format_err(err):
    err.pop("code")
    return jsonify(err)

if __name__ == "__main__":
    t=Thread(target=backend.process_task_queue)
    t.daemon = True
    t.start()
    app.run(host=os.getenv("HOST"), port=os.getenv("PORT"))