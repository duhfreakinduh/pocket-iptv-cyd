from pathlib import Path
import sys
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "pi"))
sys.path.insert(0, str(ROOT / "setup-wizard"))

from core import build_bundle, inspect_playlist, make_config


PLAYLIST = """#EXTM3U
#EXTINF:-1 group-title="Demo",Test
https://example.com/test.m3u8
"""


class WizardCoreTests(unittest.TestCase):
    def test_inspection_does_not_need_to_expose_url(self):
        report = inspect_playlist(PLAYLIST)
        self.assertEqual(report.channels[0].name, "Test")
        self.assertEqual(report.channels[0].group, "Demo")

    def test_config_uses_selected_safe_speed(self):
        config, pin = make_config(
            pin="123456", baud=921_600, fps=5, jpeg_quality=16, volume=50
        )
        self.assertEqual(pin, "123456")
        self.assertIn("baud = 921600", config)
        self.assertIn("fps = 5", config)

    def test_bundle_contains_only_expected_private_files(self):
        path, pin, report = build_bundle(PLAYLIST, pin="654321")
        self.assertEqual(pin, "654321")
        self.assertEqual(len(report.channels), 1)
        with zipfile.ZipFile(path) as archive:
            self.assertEqual(
                sorted(archive.namelist()),
                ["INSTALL.txt", "channels.m3u", "config.toml"],
            )
            self.assertIn("654321", archive.read("config.toml").decode())


if __name__ == "__main__":
    unittest.main()
