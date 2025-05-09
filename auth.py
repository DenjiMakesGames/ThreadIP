import os
import sqlite3
import hashlib
import secrets

DB_FOLDER = "Database"
DB_PATH = os.path.join(DB_FOLDER, "chat_users.db")

def init_db():
    os.makedirs(DB_FOLDER, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY,
                password TEXT NOT NULL,
                salt TEXT NOT NULL,
                is_admin INTEGER DEFAULT 0
            )
        """)
        # Create default admin if not exists
        cursor.execute("SELECT 1 FROM users WHERE username='admin'")
        if not cursor.fetchone():
            salt = secrets.token_hex(16)
            hashed = hashlib.sha256(("admin123" + salt).encode()).hexdigest()
            cursor.execute(
                "INSERT INTO users (username, password, salt, is_admin) VALUES (?, ?, ?, 1)",
                ("admin", hashed, salt)
            )
        conn.commit()

def _hash_password(password: str, salt: str) -> str:
    return hashlib.sha256((password + salt).encode()).hexdigest()

def register_user(username: str, password: str) -> bool:
    if not username.isalnum() or len(username) < 3:
        return False
        
    salt = secrets.token_hex(16)
    hashed = _hash_password(password, salt)
    
    with sqlite3.connect(DB_PATH) as conn:
        try:
            conn.execute(
                "INSERT INTO users (username, password, salt) VALUES (?, ?, ?)",
                (username, hashed, salt)
            )
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

def authenticate_user(username: str, password: str) -> bool:
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT password, salt, is_admin FROM users WHERE username=?",
            (username,)
        )
        result = cursor.fetchone()
        if not result:
            return False
        stored_hash, salt, _ = result
        return _hash_password(password, salt) == stored_hash

def is_admin(username: str) -> bool:
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT is_admin FROM users WHERE username=?",
            (username,)
        )
        result = cursor.fetchone()
        return result and result[0] == 1