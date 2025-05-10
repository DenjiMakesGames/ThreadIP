import socket
import threading
import sys
import time
from utils import NetworkUtils, Logger

class ChatClient:
    def __init__(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.running = False
        self.username = ""

    def connect(self, host: str, port: int) -> bool:
        """Establish connection with timeout handling"""
        try:
            Logger.log(f"Connecting to {host}:{port}...")
            self.socket.settimeout(5)
            self.socket.connect((host, port))
            self.running = True
            return True
        except Exception as e:
            Logger.log(f"Connection failed: {str(e)}", "ERROR")
            return False

    def authenticate(self) -> bool:
        """Handle login/registration flow"""
        try:
            # Get server prompts
            data = self.socket.recv(1024).decode()
            print(data, end='')
            choice = input().strip().upper()
            self.socket.sendall(choice.encode() + b'\n')

            data = self.socket.recv(1024).decode()
            print(data, end='')
            self.username = input().strip()
            self.socket.sendall(self.username.encode() + b'\n')

            data = self.socket.recv(1024).decode()
            print(data, end='')
            password = input().strip()
            self.socket.sendall(password.encode() + b'\n')

            # Get final response
            data = self.socket.recv(1024).decode()
            print(data, end='')
            return "Welcome" in data
        except Exception as e:
            Logger.log(f"Auth error: {str(e)}", "ERROR")
            return False

    def receive_thread(self):
        """Handle incoming messages"""
        while self.running:
            try:
                data = self.socket.recv(1024)
                if not data:
                    Logger.log("Server disconnected", "WARNING")
                    self.running = False
                    break
                print(data.decode(), end='')
            except Exception as e:
                Logger.log(f"Receive error: {str(e)}", "ERROR")
                self.running = False

    def heartbeat_thread(self):
        """Maintain connection alive"""
        while self.running:
            time.sleep(30)
            try:
                self.socket.sendall(b'\x00')
            except:
                self.running = False

    def run(self):
        """Main client loop"""
        print("\nGlobal Chat Client")
        print("=" * 40)
        
        host = input("Server IP/Domain: ").strip()
        port = int(input("Port (default 5000): ") or 5000)

        if not self.connect(host, port):
            return

        if not self.authenticate():
            self.socket.close()
            return

        # Start threads
        threading.Thread(target=self.receive_thread, daemon=True).start()
        threading.Thread(target=self.heartbeat_thread, daemon=True).start()

        # Input loop
        try:
            while self.running:
                msg = input()
                if msg.lower() == "/quit":
                    self.socket.sendall(b"/quit\n")
                    self.running = False
                else:
                    self.socket.sendall(msg.encode() + b'\n')
        except KeyboardInterrupt:
            print("\nDisconnecting...")
        finally:
            self.socket.close()
            sys.exit(0)

if __name__ == "__main__":
    ChatClient().run()