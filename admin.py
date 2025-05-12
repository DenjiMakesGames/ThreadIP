from session_manager import session_manager
from utils import debug_log
import threading

def handle_admin_command(command: str):
    if not command.startswith('/'):
        return "Invalid command format"

    parts = command.split()
    cmd = parts[0].lower() if parts else ""

    if cmd == "/kick" and len(parts) == 2:
        username = parts[1]
        if username in session_manager.connected_users:
            try:
                session_manager.connected_users[username].send(
                    b"You have been kicked by the admin.\n"
                )
            except (ConnectionError, OSError):
                pass
            session_manager.remove_user(username)
            debug_log(f"ADMIN kicked user \"{username}\"")
            return f"Kicked {username}"
        return f"User {username} not found"

    elif cmd == "/ban" and len(parts) == 2:
        username = parts[1]
        session_manager.ban_user(username)
        return f"Banned {username}"

    elif cmd == "/list":
        users = session_manager.list_users()
        return f"Online Users: {', '.join(users) or 'None'}"

    elif cmd == "/mute" and len(parts) == 2:
        username = parts[1]
        session_manager.mute_user(username)
        return f"Muted {username}"

    elif cmd == "/unmute" and len(parts) == 2:
        username = parts[1]
        session_manager.unmute_user(username)
        return f"Unmuted {username}"

    elif cmd == "/warn" and len(parts) >= 3:
        username, reason = parts[1], ' '.join(parts[2:])
        session_manager.warn_user(username, reason)
        if username in session_manager.connected_users:
            try:
                session_manager.connected_users[username].send(
                    f"WARNING: {reason}\n".encode()
                )
            except (ConnectionError, OSError):
                pass
        return f"Warned {username}"

    elif cmd == "/history" and len(parts) == 2:
        username = parts[1]
        warnings = session_manager.get_warnings(username)
        if warnings:
            return "\n".join([f"- {w}" for w in warnings])
        return f"No warnings for {username}"

    elif cmd == "/broadcast" and len(parts) >= 2:
        message = ' '.join(parts[1:])
        for user, sock in session_manager.connected_users.items():
            try:
                sock.send(f"ADMIN BROADCAST: {message}\n".encode())
            except (ConnectionError, OSError):
                pass
        debug_log(f"ADMIN broadcasted: {message}")
        return "Broadcast sent"

    elif cmd == "/shutdown":
        debug_log("ADMIN shutdown server")
        for user, sock in session_manager.connected_users.items():
            try:
                sock.send(b"Server is shutting down.\n")
                sock.close()
            except (ConnectionError, OSError):
                pass
        session_manager.connected_users.clear()
        return "SHUTDOWN"

    return "Unknown command"