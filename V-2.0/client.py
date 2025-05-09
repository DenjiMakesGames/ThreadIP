# Client.py (This file is for the users and people to want to communicate to each other.)
import socket
import threading
import sys
import time

def receive(client, running_flag):
    while running_flag[0]:
        try:
            message = client.recv(1024).decode('utf-8', errors='replace')
            if not message:
                print("\n[!] Server disconnected")
                running_flag[0] = False
                break
            print(message, end='')
        except (ConnectionResetError, OSError):
            print("\n[!] Connection lost")
            running_flag[0] = False
            break
        except Exception as e:
            print(f"\n[!] Receive error: {str(e)}")
            running_flag[0] = False
            break

def heartbeat(client, interval=30):
    while True:
        time.sleep(interval)
        try:
            client.send(b'\x00')  # Null byte heartbeat
        except:
            break

def auth_flow(client):
    try:
        # Get initial prompt
        data = client.recv(1024).decode('utf-8')
        print(data, end='')
        
        # Handle login/register
        choice = input().strip().upper()
        client.send(choice.encode() + b'\n')
        
        # Handle username/password
        for prompt in ["Username", "Password"]:
            data = client.recv(1024).decode('utf-8')
            print(data, end='')
            response = input().strip()
            client.send(response.encode() + b'\n')
        
        # Get final auth response
        data = client.recv(1024).decode('utf-8')
        print(data, end='')
        return "Welcome" in data or "successfully" in data
        
    except Exception as e:
        print(f"\n[!] Auth error: {str(e)}")
        return False

def main():
    print("Termux Chat Client\n" + "="*20)
    
    server_ip = input("Enter server IP: ").strip()
    port = 5000  # Match your server port

    try:
        # Test connection first
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as test_sock:
            test_sock.settimeout(3)
            test_sock.connect((server_ip, port))
        
        # Main connection
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.connect((server_ip, port))
        
        if not auth_flow(client):
            client.close()
            return

        running = [True]
        threading.Thread(
            target=receive, 
            args=(client, running),
            daemon=True
        ).start()
        
        threading.Thread(
            target=heartbeat,
            args=(client,),
            daemon=True
        ).start()

        while running[0]:
            try:
                msg = input()
                if msg.lower() == "/quit":
                    client.send(b"/quit\n")
                    running[0] = False
                else:
                    client.send(msg.encode() + b'\n')
            except KeyboardInterrupt:
                print("\nDisconnecting...")
                running[0] = False
            except Exception as e:
                print(f"\n[!] Send error: {str(e)}")
                running[0] = False

    except ConnectionRefusedError:
        print("[!] Server not available")
    except Exception as e:
        print(f"[!] Connection error: {str(e)}")
    finally:
        client.close()
        sys.exit(0)

if __name__ == "__main__":
    main()