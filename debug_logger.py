# debug_logger.py
import os
import time

DEBUG_LOG = "Database/debug.log"

def tail_debug_log():
    print("Starting Debug Monitor...\n(Press CTRL+C to exit)\n")
    last_size = 0
    while True:
        try:
            if os.path.exists(DEBUG_LOG):
                with open(DEBUG_LOG, "r") as file:
                    file.seek(last_size)
                    new_data = file.read()
                    if new_data:
                        print(new_data, end="")
                    last_size = file.tell()
            time.sleep(1)
        except KeyboardInterrupt:
            print("\nDebug Monitor Closed.")
            break
