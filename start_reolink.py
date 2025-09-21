#!/usr/bin/env bash
CAM_IPS=("192.168.86.27" "192.168.86.24")   # try both if your doorbell reports two IPs
RTSP_PATH="h264Preview_01_main"
USER="admin"
PASS="soup8080"                              # URL-encode if it ever has @ : / etc.
RETRY_INTERVAL

LOG="$HOME/reolink_autostart.log"

echo "$(date) boot: waiting for Wi-Fi + route�" >> "$LOG"

exho "waiting for wifi"

# Wait for wlan0 to have IPv4 and SSID
for i in {1..60}; do
  ip -4 addr show wlan0 | grep -q 'inet ' && [ -n "$(iwgetid -r)" ] && break
  sleep 2
done

# Wait for default route
for i in {1..30}; do
  ip route | grep -q '^default ' && break
  sleep 1
done

# Pick the first camera IP that answers on 554
CAM_IP=""
for ip in "${CAM_IPS[@]}"; do
  if nc -z -w1 "$ip" 554 2>/dev/null; then CAM_IP="$ip"; break; fi
done

if [ -z "$CAM_IP" ]; then
  echo "$(date) no camera answering on 554; will still try VLC loop�" >> "$LOG"
fi

URL="rtsp://${USER}:${PASS}@${CAM_IP:-${CAM_IPS[0]}}:554/${RTSP_PATH}"

# Run VLC in a retry loop so it recovers from drops
while true; do
  echo "$(date) launching VLC ? $URL" >> "$LOG"
  cvlc --fullscreen --no-video-title-show --network-caching=300 "$URL"
  echo "$(date) VLC exited; retrying in 5s�" >> "$LOG"
  sleep RETRY_INTERVAL
done
