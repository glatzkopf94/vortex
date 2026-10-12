#!/bin/sh

set -eu

project_dir="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
cd "$project_dir"

. ./release.env
release_version="$RELEASE_VERSION"
default_image="${GHCR_IMAGE}:${release_version}"

if [ "$(id -u)" -ne 0 ]; then
    echo "Bitte als root ausfuehren: sudo ./install.sh" >&2
    exit 1
fi

case "$(uname -m)" in
    x86_64|aarch64|arm64) ;;
    armv7l|armv6l)
        echo "Dieses Image benoetigt ein 64-Bit-Betriebssystem (ARM64 oder AMD64)." >&2
        exit 1
        ;;
    *)
        echo "Nicht unterstuetzte Architektur: $(uname -m) (erlaubt: x86_64, aarch64)." >&2
        exit 1
        ;;
esac

for command_name in docker curl tar unzip sha256sum; do
    command -v "$command_name" >/dev/null 2>&1 || {
        echo "$command_name wurde nicht gefunden." >&2
        exit 1
    }
done
docker info >/dev/null
docker compose version >/dev/null

if [ ! -f .env ]; then
    migrated_env=""
    for candidate in \
        ../restreamer-nistkastenlivestream-0.3.0-dev22/.env \
        ../restreamer-nistkastenlivestream-0.3.0-dev21/.env \
        ../restreamer-nistkastenlivestream-0.3.0-dev20/.env \
        ../restreamer-nistkastenlivestream-0.3.0-dev19/.env \
        ../restreamer-nistkastenlivestream-0.3.0-dev18/.env \
        ../restreamer-nistkastenlivestream-0.3.0-dev17/.env \
        ../restreamer-nistkastenlivestream-0.3.0-dev16/.env \
        ../restreamer-nistkastenlivestream-0.3.0-dev15/.env \
        ../restreamer-nistkastenlivestream-0.3.0-dev14/.env \
        ../restreamer-nistkastenlivestream-0.3.0-dev13/.env \
        ../restreamer-nistkastenlivestream-0.3.0-dev12/.env \
        ../restreamer-nistkastenlivestream-0.3.0-dev11/.env \
        ../restreamer-nistkastenlivestream-0.3.0-dev10/.env \
        ../restreamer-livechasing-0.3.0-dev10/.env \
        ../restreamer-livechasing-0.3.0-dev9/.env; do
        if [ -f "$candidate" ]; then
            cp "$candidate" .env
            migrated_env="$candidate"
            break
        fi
    done
    if [ -n "$migrated_env" ]; then
        echo "Vorhandene Einstellungen uebernommen: $migrated_env"
    else
        cp .env.example .env
    fi
fi
chmod 0600 .env

env_backup=".env.before-${release_version}"
cp -a .env "$env_backup"
chmod 0600 "$env_backup"
install_committed=false
container_change_started=false
legacy_container=false
legacy_config_volume=""
legacy_data_volume=""
legacy_container_was_running=false

rollback_install() {
    status="$?"
    trap - EXIT HUP INT TERM

    if [ "$status" -ne 0 ] && [ "$install_committed" = false ]; then
        cp -a "$env_backup" .env
        chmod 0600 .env

        if [ "$container_change_started" = true ]; then
            echo "Installation fehlgeschlagen; bisherige .env und Containerfassung werden wiederhergestellt." >&2
            docker compose -f compose.yaml down >/dev/null 2>&1 || true
            if [ "$legacy_container_was_running" = true ]; then
                docker start restreamer-livechasing >/dev/null 2>&1 || true
            else
                docker compose -f compose.yaml up --detach --remove-orphans >/dev/null 2>&1 || true
            fi
        fi
    fi

    if [ "$status" -eq 0 ]; then
        rm -f "$env_backup"
    fi
    exit "$status"
}
trap rollback_install EXIT HUP INT TERM

replace_env_default() {
    key="$1"
    old_value="$2"
    new_value="$3"
    current_value="$(sed -n "s/^${key}=//p" .env | tail -n 1)"
    if [ "$current_value" != "$old_value" ]; then
        return 1
    fi

    env_tmp=".env.tmp.$$"
    awk -v key="$key" -v value="$new_value" '
        index($0, key "=") == 1 { print key "=" value; next }
        { print }
    ' .env > "$env_tmp"
    chmod 0600 "$env_tmp"
    mv "$env_tmp" .env
    return 0
}

replace_env_default RESTREAMER_PROJECT_NAME restreamer-livechasing restreamer-nkl || true
if replace_env_default RESTREAMER_CONTAINER_NAME restreamer-livechasing vortex; then
    legacy_container=true
fi
if replace_env_default RESTREAMER_CONFIG_VOLUME restreamer-livechasing-config restreamer-nkl-config; then
    legacy_config_volume=restreamer-livechasing-config
