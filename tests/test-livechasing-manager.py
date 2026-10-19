#!/usr/bin/env python3

import importlib.util
import json
import pathlib
import tempfile
import unittest
from unittest import mock


ROOT = pathlib.Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("livechasing_manager", ROOT / "bundle" / "livechasing-manager.py")
MANAGER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MANAGER)


class LivechasingManagerTest(unittest.TestCase):
    def test_sources(self):
        self.assertEqual(
            MANAGER.parse_sources("wetter=https://example.test/weather.json\n# comment\ninvalid\n"),
            {"wetter": "https://example.test/weather.json"},
        )

    def test_template_rendering(self):
        rendered = MANAGER.render(
            "Temp: {{ wetter.temperature_c | number:1 }} °C   F: {{ wetter.humidity_pct | number:0 }} %",
            {"wetter": {"temperature_c": 14.56, "humidity_pct": 84}},
        )
        self.assertEqual(rendered, "Temp: 14.6 °C   F: 84 %")

    def test_static_text_and_missing_value(self):
        rendered = MANAGER.render("Nistkasten\nWind: {{ wetter.wind | number:1 }}", {"wetter": {}})
        self.assertEqual(rendered, "Nistkasten\nWind: --")

    def test_channel_metadata_detection(self):
        channel = "8672be5b-5a35-4a56-a970-877d7d728983"
        process_id = f"restreamer-ui:ingest:{channel}"
        database = {
            "process": [{"id": process_id, "reference": channel}],
            "metadata": {
                "process": {process_id: {"restreamer-ui": {"control": {"hls": {"dvr": {"enabled": True}}}}}},
                "system": {"restreamer-ui": {"livechasing": {"dvr": {"maxHours": 4, "minFreeGB": 20}}}},
            },
        }
        entries = list(MANAGER.channel_entries(database))
        self.assertEqual(entries[0][0], channel)
        self.assertEqual(MANAGER.dvr_channel_ids(database), {channel})
        self.assertEqual(MANAGER.system_settings(database)["dvr"]["maxHours"], 4)

    def test_per_channel_overlay_file_is_written(self):
        channel = "8672be5b-5a35-4a56-a970-877d7d728983"
        process_id = f"restreamer-ui:ingest:{channel}"
        database = {
            "process": [{"id": process_id, "reference": channel}],
            "metadata": {
                "process": {
                    process_id: {
                        "restreamer-ui": {
                            "profiles": [
                                {
                                    "video": {
                                        "filter": {
                                            "settings": {
                                                "drawtext": {
                                                    "settings": {
                                                        "enabled": True,
                                                        "sources": "weather=https://example.test/environment.json",
                                                        "interval": 60,
                                                        "template": "Temp: {{ weather.temperature_c | number:1 }} °C",
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }
                            ]
                        }
                    }
                }
            },
        }

        with tempfile.TemporaryDirectory() as directory:
            old_overlay_dir = MANAGER.OVERLAY_DIR
            MANAGER.OVERLAY_DIR = pathlib.Path(directory)
            try:
                with mock.patch.object(MANAGER, "fetch_json", return_value={"temperature_c": 14.54}):
                    active = MANAGER.update_overlays(database, {}, 100.0)
                self.assertEqual(active, {channel})
                self.assertEqual((pathlib.Path(directory) / f"{channel}.txt").read_text(encoding="utf-8"), "Temp: 14.5 °C\n")
            finally:
                MANAGER.OVERLAY_DIR = old_overlay_dir

    def test_passthrough_player_overlay_file_is_written(self):
        channel = "8672be5b-5a35-4a56-a970-877d7d728983"
        process_id = f"restreamer-ui:ingest:{channel}"
        database = {
            "metadata": {
                "process": {
                    process_id: {
                        "restreamer-ui": {
                            "player": {
                                "overlay": {
                                    "enabled": True,
                                    "sources": "weather=https://example.test/environment.json",
                                    "interval": 60,
                                    "template": "Temp: {{ weather.temperature_c | number:1 }} °C",
                                }
                            }
                        }
                    }
                }
            }
        }

        with tempfile.TemporaryDirectory() as directory:
            old_data_dir = MANAGER.DATA_DIR
            MANAGER.DATA_DIR = pathlib.Path(directory)
            try:
                with mock.patch.object(MANAGER, "fetch_json", return_value={"temperature_c": 14.54}):
                    active = MANAGER.update_overlays(database, {}, 100.0)
                target = pathlib.Path(directory) / "channels" / channel / "player-overlay.txt"
                self.assertEqual(active, {channel})
                self.assertEqual(target.read_text(encoding="utf-8"), "Temp: 14.5 °C\n")
            finally:
                MANAGER.DATA_DIR = old_data_dir

    def test_changed_template_bypasses_json_refresh_deadline(self):
        channel = "8672be5b-5a35-4a56-a970-877d7d728983"
        process_id = f"restreamer-ui:ingest:{channel}"
        settings = {
            "enabled": True,
            "sources": "weather=https://example.test/environment.json",
            "interval": 3600,
            "template": "Old: {{ weather.temperature_c }}",
        }
        database = {
            "metadata": {
                "process": {
                    process_id: {
                        "restreamer-ui": {"player": {"overlay": settings}}
                    }
                }
            }
        }

        with tempfile.TemporaryDirectory() as directory:
            old_data_dir = MANAGER.DATA_DIR
            MANAGER.DATA_DIR = pathlib.Path(directory)
            state = {}
            try:
                with mock.patch.object(MANAGER, "fetch_json", return_value={"temperature_c": 14.5}) as fetch:
                    MANAGER.update_overlays(database, state, 100.0)
                    settings["template"] = "New: {{ weather.temperature_c }}"
                    MANAGER.update_overlays(database, state, 101.0)
                target = pathlib.Path(directory) / "channels" / channel / "player-overlay.txt"
                self.assertEqual(fetch.call_count, 2)
                self.assertEqual(target.read_text(encoding="utf-8"), "New: 14.5\n")
            finally:
                MANAGER.DATA_DIR = old_data_dir

    def test_player_text_clear_disable_and_static_edit_with_unused_source(self):
        channel = "8672be5b-5a35-4a56-a970-877d7d728983"
        settings = {"enabled": True, "template": "Old text", "sources": "unused=https://example.test/offline"}
        database = {"metadata": {"process": {f"restreamer-ui:ingest:{channel}": {"restreamer-ui": {"player": {"overlay": settings}}}}}}
        with tempfile.TemporaryDirectory() as directory, mock.patch.object(MANAGER, "DATA_DIR", pathlib.Path(directory)), mock.patch.object(MANAGER, "fetch_json", side_effect=OSError("offline")) as fetch:
            state = {}
            target = pathlib.Path(directory) / "channels" / channel / "player-overlay.txt"
            MANAGER.update_overlays(database, state, 100)
            self.assertEqual(target.read_text().strip(), "Old text")
            settings["template"] = ""
            MANAGER.update_overlays(database, state, 101)
            self.assertTrue(target.exists())
            self.assertEqual(target.read_text().strip(), "")
            self.assertEqual(state, {})
            settings["template"] = "New text"
            MANAGER.update_overlays(database, state, 102)
            self.assertEqual(target.read_text().strip(), "New text")
            settings["enabled"] = False
            MANAGER.update_overlays(database, state, 103)
            self.assertEqual(target.read_text().strip(), "")
            fetch.assert_not_called()

    def test_dvr_purge_removes_only_channel_hls_content(self):
        channel = "8672be5b-5a35-4a56-a970-877d7d728983"
        other = "2579719c-8d8b-4f59-a936-3048b181710b"

        with tempfile.TemporaryDirectory() as directory:
            old_data_dir = MANAGER.DATA_DIR
            MANAGER.DATA_DIR = pathlib.Path(directory)
            try:
                dvr_root = MANAGER.DATA_DIR / channel / "0" / "20260918"
                dvr_root.mkdir(parents=True)
                (dvr_root / "segment.ts").write_bytes(b"segment")
                (dvr_root / "init.mp4").write_bytes(b"init")
                (MANAGER.DATA_DIR / f"{channel}.m3u8").write_text("playlist", encoding="utf-8")
                (MANAGER.DATA_DIR / f"{channel}_0.m3u8").write_text("variant", encoding="utf-8")
                (MANAGER.DATA_DIR / f"{channel}.mp4").write_bytes(b"root-init")
                (MANAGER.DATA_DIR / f"{channel}.jpg").write_bytes(b"poster")
                other_root = MANAGER.DATA_DIR / other / "20260918"
                other_root.mkdir(parents=True)
                (other_root / "segment.ts").write_bytes(b"other")
                overlay = MANAGER.DATA_DIR / "channels" / channel / "player-overlay.txt"
                overlay.parent.mkdir(parents=True)
                overlay.write_text("Temp: 20 °C", encoding="utf-8")

                result = MANAGER.purge_dvr_content({channel})

                self.assertTrue(result["ok"])
                self.assertEqual(result["deletedFiles"], 5)
                self.assertFalse((MANAGER.DATA_DIR / channel).exists())
                self.assertFalse((MANAGER.DATA_DIR / f"{channel}.m3u8").exists())
                self.assertTrue((MANAGER.DATA_DIR / f"{channel}.jpg").exists())
                self.assertTrue((other_root / "segment.ts").exists())
                self.assertTrue(overlay.exists())
            finally:
                MANAGER.DATA_DIR = old_data_dir

    def test_authenticated_control_request_purges_known_channel(self):
        channel = "8672be5b-5a35-4a56-a970-877d7d728983"
        request_id = "900c98fb-a1dd-441c-b5c2-6c8ff06f6857"
        process_id = f"restreamer-ui:ingest:{channel}"
        database = {
            "metadata": {
                "process": {
                    process_id: {
                        "restreamer-ui": {"control": {"hls": {"dvr": {"enabled": True}}}}
                    }
                }
            }
        }

        with tempfile.TemporaryDirectory() as directory:
            old_data_dir = MANAGER.DATA_DIR
            MANAGER.DATA_DIR = pathlib.Path(directory)
            try:
                dvr_root = MANAGER.DATA_DIR / channel / "20260918"
                dvr_root.mkdir(parents=True)
                (dvr_root / "segment.ts").write_bytes(b"segment")
                request_path = MANAGER.control_request_dir() / f"{request_id}.json"
                request_path.parent.mkdir(parents=True)
                request_path.write_text(
                    json.dumps(
                        {
                            "version": 1,
                            "action": "purge-dvr",
                            "requestId": request_id,
                            "channelIds": [channel],
                        }
                    ),
                    encoding="utf-8",
                )

                self.assertEqual(MANAGER.process_control_requests(database), 1)
                response = json.loads(
                    (MANAGER.control_response_dir() / f"{request_id}.json").read_text(encoding="utf-8")
                )
                self.assertTrue(response["ok"])
                self.assertEqual(response["deletedFiles"], 1)
                self.assertFalse(request_path.exists())
                self.assertFalse((MANAGER.DATA_DIR / channel).exists())
            finally:
                MANAGER.DATA_DIR = old_data_dir


if __name__ == "__main__":
    unittest.main()
