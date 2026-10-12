#!/bin/sh

set -eu

project_dir="${1:-}"
data_dir="${2:-}"
repository="glatzkopf94/vortex"
image_repository="ghcr.io/glatzkopf94/restreamer-nistkastenlivestream"
release_api="https://api.github.com/repos/${repository}/releases/latest"

if [ -z "$project_dir" ] || [ -z "$data_dir" ] || [ ! -f "$project_dir/compose.yaml" ] || [ ! -f "$project_dir/.env" ]; then
    echo "NKL-Updater: ungueltiges Projekt- oder Datenverzeichnis" >&2
    exit 1
fi

update_dir="$data_dir/nkl-update"
requests_dir="$update_dir/requests"
responses_dir="$update_dir/responses"
lock_dir="$update_dir/agent.lock"
mkdir -p "$requests_dir" "$responses_dir"

if ! mkdir "$lock_dir" 2>/dev/null; then
    echo "NKL-Updater: Eine Aktualisierung laeuft bereits." >&2
    exit 0
fi

temporary_dir=""
request_path=""
request_id=""
response_written=false
env_backup=""
env_changed=false
failure_code="update-failed"

json_response() {
    ok="$1"
    code="$2"
    version="$3"
    response_tmp="$responses_dir/.${request_id}.json.tmp.$$"
    printf '{"ok":%s,"requestId":"%s","version":"%s","error":"%s"}\n' \
        "$ok" "$request_id" "$version" "$code" > "$response_tmp"
    chmod 0600 "$response_tmp"
    mv "$response_tmp" "$responses_dir/$request_id.json"
    response_written=true
}

cleanup() {
    status="$?"
    trap - EXIT HUP INT TERM

    if [ "$status" -ne 0 ] && [ "$env_changed" = true ] && [ -n "$env_backup" ] && [ -f "$env_backup" ]; then
        cp "$env_backup" "$project_dir/.env"
        chmod 0600 "$project_dir/.env"
        docker compose -f "$project_dir/compose.yaml" --project-directory "$project_dir" up --detach --remove-orphans >/dev/null 2>&1 || true
    fi

    if [ "$status" -ne 0 ] && [ -n "$request_id" ] && [ "$response_written" = false ]; then
        json_response false "$failure_code" ""
    fi

    if [ -n "$request_path" ]; then
        rm -f "$request_path"
    fi
    if [ -n "$temporary_dir" ] && [ -d "$temporary_dir" ]; then
        find "$temporary_dir" -mindepth 1 -delete
        rmdir "$temporary_dir" 2>/dev/null || true
    fi
    rmdir "$lock_dir" 2>/dev/null || true
    exit "$status"
}
trap cleanup EXIT HUP INT TERM

set -- "$requests_dir"/*.json
if [ ! -f "$1" ]; then
    exit 0
fi
request_path="$1"
request_id="$(basename "$request_path" .json)"

if ! printf '%s\n' "$request_id" | grep -Eq '^[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$'; then
    failure_code="invalid-request-id"
    exit 1
fi
if [ "$(wc -c < "$request_path")" -gt 16384 ] || \
   ! grep -Fq '"action":"install-latest-nkl-release"' "$request_path" || \
   ! grep -Fq "\"requestId\":\"$request_id\"" "$request_path"; then
    failure_code="invalid-request"
    exit 1
fi

expected_version="$(sed -n 's/.*"expectedVersion":"\([^"]*\)".*/\1/p' "$request_path" | head -n 1)"
case "$expected_version" in
    ''|*[!0-9A-Za-z._-]*)
        failure_code="invalid-expected-version"
        exit 1
        ;;
esac

temporary_dir="$(mktemp -d /tmp/nkl-restreamer-update.XXXXXX)"
release_json="$temporary_dir/release.json"
curl --fail --silent --show-error --location \
    --header 'Accept: application/vnd.github+json' \
    --header 'User-Agent: NKL-Restreamer-Update-Agent' \
    "$release_api" > "$release_json"

# GitHub usually pretty-prints API responses, but proxies are allowed to
# compact the JSON onto one line. Match tag_name wherever it occurs on the
# line instead of requiring it to be the first JSON member on that line.
latest_version="$(sed -n 's/.*"tag_name"[[:space:]]*:[[:space:]]*"v\([^"]*\)".*/\1/p' "$release_json" | head -n 1)"
case "$latest_version" in
    ''|*[!0-9A-Za-z._-]*)
        failure_code="invalid-release-version"
        exit 1
        ;;
esac
if [ "$latest_version" != "$expected_version" ]; then
    failure_code="release-changed-recheck-required"
    exit 1
fi

configured_image="$(sed -n 's/^RESTREAMER_IMAGE=//p' "$project_dir/.env" | tail -n 1)"
case "$configured_image" in
    "$image_repository":*) current_version="${configured_image#*:}" ;;
    *)
        failure_code="foreign-image-blocked"
        exit 1
        ;;
esac

