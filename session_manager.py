# session_manager.py
import threading
import time
import socket
from utils import log_session, broadcast_message

class SessionManager:
    def __init__(self):
        # Thread-safe data structures
        self.connected_users = {}  # {username: socket}
        self.banned_users = set()
        self.muted_users = set()
        self.user_warnings = {}  # {username: [warnings]}
        self.message_timestamps = {}  # {username: [timestamps]} for rate limiting
        self.lock = threading.Lock()
        
        # Configuration
        self.rate_limit = 5  # Messages per second
        self.heartbeat_interval = 30  # Seconds

    def add_user(self, username: str, client_socket: socket.socket) -> bool:
        """Add a new user with thread-safe checks"""
        with self.lock:
            if username in self.banned_users:
                log_session(f"Banned user {username} tried to connect", "WARNING")
                return False
                
            if username in self.connected_users:
                log_session(f"Duplicate connection from {username}", "WARNING")
                return False
                
            self.connected_users[username] = client_socket
            self.message_timestamps[username] = []
            
        log_session(f"User {username} connected")
        self.broadcast(f"Server: {username} joined the chat", exclude=username)
        return True

    def remove_user(self, username: str):
        """Cleanly remove a user"""
        with self.lock:
            if username in self.connected_users:
                try:
                    self.connected_users[username].close()
                except:
                    pass
                del self.connected_users[username]
                if username in self.message_timestamps:
                    del self.message_timestamps[username]
                    
        log_session(f"User {username} disconnected")
        self.broadcast(f"Server: {username} left the chat", exclude=username)

    def ban_user(self, username: str):
        """Ban a user across sessions"""
        with self.lock:
            self.banned_users.add(username)
            if username in self.connected_users:
                self.remove_user(username)
        log_session(f"ADMIN banned user {username}")

    def mute_user(self, username: str):
        """Prevent a user from sending messages"""
        with self.lock:
            self.muted_users.add(username)
        log_session(f"ADMIN muted user {username}")

    def unmute_user(self, username: str):
        """Remove mute restrictions"""
        with self.lock:
            if username in self.muted_users:
                self.muted_users.remove(username)
        log_session(f"ADMIN unmuted user {username}")

    def is_muted(self, username: str) -> bool:
        """Check if user is muted"""
        with self.lock:
            return username in self.muted_users

    def warn_user(self, username: str, reason: str = "No reason provided"):
        """Issue a warning to a user"""
        with self.lock:
            if username not in self.user_warnings:
                self.user_warnings[username] = []
            self.user_warnings[username].append(reason)
        log_session(f"ADMIN warned {username}: {reason}")

    def get_warnings(self, username: str) -> list:
        """Get all warnings for a user"""
        with self.lock:
            return self.user_warnings.get(username, [])

    def can_send_message(self, username: str) -> bool:
        """Rate limiting check (thread-safe)"""
        with self.lock:
            now = time.time()
            timestamps = [
                t for t in self.message_timestamps.get(username, []) 
                if now - t < 1  # Keep messages from last 1 second
            ]
            
            if len(timestamps) >= self.rate_limit:
                return False
                
            timestamps.append(now)
            self.message_timestamps[username] = timestamps
            return True

    def broadcast(self, message: str, exclude: str = None):
        """Send a message to all connected users (thread-safe)"""
        with self.lock:
            broadcast_message(message, self.connected_users, exclude)

    def list_users(self) -> list:
        """Get all online usernames"""
        with self.lock:
            return list(self.connected_users.keys())

    def save_state(self):
        """Persist session data (for server restarts)"""
        with self.lock:
            # Save to database (implementation in utils.py)
            pass

# Global instance for modular access
session_manager = SessionManager()