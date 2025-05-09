import psutil
import threading
import time

# Function to monitor system usage (CPU, RAM)
def monitor_server():
    while True:
        # Get CPU and memory usage
        cpu_usage = psutil.cpu_percent(interval=1)  # CPU usage in percentage
        memory_info = psutil.virtual_memory()
        memory_usage = memory_info.percent  # Memory usage in percentage
        
        # Print or log the statistics
        print(f"CPU Usage: {cpu_usage}% | RAM Usage: {memory_usage}%")
        
        # You could also log this information to a file
        with open("Database/server_stats.log", "a") as log_file:
            log_file.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - CPU: {cpu_usage}% | RAM: {memory_usage}%\n")
        
        # Sleep for a while before checking again (e.g., 5 seconds)
        time.sleep(5)

# Start the monitoring thread
def start_monitoring():
    monitoring_thread = threading.Thread(target=monitor_server)
    monitoring_thread.daemon = True  # So it stops when the server stops
    monitoring_thread.start()
