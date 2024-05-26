import os
import mysql.connector
from backend import self_domain
import backend.crypto_helper as crypto

class DatabaseHelper:
    def connect(self):
        self.connection = mysql.connector.connect(
            host=os.getenv("DB_HOST"),
            user=os.getenv("DB_USERNAME"),
            password=os.getenv("DB_PASSWORD"),
            database=os.getenv("DB_DATABASE")
        )
        self.cursor = self.connection.cursor(dictionary=True)

    def setup(self):
        # max domain length is 267 bc 253 for actual domain
        # plus https:// and :65535
        self.execute("""
CREATE TABLE IF NOT EXISTS instances (
    domain VARCHAR(267) NOT NULL UNIQUE,
    is_self BOOL DEFAULT FALSE,
    public_key TEXT,
    nickname VARCHAR(30) NOT NULL,
    pronouns VARCHAR(20) NOT NULL,
    bio VARCHAR(1000) NOT NULL,
    PRIMARY KEY (domain),
    INDEX idx_domain (domain)
);
""")

        self.execute("""
CREATE TABLE IF NOT EXISTS posts (
    id CHAR(36) NOT NULL UNIQUE,
    is_self BOOL NOT NULL,
    instance_domain VARCHAR(267) NOT NULL,
    text TEXT NOT NULL,
    posted_at TIMESTAMP NOT NULL,
    signature BLOB NOT NULL,
    signature_verified BOOLEAN DEFAULT true,
    PRIMARY KEY (id),
    FOREIGN KEY (instance_domain) REFERENCES instances(domain)
);
""")

        self.execute("""
CREATE TABLE IF NOT EXISTS comments (
    id CHAR(36) NOT NULL UNIQUE,
    is_self BOOL NOT NULL,
    parent_post_id CHAR(36),
    parent_comment_id CHAR(36),
    instance_domain VARCHAR(267) NOT NULL,
    text TEXT NOT NULL,
    posted_at TIMESTAMP NOT NULL,
    signature BLOB NOT NULL,
    signature_verified BOOLEAN DEFAULT false,
    PRIMARY KEY (id),
    FOREIGN KEY (parent_post_id) REFERENCES posts(id),
    FOREIGN KEY (parent_comment_id) REFERENCES comments(id),
    FOREIGN KEY (instance_domain) REFERENCES instances(domain)
);
""")
        
        self.execute("""
CREATE TABLE IF NOT EXISTS task_queue (
    id INT auto_increment,
    instance_domain VARCHAR(267) NOT NULL,
    type VARCHAR(25),
    comment_id CHAR(36),
    PRIMARY KEY (id),
    FOREIGN KEY (instance_domain) REFERENCES instances(domain),
    FOREIGN KEY (comment_id) REFERENCES comments(id)
);
""")
        
        if not self.query(
"SELECT * FROM instances WHERE domain = %s", (self_domain,)):
            self.execute("INSERT INTO instances (is_self, domain, public_key, nickname, pronouns, bio) VALUES (%s, %s, %s, %s, %s, %s)",
                (True, self_domain, crypto.get_public_pem(), self_domain, "not set", ":D"))

    def query(self, statement, values=()):
        self.cursor.execute(statement, values)
        return self.cursor.fetchall()

    def execute(self, statement, values=()):
        self.cursor.execute(statement, values)
        self.connection.commit()

    def execute_many(self, statement, values=[()]):
        self.cursor.executemany(statement, values)
        self.connection.commit()