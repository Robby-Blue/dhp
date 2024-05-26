import requests
import json
import backend.crypto_helper as crypto
import backend.posts as posts

import backend
from backend import db

def get_index():
    results = db.query("SELECT * FROM instances WHERE is_self=true")
    result = results[0]

    return {
        "domain": backend.self_domain,
        "public_key": crypto.get_public_pem(),
        "nickname": result["nickname"], 
        "pronouns": result["pronouns"], 
        "bio": result["bio"]
    }, None

def get_instance_with_posts(instance=None):
    if not instance:
        instance = backend.self_domain

    posts_data, err = posts.get_posts(instance)
    if err:
        return None, err
    instance, err = get_instance_data(instance)
    if err:
        return None, err
    return {
        "posts": posts_data,
        "instance": instance
    }, None

def get_instance_data(domain):
    try:
        results = db.query("SELECT * FROM instances WHERE domain=%s;", (domain,))

        if len(results) == 1:
            result = results[0]
            key_string = result["public_key"]
            nickname = result["nickname"]
            pronouns = result["pronouns"]
            bio = result["bio"]
        elif domain != backend.self_domain:
            r = requests.get(f"{domain}/api/")
            data = r.json()

            key_string = data["public_key"]
            nickname = data["nickname"]
            pronouns = data["pronouns"]
            bio = data["bio"]

            db.execute("INSERT INTO instances (domain, public_key, nickname, pronouns, bio) VALUES (%s, %s, %s, %s, %s)",
                (domain, key_string, nickname, pronouns, bio))
        else:
            return None, {"error": "bad sql", "code": 500}
        
        return {
            "domain": domain,
            "public_key": crypto.public_key_from_string(key_string),
            "nickname": nickname,
            "pronouns": pronouns,
            "bio": bio
        }, None
    except requests.exceptions.RequestException:
        return None, {"error": f"http req to {domain} didn't work", "code": 400}
    except json.JSONDecodeError:
        return None, {"error": f"{domain} returned invalid json", "code": 400}
    except IndexError:
        return None, {"error": f"{domain} returned bad json", "code": 400}
    except Exception as e:
        return None, {"error": e, "code": 500}


def get_pubkey_of_instance(domain):
    data, err = get_instance_data(domain)
    if err:
        return None, err
    return data["public_key"]