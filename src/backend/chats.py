from backend import db

def get_chats():
    results = db.query("""
SELECT DISTINCT instance_domain, instances.nickname
FROM chat_messages JOIN instances ON
chat_messages.instance_domain = instances.domain;""")
    
    return results