newest_version="$(printf '%s\n%s\n' "$current_version" "$latest_version" | sort -V | tail -n 1)"
if [ "$current_version" = "$latest_version" ] || [ "$newest_version" = "$current_version" ]; then
    json_response true "" "$current_version"
    exit 0
fi

archive_name="restreamer-nistkastenlivestream-${latest_version}.zip"
download_base="https://github.com/${repository}/releases/download/v${latest_version}"
curl --fail --silent --show-error --location "$download_base/$archive_name" --output "$temporary_dir/$archive_name"
curl --fail --silent --show-error --location "$download_base/$archive_name.sha256" --output "$temporary_dir/$archive_name.sha256"
(cd "$temporary_dir" && sha256sum --check "$archive_name.sha256")
unzip -q "$temporary_dir/$archive_name" -d "$temporary_dir/package"

stage_dir="$temporary_dir/package/restreamer-nistkastenlivestream-${latest_version}"
if [ ! -f "$stage_dir/release.env" ] || \
   ! grep -Fxq "RELEASE_VERSION=$latest_version" "$stage_dir/release.env" || \
   ! grep -Fxq "GHCR_IMAGE=$image_repository" "$stage_dir/release.env" || \
   [ ! -x "$stage_dir/install.sh" ] || \
   [ ! -f "$stage_dir/scripts/nkl-update-agent.sh" ]; then
    failure_code="invalid-release-package"
    exit 1
fi

echo "NKL-Updater: Lade Image $image_repository:$latest_version"
docker pull "$image_repository:$latest_version"

config_volume="$(sed -n 's/^RESTREAMER_CONFIG_VOLUME=//p' "$project_dir/.env" | tail -n 1)"
config_volume="${config_volume:-restreamer-nkl-config}"
data_volume="$(sed -n 's/^RESTREAMER_DATA_VOLUME=//p' "$project_dir/.env" | tail -n 1)"
data_volume="${data_volume:-restreamer-nkl-data}"
container_id="$(docker compose -f "$project_dir/compose.yaml" --project-directory "$project_dir" ps -q restreamer-nkl)"
if [ -z "$container_id" ] || \
   [ "$(docker inspect "$container_id" --format '{{range .Mounts}}{{if eq .Destination "/core/data"}}{{.Name}}{{end}}{{end}}')" != "$data_volume" ] || \
   [ "$(docker volume inspect "$data_volume" --format '{{ .Mountpoint }}')" != "$data_dir" ]; then
    failure_code="instance-mismatch"
    exit 1
fi
config_mount="$(docker volume inspect "$config_volume" --format '{{ .Mountpoint }}')"
if [ -z "$config_mount" ] || [ ! -d "$config_mount" ]; then
    failure_code="config-volume-not-found"
    exit 1
fi
mkdir -p "$project_dir/backups"
timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
tar -C "$config_mount" -czf "$project_dir/backups/restreamer-config-before-${latest_version}-${timestamp}.tar.gz" .
chmod 0600 "$project_dir/backups/restreamer-config-before-${latest_version}-${timestamp}.tar.gz"

env_backup="$temporary_dir/original.env"
cp "$project_dir/.env" "$env_backup"

for item in \
    .env.example release.env compose.yaml install.sh status.sh uninstall.sh \
    RELEASE_INSTALL.md LICENSE NOTICE THIRD_PARTY_NOTICES.md scripts systemd tests; do
    if [ -e "$stage_dir/$item" ]; then
        cp -a "$stage_dir/$item" "$project_dir/"
    fi
done

agent_tmp="/usr/local/sbin/.nkl-restreamer-update-agent.$$"
cp "$stage_dir/scripts/nkl-update-agent.sh" "$agent_tmp"
chmod 0700 "$agent_tmp"
mv "$agent_tmp" /usr/local/sbin/nkl-restreamer-update-agent

env_tmp="$project_dir/.env.tmp.$$"
awk -v image="$image_repository:$latest_version" '
    BEGIN { replaced = 0 }
    /^RESTREAMER_IMAGE=/ {
        if (!replaced) {
            print "RESTREAMER_IMAGE=" image
            replaced = 1
        }
        next
    }
    { print }
    END { if (!replaced) print "RESTREAMER_IMAGE=" image }
' "$project_dir/.env" > "$env_tmp"
chmod 0600 "$env_tmp"
mv "$env_tmp" "$project_dir/.env"
env_changed=true

docker compose -f "$project_dir/compose.yaml" --project-directory "$project_dir" up --detach --remove-orphans

http_port="$(sed -n 's/^RESTREAMER_HTTP_PORT=//p' "$project_dir/.env" | tail -n 1)"
http_port="${http_port:-9080}"
attempt=0
until curl --fail --silent "http://127.0.0.1:${http_port}/" >/dev/null 2>&1; do
    attempt=$((attempt + 1))
    if [ "$attempt" -ge 90 ]; then
        failure_code="health-check-failed"
        exit 1
    fi
    sleep 2
done

"$project_dir/tests/smoke-test.sh"
env_changed=false
json_response true "" "$latest_version"
echo "NKL-Updater: Aktualisierung auf $latest_version erfolgreich."
