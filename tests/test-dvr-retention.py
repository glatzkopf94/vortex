#!/usr/bin/env python3
"""Real time DVR bounds across channels, including old stored processes."""

import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


MIGRATE = load("dvr_migration", ROOT / "scripts/migrate-dvr-retention.py")
MANAGER = load("dvr_manager", ROOT / "bundle/livechasing-manager.py")
IDS = ["8672be5b-5a35-4a56-a970-877d7d728983", "2579719c-8d8b-4f59-a936-3048b181710b"]


def fixture():
    db = {
        "version": 4,
        "process": {},
        "metadata": {
            "system": {"restreamer-ui": {"livechasing": {"dvr": {"maxHours": 3, "minFreeGB": 20}}}},
            "process": {},
        },
    }
    for number, channel in enumerate(IDS):
        key = "restreamer-ui:ingest:" + channel
        if number == 0:
            output = {"options": ["-f", "hls", "-hls_list_size", "10800"], "address": f"{{diskfs}}/{channel}_output_0.m3u8"}
        else:
            output = {"options": ["-f", "tee"], "address": f"[bsfs/a=aac_adtstoasc:f=hls:hls_list_size=10800:hls_time=2]{{diskfs}}/{channel}_output_0.m3u8"}
        db["process"][key] = {"id": key, "order": "start", "config": {
            "output": [output], "input": [{"address": "rtsp://secret.example/camera"}]}}
        db["metadata"]["process"][key] = {
            "restreamer-ui": {"control": {"hls": {"segmentDuration": 2, "listSize": 10800,
                                                   "dvr": {"enabled": True, "hours": 6}}}}
        }
    return db


