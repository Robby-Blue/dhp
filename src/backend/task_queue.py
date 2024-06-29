from backend import db
import backend.posts as posts
from datetime import datetime, timedelta
import time

def start_task_queue():
    while True:
        tasks = db.query("SELECT * FROM task_queue;")
        for task in tasks:
            handle_task(task)

        time.sleep(60)

def handle_task(task):
    if not should_try(task):
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
        else:
            db.execute("DELETE FROM task_queue WHERE id=%s",
                (task["id"],))
            
def should_try(task):
    if task["last_tried_at"] == None:
        return True
    
    last_tried_at = task["last_tried_at"]
    retries = task["retries"]
    backoff_seconds = retries ** 1.5 * 60
    next_try_at = last_tried_at + timedelta(seconds=backoff_seconds)

    now = datetime.now()

    return now > next_try_at

def process_task(task):
    task_type = task["type"]
    if task_type == "share_comment":
        return posts.process_share_comment_task(task)
    if task_type == "verify_comment":
        return posts.process_verify_comment_task(task)
    return {"state": "delete"} # idk what to do