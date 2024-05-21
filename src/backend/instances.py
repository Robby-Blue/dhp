import requests
import crypto_helper as crypto

import backend
from backend import db

def get_index():
    return {
        "public_key": crypto.get_public_pem(),
        "domain": backend.self_domain
    }, None

def get_pubkey_of_instance(domain):
    try:
        result = db.query("SELECT * FROM users WHERE domain=%s;", (domain,))

        if len(result) == 1:
            return crypto.public_key_from_string(result[0]["public_key"])
        
        r = requests.get(f"{domain}/api/")
        key_string = r.json()["public_key"]

        db.execute("INSERT INTO users (domain, public_key) VALUES (%s, %s)",
                (domain, key_string))
        
        return crypto.public_key_from_string(key_string)
    except:
        return None