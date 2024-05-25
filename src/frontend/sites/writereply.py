from frontend import *
from frontend.snippets import post

def get_writereply_site(data, err):
    if err:
        return render_err(err)

    submission = data["submission"]

    id = submission["id"]
    instance = submission["instance"]

    form_url = f"/writereply/{id}@{instance}/"

    return render("Write Reply",
        div({"id": "content", "css": "writereply.css"},
            post(submission, has_reply_button=False, is_post=False),
            form({"action": form_url, "method": "POST"},
                textarea({"name": "text"}),
                br(),
                input({"type": "submit", "value": "Reply"})
            )
        )
    )