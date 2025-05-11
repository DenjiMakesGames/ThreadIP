import socket
import threading
import subprocess
import sys
import os
from queue import Queue
from auth import init_db, authenticate_user, register_user, is_admin
from session_manager import session_manager
from utils import log_session, log_message
from admin import handle_admin_command

# Debug message queue (thread-safe)
debug_queue = Queue()

def debug_console():
    """Open a separate terminal window for debug output"""
    if os.name == 'nt':  # Windows
        subprocess.Popen(['start', 'python', 'debug_console.py'], shell=True)
    else:  # Linux/Mac
        subprocess.Popen(['x-terminal-emulator', '-e', 'python3 debug_console.py'])

def debug_log(message, level="INFO"):
    """Send messages to debug console"""
    debug_queue.put(f"[{level}] {message}")
    log_session(message, level)  # Also log to file

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

        # Start debug console
        debug_console()
        debug_log(f"Server started on {self.host}:{self.port}")

        # Admin input thread
        threading.Thread(target=self.admin_input, daemon=True).start()

        try:
            while self.running:
                conn, addr = self.server_socket.accept()
                threading.Thread(
                    target=self.handle_client,
                    args=(conn, addr),
                    daemon=True
                ).start()
        except KeyboardInterrupt:
            self.stop()

    def admin_input(self):
        """Handle admin commands from server terminal"""
        while self.running:
            try:
                cmd = input("[ADMIN] ").strip()
                if cmd.lower() == '/quit':
                    self.stop()
                    break
                
                if cmd.startswith('/'):
                    response = handle_admin_command(cmd[1:])
                    print(response)
                else:
                    # Broadcast as admin
                    session_manager.broadcast(f"ADMIN: {cmd}")
                    debug_log(f"Admin broadcast: {cmd}")
            except Exception as e:
                debug_log(f"Admin input error: {str(e)}", "ERROR")

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