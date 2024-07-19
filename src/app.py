from threading import Thread
import os
from dotenv import load_dotenv
from flask import Flask, request, jsonify, redirect
from flask_sock import Sock

from frontend import sites

# setup
load_dotenv(".env")
TOKEN = os.getenv("TOKEN")

import backend
import backend.task_queue

# web server
app = Flask(__name__)
sock = Sock(app)

# front end
@app.route("/")
def selfaccount():
    token = request.cookies.get("token")
    if token != TOKEN:
        return redirect("/login/")
    data, err = backend.instances.get_instance_with_posts()
    return sites.get_instance_site(data, err)

@app.route("/instances/<path:instance>/")
def account(instance):
    token = request.cookies.get("token")
    if token != TOKEN:
        return redirect("/login/")
    data, err = backend.instances.get_instance_with_posts(instance)
    return sites.get_instance_site(data, err)

@app.route("/posts/<path:post_id>/")
def post(post_id):
    token = request.cookies.get("token")
    if token != TOKEN:
        return redirect("/login/")
    data, err = backend.posts.get_post(post_id)
    return sites.get_post_site(data, err)

@app.route("/writepost/", methods=['GET'])
def writepost():
    token = request.cookies.get("token")
    if token != TOKEN:
        return redirect("/login/")
    return sites.get_writepost_site()

@app.route("/writepost/", methods=['POST'])
def writepost_post():
    token = request.cookies.get("token")
    if token != TOKEN:
        return redirect("/login/")
    form = request.form
    if not "text" in form:
        return format_err({"error": "text not given", "code": 400}), 400
    text = form["text"]

    res, err = backend.posts.create_post(text)
    if err:
        return format_err(err)
    
    id = res["id"]
    return redirect(f"/posts/{id}")

@app.route("/writereply/<path:id>/", methods=['GET'])
def writereply(id):
    token = request.cookies.get("token")
    if token != TOKEN:
        return redirect("/login/")
    data, err = backend.posts.get_post_or_comment(id)
    return sites.get_writereply_site(data, err)

@app.route("/writereply/<path:id>/", methods=['POST'])
def writereply_post(id):
    token = request.cookies.get("token")
    if token != TOKEN:
        return redirect("/login/")
    form = request.form
    if not "text" in form:
        return format_err({"error": "text not given", "code": 400}), 400
    
    text = form["text"]

    data, err = backend.posts.get_post_or_comment(id)
    if err:
        return format_err(err)
    
    parent = {
        "type": data["type"],
        "id": data["submission"]["id"]
    }

    res, err = backend.posts.create_comment(text, parent)
    if err:
        return format_err(err)
    
    id = res["parent_post_id"]
    return redirect(f"/posts/{id}")

@app.route("/chats/", methods=['GET'])
def chats():
    token = request.cookies.get("token")
    if token != TOKEN:
        return redirect("/login/")
    
    chats = backend.chats.get_chats()
    return sites.get_chats_site(chats)

@app.route("/chats/<path:instance>/", methods=['GET'])
def chat(instance):
    token = request.cookies.get("token")
    if token != TOKEN:
        return redirect("/login/")
    
    before = request.args.get("before", default=None)
    after = request.args.get("after", default=None)
    messages_only = request.args.get("messages_only", default=False)

    chat, err = backend.chats.get_chat(instance, before, after)
    if err:
        return format_err(err)
    if messages_only:
        return str(sites.create_messages_container(chat["messages"]))
    return sites.get_chat_site(chat)

@app.route("/chats/<path:instance>/send-message", methods=['POST'])
def send_message(instance):
    token = request.cookies.get("token")
    if token != TOKEN:
        return redirect("/login/")
    form = request.form
    if not "text" in form:
        return format_err({"error": "text not given", "code": 400}), 400
    text = form["text"]

    res, err = backend.chats.send_message(instance, text)
    if err:
        return format_err(err)
    
    return redirect(f"/chats/{instance}")

@app.route("/settings/", methods=['GET'])
def settings():
    token = request.cookies.get("token")
    if token != TOKEN:
        return redirect("/login/")
    
    data, _ = backend.instances.get_instance_data(backend.self_domain)
    return sites.get_settings_site(data)

@app.route("/settings/", methods=['POST'])
def settings_post():
    token = request.cookies.get("token")
    if token != TOKEN:
        return redirect("/login/")

    data, err = backend.instances.edit_settings(request.form)
    if err:
        return format_err(err)

    return sites.get_settings_site(data, edited=True)

@app.route("/login/", methods=['GET'])
def login():
    return sites.get_login_site()

@app.route("/login/", methods=['POST'])
def login_post():
    form = request.form
    if not "token" in form:
        return format_err({"error": "token not given", "code": 400}), 400
    
    token = form["token"]
    response = redirect("/")
    response.set_cookie("token", token, httponly=True, secure=True, samesite='Strict')
    return response

# ws events
@sock.route("/ws/chats/<path:instance>/")
def echo(ws, instance):
    token = request.cookies.get("token")
    if token != TOKEN:
        return
    backend.events.add_listener(ws, f"chat/{instance}")
    
    # if i dont do this it disconnects
    while True:
        ws.receive()

# public api
@app.route("/api/")
def api_index():
    return format_res(backend.instances.get_index())

@app.route("/api/posts/")
def api_get_posts():
    return format_res(backend.posts.get_posts())

@app.route("/api/posts/<path:post_id>")
def api_get_post(post_id):
    res = backend.posts.get_post(post_id)
    return format_res(res)

@app.route("/api/sharecomment/", methods=["POST"])
def api_sharecomment():
    json_data = request.json
    comment = json_data["comment"]
    domain = json_data["domain"]
    
    res = backend.posts.share_comment(comment, domain)
    return format_res(res)

@app.route("/api/chats/share-message/", methods=["POST"])
def api_sharemessage():
    json_data = request.json
    message = json_data["message"]
    domain = json_data["domain"]
    
    res = backend.chats.share_message(message, domain)
    return format_res(res)

def format_res(res):
    data, err = res
    if err:
        status_code = err["code"]
        return format_err(err), status_code
    return jsonify(data)

def format_err(err):
    if "code" in err:
        err.pop("code")
    return jsonify(err)

if __name__ == "__main__":
    t=Thread(target=backend.task_queue.start_task_queue)
    t.daemon = True
    t.start()
    app.run(host=os.getenv("HOST"), port=os.getenv("PORT"))
