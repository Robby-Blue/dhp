from frontend import *

def generate(*args):
    return div(
        {"class": "sidebar-container", "css": "snippets/sidebar.css"},
        div({"class": "sidebar"},
            h1("Links"),
            a({"href": "/"}, p("Home")),
            a({"href": "/chats"}, p("Chat")),
            a({"href": "/writepost"}, p("Post")),
            a({"href": "/settings"}, p("Settings"))
        ),
        div(
            {"class": "sidebar-content"},
            *args
        )
    )