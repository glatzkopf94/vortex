#!/bin/sh

set -eu

project_dir="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
cd "$project_dir"

. ./release.env

fail() {
    echo "Release-Pruefung fehlgeschlagen: $1" >&2
    exit 1
}

case "$RELEASE_VERSION" in
    *[!A-Za-z0-9._-]*|"") fail "ungueltige RELEASE_VERSION" ;;
esac
case "$PRODUCT_VERSION" in
    *[!a-z0-9._-]*|"") fail "ungueltige PRODUCT_VERSION" ;;
esac
case "$GHCR_IMAGE" in
    ghcr.io/glatzkopf94/restreamer-nistkastenlivestream) ;;
    *) fail "unerwartetes GHCR_IMAGE" ;;
esac

grep -Fq "RESTREAMER_IMAGE=${GHCR_IMAGE}:${RELEASE_VERSION}" .env.example || \
    fail ".env.example verwendet nicht das Release-Image"
grep -Fq "${GHCR_IMAGE}:${RELEASE_VERSION}" compose.yaml || \
    fail "compose.yaml verwendet nicht das Release-Image"
grep -Fq "\"version\": \"${RELEASE_VERSION}\"" ui/package.json || \
    fail "UI-Version stimmt nicht"
grep -Fq "\"nklVersion\": \"${PRODUCT_LABEL#Vortex }\"" ui/package.json || \
    fail "NKL-Produktkennung stimmt nicht"
grep -Fq -- "--extra-version=nkl-restreamer-${RELEASE_VERSION}" ffmpeg/Dockerfile || \
    fail "FFmpeg-Kennung stimmt nicht"
grep -Fq "NKL_RELEASE_VERSION=${RELEASE_VERSION}" bundle/Dockerfile || \
    fail "NKL-Updatekennung im Image stimmt nicht"
grep -Fq 'api.github.com/repos/glatzkopf94/vortex/releases/latest' ui/src/version.js || \
    fail "UI prueft nicht das NKL-GitHub-Repository"
test -x scripts/nkl-update-agent.sh || fail "Host-Update-Agent ist nicht ausfuehrbar"
test -x scripts/migrate-timestamp-repair.py || fail "Timestamp-Migration ist nicht ausfuehrbar"
test -x scripts/migrate-player-cleanup.py || fail "Player-Cleanup-Migration ist nicht ausfuehrbar"
test -x scripts/migrate-dvr-retention.py || fail "DVR-Migration ist nicht ausfuehrbar"
grep -Fq 'nkl-hls-window-duration.patch' ffmpeg/Dockerfile || fail "FFmpeg-DVR-Zeitfenster fehlt"
grep -Fq 'migrate-dvr-retention.py' bundle/run.sh || fail "DVR-Startmigration fehlt"
grep -Fq 'fps=fps=${fps}:start_time=0:round=near' ui/src/misc/filters/video/Timestamps.js || \
    fail "zeitbasierte CFR-Reparatur fehlt"
grep -Fq 'migrate-timestamp-repair.py' bundle/run.sh || \
    fail "Startmigration fuer dev12-Profile fehlt"
grep -Fq 's/.*"tag_name"[[:space:]]*:' scripts/nkl-update-agent.sh || \
    fail "Update-Agent verarbeitet keine kompakte Release-JSON"
grep -Fq "options.method === 'HEAD'" ui/src/utils/api.js || \
    fail "UI behandelt bodylose HEAD-Antworten nicht"
grep -Fq 'RESTREAMER_CONTAINER_NAME=vortex' .env.example || \
    fail "Standard-Containername ist nicht vortex"
grep -Fq 'RESTREAMER_CONFIG_VOLUME=restreamer-nkl-config' .env.example || \
    fail "Standard-Konfigurationsvolume ist nicht restreamer-nkl-config"
grep -Fq 'RESTREAMER_DATA_VOLUME=restreamer-nkl-data' .env.example || \
    fail "Standard-Datenvolume ist nicht restreamer-nkl-data"
grep -Fq 'restreamer-livechasing-config restreamer-nkl-config' install.sh || \
    fail "Migration des bisherigen Konfigurationsvolumes fehlt"
grep -Fq 'restreamer-livechasing-data restreamer-nkl-data' install.sh || \
    fail "Migration des bisherigen Datenvolumes fehlt"
grep -Fq 'ubuntu-24.04-arm' .github/workflows/release.yml || \
    fail "nativer ARM64-Build fehlt"
grep -Fq 'verify-multiarch-manifest.py' .github/workflows/release.yml || \
    fail "Pruefung des Multiarch-Manifests fehlt"
grep -Fq 'aarch64|arm64' install.sh || \
    fail "ARM64-Installerfreigabe fehlt"

echo "Release-Pruefung erfolgreich: ${PRODUCT_LABEL} / ${RELEASE_VERSION}"
