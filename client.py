import socket
import threading
import sys
import time
import requests

def get_public_ip():
    try:
        return requests.get('https://api.ipify.org').text
    except:
        return "Unable to determine public IP"

class ChatClient:
    def __init__(self):
        self.running = False
        self.client_socket = None

    def connect_to_server(self, server_ip, port):
        try:
            print(f"\nConnecting to {server_ip}:{port}...")
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.settimeout(10)
            self.client_socket.connect((server_ip, port))
            self.running = True
            return True
        except Exception as e:
            print(f"[!] Connection failed: {str(e)}")
            return False

    def receive_messages(self):
        while self.running:
            try:
                message = self.client_socket.recv(1024).decode('utf-8', errors='replace')
                if not message:
                    print("\n[!] Server disconnected")
                    self.running = False
                    break
                print(message, end='')
            except socket.timeout:
                continue
            except Exception as e:
                print(f"\n[!] Receive error: {str(e)}")
                self.running = False

    def send_heartbeat(self):
        while self.running:
            time.sleep(30)
            try:
                self.client_socket.send(b'\x00')
            except:
                self.running = False

    def start(self):
        print("Global Chat Client\n" + "="*20)
        print(f"Your public IP: {get_public_ip()}\n")
        
        server_ip = input("Enter server IP/domain: ").strip()
        port = int(input("Enter port (default 5000): ") or 5000)

        if not self.connect_to_server(server_ip, port):
            return

        threading.Thread(target=self.receive_messages, daemon=True).start()
        threading.Thread(target=self.send_heartbeat, daemon=True).start()

        try:
            while self.running:
                msg = input()
                if msg.lower() == "/quit":
                    self.client_socket.send(b"/quit\n")
                    self.running = False
                else:
                    self.client_socket.send(msg.encode() + b'\n')
        except KeyboardInterrupt:
            print("\nDisconnecting...")
        finally:
            self.client_socket.close()

if __name__ == "__main__":
    ChatClient().start()