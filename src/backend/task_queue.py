from backend import db
import backend.posts as posts
import backend.chats as chats
from datetime import datetime, timedelta
import time

next_try = { "time": None }

def start_task_queue():
    while True:
        time.sleep(1)

        if not should_try_any():
            continue
        tasks = db.query("SELECT * FROM task_queue;")
        for task in tasks:
            handle_task(task)

        update_next_try_time(tasks)

def should_try_any():
    if not next_try["time"]:
        return True
    now = datetime.now()
    return now > next_try["time"]

def handle_task(task):
    if not should_try_task(task):
        return

    state = process_task(task)["state"]

    should_delete = state == "delete" or state == "success"
    should_retry_again = state == "retry"

    if should_delete:
        db.execute("DELETE FROM task_queue WHERE id=%s",
            (task["id"],))
    if should_retry_again:
        if task["retries"] < 20:
            db.execute(
"UPDATE task_queue SET retries = retries + 1, last_tried_at = %s WHERE id=%s",
(datetime.now(), task["id"],))
            
            # used to calculate next try time later
            task["retries"] += 1
            task["last_tried_at"] = datetime.now()
        else:
            db.execute("DELETE FROM task_queue WHERE id=%s",
                (task["id"],))
            
def should_try_task(task):
    next_try_at = get_next_try_time(task)
    now = datetime.now()
    return now >= next_try_at

def process_task(task):
    task_type = task["type"]
    if task_type == "share_comment":
        return posts.process_share_comment_task(task)
    if task_type == "verify_comment":
        return posts.process_verify_comment_task(task)
    if task_type == "share_message":
        return chats.process_share_message_task(task)
    if task_type == "verify_message":
        return chats.process_verify_message_task(task)
    return {"state": "delete"} # idk what to do

def update_next_try_time(tasks):
    next_try["time"] = None

    for task in tasks:
        task_next_try_time = get_next_try_time(task)
        
        if next_try["time"] == None or \
            next_try["time"] > task_next_try_time:
            next_try["time"] = task_next_try_time

    # if theres nothing scheduled just wait until
    if next_try["time"] == None:
        next_try["time"] = datetime.now() + timedelta(hours=1)

def get_next_try_time(task):
    last_tried_at = task["last_tried_at"]
    if last_tried_at == None:
        return datetime.now()

    retries = task["retries"]
    backoff_seconds = retries ** 1.5 * 60
    next_try_at = last_tried_at + timedelta(seconds=backoff_seconds)
    return next_try_at

def add_to_task_queue(statement, values):
    db.execute(statement, values)
    notify_queue_changed()

def notify_queue_changed():
    next_try["time"] = datetime.now()
