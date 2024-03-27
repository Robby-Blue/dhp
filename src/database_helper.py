import os
import mysql.connector

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
        self.execute("""
CREATE TABLE IF NOT EXISTS posts (
    id CHAR(36) NOT NULL UNIQUE,
    is_self BOOL NOT NULL,
    user TEXT,
    text TEXT NOT NULL,
    posted_at TIMESTAMP NOT NULL,
    signature BLOB NOT NULL,
    signature_verified BOOLEAN DEFAULT true,
    PRIMARY KEY (id)
);
""")

        self.execute("""
CREATE TABLE IF NOT EXISTS comments (
    id CHAR(36) NOT NULL UNIQUE,
    is_self BOOL NOT NULL,
    parent_post_id CHAR(36),
    parent_comment_id CHAR(36),
    user TEXT,
    text TEXT NOT NULL,
    posted_at TIMESTAMP NOT NULL,
    signature BLOB NOT NULL,
    signature_verified BOOLEAN DEFAULT true,
    PRIMARY KEY (id),
    FOREIGN KEY (parent_post_id) REFERENCES posts(id),
    FOREIGN KEY (parent_comment_id) REFERENCES comments(id)
);
""")
        
        self.execute("""
CREATE TABLE IF NOT EXISTS users (
    domain TEXT NOT NULL,
    public_key TEXT NOT NULL
);
""")

    def query(self, statement, values=()):
        self.cursor.execute(statement, values)
        return self.cursor.fetchall()

    def execute(self, statement, values=()):
        self.cursor.execute(statement, values)
        self.connection.commit()

    def execute_many(self, statement, values=[()]):
        self.cursor.execute(statement, values)
        self.connection.commit()