from frontend import *
from frontend.snippets import sidebar, post, banner

def get_instance_site(data, err):
    if err:
        return render_err(err)

    instance = data["instance"]
    domain = instance["domain"]
    nickname = instance["nickname"]
    pronouns = instance["pronouns"]
    bio = instance["bio"]

    posts_data = data["posts"]

    posts = sorted(posts_data["posts"], key=lambda x: x["posted_at"], reverse=True)

    is_cached = "is_cached" in posts_data and posts_data["is_cached"]
    post_elements = [
        post(post_data, is_link=True, has_reply_button=False)
        for post_data in posts
    ]

    return render("Instance",
        sidebar(
            div(
                {"id": "content", "css": "instance.css"},
                banner(is_cached, "warning", "This data is cached"),
                div({"class": "instance-div"},
                    div({"class": "inline-bar"},
                        p({"class": "nickname"}, nickname),
                        p({"class": "secondary-color secondary-info"}, pronouns),
                    ),
                    p({"class": "secondary-info"}, domain),
                    p(bio)
                ),
                h1("Posts"),
                *post_elements
            )
        )
    )