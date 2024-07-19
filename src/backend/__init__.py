import os
import uuid
from datetime import datetime, timezone
from urllib.parse import urlparse

def fix_url(given_domain):
    if not given_domain.startswith("http"):
        default_scheme = os.getenv("DEFAULT_SCHEME")
        given_domain=f"{default_scheme}://{given_domain}"
    parsed_url = urlparse(given_domain)
    domain = parsed_url.scheme+"://"+parsed_url.hostname
    if parsed_url.port:
        domain+=":"+str(parsed_url.port)
    return domain

def parse_id(id, return_self_domain=False):
    if "@" in id:
        segments = id.split("@")
        id = segments[0]
        instance = fix_url(segments[1])
        if instance == self_domain and not return_self_domain:
            instance = None
        return (id, instance)
    else:
        return (id, None)
    
def build_id(id, instance):
    if not instance:
        instance = self_domain
    return f"{id}@{instance}"

def to_timestamp(datetime):
    return int(datetime.replace(tzinfo=timezone.utc).timestamp())

def from_timestamp(timestamp):
    return datetime.fromtimestamp(timestamp, tz=timezone.utc)

def generate_id():
    generated_uuid = uuid.uuid4()
    return str(generated_uuid)

self_domain = fix_url(os.getenv("DOMAIN"))

# db stuff
from backend.database_helper import DatabaseHelper

db = DatabaseHelper()
db.connect()
db.setup()

import backend.posts as posts
import backend.instances as instances
import backend.chats as chats
import backend.events as events
