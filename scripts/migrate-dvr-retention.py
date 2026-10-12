#!/usr/bin/env python3
"""Apply the global DVR window to every saved DVR ingest before Core starts."""

import json
import math
import os
from pathlib import Path
import re
import shutil
import tempfile
import time


INGEST_PREFIX = "restreamer-ui:ingest:"
CHANNEL_ID = re.compile(r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}")


def migrate_data(database):
    system = database.get("metadata", {}).get("system", {}).get("restreamer-ui", {})
    try:
        hours = min(168, max(1, int(system.get("livechasing", {}).get("dvr", {}).get("maxHours", 4))))
    except (AttributeError, ValueError, TypeError):
        hours = 4
    processes = database.get("process", [])
    metadata = database.get("metadata", {}).get("process", {})
    if not isinstance(processes, (list, dict)) or not isinstance(metadata, dict):
        return 0
    by_id = ({entry.get("id"): entry for entry in processes if isinstance(entry, dict)}
             if isinstance(processes, list) else processes)

    updated = 0
    for process_id, wrapped in metadata.items():
        if not process_id.startswith(INGEST_PREFIX) or not CHANNEL_ID.fullmatch(process_id[len(INGEST_PREFIX):]):
            continue
        process = by_id.get(process_id)
        if not isinstance(process, dict) or not isinstance(wrapped, dict):
            continue
        settings = wrapped.get("restreamer-ui", {})
        hls = settings.get("control", {}).get("hls", {}) if isinstance(settings, dict) else {}
        dvr = hls.get("dvr", {}) if isinstance(hls, dict) else {}
        if not isinstance(dvr, dict) or dvr.get("enabled") is not True:
            continue
        try:
            segment_duration = min(30, max(1, int(hls.get("segmentDuration", 2))))
        except (TypeError, ValueError):
            segment_duration = 2
        count = math.ceil(hours * 3600 / segment_duration)
        # AV_OPT_TYPE_DURATION accepts human-readable seconds at the CLI/tee
        # boundary; FFmpeg converts the value into microseconds internally.
        duration = hours * 3600
        # Core StoreData serializes app.Process with the FFmpeg config nested
        # under "config". Also accept legacy flat exports.
        config = process.get("config", process)
        outputs = config.get("output", []) if isinstance(config, dict) else []
        if not isinstance(outputs, list) or not outputs or not isinstance(outputs[0], dict):
            continue
        output = outputs[0]
        options = output.get("options", [])
        address = output.get("address", "")
        if isinstance(options, list) and "-hls_list_size" in options:
            index = options.index("-hls_list_size")
            if index + 1 >= len(options):
                continue
            options[index + 1] = str(count)
            # Legacy DVR processes may predate the restart boundary flag.
            # Mark timestamp resets when appending after an encoder restart.
            if "-hls_flags" in options:
                flag_index = options.index("-hls_flags") + 1
                if flag_index >= len(options):
                    continue
                if "discont_start" not in options[flag_index].split("+"):
                    options[flag_index] += "+discont_start"
            else:
                options.extend(["-hls_flags", "append_list+program_date_time+delete_segments+discont_start"])
            if "-hls_max_window_duration" in options:
                index = options.index("-hls_max_window_duration")
                if index + 1 >= len(options):
                    continue
                options[index + 1] = str(duration)
            else:
                options.extend(["-hls_max_window_duration", str(duration)])
        elif isinstance(address, str) and address.startswith("[") and "f=hls:" in address and "hls_list_size=" in address:
            head, separator, tail = address.partition("]")
            if not separator:
                continue
            head = re.sub(r"hls_list_size=\d+", f"hls_list_size={count}", head, count=1)
            flags = re.search(r"(?:^|:)hls_flags=([^:]+)", head)
            if flags:
                if "discont_start" not in flags.group(1).split("+"):
                    head = head[:flags.end(1)] + "+discont_start" + head[flags.end(1):]
            else:
                head += ":hls_flags=append_list+program_date_time+delete_segments+discont_start"
            if "hls_max_window_duration=" in head:
                head = re.sub(r"hls_max_window_duration=\d+", f"hls_max_window_duration={duration}", head, count=1)
            else:
                head += f":hls_max_window_duration={duration}"
            output["address"] = head + separator + tail
        else:
            continue
        # The old Core limits are independent of the FFmpeg playlist. In
        # particular, a stale 5406-file limit deletes the fourth DVR hour.
        # Preserve delete-channel cleanup, but let FFmpeg and the manager
        # expire DVR media without deleting playlist references.
        channel = process_id[len(INGEST_PREFIX):]
        for saved_output in outputs:
            if not isinstance(saved_output, dict):
                continue
            for rule in saved_output.get("cleanup", []) or []:
                if not isinstance(rule, dict):
                    continue
                pattern = rule.get("pattern", "")
                if isinstance(pattern, str) and re.match(
                    r"^(?:diskfs|disk|memfs|mem):/" + re.escape(channel) + r"(?:[./_*]|$)", pattern
                ):
                    rule["max_files"] = 0
                    rule["max_file_age_seconds"] = 0
        dvr["hours"] = hours
        hls["listSize"] = count
        hls["storage"] = "diskfs"
        hls["cleanup"] = True
        updated += 1
    return updated


def migrate_file(path):
    if not path.is_file():
        return 0
    original = path.read_text(encoding="utf-8")
    database = json.loads(original)
    count = migrate_data(database)
    if not count:
        return 0
    updated = json.dumps(database, ensure_ascii=False, separators=(",", ":"))
    if json.loads(original) == database:
        return 0
    backup = path.with_name(f"db.pre-dev20-{int(time.time())}.json")
    shutil.copy2(path, backup)
    os.chmod(backup, 0o600)
    descriptor, temporary = tempfile.mkstemp(prefix=".db.dev20.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as target:
            target.write(updated)
            target.flush()
            os.fsync(target.fileno())
        os.chmod(temporary, path.stat().st_mode & 0o777)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return count


if __name__ == "__main__":
    database = Path(os.environ.get("CORE_DB_DIR", "/core/config")) / "db.json"
    count = migrate_file(database)
    if count:
        print(f"NKL DVR: {count} Kanaele auf die globale Haltezeit eingestellt.")
