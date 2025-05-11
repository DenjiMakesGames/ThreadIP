# debug_console.py
from queue import Queue
from main_server import debug_queue
import time

print("=== DEBUG CONSOLE ===")
print("(Ctrl+C to close)\n")

try:
    while True:
        while not debug_queue.empty():
            print(debug_queue.get())
        time.sleep(0.1)
except KeyboardInterrupt:
    pass