#!/bin/sh
# Local images only. This script never pushes or creates a release.
set -eu
cd "$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
command -v docker >/dev/null
docker compose version >/dev/null
python3 tests/test-timelapse.py
python3 tests/test-timelapse-transfer.py
docker build -f core/Dockerfile -t nkl/restreamer-core:timelapse-local core
docker build -f ui/Dockerfile -t nkl/restreamer-ui:timelapse-local ui
docker build -f bundle/Dockerfile \
  --build-arg FFMPEG_IMAGE=ghcr.io/glatzkopf94/restreamer-nistkastenlivestream:0.3.0-dev21 \
  --build-arg CORE_IMAGE=nkl/restreamer-core:timelapse-local \
  --build-arg RESTREAMER_UI_IMAGE=nkl/restreamer-ui:timelapse-local \
  -t nkl/restreamer:timelapse-local .
echo 'Lokales Testimage fertig. Start: docker compose -f compose.timelapse-local.yaml up -d'
