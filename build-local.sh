#!/bin/sh

set -eu

project_dir="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
cd "$project_dir"

if [ "$(id -u)" -ne 0 ]; then
    echo "Bitte als root ausfuehren: sudo ./build-local.sh" >&2
    exit 1
fi

case "$(uname -m)" in
    x86_64|aarch64|arm64) ;;
    *)
        echo "Lokaler Build erfordert x86_64 oder ein 64-Bit-ARM-System; erkannt: $(uname -m)" >&2
        exit 1
        ;;
esac

command -v docker >/dev/null 2>&1 || {
    echo "Docker wurde nicht gefunden." >&2
    exit 1
}
command -v curl >/dev/null 2>&1 || {
    echo "curl wurde nicht gefunden." >&2
    exit 1
}
docker info >/dev/null
docker compose version >/dev/null

if [ ! -f .env ]; then
    cp .env.example .env
fi
chmod 0600 .env

if grep -Eq '^RESTREAMER_(PROJECT_NAME|CONTAINER_NAME)=restreamer([[:space:]]*)$' .env || \
   grep -Eq '^RESTREAMER_CONFIG_VOLUME=restreamer-config([[:space:]]*)$' .env || \
   grep -Eq '^RESTREAMER_DATA_VOLUME=restreamer-data([[:space:]]*)$' .env; then
    echo "Abbruch: Name oder Volume der offiziellen Restreamer-Instanz ist reserviert." >&2
    echo "Bitte die RESTREAMER_*-Werte in .env getrennt benennen." >&2
    exit 1
fi

release_image="$(docker compose -f compose.yaml config --images | head -n 1)"
if [ -z "$release_image" ]; then
    echo "Der Imagename konnte nicht aus compose.yaml ermittelt werden." >&2
    exit 1
fi
case "$release_image" in
    datarhei/restreamer|datarhei/restreamer:*)
        echo "Abbruch: Das offizielle datarhei/restreamer-Image darf nicht ueberschrieben werden." >&2
        exit 1
        ;;
esac

config_volume="$(sed -n 's/^RESTREAMER_CONFIG_VOLUME=//p' .env | tail -n 1)"
config_volume="${config_volume:-restreamer-nkl-config}"
data_volume="$(sed -n 's/^RESTREAMER_DATA_VOLUME=//p' .env | tail -n 1)"
data_volume="${data_volume:-restreamer-nkl-data}"

docker volume inspect "$config_volume" >/dev/null 2>&1 || \
    docker volume create --name "$config_volume" >/dev/null
docker volume inspect "$data_volume" >/dev/null 2>&1 || \
    docker volume create --name "$data_volume" >/dev/null

mkdir -p backups
timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
existing_container="$(docker compose -f compose.yaml ps --all -q restreamer-nkl 2>/dev/null || true)"

if [ -n "$existing_container" ]; then
    config_source="$(docker inspect "$existing_container" --format '{{range .Mounts}}{{if eq .Destination "/core/config"}}{{.Source}}{{end}}{{end}}')"
    if [ -n "$config_source" ] && [ -d "$config_source" ]; then
        tar -C "$config_source" -czf "backups/restreamer-config-${timestamp}.tar.gz" .
        chmod 0600 "backups/restreamer-config-${timestamp}.tar.gz"
        echo "Konfiguration gesichert: backups/restreamer-config-${timestamp}.tar.gz"
    fi
    docker compose -f compose.yaml down
fi

echo "[1/5] FFmpeg 9.0.1 mit Restreamer-Patches bauen"
docker build --pull --tag nkl/ffmpeg:9.0.1 ffmpeg

echo "[2/5] Restreamer Core bauen"
docker build --pull --tag nkl/restreamer-core:0.3.0-dev29 core

echo "[3/5] Restreamer UI bauen"
docker build --pull --tag nkl/restreamer-ui:0.3.0-dev29 ui

echo "[4/5] Release-Image zusammensetzen"
docker build \
    --file bundle/Dockerfile \
    --build-arg FFMPEG_IMAGE=nkl/ffmpeg:9.0.1 \
    --build-arg CORE_IMAGE=nkl/restreamer-core:0.3.0-dev29 \
    --build-arg RESTREAMER_UI_IMAGE=nkl/restreamer-ui:0.3.0-dev29 \
    --tag "$release_image" \
    .

echo "[5/5] Eigenstaendige Instanz starten und pruefen"
docker compose -f compose.yaml up --detach

http_port="$(sed -n 's/^RESTREAMER_HTTP_PORT=//p' .env | tail -n 1)"
http_port="${http_port:-9080}"
case "$http_port" in
    ''|*[!0-9]*)
        echo "Ungueltiger RESTREAMER_HTTP_PORT in .env" >&2
        exit 1
        ;;
esac

attempt=0
until curl --fail --silent "http://127.0.0.1:${http_port}/" >/dev/null 2>&1; do
    attempt=$((attempt + 1))
    if [ "$attempt" -ge 40 ]; then
        echo "Die Instanz antwortet nicht. Diagnose:" >&2
        docker compose -f compose.yaml ps >&2
        container_id="$(docker compose -f compose.yaml ps -q restreamer-nkl 2>/dev/null || true)"
        if [ -n "$container_id" ]; then
            docker logs --tail 120 "$container_id" >&2
        fi
        exit 1
    fi
    sleep 2
done

./tests/smoke-test.sh

echo
echo "Restreamer Nistkasten Livestream 0.3.0-dev29 wurde lokal gebaut und laeuft auf http://127.0.0.1:${http_port}"
echo "Ein vorhandener offizieller Container namens 'restreamer' wurde nicht veraendert."
