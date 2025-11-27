#!/bin/bash
# system_helper.sh — helper for Lofi Dashboard controls
# Called via sudo from dashboard.py

ACTION="$1"

case "$ACTION" in
  reboot)
    echo "System reboot requested by dashboard."
    /usr/sbin/reboot
    ;;

  camera_restart)
    echo "Clearing camera locks (ffmpeg/libcamera/picamera2)..."

    # Kill any processes using camera device nodes
    PIDS=$(lsof /dev/media* /dev/video* /dev/v4l-subdev* 2>/dev/null | awk 'NR>1 {print $2}' | sort -u)

    if [ -n "$PIDS" ]; then
      echo "Killing PIDs: $PIDS"
      kill $PIDS 2>/dev/null || true
      sleep 1
      kill -9 $PIDS 2>/dev/null || true
    else
      echo "No camera lock processes found via lsof."
    fi

    # Also kill any obvious leftovers
    pkill -f libcamera 2>/dev/null || true
    pkill -f picamera2 2>/dev/null || true
    pkill -f ffmpeg 2>/dev/null || true

    echo "Camera lock clear attempt complete."
    ;;

  *)
    echo "Unknown action: $ACTION"
    exit 1
    ;;
esac

exit 0
