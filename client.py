import socket
import threading
import utils
import sys

def receive(client, running_flag):
    while running_flag[0]:
        try:
            message = client.recv(1024).decode()
            if not message:
                break
            print(message, end='')
            if ":" in message:
                sender, msg = message.split(":", 1)
                utils.log_message(sender.strip(), msg.strip(), "received")
        except ConnectionResetError:
            print("\nConnection lost with server")
            running_flag[0] = False
            break
        except Exception as e:
            print(f"\nError: {str(e)}")
            running_flag[0] = False
            break

def write(client, username, running_flag):
    while running_flag[0]:
        try:
            msg = input()
            if msg.lower() == "/quit":
                client.send(msg.encode())
                running_flag[0] = False
                break
            client.send(msg.encode())
            utils.log_message(username, msg)
        except Exception as e:
            print(f"Send error: {str(e)}")
            running_flag[0] = False
            break

def main():
    server_ip = input("Enter server IP: ").strip()
    port = 12345

    try:
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.connect((server_ip, port))
    except Exception as e:
        print(f"Connection failed: {str(e)}")
        return

    try:
        # Auth flow
        print(client.recv(1024).decode(), end='')  # L/R prompt
        choice = input().upper()
        client.send(choice.encode())

        print(client.recv(1024).decode(), end='')  # Username prompt
        username = input().strip()
        client.send(username.encode())

        print(client.recv(1024).decode(), end='')  # Password prompt
        password = input().strip()
        client.send(password.encode())

        # Get auth response
        response = client.recv(1024).decode()
        print(response, end='')
        if "failed" in response.lower() or "invalid" in response.lower():
            client.close()
            return

        running = [True]
        threading.Thread(
            target=receive,
            args=(client, running),
            daemon=True
        ).start()
        write(client, username, running)

    except KeyboardInterrupt:
        print("\nDisconnecting...")
    finally:
        client.close()
        sys.exit(0)

if __name__ == "__main__":
    main()