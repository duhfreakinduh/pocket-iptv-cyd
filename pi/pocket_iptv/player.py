"""FFmpeg playback, media queues, serial transport, and touch commands."""

from __future__ import annotations

from collections import deque
import itertools
import logging
import os
from pathlib import Path
import queue
import re
import signal
import subprocess
import threading
import time
from urllib.parse import urlparse

from .config import AppConfig
from .m3u import Channel, load_playlist
from .protocol import PacketType, ScreenState, build_packet, encode_state
from .serial_link import SerialLink

LOGGER = logging.getLogger(__name__)
URL_RE = re.compile(r"(?:https?|rtsp|rtmp)://\S+", re.IGNORECASE)
JPEG_START = b"\xff\xd8"
JPEG_END = b"\xff\xd9"


def _redact(message: str) -> str:
    return URL_RE.sub("<stream-url>", message)


def build_ffmpeg_command(
    channel: Channel,
    config: AppConfig,
    video_fd: int,
    audio_fd: int | None,
) -> list[str]:
    screen = config.screen
    playback = config.playback
    command = [
        playback.ffmpeg_path,
        "-hide_banner",
        "-loglevel",
        "warning",
        "-nostdin",
    ]
    scheme = urlparse(channel.url).scheme.lower()
    if scheme in {"http", "https"}:
        command.extend(
            [
                "-reconnect",
                "1",
                "-reconnect_streamed",
                "1",
                "-reconnect_at_eof",
                "1",
                "-reconnect_delay_max",
                "3",
            ]
        )
        agent = channel.user_agent or playback.user_agent
        if agent:
            command.extend(["-user_agent", agent])
        if channel.referrer:
            command.extend(["-referer", channel.referrer])
    elif scheme == "rtsp":
        command.extend(["-rtsp_transport", "tcp"])
    elif scheme == "file" or not scheme:
        command.append("-re")

    command.extend(["-i", channel.url])
    video_filter = (
        f"fps={screen.fps},"
        f"scale={screen.width}:{screen.height}:"
        "force_original_aspect_ratio=decrease:flags=fast_bilinear,"
        f"pad={screen.width}:{screen.height}:(ow-iw)/2:(oh-ih)/2:black,"
        "format=yuvj420p"
    )
    command.extend(
        [
            "-map",
            "0:v:0",
            "-an",
            "-vf",
            video_filter,
            "-c:v",
            "mjpeg",
            "-q:v",
            str(screen.jpeg_quality),
            "-f",
            "image2pipe",
            f"pipe:{video_fd}",
        ]
    )
    if audio_fd is not None:
        command.extend(
            [
                "-map",
                "0:a:0?",
                "-vn",
                "-ac",
                "1",
                "-ar",
                str(screen.audio_sample_rate),
                "-c:a",
                "pcm_u8",
                "-f",
                "u8",
                f"pipe:{audio_fd}",
            ]
        )
    return command