elif replace_env_default RESTREAMER_CONFIG_VOLUME restreamer-dev-config restreamer-nkl-config; then
    legacy_config_volume=restreamer-dev-config
fi
if replace_env_default RESTREAMER_DATA_VOLUME restreamer-livechasing-data restreamer-nkl-data; then
    legacy_data_volume=restreamer-livechasing-data
elif replace_env_default RESTREAMER_DATA_VOLUME restreamer-dev-data restreamer-nkl-data; then
    legacy_data_volume=restreamer-dev-data
fi

# Bekannte lokale Entwicklungsimages automatisch auf das fertige GHCR-Image
# umstellen. Eine bewusst eingetragene andere Registry bleibt unangetastet.
configured_image="$(sed -n 's/^RESTREAMER_IMAGE=//p' .env | tail -n 1)"
replace_image=false
case "$configured_image" in
    ""|livechasing/restreamer:*)
        replace_image=true
        ;;
    ghcr.io/glatzkopf94/restreamer-nistkastenlivestream:*)
        configured_version="${configured_image##*:}"
        newest_version="$(printf '%s\n%s\n' "$configured_version" "$release_version" | sort -V | tail -n 1)"
        if [ "$newest_version" = "$release_version" ] && [ "$configured_version" != "$release_version" ]; then
            replace_image=true
        else
            echo "Vorhandenes NKL-Image bleibt aktiv: $configured_image"
        fi
        ;;
    *)
        echo "Benutzerdefiniertes Image bleibt aktiv: $configured_image"
        ;;
esac

if [ "$replace_image" = true ]; then
        env_tmp=".env.tmp.$$"
        awk -v image="$default_image" '
            BEGIN { replaced = 0 }
            /^RESTREAMER_IMAGE=/ {
                if (!replaced) {
                    print "RESTREAMER_IMAGE=" image
                    replaced = 1
                }
                next
            }
            { print }
            END {
                if (!replaced) print "RESTREAMER_IMAGE=" image
            }
        ' .env > "$env_tmp"
        chmod 0600 "$env_tmp"
        mv "$env_tmp" .env
fi

if grep -Eq '^RESTREAMER_(PROJECT_NAME|CONTAINER_NAME)=restreamer([[:space:]]*)$' .env || \
   grep -Eq '^RESTREAMER_CONFIG_VOLUME=restreamer-config([[:space:]]*)$' .env || \
   grep -Eq '^RESTREAMER_DATA_VOLUME=restreamer-data([[:space:]]*)$' .env; then
    echo "Abbruch: Name oder Volume der offiziellen Restreamer-Instanz ist reserviert." >&2
    echo "Bitte die RESTREAMER_*-Werte in .env getrennt benennen." >&2
    exit 1
fi

# Never replace an existing official datarhei container, regardless of its
# name (for example restreamer-rpi on a Raspberry Pi).
target_container="$(sed -n 's/^RESTREAMER_CONTAINER_NAME=//p' .env | tail -n 1)"
target_container="${target_container:-vortex}"
if docker container inspect "$target_container" >/dev/null 2>&1; then
    existing_image="$(docker inspect "$target_container" --format '{{.Config.Image}}')"
    case "$existing_image" in
        datarhei/restreamer|datarhei/restreamer:*)
            echo "Abbruch: Der offizielle Container $target_container ($existing_image) bleibt unveraendert." >&2
            exit 1
            ;;
    esac
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

install_update_agent() {
    if ! command -v systemctl >/dev/null 2>&1; then
        echo "Hinweis: systemd fehlt; Updates koennen weiterhin mit ./install.sh installiert werden." >&2
        return 0
    fi

    data_mount="$(docker volume inspect "$data_volume" --format '{{ .Mountpoint }}')"
    installed_container="$(docker compose -f compose.yaml ps -q restreamer-nkl)"
    if [ -z "$installed_container" ] || \
       [ "$(docker inspect "$installed_container" --format '{{range .Mounts}}{{if eq .Destination "/core/data"}}{{.Name}}{{end}}{{end}}')" != "$data_volume" ]; then
        echo "Abbruch: Der laufende Compose-Container verwendet nicht das konfigurierte NKL-Datenvolume." >&2
        return 1
    fi
    for safe_path in "$project_dir" "$data_mount"; do
        case "$safe_path" in
            ''|*[!A-Za-z0-9_./-]*)
                echo "Hinweis: Der UI-Updater wurde wegen eines ungeeigneten Pfads nicht aktiviert: $safe_path" >&2
                return 0
                ;;
        esac
    done

    update_root="$data_mount/nkl-update"
    mkdir -p "$update_root/requests" "$update_root/responses"
    chmod 0700 "$update_root" "$update_root/requests" "$update_root/responses"

    install -m 0700 scripts/nkl-update-agent.sh /usr/local/sbin/nkl-restreamer-update-agent

    service_tmp="$(mktemp)"
    path_tmp="$(mktemp)"
    sed \
        -e "s|@PROJECT_DIR@|$project_dir|g" \
        -e "s|@DATA_DIR@|$data_mount|g" \
        systemd/nkl-restreamer-update.service.in > "$service_tmp"
    sed \
        -e "s|@DATA_DIR@|$data_mount|g" \
        systemd/nkl-restreamer-update.path.in > "$path_tmp"
    install -m 0644 "$service_tmp" /etc/systemd/system/nkl-restreamer-update.service
    install -m 0644 "$path_tmp" /etc/systemd/system/nkl-restreamer-update.path
    rm -f "$service_tmp" "$path_tmp"

    # A running path unit retains the old watch directory across daemon-reload.
    # Restart it when an earlier installation watched another NKL volume.
    systemctl daemon-reload
    systemctl stop nkl-restreamer-update.path
    systemctl enable --now nkl-restreamer-update.path
    systemctl is-active --quiet nkl-restreamer-update.path
    printf '{"available":true,"protocol":1,"repository":"glatzkopf94/vortex"}\n' > "$update_root/agent.json"
    chmod 0644 "$update_root/agent.json"
    echo "Sichere Aktualisierung aus dem NKL-Webinterface ist aktiviert."
}

