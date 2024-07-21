from backend import db
from backend import instances
from backend import task_queue
from backend import events
from backend import self_domain, generate_id, to_timestamp, from_timestamp
import backend.crypto_helper as crypto
from datetime import datetime
import requests

MESSAGES_PER_PAGE = 10

def get_chats():
    results = db.query("""
SELECT DISTINCT msgs.instance_domain, i.nickname, i.pronouns, msgs.text, msgs.is_read, sender_i.nickname AS sender_nickname
FROM chat_messages msgs
JOIN instances i ON msgs.instance_domain = domain
JOIN (
    SELECT instance_domain, MAX(received_at) AS latest_received_at
    FROM chat_messages
    WHERE signature_verified
    GROUP BY instance_domain
) latest_messages ON msgs.instance_domain = latest_messages.instance_domain AND msgs.received_at = latest_messages.latest_received_at
JOIN instances sender_i ON msgs.sender_domain = sender_i.domain;
""")
    
    return results

def get_chat(domain, before=None, after=None):
    instance, err = instances.get_instance_data(domain)
    if err:
        return None, err

    messages, err = get_messages_in_chat(domain, before, after)
    if err:
        return None, err

    return {
        "messages": messages,
        "instance": instance
    }, None

def get_messages_in_chat(domain, before_id=None, after_id=None):
    # load one more but dont return it
    # use it to figure out if theres more
    # or if it loaded all
    messages_to_load = MESSAGES_PER_PAGE + 1

    if before_id:
        message, err = get_message(before_id)
        if err:
            return None, err
        before_time = from_timestamp(message["sent_at"])

        messages = db.query("""
SELECT * FROM (
    SELECT * FROM chat_messages
    JOIN instances ON chat_messages.sender_domain = instances.domain
    WHERE instance_domain = %s AND signature_verified
    AND sent_at < %s
    ORDER BY sent_at DESC
    LIMIT %s
) sub
ORDER BY sent_at ASC;
""", (domain, before_time, messages_to_load))
        to_pop = 0
    elif after_id:
        message, err = get_message(after_id)
        if err:
            return None, err
        after_time = from_timestamp(message["sent_at"])

        messages = db.query("""
SELECT * FROM chat_messages
JOIN instances ON chat_messages.sender_domain = instances.domain
WHERE instance_domain = %s AND signature_verified
AND sent_at > %s
ORDER BY sent_at ASC
LIMIT %s;
""", (domain, after_time, messages_to_load))
        to_pop = -1
    else:
        messages = db.query("""
SELECT * FROM (
    SELECT * FROM chat_messages
    JOIN instances ON chat_messages.sender_domain = instances.domain
    WHERE instance_domain = %s AND signature_verified
    ORDER BY sent_at DESC
    LIMIT %s
) sub
ORDER BY sent_at ASC;
""", (domain, messages_to_load))
        to_pop = 0

        # mark as read if they see the newwest messages
        mark_chat_as_read(domain)

    has_more = len(messages) == messages_to_load
    if has_more:
        messages.pop(to_pop)

    return {
        "messages": messages,
        "before": before_id,
        "after": after_id,
        "has_more": has_more
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
    now = from_timestamp(timestamp)

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
INSERT INTO chat_messages (id, instance_domain, sender_domain, text, sent_at, is_read, received_at, last_message_id, signature, signature_verified)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, true);
""", (uuid, instance, self_domain, text, now, True, now, last_message_id, signature))

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

    timestamp = to_timestamp(datetime.now())
    now = from_timestamp(timestamp)

    db.execute("""
INSERT INTO chat_messages (id, instance_domain, sender_domain, text, sent_at, received_at, last_message_id, signature, signature_verified)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s);
""", (id, domain, domain, text, sent_at, now, last_message_id, signature, False))

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
        if not last_message or not last_message["signature_verified"]:
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

    # if theres any messages depending on this one, verify them too
    depend_results = db.query(
"SELECT * FROM chat_messages WHERE last_message_id = %s", (message["id"],))
    if len(depend_results) == 1:
        # tell the task_queue to do it now
        depending_message = depend_results[0]
        depending_id = depending_message["id"]
        db.execute(
"UPDATE task_queue SET last_tried_at = null WHERE type = 'verify_message' AND message_id = %s", (depending_id,))
        task_queue.notify_queue_changed()

    events.send_event(f"chat/{instance}")

    return {
        "state": "success",
        "verified": True
    }

def mark_chat_as_read(instance):
    db.execute(
"UPDATE chat_messages SET is_read=true WHERE instance_domain = %s;", (instance ,))

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
        "read": bool(message["is_read"]),
        "last_message_id": message["last_message_id"],
        "signature": crypto.signature_to_string(message["signature"]),
        "signature_verified": message["signature_verified"]
    }, None
