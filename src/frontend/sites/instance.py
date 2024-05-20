import os
from frontend import *
from frontend.snippets import post, warning

script_dir = os.path.dirname(__file__)
css_file_path = os.path.join(script_dir, "../css/posts.css")

with open(css_file_path, "r") as css_file:
    css_string = css_file.read()

def get_instance_site(data, err):
    if err:
        return render_err(err)
    
    is_cached = "is_cached" in data and data["is_cached"]
    posts = [
        post(post_data, is_link=True, has_bottom_bar=False)
        for post_data in data["posts"]
    ]

    return site(page_title="Post", css=css_string, page_body=
        div(
            {"id": "content"},
            warning(is_cached, "These posts are cached"),
            *posts
        )
    )