from datetime import datetime, timezone
from frontend import *

def format_timestamp(timestamp):
    date_time = datetime.fromtimestamp(timestamp, timezone.utc)
    return date_time.strftime("%B %d, %Y, %H:%M")

def generate(data, /, is_post=True, has_reply_button=True, is_link=False):
    instance = data["instance"]
    id = data["id"]
    text = data["text"]

    submission_class = "submission post" if is_post else "submission"

    author = data["author"]

    nickname = author["nickname"]
    pronouns = author["pronouns"]

    instance_path = f"/instances/{instance}"
    reply_path = f"/writereply/{id}@{instance}/"
    
    date_text_element = p(
        {"class": "secondary-info"},
        format_timestamp(data["posted_at"]))

    if is_link:
        date_element = a({"href": f"/posts/{id}@{instance}/"},
            date_text_element)
    else:
        date_element = date_text_element

    if has_reply_button:
        bottom_bar = div({"class": "inline-bar space-between"},
            date_element,
            a(
                {"href": reply_path},
                button({"class": "reply-button"}, "Reply")
            )
        )
    else:
        bottom_bar = date_element

    return div({"class": submission_class, "css": "snippets/post.css"},
        a({"href": instance_path},
            div({"class": "inline-bar"},
                p({"class": "nickname"}, nickname),
                p({"class": "secondary-color secondary-info"}, pronouns),
            ),
            p({"class": "secondary-info"}, instance),
        ),
        p(text),
        bottom_bar
    )
