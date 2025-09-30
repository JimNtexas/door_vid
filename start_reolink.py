#!/usr/bin/env python3
import os
import sys
import time
import socket
import signal
import logging
import subprocess
from logging.handlers import RotatingFileHandler

#9/29/2025
#git kinda messed up

# --- Configuration (prefer env vars) ---
CAM_IPS = os.getenv("REOLINK_IPS", "192.168.86.27,192.168.86.24").split(",")
RTSP_PATH = os.getenv("REOLINK_RTSP_PATH", "h264Preview_01_main")
USER = os.getenv("REOLINK_USER", "admin")
PASS = os.getenv("REOLINK_PASS", "CHANGE_ME")  # <-- set via env!
RTSP_PORT = int(os.getenv("REOLINK_RTSP_PORT", "554"))
NETWORK_CACHING_MS = int(os.getenv("REOLINK_CACHING_MS", "800"))  # 300–1000 typical
FULLSCREEN = os.getenv("REOLINK_FULLSCREEN", "1") == "1"
USE_RTSP_TCP = os.getenv("REOLINK_RTSP_TCP", "1") == "1"
EXTRA_VLC_ARGS = os.getenv("REOLINK_VLC_ARGS", "")  # e.g. "--avcodec-hw=drm_prime"
LOG_FILE = os.path.expanduser(os.getenv("REOLINK_LOG", "~/reolink_autostart.log"))
INITIAL_RETRY_DELAY = float(os.getenv("RETRY_DELAY_SEC", "3"))
MAX_RETRY_DELAY = float(os.getenv("MAX_RETRY_DELAY_SEC", "30"))
CHECK_INTERVAL = float(os.getenv("IP_CHECK_INTERVAL_SEC", "120"))  # re-check alternate IPs

# --- Logging Setup (rotate) ---
logger = logging.getLogger("reolink_vlc")
logger.setLevel(logging.INFO)
handler = RotatingFileHandler(LOG_FILE, maxBytes=2_000_000, backupCount=3)
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)

vlc_proc = None

def reachable(ip: str, port: int, timeout: float = 1.0) -> bool:
    try:
        with socket.create_connection((ip, port), timeout=timeout):
            return True
    except OSError:
        return False

def get_camera_ip() -> str:
    """Return first reachable IP; fallback to first in list."""
    for ip in CAM_IPS:
        ip = ip.strip()
        if not ip:
            continue
        logger.info(f"Checking camera IP: {ip}")
        if reachable(ip, RTSP_PORT, timeout=1.0):
            logger.info(f"Found camera at {ip}")
            return ip
    fallback = CAM_IPS[0].strip()
    logger.warning(f"No camera reachable. Falling back to {fallback}")
    return fallback

def build_vlc_cmd(url: str):
    args = [
        "cvlc",
        "--no-video-title-show",
        f"--network-caching={NETWORK_CACHING_MS}",
    ]
    if USE_RTSP_TCP:
        args.append("--rtsp-tcp")
    if FULLSCREEN:
        args.append("--fullscreen")
    # Some Pi setups benefit from these; harmless elsewhere if unsupported:
    # args += ["--avcodec-hw=drm_prime", "--no-drm-vblank"]

    if EXTRA_VLC_ARGS:
        args += EXTRA_VLC_ARGS.split()

    args.append(url)
    return args

def start_vlc(url: str) -> subprocess.Popen:
    logger.info(f"Launching VLC: {url}")
    # New session so we can kill the whole group on restart
    return subprocess.Popen(
        build_vlc_cmd(url),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )

def stop_vlc():
    global vlc_proc
    if vlc_proc and vlc_proc.poll() is None:
        logger.info("Stopping VLC process group…")
        try:
            os.killpg(vlc_proc.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        # Give it a moment, then hard-kill if needed
        try:
            vlc_proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            logger.warning("VLC didn’t exit on SIGTERM—sending SIGKILL")
            try:
                os.killpg(vlc_proc.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
    vlc_proc = None

def main():
    global vlc_proc
    backoff = INITIAL_RETRY_DELAY
    last_ip_check = 0.0
    current_ip = get_camera_ip()

    def _sigterm(_signo, _frame):
        logger.info("Received termination signal. Exiting.")
        stop_vlc()
        sys.exit(0)

    signal.signal(signal.SIGINT, _sigterm)
    signal.signal(signal.SIGTERM, _sigterm)

    while True:
        url = f"rtsp://{USER}:{PASS}@{current_ip}:{RTSP_PORT}/{RTSP_PATH}"

        try:
            vlc_proc = start_vlc(url)
            # Monitor loop
            while True:
                ret = vlc_proc.poll()
                now = time.time()

                # Periodically re-check if another IP in the list has become reachable.
                if now - last_ip_check > CHECK_INTERVAL:
                    last_ip_check = now
                    best_ip = get_camera_ip()
                    if best_ip != current_ip:
                        logger.info(f"Switching camera IP {current_ip} → {best_ip}")
                        current_ip = best_ip
                        stop_vlc()
                        break  # restart outer loop to relaunch with new IP

                if ret is not None:
                    logger.warning(f"VLC exited (code {ret}). Restarting in {backoff:.1f}s.")
                    time.sleep(backoff)
                    backoff = min(backoff * 1.6, MAX_RETRY_DELAY)
                    break  # restart outer loop

                # VLC still running
                time.sleep(1)

            # loop continues to relaunch
        except Exception as e:
            logger.exception(f"Unexpected error: {e}")
            logger.info(f"Retrying in {backoff:.1f}s…")
            time.sleep(backoff)
            backoff = min(backoff * 1.6, MAX_RETRY_DELAY)
        finally:
            stop_vlc()
            # If we got here due to IP switch, reset backoff
            backoff = INITIAL_RETRY_DELAY

if __name__ == "__main__":
    main()
