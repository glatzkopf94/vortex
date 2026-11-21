#!/bin/sh
# Only the Core's standard JPEG snapshot command enters Python.
case "$*" in
  *'-vframes 1'*'-f image2'*'-update 1'*) exec python3 /core/bin/timelapse/snapshot_overlay.py "$@" ;;
  *hls_max_window_duration*) exec python3 /core/bin/timelapse/snapshot_overlay.py --dvr-start "$@" ;;
  *) exec /usr/bin/ffmpeg-vortex-real "$@" ;;
esac
