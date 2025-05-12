# main_server.py
import socket
import threading
import subprocess
import os
from config import debug_queue, session_manager
from auth import init_db, register_user, authenticate_user, is_admin
from admin import handle_admin_command
from utils import log_message, debug_log

class ChatServer:
    def __init__(self, host='0.0.0.0', port=5000):
        self.host = host
        self.port = port
        self.server_socket = None
        self.running = False

    def debug_console(self):
        """Start debug console in separate window"""
        try:
            if os.name == 'nt':
                subprocess.Popen(['start', 'python', 'debug_console.py'], shell=True)
            else:
                subprocess.Popen(['x-terminal-emulator', '-e', 'python3 debug_console.py'])
        except Exception as e:
            print(f"Debug console error: {str(e)}")

    def start(self):
        """Main server startup sequence"""
        init_db()
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(5)
        self.running = True

        self.debug_console()
        debug_log(f"Server started on {self.host}:{self.port}")

        # Start admin interface
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

    def stop(self):
        """Clean server shutdown"""
        self.running = False
        if self.server_socket:
            self.server_socket.close()
        debug_log("Server stopped")

    def admin_input(self):
        """Handle admin commands from console"""
        print("\nADMIN CONSOLE (type /help for commands)")
        while self.running:
            try:
                cmd = input("ADMIN> ").strip()
                if not cmd:
                    continue

                if cmd.lower() == '/quit':
                    self.stop()
                    break

                if cmd.startswith('/'):
                    response = handle_admin_command(cmd[1:])
                    print(f"Server: {response}")
                else:
                    session_manager.broadcast(f"ADMIN: {cmd}")
                    debug_log(f"Admin broadcast: {cmd}")

            except Exception as e:
                debug_log(f"Admin command error: {str(e)}", "ERROR")

    def handle_client(self, conn, addr):
        """Handle individual client connection"""
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
                    conn.send(b"Registration failed.\n")
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
            debug_log(f"{username} connected from {addr[0]}")

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
                    conn.send(b"\nPing...\n")
                except (ConnectionResetError, OSError):
                    break

        except Exception as e:
            debug_log(f"Error with {username or addr}: {str(e)}", "ERROR")
        finally:
            if username:
                session_manager.remove_user(username)
                session_manager.broadcast(f"{username} left the chat")
            conn.close()

if __name__ == "__main__":
    # Initialize core components
    init_db()
    server = ChatServer()
    server.start()