class DVRRetentionTests(unittest.TestCase):
    def test_three_to_four_hours_removes_stale_core_limits(self):
        db = fixture()
        db["metadata"]["system"]["restreamer-ui"]["livechasing"]["dvr"]["maxHours"] = 4
        for channel in IDS:
            output = db["process"]["restreamer-ui:ingest:" + channel]["config"]["output"][0]
            output["cleanup"] = [
                {"pattern": f"diskfs:/{channel}/**.ts", "max_files": 5406,
                 "max_file_age_seconds": 10812, "purge_on_delete": True},
                {"pattern": "diskfs:/unrelated/**", "max_files": 10},
            ]
        MIGRATE.migrate_data(db)
        for channel in IDS:
            output = db["process"]["restreamer-ui:ingest:" + channel]["config"]["output"][0]
            rule = output["cleanup"][0]
            self.assertEqual(rule["max_files"], 0)
            self.assertEqual(rule["max_file_age_seconds"], 0)
            self.assertTrue(rule["purge_on_delete"])
            self.assertEqual(output["cleanup"][1]["max_files"], 10)
            self.assertIn("14400", str(output))
        before = json.dumps(db, sort_keys=True)
        MIGRATE.migrate_data(db)
        self.assertEqual(json.dumps(db, sort_keys=True), before)

    def test_four_hour_retention_and_disk_pressure_protect_playlist(self):
        wall = 1_800_000_000
        db = fixture()
        db["metadata"]["system"]["restreamer-ui"]["livechasing"]["dvr"]["maxHours"] = 4
        with tempfile.TemporaryDirectory() as directory, patch.object(MANAGER, "DATA_DIR", Path(directory)):
            root = Path(directory) / IDS[0]
            root.mkdir()
            for name, age in [("fourth-hour.ts", 3.5), ("expired.ts", 5), ("referenced.ts", 5)]:
                path = root / name
                path.write_bytes(b"video")
                os.utime(path, (wall-age*3600, wall-age*3600))
            (Path(directory) / f"{IDS[0]}_output_0.m3u8").write_text(
                f"#EXTM3U\n#EXTINF:2,\n{IDS[0]}/referenced.ts\n")
            os.utime(Path(directory) / f"{IDS[0]}_output_0.m3u8", (wall, wall))
            MANAGER.enforce_dvr_retention(db, 0, 100, wall)
            self.assertTrue((root / "fourth-hour.ts").exists())
            self.assertFalse((root / "expired.ts").exists())
            self.assertTrue((root / "referenced.ts").exists())
            with patch.object(MANAGER.shutil, "disk_usage", return_value=SimpleNamespace(free=0)), patch.object(MANAGER.time, "time", return_value=wall):
                MANAGER.enforce_disk_reserve(db, 0, 100)
            self.assertTrue((root / "referenced.ts").exists())
            self.assertTrue((root / "fourth-hour.ts").exists())

    def test_nested_core_config_preserves_inputs_and_disabled_channels(self):
        db = fixture()
        disabled = "restreamer-ui:ingest:" + IDS[1]
        db["metadata"]["process"][disabled]["restreamer-ui"]["control"]["hls"]["dvr"]["enabled"] = False
        original = json.loads(json.dumps(db))
        self.assertEqual(MIGRATE.migrate_data(db), 1)
        self.assertEqual(db["process"][disabled], original["process"][disabled])
        active = "restreamer-ui:ingest:" + IDS[0]
        self.assertEqual(db["process"][active]["config"]["input"], original["process"][active]["config"]["input"])
        self.assertEqual(db["process"][active]["order"], "start")

    def test_global_window_updates_each_native_and_tee_process_atomically(self):
        with tempfile.TemporaryDirectory() as directory:
            db_path = Path(directory) / "db.json"
            db_path.write_text(json.dumps(fixture()), encoding="utf-8")
            self.assertEqual(MIGRATE.migrate_file(db_path), 2)
            result = json.loads(db_path.read_text(encoding="utf-8"))
            for channel in IDS:
                key = "restreamer-ui:ingest:" + channel
                hls = result["metadata"]["process"][key]["restreamer-ui"]["control"]["hls"]
                self.assertEqual(hls["dvr"]["hours"], 3)
                self.assertEqual(hls["listSize"], 5400)
            self.assertEqual(result["process"]["restreamer-ui:ingest:" + IDS[0]]["config"]["output"][0]["options"][-2:],
                             ["-hls_max_window_duration", "10800"])
            self.assertIn("hls_max_window_duration=10800", result["process"]["restreamer-ui:ingest:" + IDS[1]]["config"]["output"][0]["address"])
            for channel in IDS:
                output = result["process"]["restreamer-ui:ingest:" + channel]["config"]["output"][0]
                self.assertIn("discont_start", str(output))
            self.assertEqual(MIGRATE.migrate_file(db_path), 0)
            self.assertEqual(len(list(Path(directory).glob("db.pre-dev20-*.json"))), 1)

    def test_expired_unreferenced_segments_are_deleted_for_every_dvr_channel(self):
        wall = 1_800_000_000
        with tempfile.TemporaryDirectory() as directory:
            previous = MANAGER.DATA_DIR
            MANAGER.DATA_DIR = Path(directory)
            try:
                db = fixture()
                for channel in IDS:
                    root = MANAGER.DATA_DIR / channel / "output_0" / "20260926"
                    root.mkdir(parents=True)
                    old = root / "old.ts"
                    kept = root / "referenced.ts"
                    recent = root / "recent.ts"
                    for item in (old, kept, recent):
                        item.write_bytes(b"video")
                    os.utime(old, (wall - 6 * 3600, wall - 6 * 3600))
                    os.utime(kept, (wall - 6 * 3600, wall - 6 * 3600))
                    os.utime(recent, (wall - 10, wall - 10))
                    (MANAGER.DATA_DIR / f"{channel}_output_0.m3u8").write_text(
                        "#EXTM3U\n#EXTINF:2,\n" + f"{channel}/output_0/20260926/referenced.ts\n",
                        encoding="utf-8",
                    )
                for playlist in MANAGER.DATA_DIR.glob("*.m3u8"):
                    os.utime(playlist, (wall, wall))
                self.assertEqual(MANAGER.enforce_dvr_retention(db, 0, 100, wall), 100)
                for channel in IDS:
                    root = MANAGER.DATA_DIR / channel / "output_0" / "20260926"
                    self.assertFalse((root / "old.ts").exists())
                    self.assertTrue((root / "referenced.ts").exists())
                    self.assertTrue((root / "recent.ts").exists())
            finally:
                MANAGER.DATA_DIR = previous

    def test_stale_playlist_expires_but_recent_segments_survive(self):
        wall = 1_800_000_000
        with tempfile.TemporaryDirectory() as directory, patch.object(MANAGER, "DATA_DIR", Path(directory)):
            root = Path(directory) / IDS[0]
            root.mkdir()
            old = root / "old.ts"
            recent = root / "recent.ts"
            old.write_bytes(b"old")
            recent.write_bytes(b"new")
            os.utime(old, (wall-8*3600, wall-8*3600))
            os.utime(recent, (wall-30, wall-30))
            playlist = Path(directory) / f"{IDS[0]}_output_0.m3u8"
            playlist.write_text(f"#EXTM3U\n#EXTINF:2,\n{IDS[0]}/old.ts\n")
            os.utime(playlist, (wall-8*3600, wall-8*3600))
            MANAGER.enforce_dvr_retention(fixture(), 0, 100, wall)
            self.assertFalse(old.exists())
            self.assertTrue(recent.exists())

    def test_missing_playlist_does_not_pin_expired_segments(self):
        with tempfile.TemporaryDirectory() as directory:
            previous = MANAGER.DATA_DIR
            MANAGER.DATA_DIR = Path(directory)
            try:
                root = MANAGER.DATA_DIR / IDS[0]
                root.mkdir()
                old = root / "old.ts"
                old.write_bytes(b"old")
                os.utime(old, (1, 1))
                MANAGER.enforce_dvr_retention(fixture(), 0, 100, 1_800_000_000)
                self.assertFalse(old.exists())
            finally:
                MANAGER.DATA_DIR = previous


if __name__ == "__main__":
    unittest.main()
