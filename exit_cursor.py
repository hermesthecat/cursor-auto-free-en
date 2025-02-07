import psutil
from logger import logging  
import time

def ExitCursor(timeout=5):
    """
    Gracefully close Cursor processes
    
    Args:
        timeout (int): Timeout in seconds to wait for processes to terminate naturally
    Returns:
        bool: Whether all processes were successfully closed
    """
    try:
        logging.info("Starting to exit Cursor...")
        cursor_processes = []
        # Collect all Cursor processes
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                if proc.info['name'].lower() in ['cursor.exe', 'cursor']:
                    cursor_processes.append(proc)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        if not cursor_processes:
            logging.info("No running Cursor processes found")
            return True

        # Gracefully request process termination
        for proc in cursor_processes:
            try:
                if proc.is_running():
                    proc.terminate()  # Send termination signal
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        # Wait for processes to terminate naturally
        start_time = time.time()
        while time.time() - start_time < timeout:
            still_running = []
            for proc in cursor_processes:
                try:
                    if proc.is_running():
                        still_running.append(proc)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            if not still_running:
                logging.info("All Cursor processes have been closed normally")
                return True
                
            # Wait a short time before checking again
            time.sleep(0.5)
            
        # If processes are still running after timeout
        if still_running:
            process_list = ", ".join([str(p.pid) for p in still_running])
            logging.warning(f"The following processes did not close within the time limit: {process_list}")
            return False
            
        return True

    except Exception as e:
        logging.error(f"Error occurred while closing Cursor processes: {str(e)}")
        return False

if __name__ == "__main__":
    ExitCursor()
