import os

from urllib.parse import urlparse
from base64 import urlsafe_b64encode, urlsafe_b64decode

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.asymmetric import rsa

key_file = "key.pem"

if os.path.exists(key_file):
    with open(key_file, "rb") as key_file:
        private_key = serialization.load_pem_private_key(
            key_file.read(),
            password=None
        )
else:
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048
    )

    pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption()
    )
    with open(key_file, "wb") as f:
        f.write(pem)

public_key = private_key.public_key()

def sign_string(text):
    signature = private_key.sign(
        text.encode("UTF-8"),
        padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()),
            salt_length=padding.PSS.MAX_LENGTH
        ),
        hashes.SHA256()
    )
    return signature

def verify_signature(text, signature, pubkey):
    try:
        pubkey.verify(
            signature,
            text.encode("UTF-8"),
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )
        return True
    except InvalidSignature:
        return False

def get_public_pem():
    pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )
    return pem.decode("UTF-8")

def public_key_from_string(string):
    return serialization.load_pem_public_key(
        string.encode("UTF-8")
    )

def signature_to_string(signature):
    return urlsafe_b64encode(signature).decode("UTF-8")

def signature_from_string(signature_string):
    return urlsafe_b64decode(signature_string)

def stringify_post(post):
    return "\n---\n".join([
        post["id"],
        str(post["posted_at"]),
        post["text"].replace("-", "\\-"), 
        remove_scheme_from_url(post["instance"])
    ])

def stringify_comment(comment):
    parent_post_signature = comment["parent_post_signature"]
    parent_comment_signature = comment["parent_comment_signature"]

    return "\n---\n".join([
        comment["id"],
        str(comment["parent_post_id"]),
        str(comment["parent_comment_id"]),
        signature_to_string(parent_post_signature),
        signature_to_string(parent_comment_signature) if parent_comment_signature else str(None),
        str(comment["posted_at"]),
        comment["text"].replace("-", "\\-"),
        remove_scheme_from_url(comment["instance"])
    ])

def stringify_chat_message(message):
    last_signature = message["last_message_signature"]

    return "\n---\n".join([
        message["id"],
        str(message["sent_at"]),
        str(message["last_message_id"]),
        signature_to_string(last_signature) if last_signature else str(None),
        message["text"].replace("-", "\\-"),
        remove_scheme_from_url(message["sender"]),
        remove_scheme_from_url(message["receiver"])
    ])

def remove_scheme_from_url(given_domain):
    parsed_url = urlparse(given_domain)
    domain = parsed_url.hostname
    if parsed_url.port:
        domain+=":"+str(parsed_url.port)
    return domain
