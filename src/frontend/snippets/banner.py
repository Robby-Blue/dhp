from frontend import *

def generate(is_cached, type, text):
    if not is_cached:
        return None
    
    return div(
        {"class": f"banner {type}", "css": "snippets/warning.css"},
        text
    )