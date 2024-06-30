from frontend import *
from frontend.snippets import banner

def get_settings_site(data, edited=False):
    return render("Settings",
        div(
            {"id": "content", "css": "settings.css"},
            h1("Settings"),
            banner(edited, "success", "success"),
            form({"action": "/settings/", "method": "POST"},
                *setting("nickname", data["nickname"]),
                *setting("pronouns", data["pronouns"]),
                *setting("bio", data["bio"], type="textarea"),
                input({"type": "submit", "value": "save"})
            )
        )
    )

def setting(id, value, type="text"):
    if type == "text":
        input_element = input({"value": value, "id": id, "name": id, "type": "text"})
    elif type == "textarea":
        input_element = textarea({"id": id, "name": id}, value)
    else:
        input_element = None

    return (
        label({"for": id}, id),
        br(),
        input_element,
        br(),
        br(),
    )