echo "[1/4] Fertiges Release-Image laden: $release_image"
if ! docker compose -f compose.yaml pull restreamer-nkl; then
    echo >&2
    echo "Das Release-Image konnte nicht geladen werden." >&2
    echo "Pruefe, ob das GHCR-Paket veroeffentlicht und auf Public gestellt wurde." >&2
    exit 1
fi

echo "[2/4] Vorhandene Konfiguration sichern"
mkdir -p backups
timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
backup_volume="$config_volume"
if [ -n "$legacy_config_volume" ] && docker volume inspect "$legacy_config_volume" >/dev/null 2>&1; then
    backup_volume="$legacy_config_volume"
fi
config_source="$(docker volume inspect "$backup_volume" --format '{{ .Mountpoint }}')"
if [ -n "$config_source" ] && [ -d "$config_source" ] && [ -n "$(find "$config_source" -mindepth 1 -print -quit)" ]; then
    tar -C "$config_source" -czf "backups/restreamer-config-${timestamp}.tar.gz" .
    chmod 0600 "backups/restreamer-config-${timestamp}.tar.gz"
    echo "Konfiguration gesichert: backups/restreamer-config-${timestamp}.tar.gz"
else
    echo "Keine vorhandene Instanz gefunden; keine Sicherung erforderlich."
fi

echo "[3/4] Container aktualisieren und starten"
container_change_started=true

if [ "$legacy_container" = true ] && docker container inspect restreamer-livechasing >/dev/null 2>&1; then
    if [ "$(docker inspect restreamer-livechasing --format '{{ .State.Running }}')" = true ]; then
        legacy_container_was_running=true
        docker stop restreamer-livechasing >/dev/null
    fi
fi

copy_legacy_volume() {
    source_volume="$1"
    target_volume="$2"
    label="$3"
    if [ -z "$source_volume" ] || ! docker volume inspect "$source_volume" >/dev/null 2>&1; then
        return 0
    fi

    source_mount="$(docker volume inspect "$source_volume" --format '{{ .Mountpoint }}')"
    target_mount="$(docker volume inspect "$target_volume" --format '{{ .Mountpoint }}')"
    if [ -n "$(find "$target_mount" -mindepth 1 -print -quit)" ]; then
        echo "$label-Zielvolume ist bereits befuellt; vorhandener Inhalt bleibt unveraendert."
        return 0
    fi

    echo "$label wird von $source_volume nach $target_volume migriert."
    tar -C "$source_mount" -cf - . | tar -C "$target_mount" -xf -
}

copy_legacy_volume "$legacy_config_volume" "$config_volume" "Konfiguration"
copy_legacy_volume "$legacy_data_volume" "$data_volume" "Daten und DVR"

docker compose -f compose.yaml up --detach --remove-orphans

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

echo "[4/4] Release pruefen"
./tests/smoke-test.sh

install_update_agent

if [ "$legacy_container" = true ] && docker container inspect restreamer-livechasing >/dev/null 2>&1; then
    docker rm restreamer-livechasing >/dev/null
    echo "Alter Container restreamer-livechasing wurde nach erfolgreicher Migration entfernt."
fi

container_id="$(docker compose -f compose.yaml ps -q restreamer-nkl)"
image_id="$(docker inspect "$container_id" --format '{{.Image}}')"
install_committed=true

echo
echo "Restreamer Nistkasten Livestream ${release_version} laeuft auf http://127.0.0.1:${http_port}"
echo "Image: $release_image"
echo "Image-ID: $image_id"
echo "Ein vorhandener offizieller Container namens 'restreamer' wurde nicht veraendert."
