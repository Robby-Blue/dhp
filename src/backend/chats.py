from backend import db
from backend import instances

def get_chats():
    results = db.query("""
SELECT DISTINCT instance_domain, instances.nickname, instances.pronouns
FROM chat_messages JOIN instances ON
chat_messages.instance_domain = instances.domain;""")
    
    return results

def get_chat(domain):
    instance, err = instances.get_instance_data(domain)

    if err:
        return None, err

    messages = db.query("""
SELECT * FROM chat_messages
JOIN instances ON chat_messages.sender_domain = instances.domain
WHERE instance_domain = %s;
""", (domain,))
    
    return {
        "messages": messages,
        "instance": instance
    }, None