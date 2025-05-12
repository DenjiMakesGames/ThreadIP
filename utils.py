import os
import sqlite3
from datetime import datetime
import socket
import requests
from typing import Dict, Optional, Tuple
import logging
from config import (
    debug_queue,
    DATABASE_FOLDER,
    USER_STATUS_DB,
    SESSION_LOG,
    MESSAGE_LOG
)
os.makedirs(DATABASE_FOLDER, exist_ok=True)

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
def debug_log(message, level="INFO"):
    """Universal logging function for both console and files"""
    timestamp = datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
    log_entry = f"{timestamp} [{level}] {message}"
    
    # Write to session log
    with open(SESSION_LOG, "a") as f:
        f.write(log_entry + "\n")
    
    # Send to debug queue
    debug_queue.put(log_entry)
    
    # Print important messages to console
    if level in ("ERROR", "WARNING"):
        print(log_entry)

def log_message(sender, message, direction="sent"):
    """Specialized message logging"""
    entry = f"{datetime.now().strftime('[%Y-%m-%d %H:%M:%S]')} {direction.upper()} - {sender}: {message}"
    with open(MESSAGE_LOG, "a") as f:
        f.write(entry + "\n")
    debug_queue.put(entry)

def broadcast_message(message, connected_users, exclude=None):
    """Send message to all connected users"""
    for username, sock in connected_users.items():
        if username != exclude:
            try:
                sock.send(f"{message}\n".encode())
            except:
                debug_log(f"Failed to send to {username}", "WARNING")