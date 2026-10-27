#!/usr/bin/env python3
"""Static regression tests for the public DVR player controls."""

from pathlib import Path
import importlib.util
import json
import re
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
PLAYER = ROOT / "ui/public/_player/videojs/player.html"
SKIN = ROOT / "ui/public/_player/videojs/dist/video-js-skin.css"
MINIFIED_SKIN = ROOT / "ui/public/_player/videojs/dist/video-js-skin.min.css"


class PlayerUITest(unittest.TestCase):
    def test_existing_public_pages_are_migrated_without_changing_metadata(self):
        module_path = ROOT / "scripts/migrate-player-1.4.py"
        spec = importlib.util.spec_from_file_location("player_migration", module_path)
        migration = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(migration)
        with tempfile.TemporaryDirectory() as directory:
            data = Path(directory) / "data"
            ui = Path(directory) / "ui"
            (ui / "_player/videojs/dist").mkdir(parents=True)
            (data / "player/videojs/dist").mkdir(parents=True)
            (ui / "_player/videojs/player.html").write_text(PLAYER.read_text())
            (ui / "_player/videojs/dist/video-js-skin.min.css").write_text("new skin")
            (data / "player/videojs/dist/video-js-skin.min.css").write_text("old skin")
            old = PLAYER.read_text().replace("NKL 1.4 Beta", "NKL 1.3 Beta")
            old = old.replace("var publicStreamActivated = false;", "var oldPlayerCode = true;")
            old = old.replace("?nkl=1.4-beta-dev21", "")
            old = re.sub(r"\s*#lc-activation-hint\s*\{.*?\}\s*#lc-activation-hint\.is-visible\s*\{.*?\}", "", old, flags=re.S)
            old = old.replace('<div id="lc-activation-hint" aria-live="polite"></div>', "")
            old = old.replace("{{name}}", "Unchanged channel &amp; title")
            channel = data / "f74edb08-dfb3-44f5-9873-1afe0699c846.html"
            channel.write_text(old)
            custom = data / "custom.html"
            custom.write_text("<html>Custom page</html>")
            migration.migrate(data, ui)
            result = channel.read_text()
            self.assertIn("Unchanged channel &amp; title", result)
            self.assertIn("var publicStreamActivated = false;", result)
            self.assertIn("document.createElement('div')", result)
            self.assertNotIn('<div id="lc-activation-hint"', result)
            self.assertNotIn("var oldPlayerCode = true;", result)
            self.assertIn("video-js-skin.min.css?nkl=1.5-beta-dev24", result)
            self.assertEqual(custom.read_text(), "<html>Custom page</html>")
            self.assertEqual((data / "player/videojs/dist/video-js-skin.min.css").read_text(), "new skin")
            migration.migrate(data, ui)
            self.assertEqual(channel.read_text(), result)

    def test_restart_refreshes_dvr_sources_without_resaving_player(self):
        spec = importlib.util.spec_from_file_location("player_migration", ROOT / "scripts/migrate-player-1.4.py")
        migration = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(migration)
        with tempfile.TemporaryDirectory() as directory:
            data = Path(directory)
            ids = ["f74edb08-dfb3-44f5-9873-1afe0699c846", "2579719c-8d8b-4f59-a936-3048b181710b"]
            db = {"process": {}, "metadata": {"process": {}}}
            for channel in ids:
                key = "restreamer-ui:ingest:" + channel
                db["process"][key] = {"config": {"output": [{"address": "{diskfs}/" + channel + "_output_0.m3u8"}]}}
                db["metadata"]["process"][key] = {"restreamer-ui": {"control": {
                    "hls": {"storage": "diskfs", "segmentDuration": 2, "dvr": {"enabled": True, "hours": 3}},
                    "preview": {"enable": True}}}}
                path = data / "channels" / channel / "config.js"
                path.parent.mkdir(parents=True)
                path.write_text('var playerConfig = ' + json.dumps({"source": "memfs/" + channel + "_h264.m3u8", "poster": "custom.jpg", "overlay": {"enabled": True}, "dvr": {"enabled": False}}))
            database = data / "db.json"
            database.write_text(json.dumps(db))
            migration.synchronize_player_configs(data, database)
            for channel in ids:
                path = data / "channels" / channel / "config.js"
                content = path.read_text()
                config = json.loads(content.split("=", 1)[1].strip().rstrip(";"))
                self.assertEqual(config["source"], channel + ".m3u8")
                self.assertEqual(config["dvr"], {"enabled": True, "hours": 3, "segmentDuration": 2})
                self.assertEqual(config["poster"], "custom.jpg")
                self.assertTrue(config["overlay"]["enabled"])
                migration.synchronize_player_configs(data, database)
                self.assertEqual(path.read_text(), content)
            self.assertEqual(json.loads(database.read_text()), db)

    def test_duplicate_dvr_panel_is_removed(self):
        html = PLAYER.read_text(encoding="utf-8")
        self.assertNotIn('id="dvr-panel"', html)
        self.assertNotIn('id="dvr-live"', html)
        self.assertNotIn('id="dvr-time"', html)
        self.assertNotIn("ZUM LIVEBILD", html)
        self.assertIn("liveui: true", html)

    def test_native_live_control_has_compact_emphasis(self):
        css = SKIN.read_text(encoding="utf-8")
        self.assertIn(".vjs-public .vjs-seek-to-live-control::after", css)
        self.assertIn("top: 10px", css)
        self.assertIn("bottom: 10px", css)
        self.assertIn(".vjs-at-live-edge::after", css)

        minified = MINIFIED_SKIN.read_text(encoding="utf-8")
        self.assertIn("vjs-seek-to-live-control", minified)
        self.assertIn("vjs-at-live-edge", minified)

    def test_non_dvr_shows_one_live_label(self):
        html = PLAYER.read_text(encoding="utf-8")
        css = SKIN.read_text(encoding="utf-8")
        minified = MINIFIED_SKIN.read_text(encoding="utf-8")

        self.assertIn("player.addClass('vjs-live-no-dvr')", html)
        self.assertIn(".vjs-public.vjs-live-no-dvr .vjs-live-control", css)
        self.assertIn(".vjs-public.vjs-live-no-dvr .vjs-live-control {display:flex", css)
        self.assertIn(".vjs-public.vjs-live-no-dvr .vjs-seek-to-live-control {display:none!important}", css)
        self.assertEqual(css, minified)
        self.assertIn(".vjs-public .vjs-seek-to-live-control.vjs-at-live-edge::after", css)

    def test_empty_license_settings_menu_is_not_initialized(self):
        html = PLAYER.read_text(encoding="utf-8")
        self.assertNotIn("player.license(playerConfig.license)", html)
        self.assertNotIn("videojs-license.min.js", html)
        self.assertNotIn("videojs-license.min.css", html)

    def test_passthrough_overlay_uses_safe_player_elements(self):
        html = PLAYER.read_text(encoding="utf-8")
        self.assertIn('id="lc-player-overlay-root"', html)
        self.assertIn('id="lc-player-overlay-text"', html)
        self.assertIn("playerConfig.overlay", html)
        self.assertIn("response.text()", html)
        self.assertIn("overlayText.textContent", html)
        self.assertIn("playerOverlay.logo1", html)
        self.assertIn("playerOverlay.logo2", html)
        self.assertIn("player.el().appendChild(overlayRoot)", html)
        self.assertIn("pointer-events: none", html)
        self.assertIn("cache: 'no-store'", html)
        self.assertIn("lc-position-top-center", html)
        self.assertIn("lc-position-bottom-center", html)
        self.assertIn("'top-center'", html)
        self.assertIn("'bottom-center'", html)
        self.assertIn("window.setTimeout(refreshOverlayText, 5000)", html)
        self.assertIn("--lc-overlay-font-size", html)
        self.assertIn("updatePlayerOverlayLayout", html)
        self.assertIn("new ResizeObserver", html)
        self.assertIn("logo.image.naturalWidth", html)
        self.assertIn("logo.image.style.height = 'auto'", html)

        compose = (ROOT / "compose.yaml").read_text(encoding="utf-8")
        self.assertIn('CORE_STORAGE_DISK_CACHE_TYPES_BLOCK: ".m3u8 .mpd .txt .html .js"', compose)

    def test_dvr_seek_has_two_segment_safety_margin(self):
        html = PLAYER.read_text(encoding="utf-8")
        self.assertIn("playerConfig.dvr && playerConfig.dvr.enabled", html)
        self.assertIn("var safeStart = first + dvrSegmentDuration * 2", html)
        self.assertIn("player.currentTime(safeStart)", html)

    def test_burnin_and_player_share_overlay_assistant(self):
        player_overlay = (ROOT / "ui/src/views/Publication/PlayerOverlay.js").read_text(encoding="utf-8")
        burnin_overlay = (ROOT / "ui/src/misc/filters/video/TextOverlay.js").read_text(encoding="utf-8")
        self.assertIn("overlay-assistant-v2-burnin", player_overlay)
        self.assertIn("overlay-assistant-v2-player", player_overlay)
        self.assertIn("<PlayerOverlay", burnin_overlay)
        self.assertIn('assistantType="burnin"', burnin_overlay)
        self.assertIn("showAppearance={false}", burnin_overlay)

    def test_adaptive_player_and_bandwidth_guards_are_optional(self):
        html = PLAYER.read_text(encoding="utf-8")
        player_settings = (ROOT / "ui/src/views/Publication/Player.js").read_text(encoding="utf-8")
        restreamer = (ROOT / "ui/src/utils/restreamer.js").read_text(encoding="utf-8")

        self.assertIn("--lc-player-ratio", html)
        self.assertIn("playerPlayback.aspectRatio === '4:3'", html)
        self.assertIn("player.on('loadedmetadata'", html)
        self.assertIn("BroadcastChannel", html)
        self.assertIn("livechasing-active-player-v1", html)
        self.assertIn("player.reset()", html)
        self.assertIn("sessionLimitMinutes", html)
        self.assertIn("playbackGateButton.addEventListener('click'", html)
        self.assertIn("Automatically detect 16:9 or 4:3", player_settings)
        self.assertIn("Allow only one active stream per viewer", player_settings)
        self.assertIn("Require Play again after 15 minutes", player_settings)
        self.assertIn("autoAspectRatio: true", restreamer)
        self.assertIn("singleActiveStream: true", restreamer)
        self.assertIn("sessionLimitEnabled: true", restreamer)
        self.assertIn("aspect-ratio:${cssRatio}", restreamer)

    def test_forced_player_reactivation_has_no_duplicate_load(self):
        html = PLAYER.read_text(encoding="utf-8")

        self.assertIn("var playbackActivationPending = false", html)
        self.assertIn("clearPlaybackActivation", html)
        self.assertIn("restorePlaybackGate", html)
        self.assertIn("12000", html)
        self.assertNotIn("player.load();", html)

    def test_legacy_logo_tab_and_renderer_are_removed(self):
        html = PLAYER.read_text(encoding="utf-8")
        player_settings = (ROOT / "ui/src/views/Publication/Player.js").read_text(encoding="utf-8")
        player_component = (ROOT / "ui/src/misc/Player/index.js").read_text(encoding="utf-8")

        self.assertNotIn('value="logo"', player_settings)
        self.assertNotIn('index="logo"', player_settings)
        self.assertNotIn("handleLogoUpload", player_settings)
        self.assertNotIn("playerConfig.logo.image", html)
        self.assertNotIn("logo.image.length", player_component)

    def test_unique_viewer_identity_is_propagated(self):
        html = PLAYER.read_text(encoding="utf-8")
        middleware = (ROOT / "core/http/middleware/session/HLS.go").read_text(encoding="utf-8")
        footer = (ROOT / "ui/src/Footer.js").read_text(encoding="utf-8")
        restreamer = (ROOT / "ui/src/utils/restreamer.js").read_text(encoding="utf-8")

        self.assertIn("livechasing-viewer-id-v1", html)
        self.assertIn("publicSourceURL.searchParams.set('viewer', viewerToken)", html)
        self.assertIn('extra = "[viewer:" + viewerID + "] " + extra', middleware)
        self.assertIn("q.Set(\"viewer\", viewerID)", middleware)
        self.assertIn("countUniqueHLSViewers", restreamer)
        self.assertIn("core.viewer_used", footer)

    def test_nkl_branding_and_background_are_active(self):
        package = (ROOT / "ui/package.json").read_text(encoding="utf-8")
        version = (ROOT / "ui/src/version.js").read_text(encoding="utf-8")
        global_theme = (ROOT / "ui/src/theme/global.js").read_text(encoding="utf-8")
        background = ROOT / "ui/src/assets/images/vortex-background.jpg"

        release = (ROOT / "release.env").read_text(encoding="utf-8")
        label = re.search(r'^PRODUCT_LABEL="Vortex (.+)"$', release, re.MULTILINE)
        self.assertIsNotNone(label)
        self.assertEqual(json.loads(package)["nklVersion"], label.group(1))
        self.assertIn("`Vortex ${pkg.nklVersion || Version}`", version)
        self.assertIn("vortex-background.jpg", global_theme)
        self.assertTrue(background.is_file())
        self.assertGreater(background.stat().st_size, 100000)

    def test_nkl_update_flow_uses_only_the_fork_repository(self):
        version = (ROOT / "ui/src/version.js").read_text(encoding="utf-8")
        restreamer = (ROOT / "ui/src/utils/restreamer.js").read_text(encoding="utf-8")
        settings = (ROOT / "ui/src/views/Settings.js").read_text(encoding="utf-8")
        core_update = (ROOT / "core/update/update.go").read_text(encoding="utf-8")
        installer = (ROOT / "install.sh").read_text(encoding="utf-8")
        agent = (ROOT / "scripts/nkl-update-agent.sh").read_text(encoding="utf-8")

        repository = "glatzkopf94/vortex"
        self.assertIn(repository, version)
        self.assertIn("InstallLatestUpdate", restreamer)
        self.assertIn("install-latest-nkl-release", restreamer)
        self.assertIn("Install update", settings)
        self.assertIn(repository, core_update)
        self.assertNotIn("service.datarhei.com/api/v1/app_version", core_update)
        self.assertIn("install_update_agent", installer)
        self.assertIn("foreign-image-blocked", agent)
        self.assertIn("sha256sum --check", agent)

        compose = (ROOT / "compose.yaml").read_text(encoding="utf-8")
        env_example = (ROOT / ".env.example").read_text(encoding="utf-8")
        self.assertIn("restreamer-nkl:", compose)
        self.assertIn("RESTREAMER_CONTAINER_NAME=vortex", env_example)
        self.assertIn("RESTREAMER_CONFIG_VOLUME=restreamer-nkl-config", env_example)
        self.assertIn("RESTREAMER_DATA_VOLUME=restreamer-nkl-data", env_example)


if __name__ == "__main__":
    unittest.main()
