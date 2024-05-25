import requests
import backend.crypto_helper as crypto

import backend
from backend import db

def get_index():
    results = db.query("SELECT * FROM instances WHERE is_self=true")
    result = results[0]

    return {
        "public_key": crypto.get_public_pem(),
        "domain": backend.self_domain,
        "nickname": result["nickname"], 
        "pronouns": result["pronouns"], 
        "bio": result["bio"]
    }, None

def get_instance(domain):
    try:
        results = db.query("SELECT * FROM instances WHERE domain=%s;", (domain,))

        if len(results) == 1:
            result = results[0]
            key_string = result["public_key"]
            nickname = result["nickname"]
            pronouns = result["pronouns"]
            bio = result["bio"]
        else:
            r = requests.get(f"{domain}/api/")
            data = r.json()

            key_string = data["public_key"]
            nickname = data["nickname"]
            pronouns = data["pronouns"]
            bio = data["bio"]

            db.execute("INSERT INTO instances (domain, public_key, nickname, pronouns, bio) VALUES (%s, %s, %s, %s, %s)",
                (domain, key_string, nickname, pronouns, bio))
        
        return {
            "public_key": crypto.public_key_from_string(key_string),
            "nickname": nickname,
            "pronouns": pronouns,
            "bio": bio
        }
    except:
        return None

def get_pubkey_of_instance(domain):
    return get_instance(domain)["public_key"]