import subprocess
import time
import sys
import logging
import os

# --- Configuration ---
CAM_IPS = ["192.168.86.27", "192.168.86.24"]
RTSP_PATH = "h264Preview_01_main"
USER = "admin"
PASS = "soup8080"
RETRY_INTERVAL = 5 # seconds
LOG_FILE = os.path.expanduser("~/reolink_autostart.log")

# --- Logging Setup ---
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# --- Main Logic ---
def get_camera_ip():
    """Finds the first reachable camera IP."""
    for ip in CAM_IPS:
        logging.info(f"Checking camera IP: {ip}")
        # -z: zero-I/O mode. -w1: wait 1 second for a connection.
        result = subprocess.run(['nc', '-z', '-w1', ip, '554'], capture_output=True)
        if result.returncode == 0:
            logging.info(f"Found camera at {ip}")
            return ip
    logging.warning("No camera found. Using the first IP in the list.")
    return CAM_IPS[0]

def main():
    """Main function to run and manage the video stream."""
    try:
        # Build the full RTSP URL
        camera_ip = get_camera_ip()
        url = f"rtsp://{USER}:{PASS}@{camera_ip}:554/{RTSP_PATH}"
        logging.info(f"Attempting to launch VLC for URL: {url}")
        
        while True:
            try:
                # Start VLC as a subprocess
                vlc_process = subprocess.Popen([
                    'cvlc',
                    '--fullscreen',
                    '--no-video-title-show',
                    '--network-caching=300',
                    '--no-xlib', # Prevents some X11 errors on headless systems
                    url
                ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                
                # Wait for the process to terminate.
                vlc_process.wait()
                
                # If we reach here, VLC has exited.
                logging.warning(f"VLC exited with return code: {vlc_process.returncode}. Restarting in {RETRY_INTERVAL} seconds.")
                time.sleep(RETRY_INTERVAL)

            except Exception as e:
                logging.error(f"An error occurred while running VLC: {e}")
                logging.info(f"Retrying in {RETRY_INTERVAL} seconds...")
                time.sleep(RETRY_INTERVAL)
                
    except KeyboardInterrupt:
        logging.info("Script terminated by user.")
    finally:
        # Clean up any remaining processes if needed
        if 'vlc_process' in locals() and vlc_process.poll() is None:
            vlc_process.kill()
        logging.info("Script finished.")

if __name__ == "__main__":
    main()