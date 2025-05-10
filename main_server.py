import socket
import threading
from utils import log_session
from session_manager import session_manager
import auth
from admin import handle_admin_command

class ChatServer:
    def __init__(self, port=5000):
        self.port = port
        self.server_socket = None
        self.running = False

    def start(self):
        auth.init_db()
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind(('0.0.0.0', self.port))
        self.server_socket.listen()
        self.running = True

        print(f"[+] Server started on port {self.port}")
        print(f"Global connect using your public IP and port {self.port}")
        log_session("Server started")

        try:
            while self.running:
                conn, addr = self.server_socket.accept()
                threading.Thread(
                    target=self.handle_client,
                    args=(conn, addr),
                    daemon=True
                ).start()
        except OSError:
            pass  # Socket closed intentionally

    def handle_client(self, conn, addr):
        username = ""
        try:
            # Authentication flow
            conn.settimeout(30)
            conn.send(b"Login or Register? (L/R): ")
            choice = conn.recv(1024).decode('utf-8', errors='ignore').strip().upper()

            conn.send(b"Username: ")
            username = conn.recv(1024).decode('utf-8', errors='replace').strip()

            conn.send(b"Password: ")
            password = conn.recv(1024).decode('utf-8', errors='replace').strip()

            # Auth logic
            if choice == 'R':
                if not auth.register_user(username, password):
                    conn.send(b"Registration failed.\n")
                    return
                conn.send(b"Registered successfully.\n")
            elif choice == 'L':
                if not auth.authenticate_user(username, password):
                    conn.send(b"Invalid credentials.\n")
                    return
            else:
                conn.send(b"Invalid choice.\n")
                return

            if not session_manager.add_user(username, conn):
                conn.send(b"You are banned.\n")
                return

            conn.send(b"Welcome to global chat!\n")
            log_session(f"{username} connected from {addr[0]}")

            # Message handling
            while self.running:
                try:
                    data = conn.recv(1024)
                    if not data:
                        break

                    message = data.decode('utf-8', errors='replace').strip()
                    self.process_message(username, conn, message)

                except socket.timeout:
                    continue
                except Exception as e:
                    log_session(f"Error with {username}: {str(e)}", "ERROR")
                    break

        finally:
            if username:
                session_manager.remove_user(username)
            conn.close()

    def process_message(self, username, conn, message):
        if message.lower() == "/quit":
            conn.send(b"Goodbye!\n")
            return

        if message.startswith("/admin"):
            if auth.is_admin(username):
                response = handle_admin_command(message[6:].strip())
                conn.send(f"{response}\n".encode())
            else:
                conn.send(b"Permission denied.\n")
            return

        if session_manager.is_muted(username):
            conn.send(b"You are muted.\n")
            return

        session_manager.broadcast(f"{username}: {message}")

    def stop(self):
        self.running = False
        if self.server_socket:
            self.server_socket.close()
        print("\n[!] Server stopped")

if __name__ == "__main__":
    server = ChatServer(port=5000)
    try:
        server.start()
    except KeyboardInterrupt:
        server.stop()