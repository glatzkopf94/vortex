#!/bin/sh

set -u

if [ -x /core/bin/import ]; then
    /core/bin/import || exit 1
fi

if [ -x /core/bin/ffmigrate ]; then
    /core/bin/ffmigrate || exit 1
fi

if [ -x /core/bin/migrate-timestamp-repair.py ]; then
    /core/bin/migrate-timestamp-repair.py || exit 1
fi

if [ -x /core/bin/migrate-dvr-retention.py ]; then
    /core/bin/migrate-dvr-retention.py || exit 1
fi

if [ -x /core/bin/migrate-player-cleanup.py ]; then
    /core/bin/migrate-player-cleanup.py || exit 1
fi

if [ -x /core/bin/migrate-player-1.4.py ]; then
    /core/bin/migrate-player-1.4.py || exit 1
fi

# Modified 2026-10-10: migrate the supplied landing page; preserve custom pages.
python3 - <<'PYLANDING' || exit 1
import hashlib, os, shutil
from pathlib import Path
root = Path(os.environ.get("CORE_STORAGE_DISK_DIR") or "/core/data")
root.mkdir(parents=True, exist_ok=True)
page = root / "index.html"
source = Path("/core/ui-root/index.html")
old = page.read_bytes() if page.is_file() else b""
if not page.exists() or hashlib.sha256(old).hexdigest() == "0f64c13a024089d7e3a4d81f086f15fcc37c20f4bb5eaf7e4188537c44848cd5" or b"Vortex managed landing page" in old:
    new = source.read_bytes()
    if old != new:
        if old and not (root / "index.html.before-vortex").exists():
            shutil.copy2(page, root / "index.html.before-vortex")
        temporary = root / ".vortex-index.html.tmp"
        temporary.write_bytes(new)
        temporary.chmod(0o644)
        temporary.replace(page)
PYLANDING

/core/bin/overlay-updater.sh &
/core/bin/livechasing-manager.py &

if [ "${NKL_TIMELAPSE_ENABLE:-false}" = "true" ]; then
    nice -n 10 python3 /core/bin/timelapse/httpd.py &
fi

exec /core/bin/core
