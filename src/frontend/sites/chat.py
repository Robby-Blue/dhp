from frontend import *
from frontend.snippets import sidebar

def get_chat_site(chat):
    instance = chat["instance"]
    nickname = instance["nickname"]

    # maybe make this instance instead
    return render(f"Chat - {nickname}",
        sidebar(
            div({"id": "content", "css": "chat.css"},
                div({"class": "chat"},
                    *create_chat_container(chat)
                )
            )
        )
    )

def create_chat_container(chat):
    messages = chat["messages"]
    instance = chat["instance"]
    nickname = instance["nickname"]

    return (
        h1({"class": "title"}, nickname),
        div({"class": "messages-container"},
            *[create_message(message) for message in messages],
        ),
        form({"class": "send-container", "action": "/chats/send-message/", "method": "POST"},
            input({"type": "text", "name": "message", "class": "message-input"}),
            input({"type": "submit", "value": "Send"})
        )
    )

def create_message(message):
    nickname = message["nickname"]
    domain = message["domain"]
    text = message["text"]

    return div({"class": "message-container"},
        div({"class": "message-top-bar"},
            p(nickname),
            p({"class": "secondary-info"}, domain)
        ),
        p({"class": "secondary-info"}, text)
    )