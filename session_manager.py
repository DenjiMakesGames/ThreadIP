import threading
from utils import log_session, broadcast_message

class SessionManager:
    def __init__(self):
        self.connected_users = {}
        self.banned_users = set()
        self.muted_users = set()
        self.lock = threading.Lock()

    def add_user(self, username, conn):
        with self.lock:
            if username in self.banned_users:
                return False
            self.connected_users[username] = conn
            return True

    def remove_user(self, username: str):
        with self.lock:
            if username in self.connected_users:
                del self.connected_users[username]
                broadcast_message(f"{username} has left the chat.", self.connected_users)
                log_session(f"{username} disconnected.")

    def broadcast(self, message):
        with self.lock:
            for user, sock in list(self.connected_users.items()):
                try:
                    sock.send(f"{message}\n".encode())
                except:
                    self.remove_user(user)

    def list_users(self) -> list:
        with self.lock:
            return list(self.connected_users.keys())

    def mute_user(self, username: str):
        with self.lock:
            self.muted_users.add(username)
        log_session(f"ADMIN muted user \"{username}\"")

    def unmute_user(self, username: str):
        with self.lock:
            if username in self.muted_users:
                self.muted_users.remove(username)
        log_session(f"ADMIN unmuted user \"{username}\"")

    def is_muted(self, username: str) -> bool:
        with self.lock:
            return username in self.muted_users

    def warn_user(self, username: str, reason: str = "No reason provided"):
        with self.lock:
            if username not in self.user_warnings:
                self.user_warnings[username] = []
            self.user_warnings[username].append(reason)
        log_session(f"ADMIN warned user \"{username}\" for: {reason}")

    def get_warnings(self, username: str) -> list:
        with self.lock:
            return self.user_warnings.get(username, [])

    def ban_user(self, username: str):
        with self.lock:
            self.banned_users.add(username)
            if username in self.connected_users:
                del self.connected_users[username]
        log_session(f"ADMIN banned user \"{username}\"")

# Global instance
session_manager = SessionManager()