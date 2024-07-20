from frontend import *
from frontend.snippets import sidebar

def get_chats_site(chats):
    return render("Chats",
        sidebar(
            div(
                {"id": "content", "css": "chats.css"},
                h1("Chats"),
                *[create_chat(chat) for chat in chats],
            )
        )
    )

def create_chat(chat):
    nickname = chat["nickname"]
    domain = chat["instance_domain"]
    
    last_text = chat["text"]
    last_sender = chat["sender_nickname"]
    preview_text = last_text[:100].replace("\n", " ")

    url = f"/chats/{domain}"

    return a({"href": url},
        div({"class": "chat-container"},
            div({"class": "chat-top-bar"},
                p(nickname),
                p({"class": "secondary-info"}, domain)
            ),
            p({"class": "secondary-info"}, f"{last_sender}: {preview_text}")
        )
    )
