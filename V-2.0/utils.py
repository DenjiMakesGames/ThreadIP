import os
import sqlite3
from datetime import datetime

DATABASE_FOLDER = "Database"
USER_STATUS_DB = os.path.join(DATABASE_FOLDER, "user_status.db")
SESSION_LOG = os.path.join(DATABASE_FOLDER, "session.log")

os.makedirs(DATABASE_FOLDER, exist_ok=True)

def initialize_user_status_db():
    with sqlite3.connect(USER_STATUS_DB) as conn:
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS muted_users (
            username TEXT PRIMARY KEY,
            timestamp TEXT
        )''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS banned_users (
            username TEXT PRIMARY KEY,
            timestamp TEXT
        )''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS warnings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            reason TEXT,
            timestamp TEXT
        )''')
        conn.commit()

def log_message(sender: str, message: str, direction: str = "sent"):
    log_session(f"{direction.upper()} - {sender}: {message}")

def broadcast_message(message: str, connected_users: dict, exclude_user: str = None):
    for username, sock in connected_users.items():
        if username != exclude_user:
            try:
                sock.send(f"{message}\n".encode())
            except (ConnectionError, OSError) as e:
                log_session(f"Error broadcasting to {username}: {str(e)}", level="ERROR")

def log_session(entry: str, level: str = "INFO"):
    timestamp = datetime.now().strftime("[%Y-%m-%d %H:%M:%S] ")
    log_entry = f"{timestamp} [{level}] {entry}\n"
    
    print(log_entry, end='')
    
    with open(SESSION_LOG, "a") as f:
        f.write(log_entry)
    
    if level == "ERROR":
        with open(os.path.join(DATABASE_FOLDER, "server_error.log"), "a") as error_log:
            error_log.write(log_entry)