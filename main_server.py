import socket
import threading
import select
from auth import init_db, authenticate_user, register_user, is_admin
from session_manager import session_manager
from utils import log_session, log_message
from admin import handle_admin_command

class ChatServer:
    def __init__(self, host='0.0.0.0', port=5000):
        self.host = host
        self.port = port
        self.server_socket = None
        self.running = False

    def start(self):
        init_db()
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(5)
        self.running = True

        print(f"[+] Server started on {self.host}:{self.port}")
        log_session("Server started")

        try:
            while self.running:
                readable, _, _ = select.select([self.server_socket], [], [], 1)
                if readable:
                    conn, addr = self.server_socket.accept()
                    threading.Thread(
                        target=self.handle_client,
                        args=(conn, addr),
                        daemon=True
                    ).start()
        except KeyboardInterrupt:
            self.stop()

    def stop(self):
        self.running = False
        if self.server_socket:
            self.server_socket.close()
        print("\n[!] Server stopped")

    def handle_client(self, conn, addr):
        username = ""
        try:
            conn.settimeout(30)
            
            # Auth flow
            conn.send(b"Login or Register? (L/R): ")
            choice = conn.recv(1024).decode('utf-8', errors='ignore').strip().upper()

            conn.send(b"Username: ")
            username = conn.recv(1024).decode('utf-8', errors='replace').strip()

            conn.send(b"Password: ")
            password = conn.recv(1024).decode('utf-8', errors='replace').strip()

            if choice == 'R':
                if not register_user(username, password):
                    conn.send(b"Registration failed (invalid username or exists).\n")
                    return
                conn.send(b"Registered successfully.\n")
            elif choice == 'L':
                if not authenticate_user(username, password):
                    conn.send(b"Invalid credentials.\n")
                    return
            else:
                conn.send(b"Invalid choice.\n")
                return

            if not session_manager.add_user(username, conn):
                conn.send(b"You are banned.\n")
                return

            conn.send(b"Welcome! Type /quit to exit.\n")
            log_session(f"{username} connected from {addr[0]}")
            session_manager.broadcast(f"{username} joined the chat")

            # Main message loop
            while self.running:
                try:
                    data = conn.recv(1024)
                    if not data:
                        break

                    message = data.decode('utf-8', errors='replace').strip()
                    if not message:
                        continue

                    if message.lower() == "/quit":
                        conn.send(b"Goodbye!\n")
                        break

                    if message.startswith("/admin"):
                        if is_admin(username):
                            response = handle_admin_command(message[6:].strip())
                            conn.send(f"{response}\n".encode())
                        else:
                            conn.send(b"Permission denied.\n")
                        continue

                    if session_manager.is_muted(username):
                        conn.send(b"You are muted.\n")
                        continue

                    log_message(username, message)
                    session_manager.broadcast(f"{username}: {message}", exclude=username)

                except socket.timeout:
                    conn.send(b"\nPing...\n")  # Keepalive check
                except (ConnectionResetError, OSError):
                    break

        except Exception as e:
            log_session(f"Error with {username or addr}: {str(e)}", "ERROR")
        finally:
            if username:
                session_manager.remove_user(username)
                session_manager.broadcast(f"{username} left the chat")
            conn.close()

if __name__ == "__main__":
    server = ChatServer()
    server.start()