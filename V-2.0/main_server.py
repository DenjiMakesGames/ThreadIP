# Server.py (Run this, as this will handle the server-side and the admin access.)
import socket
import threading
import auth
from session_manager import session_manager
from utils import log_session
from admin import handle_admin_command

HOST = '0.0.0.0'
PORT = 5000  # Changed to match your port

auth.init_db()

server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server_socket.bind((HOST, PORT))
server_socket.listen()

print(f"[+] Server started on {HOST}:{PORT}")
log_session("Server started.")

def heartbeat_monitor(conn, timeout=60):
    conn.settimeout(timeout)
    while True:
        try:
            if conn.recv(1) == b'':  # Connection closed
                conn.close()
                break
        except socket.timeout:
            conn.close()
            break
        except:
            break

def broadcast_to_all(sender, message):
    for user, sock in session_manager.connected_users.items():
        try:
            if user != sender:
                sock.send(f"{sender}: {message}\n".encode())
        except:
            pass

def client_thread(conn, addr):
    username = ""
    try:
        # Auth flow
        conn.send(b"Login or Register? (L/R): ")
        choice = conn.recv(1024).decode('utf-8', errors='ignore').strip().upper()

        conn.send(b"Username: ")
        username = conn.recv(1024).decode('utf-8', errors='replace').strip()

        conn.send(b"Password: ")
        password = conn.recv(1024).decode('utf-8', errors='replace').strip()

        if choice == 'R':
            if not auth.register_user(username, password):
                conn.send(b"Registration failed.\n")
                conn.close()
                return
            conn.send(b"Registered successfully.\n")
        elif choice == 'L':
            if not auth.authenticate_user(username, password):
                conn.send(b"Invalid credentials.\n")
                conn.close()
                return
        else:
            conn.send(b"Invalid choice.\n")
            conn.close()
            return

        if not session_manager.add_user(username, conn):
            conn.send(b"You are banned from this server.\n")
            conn.close()
            return

        conn.send(b"Welcome to the chat! Type /quit to exit.\n")
        log_session(f"{username} logged in from {addr[0]}")
        broadcast_to_all("Server", f"{username} joined the chat.")

        # Start heartbeat monitor
        threading.Thread(
            target=heartbeat_monitor,
            args=(conn,),
            daemon=True
        ).start()

        while True:
            try:
                data = conn.recv(1024)
                if not data:
                    break

                try:
                    message = data.decode('utf-8').strip()
                except UnicodeDecodeError:
                    message = data.decode('utf-8', errors='replace').strip()
                    log_session(f"Invalid encoding from {username}", "WARNING")

                if message.lower() == "/quit":
                    conn.send(b"Goodbye!\n")
                    break

                if message.startswith("/admin"):
                    if auth.is_admin(username):
                        response = handle_admin_command(message[6:].strip())
                        conn.send(f"{response}\n".encode())
                    else:
                        conn.send(b"Permission denied.\n")
                    continue

                if session_manager.is_muted(username):
                    conn.send(b"You are muted.\n")
                    continue

                log_session(f"SENT - {username}: {message}")
                broadcast_to_all(username, message)

            except (ConnectionResetError, socket.timeout):
                break
            except Exception as e:
                log_session(f"Error with {username}: {str(e)}", "ERROR")
                break

    except Exception as e:
        log_session(f"Client error: {str(e)}", "ERROR")
    finally:
        if username:
            session_manager.remove_user(username)
            broadcast_to_all("Server", f"{username} left the chat.")
        conn.close()

def accept_connections():
    while True:
        try:
            conn, addr = server_socket.accept()
            log_session(f"Connection from {addr[0]}", "DEBUG")
            threading.Thread(
                target=client_thread,
                args=(conn, addr),
                daemon=True
            ).start()
        except OSError:
            break  # Server shutdown

try:
    accept_connections()
except KeyboardInterrupt:
    print("\n[!] Server shutting down...")
    log_session("Server stopped by admin")
    server_socket.close()