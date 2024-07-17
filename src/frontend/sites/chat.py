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

    domain = instance["domain"]
    send_url = f"/chats/{domain}/send-message"

    return (
        div({"class": "instance-top-container"},
            h1({"class": "title"}, nickname),
        ),
        create_messages_container(messages),
        form({"class": "send-container", "action": send_url, "method": "POST"},
            textarea({"name": "text", "class": "message-input"}),
            input({"type": "submit", "value": "Send"})
        )
    )

def create_messages_container(message_data):
    messages = message_data["messages"]
    has_more = message_data["has_more"]

    load_older_button = None
    can_load_older = has_more or not message_data["before"]
    if can_load_older:
        first_message_id = messages[0]["id"]
        older_url = f"?before={first_message_id}"
        load_older_button = button({"class": "load-more-button"},
            a({"href": older_url}, "load older")
        )
    
    load_newer_button = None
    can_load_newer = message_data["before"] or (message_data["after"] and has_more)
    if can_load_newer:
        last_message_id = messages[-1]["id"]
        newer_url = f"?after={last_message_id}"
        load_newer_button = button({"class": "load-more-button"},
            a({"href": newer_url}, "load newer")
        )

    return div({"class": "messages-container"},
        load_older_button,
        *[create_message(message) for message in messages],
        load_newer_button,
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
        p({"class": "secondary-info"}, text),
               p(message["id"])
    )
