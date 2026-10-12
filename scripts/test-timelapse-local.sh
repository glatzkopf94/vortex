#!/bin/sh
set -eu
project_dir="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
cd "$project_dir"
# Requires Go, Python, FFmpeg, Node, esbuild and Playwright/Chromium.
# NODE_PATH can point to an isolated npm prefix with React/MUI test dependencies.
python3 tests/test-timelapse.py
python3 tests/test-timelapse-transfer.py
node tests/test-player-behavior.js
node tests/test-timelapse-poster.cjs
work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT
(cd core && go test ./http/cache && go test ./http -run TestTimelapse && CGO_ENABLED=0 go build -buildvcs=false -o "$work/core" .)
mkdir "$work/ui"
printf '%s\n' '<!doctype html><html lang="de"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><div id="root"></div><script src="/ui/app.js"></script></html>' > "$work/ui/index.html"
"${NKL_ESBUILD:-esbuild}" tests/timelapse-admin-entry.jsx --bundle --loader:.js=jsx --outfile="$work/ui/app.js"
python3 tests/timelapse-local-fixture.py "$work/core" "$work/ui" --test
