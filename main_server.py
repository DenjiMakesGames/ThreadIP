import socket
import threading
import auth
from session_manager import session_manager
import utils
from admin import handle_admin_command

HOST = '0.0.0.0'
PORT = 12345

auth.init_db()
utils.initialize_user_status_db()

server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server_socket.bind((HOST, PORT))
server_socket.listen()

print(f"[+] Server started on {HOST}:{PORT}")
utils.log_session("Server started.")

def broadcast_to_all(sender: str, message: str):
    utils.broadcast_message(
        f"{sender}: {message}",
        session_manager.connected_users,
        exclude_user=sender
    )

def client_thread(conn, addr):
    username = ""
    try:
        conn.send(b"Login or Register? (L/R): ")
        choice = conn.recv(1024).decode().strip().upper()

        conn.send(b"Username: ")
        username = conn.recv(1024).decode().strip()

        conn.send(b"Password: ")
        password = conn.recv(1024).decode().strip()

        if choice == 'R':
            if not auth.register_user(username, password):
                conn.send(b"Registration failed (invalid username or already exists).\n")
                conn.close()
                return
            conn.send(b"Registered successfully.\n")
        elif choice == 'L':
            if not auth.authenticate_user(username, password):
                conn.send(b"Invalid credentials.\n")
                conn.close()
                return
        else:
            conn.send(b"Invalid choice.\n")
            conn.close()
            return

        if not session_manager.add_user(username, conn):
            conn.send(b"You are banned from this server.\n")
            conn.close()
            return

        conn.send(b"Welcome to the chat! Type /quit to exit.\n")
        utils.log_session(f"{username} logged in from {addr[0]}")
        broadcast_to_all("Server", f"{username} joined the chat.")

        while True:
            data = conn.recv(1024)
            if not data:
                break

            message = data.decode().strip()
            if not message:
                continue

            if message.lower() == "/quit":
                conn.send(b"Goodbye!\n")
                break

            if message.startswith("/admin"):
                if auth.is_admin(username):
                    response = handle_admin_command(message[6:].strip())
                    conn.send(f"{response}\n".encode())
                else:
                    conn.send(b"Permission denied.\n")
                continue

            if session_manager.is_muted(username):
                conn.send(b"You are muted and cannot send messages.\n")
                continue

            utils.log_message(username, message)
            broadcast_to_all(username, message)

    except (ConnectionError, OSError) as e:
        utils.log_session(f"Connection error with {username or addr}: {str(e)}", "ERROR")
    finally:
        if username:
            session_manager.remove_user(username)
            broadcast_to_all("Server", f"{username} has left the chat.")
        conn.close()

def accept_connections():
    while True:
        try:
            conn, addr = server_socket.accept()
            threading.Thread(
                target=client_thread,
                args=(conn, addr),
                daemon=True
            ).start()
        except OSError:
            break  # Socket closed during shutdown

try:
    accept_connections()
except KeyboardInterrupt:
    print("\nShutting down...")
    utils.log_session("Server shutdown by admin")
    server_socket.close()