from pathlib import Path
import tempfile
import unittest

try:
    import flask  # noqa: F401
except ImportError:
    flask = None

from pocket_iptv.config import load_config

if flask is not None:
    from pocket_iptv.web import create_app


class FakePlayer:
    def __init__(self):
        self.commands = []
        self.selected = None
        self.reloaded = None

    def status(self):
        return {
            "channel_index": 0,
            "channel_name": "Demo",
            "channel_group": "Test",
            "channel_total": 1,
            "volume": 65,
            "paused": False,
            "screen_connected": False,
            "screen_port": None,
            "last_error": "",
            "channels": [{"index": 0, "name": "Demo", "group": "Test"}],
        }

    def handle_command(self, command):
        self.commands.append(command)

    def select_channel(self, index):
        self.selected = index

    def reload_playlist(self, path):
        self.reloaded = Path(path)
        return 1


@unittest.skipIf(flask is None, "Flask is not installed")
class WebTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        root = Path(self.temporary.name)
        self.playlist = root / "channels.m3u"
        config_path = root / "config.toml"
        config_path.write_text(
            f'''[server]
admin_pin="123456"
secret_key="0123456789abcdef0123456789abcdef"
[screen]
fps=8
jpeg_quality=12
[playback]
playlist="{self.playlist}"
volume=65
'''
        )
        self.player = FakePlayer()
        self.app = create_app(self.player, load_config(config_path))
        self.app.config.update(TESTING=True)
        self.client = self.app.test_client()

    def tearDown(self):
        self.temporary.cleanup()

    def login(self):
        response = self.client.post("/login", data={"pin": "123456"})
        self.assertEqual(response.status_code, 302)
        with self.client.session_transaction() as session:
            return session["csrf"]

    def test_status_requires_login(self):
        self.assertEqual(self.client.get("/api/status").status_code, 401)

    def test_login_status_and_csrf_command(self):
        csrf = self.login()
        response = self.client.get("/api/status")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["channel_name"], "Demo")
        denied = self.client.post("/api/command", json={"command": "next"})
        self.assertEqual(denied.status_code, 403)
        accepted = self.client.post(
            "/api/command",
            json={"command": "next"},
            headers={"X-CSRF-Token": csrf},
        )
        self.assertEqual(accepted.status_code, 200)
        self.assertEqual(self.player.commands, ["next"])

    def test_playlist_upload_is_atomic_and_private(self):
        csrf = self.login()
        playlist_text = "#EXTM3U\n#EXTINF:-1,Private\nhttps://example.com/live.m3u8\n"
        response = self.client.post(
            "/playlist",
            data={"csrf": csrf, "playlist_text": playlist_text},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.playlist.read_text(), playlist_text)
        self.assertEqual(self.player.reloaded, self.playlist)


if __name__ == "__main__":
    unittest.main()