class Player:
    def __init__(self, config: AppConfig, channels: list[Channel]) -> None:
        self.config = config
        self.channels = channels
        self.current_index = min(config.playback.start_channel, max(0, len(channels) - 1))
        self.volume = config.playback.volume
        self.paused = False
        self._stop = threading.Event()
        self._lock = threading.RLock()
        self._process: subprocess.Popen | None = None
        self._generation = 0
        self._sequence = itertools.count(1)
        self._video_queue: queue.Queue[bytes] = queue.Queue(maxsize=1)
        self._audio_queue: queue.Queue[bytes] = queue.Queue(maxsize=32)
        self._state_queue: queue.Queue[bytes] = queue.Queue(maxsize=1)
        self._last_error = ""
        self._errors: dict[int, deque[str]] = {}
        self._writer: threading.Thread | None = None
        self.link = SerialLink(
            config.screen.serial_port,
            config.screen.baud,
            self.handle_command,
            self._queue_state,
        )

    def start(self) -> None:
        self.link.start()
        self._writer = threading.Thread(
            target=self._writer_loop, name="screen-writer", daemon=True
        )
        self._writer.start()
        if self.channels:
            with self._lock:
                self._start_current_locked()
        else:
            LOGGER.warning("Playlist contains no supported channels")

    def stop(self) -> None:
        self._stop.set()
        with self._lock:
            self._stop_process_locked()
        self.link.stop()
        if self._writer:
            self._writer.join(timeout=2)

    def status(self) -> dict:
        with self._lock:
            channel = self.channels[self.current_index] if self.channels else None
            return {
                "channel_index": self.current_index,
                "channel_name": channel.name if channel else "No playlist",
                "channel_group": channel.group if channel else "",
                "channel_total": len(self.channels),
                "volume": self.volume,
                "paused": self.paused,
                "screen_connected": self.link.connected,
                "screen_port": self.link.port,
                "last_error": self._last_error,
                "channels": [
                    {"index": index, "name": item.name, "group": item.group}
                    for index, item in enumerate(self.channels)
                ],
            }

    def handle_command(self, command: str) -> None:
        command = command.strip().lower()
        LOGGER.info("Touch command: %s", command)
        if command == "next":
            self.next_channel()
        elif command == "prev":
            self.previous_channel()
        elif command in {"toggle", "play", "pause"}:
            self.toggle_pause()
        elif command == "vol_up":
            self.set_volume(self.volume + 5)
        elif command == "vol_down":
            self.set_volume(self.volume - 5)
        elif command == "ready":
            self._queue_state()
        elif command.startswith("select:"):
            try:
                self.select_channel(int(command.split(":", 1)[1]))
            except ValueError:
                LOGGER.warning("Ignored malformed select command")

    def next_channel(self) -> None:
        if self.channels:
            self.select_channel((self.current_index + 1) % len(self.channels))

    def previous_channel(self) -> None:
        if self.channels:
            self.select_channel((self.current_index - 1) % len(self.channels))

    def select_channel(self, index: int) -> None:
        with self._lock:
            if not 0 <= index < len(self.channels):
                raise IndexError("channel index is out of range")
            self.current_index = index
            self.paused = False
            self._start_current_locked()

    def toggle_pause(self) -> None:
        with self._lock:
            if not self.channels:
                return
            self.paused = not self.paused
            if self.paused:
                self._generation += 1
                self._stop_process_locked()
                self._clear_queue(self._audio_queue)
            else:
                self._start_current_locked()
            self._queue_state()

    def set_volume(self, value: int) -> None:
        with self._lock:
            self.volume = max(0, min(100, int(value)))
            self._queue_state()

    def reload_playlist(self, path: str | Path | None = None) -> int:
        playlist_path = path or self.config.playback.playlist
        channels = load_playlist(playlist_path)
        if not channels:
            raise ValueError("playlist has no supported channel URLs")
        with self._lock:
            old_name = (
                self.channels[self.current_index].name if self.channels else ""
            )
            self.channels = channels
            matches = [i for i, item in enumerate(channels) if item.name == old_name]
            self.current_index = matches[0] if matches else 0
            self.paused = False
            self._start_current_locked()
        return len(channels)

    def _queue_state(self) -> None:
        with self._lock:
            channel_name = (
                self.channels[self.current_index].name if self.channels else "No playlist"
            )
            payload = encode_state(
                ScreenState(
                    self.volume,
                    self.paused,
                    self.current_index,
                    len(self.channels),
                    channel_name,
                )
            )
        self._put_latest(self._state_queue, payload)

    def _start_current_locked(self) -> None:
        self._generation += 1
        generation = self._generation
        self._stop_process_locked()
        self._clear_queue(self._video_queue)
        self._clear_queue(self._audio_queue)
        self._last_error = ""
        self._queue_state()
        if self.paused or not self.channels:
            return
        self._spawn_ffmpeg_locked(self.channels[self.current_index], generation, True)

    def _spawn_ffmpeg_locked(
        self, channel: Channel, generation: int, audio_enabled: bool
    ) -> None:
        video_read, video_write = os.pipe()
        audio_read = audio_write = None
        pass_fds = [video_write]
        if audio_enabled:
            audio_read, audio_write = os.pipe()
            pass_fds.append(audio_write)
        command = build_ffmpeg_command(channel, self.config, video_write, audio_write)
        LOGGER.info(
            "Starting channel %d/%d: %s",
            self.current_index + 1,
            len(self.channels),
            channel.name,
        )
        try:
            process = subprocess.Popen(
                command,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                pass_fds=tuple(pass_fds),
                start_new_session=True,
                close_fds=True,
            )
        except Exception:
            os.close(video_read)
            os.close(video_write)
            if audio_read is not None:
                os.close(audio_read)
            if audio_write is not None:
                os.close(audio_write)
            raise
        os.close(video_write)
        if audio_write is not None:
            os.close(audio_write)
        self._process = process
        self._errors[generation] = deque(maxlen=12)
        threading.Thread(
            target=self._video_reader,
            args=(video_read, generation),
            name=f"video-{generation}",
            daemon=True,
        ).start()
        if audio_read is not None:
            threading.Thread(
                target=self._audio_reader,
                args=(audio_read, generation),
                name=f"audio-{generation}",
                daemon=True,
            ).start()
        threading.Thread(
            target=self._stderr_reader,
            args=(process, generation),
            name=f"ffmpeg-log-{generation}",
            daemon=True,
        ).start()
        threading.Thread(
            target=self._monitor,
            args=(process, generation, channel, audio_enabled),
            name=f"ffmpeg-watch-{generation}",
            daemon=True,
        ).start()

    def _video_reader(self, fd: int, generation: int) -> None:
        buffer = bytearray()
        try:
            while not self._stop.is_set() and generation == self._generation:
                chunk = os.read(fd, 8192)
                if not chunk:
                    break
                buffer.extend(chunk)
                while True:
                    start = buffer.find(JPEG_START)
                    if start < 0:
                        if len(buffer) > 2:
                            del buffer[:-2]
                        break
                    end = buffer.find(JPEG_END, start + 2)
                    if end < 0:
                        if start:
                            del buffer[:start]
                        if len(buffer) > 64 * 1024:
                            buffer.clear()
                        break
                    frame = bytes(buffer[start : end + 2])
                    del buffer[: end + 2]
                    if len(frame) <= 64 * 1024:
                        self._put_latest(self._video_queue, frame)
        finally:
            os.close(fd)

    def _audio_reader(self, fd: int, generation: int) -> None:
        try:
            while not self._stop.is_set() and generation == self._generation:
                data = os.read(fd, 1024)
                if not data:
                    break
                self._put_bounded(self._audio_queue, data)
        finally:
            os.close(fd)

    def _stderr_reader(self, process: subprocess.Popen, generation: int) -> None:
        if process.stderr is None:
            return
        for raw in iter(process.stderr.readline, b""):
            message = _redact(raw.decode("utf-8", errors="replace").strip())
            if message:
                self._errors.setdefault(generation, deque(maxlen=12)).append(message)

    def _monitor(
        self,
        process: subprocess.Popen,
        generation: int,
        channel: Channel,
        audio_enabled: bool,
    ) -> None:
        return_code = process.wait()
        if self._stop.is_set():
            return
        errors = list(self._errors.pop(generation, []))
        no_audio = any(
            "does not contain any stream" in item.lower()
            or "matches no streams" in item.lower()
            for item in errors
        )
        with self._lock:
            if generation != self._generation or self.paused:
                return
            if audio_enabled and no_audio:
                LOGGER.info("Channel has no audio; retrying video-only")
                self._generation += 1
                new_generation = self._generation
                self._spawn_ffmpeg_locked(channel, new_generation, False)
                return
            self._last_error = errors[-1] if errors else f"FFmpeg exited ({return_code})"
        LOGGER.warning("Playback stopped: %s", self._last_error)
        if self._stop.wait(self.config.playback.reconnect_delay):
            return
        with self._lock:
            if generation == self._generation and not self.paused:
                self._generation += 1
                new_generation = self._generation
                self._spawn_ffmpeg_locked(channel, new_generation, audio_enabled)

    def _stop_process_locked(self) -> None:
        process, self._process = self._process, None
        if process is None or process.poll() is not None:
            return
        try:
            os.killpg(process.pid, signal.SIGTERM)
            process.wait(timeout=1.0)
        except (ProcessLookupError, subprocess.TimeoutExpired):
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass

    def _writer_loop(self) -> None:
        audio_burst = 0
        while not self._stop.is_set():
            if not self.link.connected:
                self._clear_queue(self._audio_queue)
                self._stop.wait(0.2)
                continue
            packet_type = None
            payload = None
            try:
                payload = self._state_queue.get_nowait()
                packet_type = PacketType.STATE
                audio_burst = 0
            except queue.Empty:
                pass
            if payload is None and audio_burst < 4:
                try:
                    payload = self._audio_queue.get_nowait()
                    packet_type = PacketType.PCM_U8
                    audio_burst += 1
                except queue.Empty:
                    pass
            if payload is None:
                try:
                    payload = self._video_queue.get_nowait()
                    packet_type = PacketType.JPEG
                    audio_burst = 0
                except queue.Empty:
                    pass
            if payload is None:
                try:
                    payload = self._audio_queue.get(timeout=0.01)
                    packet_type = PacketType.PCM_U8
                    audio_burst += 1
                except queue.Empty:
                    continue
            packet = build_packet(packet_type, next(self._sequence), payload)
            self.link.write(packet)

    @staticmethod
    def _put_latest(target: queue.Queue, value: bytes) -> None:
        try:
            target.put_nowait(value)
            return
        except queue.Full:
            pass
        try:
            target.get_nowait()
        except queue.Empty:
            pass
        try:
            target.put_nowait(value)
        except queue.Full:
            pass

    @staticmethod
    def _put_bounded(target: queue.Queue, value: bytes) -> None:
        try:
            target.put_nowait(value)
        except queue.Full:
            try:
                target.get_nowait()
                target.put_nowait(value)
            except (queue.Empty, queue.Full):
                pass

    @staticmethod
    def _clear_queue(target: queue.Queue) -> None:
        while True:
            try:
                target.get_nowait()
            except queue.Empty:
                return
