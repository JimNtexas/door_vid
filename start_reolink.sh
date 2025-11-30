#!/usr/bin/env bash

# This script is a launcher for the more robust Python script.
# Configure settings via environment variables, not by editing this file.

# --- Environment Variables ---
# Set these in your environment (e.g., in /etc/environment or a systemd service file)
#
# export REOLINK_IPS="192.168.86.27,192.168.86.24"
# export REOLINK_RTSP_PATH="h264Preview_01_main"
# export REOLINK_USER="admin"
# export REOLINK_PASS="XXXXX"
# export REOLINK_LOG="~/reolink_autostart.log"
# export REOLINK_FULLSCREEN="1"
# export REOLINK_VLC_ARGS="--avcodec-hw=drm_prime" # Example for Pi

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

# Path to the Python script
PYTHON_SCRIPT="$SCRIPT_DIR/start_reolink.py"

echo "$(date) - Starting Reolink VLC stream..."

# Check if the Python script exists
if [ ! -f "$PYTHON_SCRIPT" ]; then
    echo "$(date) - ERROR: Python script not found at $PYTHON_SCRIPT" >&2
    exit 1
fi

# Run the Python script
# The Python script handles logging, network checks, and VLC process management.
"$PYTHON_SCRIPT"