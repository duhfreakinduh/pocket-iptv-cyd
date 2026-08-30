"""Pure functions for the optional Gradio setup wizard."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import secrets
import tempfile
import zipfile

from pocket_iptv.m3u import Channel, parse_m3u


@dataclass(frozen=True)
class PlaylistReport:
    channels: list[Channel]
    warnings: list[str]


def inspect_playlist(text: str) -> PlaylistReport:
    if len(text.encode("utf-8")) > 2 * 1024 * 1024:
        raise ValueError("Playlist is larger than the 2 MB player limit.")
    channels = parse_m3u(text)
    if not channels:
        raise ValueError("No supported HTTP/HLS/RTSP channel URLs were found.")
    warnings: list[str] = []
    if any(item.drm_hint for item in channels):
        warnings.append("At least one entry advertises DRM and will not play.")
    insecure = sum(item.scheme == "http" for item in channels)
    if insecure:
        warnings.append(f"{insecure} channel URL(s) use unencrypted HTTP.")
    duplicates = len(channels) - len({item.url for item in channels})
    if duplicates:
        warnings.append(f"{duplicates} duplicate channel URL(s) were found.")
    if len(channels) > 500:
        warnings.append("More than 500 channels may make the phone page slow.")
    return PlaylistReport(channels, warnings)


def make_config(
    *,
    pin: str,
    baud: int,
    fps: int,
    jpeg_quality: int,
    volume: int,
) -> tuple[str, str]:
    pin = pin.strip()
    if not pin:
        pin = f"{secrets.randbelow(1_000_000):06d}"
    if not (pin.isdigit() and 4 <= len(pin) <= 12):
        raise ValueError("PIN must contain 4 to 12 digits, or be left blank.")
    if baud not in {921_600, 2_000_000}:
        raise ValueError("Choose the fast or safe serial speed.")
    if not 1 <= int(fps) <= 15:
        raise ValueError("FPS must be 1..15.")
    if not 2 <= int(jpeg_quality) <= 31:
        raise ValueError("JPEG quality must be 2..31.")
    if not 0 <= int(volume) <= 100:
        raise ValueError("Volume must be 0..100.")
    secret_key = secrets.token_hex(32)
    config = f'''[server]
host = "0.0.0.0"
port = 8080
admin_pin = "{pin}"
secret_key = "{secret_key}"

[screen]
serial_port = "auto"
baud = {baud}
width = 320
height = 240
fps = {int(fps)}
jpeg_quality = {int(jpeg_quality)}
audio_sample_rate = 16000

[playback]
playlist = "/etc/pocket-iptv/channels.m3u"
start_channel = 0
volume = {int(volume)}
user_agent = "PocketIPTV/1.0"
ffmpeg_path = "/usr/bin/ffmpeg"
reconnect_delay = 2.0
'''
    return config, pin


def build_bundle(
    playlist_text: str,
    *,
    pin: str = "",
    baud: int = 2_000_000,
    fps: int = 8,
    jpeg_quality: int = 12,
    volume: int = 65,
) -> tuple[Path, str, PlaylistReport]:
    report = inspect_playlist(playlist_text)
    if any(item.drm_hint for item in report.channels):
        raise ValueError("Remove DRM entries before building the player bundle.")
    config, resolved_pin = make_config(
        pin=pin,
        baud=int(baud),
        fps=int(fps),
        jpeg_quality=int(jpeg_quality),
        volume=int(volume),
    )
    output_dir = Path(tempfile.mkdtemp(prefix="pocket-iptv-config-"))
    output = output_dir / "pocket-iptv-config.zip"
    instructions = """Pocket IPTV private configuration

Copy config.toml and channels.m3u to /etc/pocket-iptv on your Pi, then run:

sudo chown pocketiptv:pocketiptv /etc/pocket-iptv/config.toml /etc/pocket-iptv/channels.m3u
sudo chmod 640 /etc/pocket-iptv/config.toml /etc/pocket-iptv/channels.m3u
sudo systemctl restart pocket-iptv

Never upload this ZIP or channels.m3u to GitHub. It may contain account tokens.
"""
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("config.toml", config)
        archive.writestr("channels.m3u", playlist_text)
        archive.writestr("INSTALL.txt", instructions)
    return output, resolved_pin, report
