from frontend import *

def generate(is_cached, text):
    if not is_cached:
        return None
    return div(
        {"class": "warning", "css": "snippets/warning.css"},
        text
    )