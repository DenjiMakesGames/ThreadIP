import socket
import threading
import sys
import time
from utils import log_message

class ChatClient:
    def __init__(self):
        self.running = False
        self.client_socket = None

    def receive_messages(self):
        while self.running:
            try:
                data = self.client_socket.recv(1024)
                if not data:
                    self.shutdown()
                    break
                message = data.decode('utf-8', errors='replace')
                print(message, end='')
                if ":" in message:
                    sender, content = message.split(":", 1)
                    log_message(sender.strip(), content.strip(), "received")
            except (ConnectionResetError, socket.timeout):
                print("\n[!] Connection lost")
                self.shutdown()
                break
            except Exception as e:
                print(f"\n[!] Receive error: {str(e)}")
                self.shutdown()
                break

    def send_heartbeat(self):
        while self.running:
            time.sleep(30)
            try:
                self.client_socket.send(b'\x00')  # Null byte heartbeat
            except:
                self.shutdown()
                break

    def connect_to_server(self, host, port):
        try:
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.settimeout(10)  # Connection timeout
            self.client_socket.connect((host, port))
            self.running = True
            return True
        except Exception as e:
            print(f"[!] Connection failed: {str(e)}")
            return False

    def shutdown(self):
        self.running = False
        if self.client_socket:
            self.client_socket.close()

    def auth_flow(self):
        try:
            # Get initial prompt
            data = self.client_socket.recv(1024).decode('utf-8')
            print(data, end='')
            
            # Send auth choice
            choice = input().strip().upper()
            self.client_socket.send(choice.encode() + b'\n')
            
            # Handle username/password
            for prompt in ["Username", "Password"]:
                data = self.client_socket.recv(1024).decode('utf-8')
                print(data, end='')
                response = input().strip()
                self.client_socket.send(response.encode() + b'\n')
            
            # Get final response
            data = self.client_socket.recv(1024).decode('utf-8')
            print(data, end='')
            return "Welcome" in data
        except Exception as e:
            print(f"\n[!] Auth error: {str(e)}")
            return False

    def run(self):
        print("Termux Chat Client\n" + "="*20)
        host = input("Enter server IP/hostname: ").strip()
        port = int(input("Enter port (default 5000): ")) or 5000

        if not self.connect_to_server(host, port):
            return

        if not self.auth_flow():
            self.shutdown()
            return

        threading.Thread(target=self.receive_messages, daemon=True).start()
        threading.Thread(target=self.send_heartbeat, daemon=True).start()

        try:
            while self.running:
                msg = input()
                if msg.lower() == "/quit":
                    self.client_socket.send(b"/quit\n")
                    self.shutdown()
                else:
                    self.client_socket.send(msg.encode() + b'\n')
                    log_message("You", msg, "sent")
        except KeyboardInterrupt:
            print("\nDisconnecting...")
        finally:
            self.shutdown()

if __name__ == "__main__":
    ChatClient().run()