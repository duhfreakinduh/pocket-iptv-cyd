from pathlib import Path
import tempfile
import unittest

from pocket_iptv.config import load_config


VALID_CONFIG = """
[server]
admin_pin = "123456"
secret_key = "0123456789abcdef0123456789abcdef"
[screen]
fps = 8
jpeg_quality = 12
[playback]
volume = 65
"""


class ConfigTests(unittest.TestCase):
    def _load(self, text):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.toml"
            path.write_text(text)
            return load_config(path)

    def test_defaults_and_values(self):
        config = self._load(VALID_CONFIG)
        self.assertEqual(config.server.port, 8080)
        self.assertEqual(config.screen.baud, 2_000_000)
        self.assertEqual(config.playback.volume, 65)

    def test_bad_pin_rejected(self):
        with self.assertRaises(ValueError):
            self._load(VALID_CONFIG.replace("123456", "abc"))

    def test_bad_fps_rejected(self):
        with self.assertRaises(ValueError):
            self._load(VALID_CONFIG.replace("fps = 8", "fps = 99"))


if __name__ == "__main__":
    unittest.main()
