#!/usr/bin/env python3
"""Runtime helper for per-channel overlays and DVR disk protection."""

from __future__ import annotations

import json
import os
import re
import shutil
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit


DB_FILE = Path(os.environ.get("CORE_DB_DIR", "/core/config")) / "db.json"
DATA_DIR = Path(os.environ.get("CORE_STORAGE_DISK_DIR", "/core/data"))
OVERLAY_DIR = DATA_DIR / "overlays"
MAX_RESPONSE_BYTES = 256 * 1024
MAX_CONTROL_REQUEST_BYTES = 16 * 1024
CHANNEL_ID = re.compile(r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}")
REQUEST_ID = re.compile(r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}")
TOKEN = re.compile(
    r"{{\s*([A-Za-z][A-Za-z0-9_-]*)\.([A-Za-z0-9_.-]+)"
    r"(?:\s*\|\s*number\s*:\s*([0-3]))?\s*}}"
)


def log(message: str) -> None:
    print(f"Livechasing manager: {message}", flush=True)


def read_database() -> dict[str, Any]:
    try:
        with DB_FILE.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, json.JSONDecodeError):
        return {}


def restreamer_metadata(entry: Any) -> dict[str, Any]:
    if not isinstance(entry, dict):
        return {}
    metadata = entry.get("restreamer-ui", {})
    return metadata if isinstance(metadata, dict) else {}


def system_settings(database: dict[str, Any]) -> dict[str, Any]:
    system = database.get("metadata", {}).get("system", {}).get("restreamer-ui", {})
    livechasing = system.get("livechasing", {}) if isinstance(system, dict) else {}
    return livechasing if isinstance(livechasing, dict) else {}


def channel_entries(database: dict[str, Any]):
    process_metadata = database.get("metadata", {}).get("process", {})
    if not isinstance(process_metadata, dict):
        return

    for process_id, wrapped in process_metadata.items():
        if not process_id.startswith("restreamer-ui:ingest:") or process_id.endswith("_snapshot") or process_id.endswith("_h264"):
            continue
        metadata = restreamer_metadata(wrapped)
        # Process metadata is keyed by the ingest ID in Core's database.
        channel_id = process_id.removeprefix("restreamer-ui:ingest:")
        if isinstance(channel_id, str) and re.fullmatch(r"[A-Za-z0-9-]+", channel_id):
            yield channel_id, metadata


def overlay_settings(metadata: dict[str, Any]) -> dict[str, Any]:
    try:
        settings = metadata["profiles"][0]["video"]["filter"]["settings"]["drawtext"]["settings"]
        return settings if isinstance(settings, dict) else {}
    except (KeyError, IndexError, TypeError):
        return {}


def player_overlay_settings(metadata: dict[str, Any]) -> dict[str, Any]:
    player = metadata.get("player", {}) if isinstance(metadata, dict) else {}
    overlay = player.get("overlay", {}) if isinstance(player, dict) else {}
    return overlay if isinstance(overlay, dict) else {}


def parse_sources(value: Any) -> dict[str, str]:
    sources: dict[str, str] = {}
    if not isinstance(value, str):
        return sources
    for raw_line in value.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, url = (part.strip() for part in line.split("=", 1))
        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]*", name):
            continue
        if url.startswith("https://") or url.startswith("http://"):
            sources[name] = url
    return sources


def fetch_json(url: str) -> Any:
    request = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": "Restreamer-Livechasing/0.3"})
    with urllib.request.urlopen(request, timeout=15) as response:
        content_type = response.headers.get("Content-Type", "").lower()
        if "json" not in content_type and "text/plain" not in content_type and content_type:
            raise ValueError(f"unsupported content type {content_type}")
        payload = response.read(MAX_RESPONSE_BYTES + 1)
        if len(payload) > MAX_RESPONSE_BYTES:
            raise ValueError("JSON response exceeds 256 KiB")
    return json.loads(payload.decode("utf-8"))


