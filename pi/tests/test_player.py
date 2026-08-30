from pathlib import Path
import tempfile
import unittest

from pocket_iptv.config import load_config
from pocket_iptv.m3u import Channel
from pocket_iptv.player import build_ffmpeg_command


class PlayerCommandTests(unittest.TestCase):
    def test_http_command_has_two_private_pipe_outputs(self):
        text = """
[server]
admin_pin="123456"
secret_key="0123456789abcdef0123456789abcdef"
[screen]
fps=8
jpeg_quality=12
[playback]
volume=65
"""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.toml"
            path.write_text(text)
            config = load_config(path)
        channel = Channel("Demo", "https://example.com/live.m3u8")
        command = build_ffmpeg_command(channel, config, 7, 8)
        self.assertIn("-reconnect", command)
        self.assertIn("pipe:7", command)
        self.assertIn("pipe:8", command)
        self.assertIn("pcm_u8", command)
        self.assertIn("mjpeg", command)


if __name__ == "__main__":
    unittest.main()
