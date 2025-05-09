import os
import sqlite3

DB_FOLDER = "Database"
DB_PATH = os.path.join(DB_FOLDER, "chat_users.db")

def initialize_database():
    os.makedirs(DB_FOLDER, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()
    print(f"Database initialized at '{DB_PATH}'.")

if __name__ == "__main__":
    initialize_database()
