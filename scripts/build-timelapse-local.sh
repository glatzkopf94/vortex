#!/bin/sh
# Local images only. This script never pushes or creates a release.
set -eu
cd "$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
command -v docker >/dev/null
docker compose version >/dev/null
python3 tests/test-timelapse.py
python3 tests/test-timelapse-transfer.py
python3 tests/test-ftps-trust.py
python3 tests/test-ftps-session.py
python3 tests/test-timelapse-combined.py
python3 tests/test-timelapse-player-overlay.py
image_prefix=${VORTEX_UID_BUILD_PREFIX:-nkl/restreamer}
image=${VORTEX_UID_IMAGE:-nkl/restreamer:timelapse-local}
docker build -f core/Dockerfile -t "${image_prefix}-core:timelapse-local" core
docker build -f ui/Dockerfile -t "${image_prefix}-ui:timelapse-local" ui
docker build -f bundle/Dockerfile \
  --build-arg FFMPEG_IMAGE=ghcr.io/glatzkopf94/restreamer-nistkastenlivestream:0.3.0-dev21 \
  --build-arg CORE_IMAGE="${image_prefix}-core:timelapse-local" \
  --build-arg RESTREAMER_UI_IMAGE="${image_prefix}-ui:timelapse-local" \
  -t "$image" .
echo 'Lokales Testimage fertig. Start: docker compose -f compose.timelapse-local.yaml up -d'
