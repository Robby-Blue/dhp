from frontend import *
from frontend.snippets import post, warning

def get_instance_site(data, err):
    if err:
        return render_err(err)
    

    posts = sorted(data["posts"], key=lambda x: x["posted_at"], reverse=True)

    is_cached = "is_cached" in data and data["is_cached"]
    post_elements = [
        post(post_data, is_link=True, has_bottom_bar=False)
        for post_data in posts
    ]

    return render("Instance",
        div(
            {"id": "content", "css": "posts.css"},
            warning(is_cached, "These posts are cached"),
            *post_elements
        )
    )