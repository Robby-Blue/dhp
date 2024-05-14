import os
from frontend import *

script_dir = os.path.dirname(__file__)
css_file_path = os.path.join(script_dir, "../css/writepost.css")

with open(css_file_path, "r") as css_file:
    css_string = css_file.read()

def get_writepost_site():
    return site(page_title="Write Post", css=css_string, page_body=
        form({"id": "content", "action": "/writepost/", "method": "POST"},
            textarea({"name": "text"}),
            br(),
            input({"type": "submit", "value": "Post"})
        )
    )