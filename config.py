# config.py (new file)
from queue import Queue

# Shared objects
debug_queue = Queue()
session_manager = None  # Will be initialized later

# Constants
DATABASE_FOLDER = "Database"
USER_STATUS_DB = f"{DATABASE_FOLDER}/user_status.db"
SESSION_LOG = f"{DATABASE_FOLDER}/session.log"
MESSAGE_LOG = f"{DATABASE_FOLDER}/messages.log"