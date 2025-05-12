# debug_console.py
import sys
from queue import Queue
from main_server import debug_queue

def debug_printer():
    print("=== SERVER DEBUG CONSOLE ===")
    print("(All server events will appear here)\n")
    try:
        while True:
            while not debug_queue.empty():
                message = debug_queue.get()
                print(message)
                sys.stdout.flush()  # Force immediate output
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\nClosing debug console...")

if __name__ == "__main__":
    import time
    debug_printer()