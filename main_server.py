import socket
import threading
from utils import DatabaseManager, NetworkUtils, Logger
from session_manager import session_manager
import auth

class ChatServer:
    def __init__(self, port=5000):
        self.port = port
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.running = False

    def start(self):
        """Start the server with proper initialization"""
        DatabaseManager.initialize()
        auth.init_db()

        try:
            self.server_socket.bind(('0.0.0.0', self.port))
            self.server_socket.listen()
            self.running = True
            
            local_ip, public_ip = NetworkUtils.get_ip_info()
            Logger.log(f"Server started on port {self.port}")
            Logger.log(f"Local: {local_ip}:{self.port}")
            Logger.log(f"Public: {public_ip}:{self.port}")

            while self.running:
                conn, addr = self.server_socket.accept()
                threading.Thread(
                    target=self.handle_client,
                    args=(conn, addr),
                    daemon=True
                ).start()
        except Exception as e:
            Logger.log(f"Server error: {str(e)}", "ERROR")

    def handle_client(self, conn, addr):
        """Handle individual client connection"""
        username = ""
        try:
            conn.settimeout(30)
            
            # Authentication flow
            if not self.authenticate_client(conn):
                return

            # Main message loop
            while self.running:
                try:
                    data = conn.recv(1024)
                    if not data:
                        break
                    
                    self.process_message(conn, username, data)
                except socket.timeout:
                    continue
                except Exception as e:
                    Logger.log(f"Client error: {str(e)}", "ERROR")
                    break
        finally:
            if username:
                session_manager.remove_user(username)
            conn.close()

    def authenticate_client(self, conn) -> bool:
        """Handle client authentication"""
        try:
            conn.sendall(b"Login or Register? (L/R): ")
            choice = conn.recv(1024).decode().strip().upper()

            conn.sendall(b"Username: ")
            username = conn.recv(1024).decode().strip()

            conn.sendall(b"Password: ")
            password = conn.recv(1024).decode().strip()

            if choice == 'R':
                if not auth.register_user(username, password):
                    conn.sendall(b"Registration failed.\n")
                    return False
                conn.sendall(b"Registered successfully.\n")
            elif choice == 'L':
                if not auth.authenticate_user(username, password):
                    conn.sendall(b"Invalid credentials.\n")
                    return False
            else:
                conn.sendall(b"Invalid choice.\n")
                return False

            if not session_manager.add_user(username, conn):
                conn.sendall(b"You are banned.\n")
                return False

            conn.sendall(b"Welcome to global chat!\n")
            Logger.log(f"{username} connected from {addr[0]}")
            return True
        except Exception as e:
            Logger.log(f"Auth error: {str(e)}", "ERROR")
            return False

    def process_message(self, conn, username, data):
        """Process incoming messages"""
        try:
            message = data.decode('utf-8').strip()
            
            if message.lower() == "/quit":
                conn.sendall(b"Goodbye!\n")
                return
                
            # Process admin commands or broadcast
            session_manager.handle_message(username, message, conn)
        except UnicodeDecodeError:
            Logger.log(f"Invalid encoding from {username}", "WARNING")

    def stop(self):
        """Graceful shutdown"""
        self.running = False
        self.server_socket.close()
        Logger.log("Server stopped")

if __name__ == "__main__":
    server = ChatServer(port=5000)
    try:
        server.start()
    except KeyboardInterrupt:
        server.stop()