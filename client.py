import socket
import threading
import sys
import time
from queue import Queue
from utils import log_message

class ChatClient:
    def __init__(self):
        self.running = False
        self.socket = None
        self.username = ""
        self.debug_queue = Queue()  # For future debug expansion

    def _send(self, message: str):
        """Thread-safe socket sending with error handling"""
        try:
            if self.socket:
                self.socket.send(message.encode() + b'\n')
        except (ConnectionError, OSError) as e:
            self.debug_queue.put(f"[NETWORK ERROR] Send failed: {str(e)}")
            self.shutdown()

    def _receive(self):
        """Main receive loop with proper decoding"""
        while self.running:
            try:
                data = self.socket.recv(1024)
                if not data:
                    self.debug_queue.put("[SERVER] Connection closed")
                    self.shutdown()
                    break

                message = data.decode('utf-8', errors='replace').strip()
                if message:  # Only process non-empty messages
                    print(message)
                    if ":" in message:  # Log chat messages
                        sender, content = message.split(":", 1)
                        log_message(sender.strip(), content.strip(), "received")

            except (ConnectionResetError, socket.timeout) as e:
                self.debug_queue.put(f"[NETWORK ERROR] {str(e)}")
                self.shutdown()
                break
            except Exception as e:
                self.debug_queue.put(f"[UNKNOWN ERROR] {str(e)}")
                self.shutdown()
                break

    def _heartbeat(self):
        """Maintain connection with keepalive packets"""
        while self.running:
            time.sleep(30)
            try:
                self._send("\x00")  # Null byte heartbeat
            except:
                self.shutdown()
                break

    def auth_flow(self) -> bool:
        """Handle authentication process"""
        try:
            # Get server prompts
            for _ in range(3):  # Expect 3 prompts (L/R, username, password)
                data = self.socket.recv(1024).decode('utf-8', errors='replace')
                if not data:
                    return False

                print(data, end='')
                if "Username:" in data or "Password:" in data or "Login or Register" in data:
                    response = input().strip()
                    self._send(response)

            # Get final auth response
            data = self.socket.recv(1024).decode('utf-8', errors='replace')
            print(data)
            return "Welcome" in data or "successfully" in data

        except Exception as e:
            self.debug_queue.put(f"[AUTH ERROR] {str(e)}")
            return False

    def connect(self, host: str, port: int) -> bool:
        """Establish connection with timeout"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(10)
            self.socket.connect((host, port))
            self.running = True
            return True
        except Exception as e:
            self.debug_queue.put(f"[CONNECTION FAILED] {str(e)}")
            return False

    def shutdown(self):
        """Cleanup resources"""
        self.running = False
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
        sys.exit(0)

    def run(self):
        print("=== Chat Client ===")
        host = input("Server IP: ").strip()
        port = int(input("Port [5000]: ")).strip() or 5000

        if not self.connect(host, port):
            print("\n[!] Connection failed (see debug for details)")
            return

        if not self.auth_flow():
            print("\n[!] Authentication failed")
            self.shutdown()
            return

        # Start network threads
        threading.Thread(target=self._receive, daemon=True).start()
        threading.Thread(target=self._heartbeat, daemon=True).start()

        # Main input loop
        try:
            while self.running:
                msg = input()
                if msg.lower() == "/quit":
                    self._send("/quit")
                    self.shutdown()
                else:
                    self._send(msg)
                    log_message("You", msg, "sent")
        except KeyboardInterrupt:
            print("\nDisconnecting...")
        finally:
            self.shutdown()

if __name__ == "__main__":
    ChatClient().run()