def lookup(value: Any, path: str) -> Any:
    current = value
    for part in path.split("."):
        if isinstance(current, dict) and part in current:
            current = current[part]
        elif isinstance(current, list) and part.isdigit() and int(part) < len(current):
            current = current[int(part)]
        else:
            return None
    return current


def render(template: str, payloads: dict[str, Any]) -> str:
    def replace(match: re.Match[str]) -> str:
        value = lookup(payloads.get(match.group(1)), match.group(2))
        decimals = match.group(3)
        if value is None or isinstance(value, (dict, list, bool)):
            return "--"
        if decimals is not None:
            try:
                return f"{float(value):.{int(decimals)}f}"
            except (TypeError, ValueError):
                return "--"
        return str(value)

    return TOKEN.sub(replace, template).replace("\r\n", "\n").replace("\r", "\n")


def atomic_write(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(value.rstrip("\n") + "\n")
        os.replace(temporary, path)
    finally:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass


def update_overlays(database: dict[str, Any], state: dict[str, Any], now: float) -> set[str]:
    active_channels: set[str] = set()
    active_state_keys: set[str] = set()
    for channel_id, metadata in channel_entries(database):
        targets = (
            ("burnin", overlay_settings(metadata), OVERLAY_DIR / f"{channel_id}.txt"),
            ("player", player_overlay_settings(metadata), DATA_DIR / "channels" / channel_id / "player-overlay.txt"),
        )

        for mode, settings, target in targets:
            template = settings.get("template", "")
            if not settings.get("enabled") or not isinstance(template, str) or not template:
                continue

            active_channels.add(channel_id)
            state_key = f"{channel_id}:{mode}"
            active_state_keys.add(state_key)
            interval = settings.get("interval", 60)
            try:
                interval = min(3600, max(15, int(interval)))
            except (TypeError, ValueError):
                interval = 60

            fingerprint = json.dumps([settings.get("sources", ""), template], ensure_ascii=False, sort_keys=True)
            channel_state = state.setdefault(state_key, {})
            if channel_state.get("fingerprint") == fingerprint and now < channel_state.get("next", 0):
                continue

            payloads: dict[str, Any] = {}
            failed = False
            for name, url in parse_sources(settings.get("sources")).items():
                try:
                    payloads[name] = fetch_json(url)
                except (OSError, ValueError, json.JSONDecodeError, urllib.error.URLError) as error:
                    log(f"{channel_id}/{mode}: JSON source {name} failed ({error})")
                    failed = True
                    break

            if not failed:
                atomic_write(target, render(template, payloads))
                channel_state["fingerprint"] = fingerprint
            channel_state["next"] = now + interval

    for state_key in list(state):
        if state_key not in active_state_keys:
            del state[state_key]
    return active_channels


def dvr_channel_ids(database: dict[str, Any]) -> set[str]:
    enabled: set[str] = set()
    for channel_id, metadata in channel_entries(database):
        dvr = metadata.get("control", {}).get("hls", {}).get("dvr", {})
        if isinstance(dvr, dict) and dvr.get("enabled") is True:
            enabled.add(channel_id)
    return enabled


def control_request_dir() -> Path:
    return DATA_DIR / "livechasing-control" / "requests"


def control_response_dir() -> Path:
    return DATA_DIR / "livechasing-control" / "responses"


def purge_dvr_content(channel_ids: set[str]) -> dict[str, Any]:
    deleted_files = 0
    freed_bytes = 0
    deleted_channels = 0

    def remove_file(path: Path) -> None:
        nonlocal deleted_files, freed_bytes
        if not path.is_file() or path.is_symlink():
            return
        try:
            freed_bytes += path.stat().st_size
            path.unlink()
            deleted_files += 1
        except OSError as error:
            raise RuntimeError(f"could not delete DVR file {path.name}: {error}") from error

    for channel_id in sorted(channel_ids):
        if CHANNEL_ID.fullmatch(channel_id) is None:
            raise ValueError("invalid channel ID")

        channel_files = 0
        channel_root = DATA_DIR / channel_id
        if channel_root.is_symlink():
            raise RuntimeError("refusing to delete a symlinked DVR directory")
        if channel_root.is_dir():
            for path in channel_root.rglob("*"):
                if path.is_file() and not path.is_symlink():
                    try:
                        freed_bytes += path.stat().st_size
                        deleted_files += 1
                        channel_files += 1
                    except OSError:
                        pass
            try:
                shutil.rmtree(channel_root)
            except OSError as error:
                raise RuntimeError(f"could not delete DVR directory for {channel_id}: {error}") from error

        root_files = [
            DATA_DIR / f"{channel_id}.m3u8",
            DATA_DIR / f"{channel_id}.m3u8.tmp",
            DATA_DIR / f"{channel_id}.mp4",
            DATA_DIR / f"{channel_id}.mp4.tmp",
        ]
        root_files.extend(DATA_DIR.glob(f"{channel_id}_*.m3u8"))
        root_files.extend(DATA_DIR.glob(f"{channel_id}_*.m3u8.tmp"))
        before = deleted_files
        for path in root_files:
            remove_file(path)
        channel_files += deleted_files - before
        if channel_files > 0:
            deleted_channels += 1

    return {
        "ok": True,
        "channelCount": len(channel_ids),
        "deletedChannelCount": deleted_channels,
        "deletedFiles": deleted_files,
        "freedBytes": freed_bytes,
    }


def process_control_requests(database: dict[str, Any], now: float | None = None) -> int:
    requests = control_request_dir()
    responses = control_response_dir()
    requests.mkdir(parents=True, exist_ok=True)
    responses.mkdir(parents=True, exist_ok=True)
    known_channels = {channel_id for channel_id, _ in channel_entries(database)}
    processed = 0

    for request_path in sorted(requests.glob("*.json"))[:10]:
        request_id = request_path.stem
        if REQUEST_ID.fullmatch(request_id) is None or request_path.is_symlink():
            try:
                request_path.unlink()
            except OSError:
                pass
            continue

        response: dict[str, Any]
        try:
            if request_path.stat().st_size > MAX_CONTROL_REQUEST_BYTES:
                raise ValueError("control request is too large")
            request = json.loads(request_path.read_text(encoding="utf-8"))
            if request.get("version") != 1 or request.get("action") != "purge-dvr":
                raise ValueError("unsupported control request")
            if request.get("requestId") != request_id:
                raise ValueError("control request ID mismatch")
            requested_channels = request.get("channelIds")
            if not isinstance(requested_channels, list) or len(requested_channels) > 100:
                raise ValueError("invalid DVR channel list")
            channel_ids = set(requested_channels)
            if any(not isinstance(channel_id, str) or CHANNEL_ID.fullmatch(channel_id) is None for channel_id in channel_ids):
                raise ValueError("invalid DVR channel ID")
            if not channel_ids.issubset(known_channels):
                raise ValueError("unknown DVR channel ID")
            response = purge_dvr_content(channel_ids)
        except (OSError, ValueError, json.JSONDecodeError, RuntimeError) as error:
            response = {"ok": False, "error": str(error)}

        response["requestId"] = request_id
        atomic_write(responses / f"{request_id}.json", json.dumps(response, separators=(",", ":")))
        try:
            request_path.unlink()
        except OSError:
            pass
        processed += 1

    cutoff = time.time() - 3600 if now is None else now - 3600
    for response_path in responses.glob("*.json"):
        try:
            if response_path.stat().st_mtime < cutoff:
                response_path.unlink()
        except OSError:
            pass

    return processed


def dvr_max_hours(database: dict[str, Any]) -> int:
    try:
        return min(168, max(1, int(system_settings(database).get("dvr", {}).get("maxHours", 4))))
    except (AttributeError, TypeError, ValueError):
        return 4


def referenced_dvr_segments(channel_id: str) -> set[Path] | None:
    """Return live playlist references, or None if cleanup cannot be proven safe."""
    playlists = list(DATA_DIR.glob(f"{channel_id}_*.m3u8"))
    playlists.append(DATA_DIR / f"{channel_id}.m3u8")
    references: set[Path] = set()
    media_playlists = 0
    for playlist in playlists:
        if not playlist.is_file() or playlist.is_symlink():
            continue
        try:
            content = playlist.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            return None
        if "#EXTINF:" not in content:
            continue
        media_playlists += 1
        for line in content.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            uri = urlsplit(line).path.lstrip("/")
            if not uri.startswith(channel_id + "/") or ".." in Path(uri).parts:
                return None
            references.add(DATA_DIR / uri)
    return references if media_playlists else None


def enforce_dvr_retention(database: dict[str, Any], last_check: float, now: float, wall_time: float | None = None) -> float:
    if now - last_check < 60:
        return last_check
    cutoff = (time.time() if wall_time is None else wall_time) - dvr_max_hours(database) * 3600 - 60
    removed = 0
    for channel_id in dvr_channel_ids(database):
        if CHANNEL_ID.fullmatch(channel_id) is None:
            continue
        root = DATA_DIR / channel_id
        if not root.is_dir() or root.is_symlink():
            continue
        referenced = referenced_dvr_segments(channel_id)
        if referenced is None:
            continue
        for path in root.rglob("*"):
            if path.suffix not in {".ts", ".mp4"} or path.is_symlink() or not path.is_file():
                continue
            try:
                if path not in referenced and path.stat().st_mtime < cutoff:
                    path.unlink()
                    removed += 1
            except OSError as error:
                log(f"DVR retention: could not remove old segment for {channel_id} ({type(error).__name__})")
    if removed:
        log(f"DVR retention removed {removed} unreferenced segments older than {dvr_max_hours(database)}h")
    return now


def enforce_disk_reserve(database: dict[str, Any], last_check: float, now: float) -> float:
    if now - last_check < 60:
        return last_check
    dvr = system_settings(database).get("dvr", {})
    try:
        reserve = min(500, max(1, int(dvr.get("minFreeGB", 20)))) * 1024**3
    except (AttributeError, TypeError, ValueError):
        reserve = 20 * 1024**3

    free = shutil.disk_usage(DATA_DIR).free
    if free >= reserve:
        return now

    candidates: list[Path] = []
    for channel_id in dvr_channel_ids(database):
        root = DATA_DIR / channel_id
        referenced = referenced_dvr_segments(channel_id)
        if root.is_dir() and not root.is_symlink() and referenced is not None:
            # Even disk pressure must not silently break the live playlist.
            candidates.extend(path for path in root.rglob("*")
                              if path.suffix in {".ts", ".mp4"} and path.is_file()
                              and not path.is_symlink() and path not in referenced)

    candidates_with_age = []
    cutoff = time.time() - dvr_max_hours(database) * 3600 - 60
    for path in candidates:
        try:
            modified = path.stat().st_mtime
            if modified < cutoff:
                candidates_with_age.append((modified, path))
        except OSError:
            pass
    candidates_with_age.sort(key=lambda item: item[0])
    removed = 0
    for _, path in candidates_with_age:
        if shutil.disk_usage(DATA_DIR).free >= reserve:
            break
        try:
            path.unlink()
            removed += 1
        except OSError:
            pass
    if removed:
        log(f"disk reserve protection removed {removed} oldest DVR segments")
    return now


def main() -> None:
    OVERLAY_DIR.mkdir(parents=True, exist_ok=True)
    control_request_dir().mkdir(parents=True, exist_ok=True)
    control_response_dir().mkdir(parents=True, exist_ok=True)
    overlay_state: dict[str, Any] = {}
    last_disk_check = 0.0
    last_retention_check = 0.0
    log("started")
    while True:
        database = read_database()
        now = time.monotonic()
        processed = process_control_requests(database)
        if processed:
            log(f"processed {processed} DVR cleanup request(s)")
        update_overlays(database, overlay_state, now)
        last_retention_check = enforce_dvr_retention(database, last_retention_check, now)
        last_disk_check = enforce_disk_reserve(database, last_disk_check, now)
        time.sleep(2)


if __name__ == "__main__":
    main()
