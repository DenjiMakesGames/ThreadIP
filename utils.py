import os
import sqlite3
from datetime import datetime
import socket
import requests
from typing import Dict, Optional, Tuple
import logging
from main_server import debug_queue

# Constants
DATABASE_FOLDER = "Database"
USER_STATUS_DB = os.path.join(DATABASE_FOLDER, "user_status.db")
SESSION_LOG = os.path.join(DATABASE_FOLDER, "session.log")
SERVER_ERROR_LOG = os.path.join(DATABASE_FOLDER, "server_error.log")

# Setup
os.makedirs(DATABASE_FOLDER, exist_ok=True)
logging.basicConfig(level=logging.INFO)

class NetworkUtils:
    @staticmethod
    def get_ip_info() -> Tuple[str, str]:
        """Returns (local_ip, public_ip)"""
        local_ip = socket.gethostbyname(socket.gethostname())
        try:
            public_ip = requests.get('https://api.ipify.org', timeout=3).text
        except:
            public_ip = "unknown"
        return local_ip, public_ip

    @staticmethod
    def is_port_open(port: int) -> bool:
        """Check if port is available"""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex(('0.0.0.0', port)) != 0

class DatabaseManager:
    @staticmethod
    def initialize():
        """Initialize all database tables"""
        tables = {
            'muted_users': '(username TEXT PRIMARY KEY, timestamp TEXT)',
            'banned_users': '(username TEXT PRIMARY KEY, timestamp TEXT)',
            'warnings': '''(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT,
                reason TEXT,
                timestamp TEXT)''',
            'message_history': '''(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sender TEXT,
                message TEXT,
                timestamp TEXT)'''
        }
        
        try:
            with sqlite3.connect(USER_STATUS_DB) as conn:
                for name, schema in tables.items():
                    conn.execute(f'CREATE TABLE IF NOT EXISTS {name} {schema}')
                conn.commit()
        except sqlite3.Error as e:
            logging.error(f"Database error: {str(e)}")

class Logger:
    @staticmethod
    def log(entry: str, level: str = "INFO"):
        """Enhanced logging with network context"""
        timestamp = datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
        local_ip, public_ip = NetworkUtils.get_ip_info()
        
        log_entry = (
            f"{timestamp} [NET:{local_ip}/{public_ip}] "
            f"[{level}] {entry}\n"
        )
        
        # Console output
        if level == "ERROR":
            print(f"\033[91m{log_entry}\033[0m", end='')
        elif level == "WARNING":
            print(f"\033[93m{log_entry}\033[0m", end='')
        else:
            print(log_entry, end='')
        
        # File output
        try:
            with open(SESSION_LOG, "a") as f:
                f.write(log_entry)
            if level in ("ERROR", "WARNING"):
                with open(SERVER_ERROR_LOG, "a") as f:
                    f.write(log_entry)
        except IOError as e:
            print(f"\033[91mLog write failed: {str(e)}\033[0m")

# Legacy functions for backward compatibility
def log_message(sender, message, direction="sent"):
    """Log messages to messages.log"""
    timestamp = datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
    entry = f"{timestamp} {direction.upper()} - {sender}: {message}\n"
    
    # Write to messages.log
    with open("Database/messages.log", "a") as f:
        f.write(entry)
    
    # Also show in debug console if needed
    debug_queue.put(f"[MSG] {entry.strip()}")

def broadcast_message(message: str, clients: Dict[str, socket.socket], 
                    exclude: Optional[str] = None) -> int:
    success = 0
    for user, sock in list(clients.items()):
        if user != exclude:
            try:
                sock.sendall(f"{message}\n".encode('utf-8'))
                success += 1
            except (ConnectionError, OSError) as e:
                Logger.log(f"Broadcast failed to {user}: {str(e)}", "WARNING")
    return success

def log_session(entry, level="INFO"):
    """Log server events to session.log"""
    timestamp = datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
    log_entry = f"{timestamp} [{level}] {entry}\n"
    
    # Write to session.log
    with open("Database/session.log", "a") as f:
        f.write(log_entry)
    
    # Send to debug console
    debug_queue.put(log_entry.strip())