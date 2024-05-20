from frontend import *
from frontend.snippets import post, warning

def get_post_site(data, err):
    if err:
        return render_err(err)
    
    comments_lookup = create_comments_lookup(data["comments"])
    is_cached = "is_cached" in data and data["is_cached"]

    return render("Post",
        div(
            {"id": "content", "css": "posts.css"},
            warning(is_cached, "This post is cached"),
            post(data),
            create_replies(data["id"], comments_lookup)
        )
    )

def create_replies(parent_id, comments_lookup):
    if parent_id not in comments_lookup:
        return None
    
    replies = []

    for comment in comments_lookup[parent_id]:
        replies.append(post(comment, False, True))
        if comment["id"] in comments_lookup:
            replies.append(create_replies(comment["id"], comments_lookup))

    return div(
        {"class": "replies-container"},
        *replies
    )

def create_comments_lookup(comments):
    comments_lookup = {}
    for comment in comments:
        if comment['parent']['id'] not in comments_lookup:
            comments_lookup[comment['parent']['id']] = []
        comments_lookup[comment['parent']['id']].append(comment)
    return comments_lookup