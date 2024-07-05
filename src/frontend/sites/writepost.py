from frontend import *
from frontend.snippets import sidebar

def get_writepost_site():
    return render("Write Post",
        sidebar(
            form({"id": "content", "action": "/writepost/", "method": "POST", "css": "writepost.css"},
                textarea({"name": "text"}),
                br(),
                input({"type": "submit", "value": "Post"})
            )
        )
    )