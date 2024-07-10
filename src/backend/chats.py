from backend import db
from backend import instances
from backend import task_queue
from backend import self_domain, generate_id, to_timestamp, from_timestamp
import backend.crypto_helper as crypto
from datetime import datetime
import requests

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
WHERE instance_domain = %s AND signature_verified
ORDER BY sent_at ASC;
""", (domain,))
    
    return {
        "messages": messages,
        "instance": instance
    }, None

def send_message(instance, text):
    results = db.query("""
SELECT * FROM chat_messages
WHERE instance_domain = %s AND sender_domain = %s
ORDER BY sent_at DESC LIMIT 1
""", (instance, self_domain))

    if len(results) == 1:
        last_message = results[0]
        last_message_id = last_message["id"]
        last_message_signature = last_message["signature"]
    else:
        last_message_id = None
        last_message_signature = None

    uuid = generate_id()
    timestamp = to_timestamp(datetime.now())

    signature = crypto.sign_string(crypto.stringify_chat_message({
        "id": uuid,
        "sent_at": timestamp,
        "last_message_id": last_message_id,
        "last_message_signature": last_message_signature,
        "text": text,
        "sender": self_domain,
        "receiver": instance
    }))

    db.execute("""
INSERT INTO chat_messages (id, instance_domain, sender_domain, text, sent_at, last_message_id, signature, signature_verified)
VALUES (%s, %s, %s, %s, %s, %s, %s, true);
""", (uuid, instance, self_domain, text, from_timestamp(timestamp), last_message_id, signature))

    task_queue.add_to_task_queue("""
INSERT INTO task_queue (type, instance_domain, message_id) VALUES (%s, %s, %s) 
""", ("share_message", instance, uuid)) 

    return {"success": True}, None

def process_share_message_task(task):
    instance = task["instance_domain"]
    id = task["message_id"]

    try:
        r = requests.post(f"{instance}/api/chats/share-message/", 
                json={
                    "domain": self_domain,
                    "message": get_message(id)[0]
                })
        if r.status_code == 200:
            return {"state": "success"}
        if r.status_code == 400:
            return {"state": "delete"}
        return {"state": "retry"}
    except:
       return {"state": "retry"}

def share_message(message, domain):
    id = message["id"]
    db_message, _ = get_message(id)
    if db_message:
        return None, {"error": "already exists", "code": 400}
    
    id = message["id"]
    sender = message["sender_domain"]
    text = message["text"]
    sent_at = from_timestamp(message["sent_at"])
    last_message_id = message["last_message_id"]
    signature = crypto.signature_from_string(message["signature"])

    _, err = instances.get_instance_data(domain, True)
    if err:
        return None, {"error": "instance err", "code": 500}

    db.execute("""
INSERT INTO chat_messages (id, instance_domain, sender_domain, text, sent_at, last_message_id, signature, signature_verified)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s);
""", (id, domain, domain, text, sent_at, last_message_id, signature, False))

    task_queue.add_to_task_queue("""
INSERT INTO task_queue (type, instance_domain, message_id) VALUES (%s, %s, %s) 
""", ("verify_message", sender, id))
    return {"success": True}, None

def process_verify_message_task(task):
    instance = task["instance_domain"]
    message, _ = get_message(task["message_id"])
    signature = crypto.signature_from_string(message["signature"])

    pubkey = instances.get_pubkey_of_instance(instance)

    if not pubkey:
        return {"state": "retry", "verified": False}

    last_message_id = message["last_message_id"]
    if last_message_id:
        last_message, _ = get_message(last_message_id)
        if not last_message:
            # received in wrong order, try again later when all received
            return {"state": "retry", "verified": False}

    results = db.query("""
SELECT * FROM chat_messages
WHERE instance_domain = %s AND sender_domain = %s AND signature_verified
ORDER BY sent_at DESC LIMIT 1
""", (instance, instance))

    if len(results) == 1:
        last_message = results[0]
        last_message_id = last_message["id"]
        last_message_signature = last_message["signature"]
        last_message_time = last_message["sent_at"]
        if to_timestamp(last_message_time) > message["sent_at"]:
            return {"state": "delete", "verified": False}
    else:
        last_message_id = None
        last_message_signature = None

    if not crypto.verify_signature(crypto.stringify_chat_message({
        "id": message["id"],
        "sent_at": message["sent_at"],
        "last_message_id": last_message_id,
        "last_message_signature": last_message_signature,
        "text": message["text"],
        "sender": message["sender_domain"],
        "receiver": self_domain
    }), signature, pubkey):
        return {"state": "delete", "verified": False}

    db.execute("UPDATE chat_messages SET signature_verified = true WHERE id = %s",
(task["message_id"],))

    return {
        "state": "success",
        "verified": True
    }

def get_message(id):
    results = db.query("SELECT * FROM chat_messages WHERE id = %s", (id,))
    if len(results) == 0:
        return None, {"error": "post not found", "code": 404}
    message = results[0]

    return {
        "id": message["id"],
        "sender_domain": message["sender_domain"],
        "text": message["text"],
        "sent_at": to_timestamp(message["sent_at"]),
        "last_message_id": message["last_message_id"],
        "signature": crypto.signature_to_string(message["signature"])
    }, None
