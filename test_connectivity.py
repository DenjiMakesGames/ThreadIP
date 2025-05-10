# test_connectivity.py
import socket
def test_connection(ip, port):
    try:
        with socket.create_connection((ip, port), timeout=5):
            return "✅ Success"
    except Exception as e:
        return f"❌ Failed: {str(e)}"

print(test_connection("your_public_ip", 5000))