import os
from frontend import *
from frontend.snippets import post

script_dir = os.path.dirname(__file__)
css_file_path = os.path.join(script_dir, "../css/writereply.css")

with open(css_file_path, "r") as css_file:
    css_string = css_file.read()

def get_writereply_site(data, err):
    if err:
        return render_err(err)

    submission = data["submission"]

    id = submission["id"]
    user = submission["user"]

    form_url = f"/{id}@{user}/writereply/"

    return site(page_title="Write Reply", css=css_string, page_body=
        div({"id": "content"},
            post(submission, has_bottom_bar=False, is_post=False),
            form({"action": form_url, "method": "POST"},
                textarea({"name": "text"}),
                br(),
                input({"type": "submit", "value": "Reply"})
            )
        )
    )