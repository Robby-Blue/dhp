from frontend import *
from frontend.snippets import post, warning

def get_instance_site(data, err):
    if err:
        return render_err(err)
    
    is_cached = "is_cached" in data and data["is_cached"]
    posts = [
        post(post_data, is_link=True, has_bottom_bar=False)
        for post_data in data["posts"]
    ]

    return render("Instance",
        div(
            {"id": "content", "css": "posts.css"},
            warning(is_cached, "These posts are cached"),
            *posts
        )
    )