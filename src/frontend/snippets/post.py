from datetime import datetime, timezone
from frontend import *

def format_timestamp(timestamp):
    date_time = datetime.fromtimestamp(timestamp, timezone.utc)
    return date_time.strftime("%B %d, %Y, %H:%M")

def generate(data, /, is_post=True, has_bottom_bar=True, is_link=False):
    user = data["user"]
    id = data["id"]
    text = data["text"]

    href = f"/writereply/{id}@{user}/"
    
    date_text_element = p(
        {"class": "date"},
        format_timestamp(data["posted_at"]))

    if is_link:
        date_element = a({"href": f"/posts/{id}@{user}/"},
            date_text_element)
    else:
        date_element = date_text_element

    if has_bottom_bar:
        bottom_bar = div({"class": "bottom-bar"},
            date_element,
            a(
                {"href": href},
                button({"class": "reply-button"}, "Reply")
            )
        )
    else:
        bottom_bar = date_element
    
    submission_class = "submission post" if is_post else "submission"

    return div({"class": submission_class},
        p({"class": "author"}, user),
        p({"class": "text"}, text),
        bottom_bar
    )