import unittest

from pocket_iptv.m3u import parse_m3u


class M3UTests(unittest.TestCase):
    def test_parses_metadata_and_http_options(self):
        playlist = """#EXTM3U
#EXTINF:-1 tvg-id="abc" tvg-logo="https://img/logo.png" group-title="News",Local News
#EXTVLCOPT:http-referrer=https://example.com/
https://media.example.com/live.m3u8|User-Agent=Pocket%20Test
"""
        channels = parse_m3u(playlist)
        self.assertEqual(len(channels), 1)
        item = channels[0]
        self.assertEqual(item.name, "Local News")
        self.assertEqual(item.group, "News")
        self.assertEqual(item.tvg_id, "abc")
        self.assertEqual(item.user_agent, "Pocket Test")
        self.assertEqual(item.referrer, "https://example.com/")
        self.assertEqual(item.url, "https://media.example.com/live.m3u8")

    def test_plain_url_gets_safe_name(self):
        channels = parse_m3u("https://example.com/path/demo.m3u8")
        self.assertEqual(channels[0].name, "demo.m3u8")

    def test_unsupported_scheme_is_ignored(self):
        self.assertEqual(parse_m3u("javascript:alert(1)"), [])

    def test_drm_hint_is_preserved(self):
        playlist = """#EXTINF:-1,Protected
#KODIPROP:inputstream.adaptive.license_type=com.widevine.alpha
https://example.com/protected.mpd
"""
        channels = parse_m3u(playlist)
        self.assertEqual(len(channels), 1)
        self.assertTrue(channels[0].drm_hint)


if __name__ == "__main__":
    unittest.main()
