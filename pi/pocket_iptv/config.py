"""Typed configuration loading and validation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import tomllib


@dataclass(frozen=True)
class ServerConfig:
    host: str = "0.0.0.0"
    port: int = 8080
    admin_pin: str = "000000"
    secret_key: str = "change-me"


@dataclass(frozen=True)
class ScreenConfig:
    serial_port: str = "auto"
    baud: int = 2_000_000
    width: int = 320
    height: int = 240
    fps: int = 8
    jpeg_quality: int = 12
    audio_sample_rate: int = 16_000


@dataclass(frozen=True)
class PlaybackConfig:
    playlist: str = "/etc/pocket-iptv/channels.m3u"
    start_channel: int = 0
    volume: int = 65
    user_agent: str = "PocketIPTV/1.0"
    ffmpeg_path: str = "/usr/bin/ffmpeg"
    reconnect_delay: float = 2.0


@dataclass(frozen=True)
class AppConfig:
    server: ServerConfig
    screen: ScreenConfig
    playback: PlaybackConfig
    path: Path


def _section(data: dict, name: str) -> dict:
    value = data.get(name, {})
    if not isinstance(value, dict):
        raise ValueError(f"[{name}] must be a TOML table")
    return value


def load_config(path: str | Path) -> AppConfig:
    config_path = Path(path)
    with config_path.open("rb") as handle:
        data = tomllib.load(handle)

    server = ServerConfig(**_section(data, "server"))
    screen = ScreenConfig(**_section(data, "screen"))
    playback = PlaybackConfig(**_section(data, "playback"))
    _validate(server, screen, playback)
    return AppConfig(server, screen, playback, config_path)


def _validate(
    server: ServerConfig,
    screen: ScreenConfig,
    playback: PlaybackConfig,
) -> None:
    if not 1 <= server.port <= 65535:
        raise ValueError("server.port must be 1..65535")
    if not (server.admin_pin.isdigit() and 4 <= len(server.admin_pin) <= 12):
        raise ValueError("server.admin_pin must contain 4..12 digits")
    if len(server.secret_key) < 16:
        raise ValueError("server.secret_key must contain at least 16 characters")
    if (screen.width, screen.height) != (320, 240):
        raise ValueError("release 1.0 firmware requires screen width=320 and height=240")
    if not 1 <= screen.fps <= 15:
        raise ValueError("screen.fps must be 1..15")
    if not 2 <= screen.jpeg_quality <= 31:
        raise ValueError("screen.jpeg_quality must be 2..31")
    if not 115_200 <= screen.baud <= 3_000_000:
        raise ValueError("screen.baud must be 115200..3000000")
    if screen.audio_sample_rate != 16_000:
        raise ValueError("release 1.0 firmware requires audio_sample_rate=16000")
    if not 0 <= playback.volume <= 100:
        raise ValueError("playback.volume must be 0..100")
    if playback.start_channel < 0:
        raise ValueError("playback.start_channel cannot be negative")
    if playback.reconnect_delay < 0.5:
        raise ValueError("playback.reconnect_delay must be at least 0.5 seconds")
