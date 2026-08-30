import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import threading
import unittest

from pocket_iptv.config import load_config
from pocket_iptv.m3u import Channel
from pocket_iptv.player import build_ffmpeg_command


@unittest.skipUnless(shutil.which("ffmpeg"), "FFmpeg is not installed")
class FFmpegSmokeTests(unittest.TestCase):
    def test_real_ffmpeg_produces_jpeg_and_pcm(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "sample.mp4"
            subprocess.run(
                [
                    shutil.which("ffmpeg"),
                    "-hide_banner",
                    "-loglevel",
                    "error",
                    "-f",
                    "lavfi",
                    "-i",
                    "testsrc2=size=640x360:rate=24",
                    "-f",
                    "lavfi",
                    "-i",
                    "sine=frequency=440:sample_rate=48000",
                    "-t",
                    "1.2",
                    "-c:v",
                    "mpeg4",
                    "-c:a",
                    "aac",
                    str(source),
                ],
                check=True,
                timeout=15,
            )
            config_path = root / "config.toml"
            config_path.write_text(
                f'''[server]
admin_pin="123456"
secret_key="0123456789abcdef0123456789abcdef"
[screen]
fps=8
jpeg_quality=12
[playback]
volume=65
ffmpeg_path="{shutil.which("ffmpeg")}"
'''
            )
            config = load_config(config_path)
            video_read, video_write = os.pipe()
            audio_read, audio_write = os.pipe()
            command = build_ffmpeg_command(
                Channel("Local test", source.as_uri()),
                config,
                video_write,
                audio_write,
            )
            process = subprocess.Popen(
                command,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                pass_fds=(video_write, audio_write),
            )
            os.close(video_write)
            os.close(audio_write)
            result = {}

            def collect(name, fd):
                chunks = []
                while True:
                    chunk = os.read(fd, 8192)
                    if not chunk:
                        break
                    chunks.append(chunk)
                os.close(fd)
                result[name] = b"".join(chunks)

            video_thread = threading.Thread(target=collect, args=("video", video_read))
            audio_thread = threading.Thread(target=collect, args=("audio", audio_read))
            video_thread.start()
            audio_thread.start()
            _, errors = process.communicate(timeout=15)
            video_thread.join(timeout=2)
            audio_thread.join(timeout=2)
            self.assertEqual(process.returncode, 0, errors.decode(errors="replace"))
            self.assertIn(b"\xff\xd8", result["video"])
            self.assertIn(b"\xff\xd9", result["video"])
            self.assertGreater(len(result["audio"]), 8_000)


if __name__ == "__main__":
    unittest.main()
