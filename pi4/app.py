#!/usr/bin/env python3
"""Pocket IPTV v2 - Raspberry Pi 4 touchscreen player."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re
import shutil
import sys
from typing import Optional

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QKeySequence
from PyQt5.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QShortcut,
    QSlider,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

import vlc


APP_DIR = Path.home() / "PocketIPTV"
CONFIG_DIR = Path.home() / ".config" / "pocket-iptv"
CONFIG_FILE = CONFIG_DIR / "config.json"
DEFAULT_PLAYLIST = APP_DIR / "channels.m3u"

ATTR_RE = re.compile(r'([\w-]+)="([^"]*)"')


@dataclass
class Channel:
    name: str
    url: str
    group: str = "Other"
    logo: str = ""
    user_agent: str = ""
    referrer: str = ""


def parse_m3u(path: Path) -> list[Channel]:
    channels: list[Channel] = []
    if not path.exists():
        return channels

    current_name = ""
    current_group = "Other"
    current_logo = ""
    current_user_agent = ""
    current_referrer = ""

    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line:
            continue

        if line.startswith("#EXTINF"):
            attrs = dict(ATTR_RE.findall(line))
            current_group = attrs.get("group-title", "Other") or "Other"
            current_logo = attrs.get("tvg-logo", "")
            current_name = line.split(",", 1)[1].strip() if "," in line else "Channel"
            current_user_agent = ""
            current_referrer = ""
            continue

        if line.startswith("#EXTVLCOPT:http-user-agent="):
            current_user_agent = line.split("=", 1)[1].strip()
            continue

        if line.startswith("#EXTVLCOPT:http-referrer="):
            current_referrer = line.split("=", 1)[1].strip()
            continue

        if line.startswith("#"):
            continue

        if "://" in line or line.startswith(("file:", "/")):
            name = current_name or f"Channel {len(channels) + 1}"
            channels.append(
                Channel(
                    name=name,
                    url=line,
                    group=current_group,
                    logo=current_logo,
                    user_agent=current_user_agent,
                    referrer=current_referrer,
                )
            )
            current_name = ""
            current_group = "Other"
            current_logo = ""
            current_user_agent = ""
            current_referrer = ""

    return channels


class PocketIPTV(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Pocket IPTV")
        self.resize(1024, 600)

        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        APP_DIR.mkdir(parents=True, exist_ok=True)

        self.settings = self._load_settings()
        self.playlist_path = Path(self.settings.get("playlist", str(DEFAULT_PLAYLIST)))
        self.favorites = set(self.settings.get("favorites", []))
        self.channels: list[Channel] = []
        self.filtered_indexes: list[int] = []
        self.current_index: Optional[int] = None
        self.last_playing_index: Optional[int] = None
        self.retry_count = 0

        self.vlc_instance = vlc.Instance(
            "--no-video-title-show",
            "--network-caching=1200",
            "--live-caching=1200",
            "--file-caching=500",
            "--quiet",
        )
        self.player = self.vlc_instance.media_player_new()

        self._build_ui()
        self._wire_shortcuts()
        self.reload_playlist()

        QTimer.singleShot(250, self._bind_video_output)
        self.status_timer = QTimer(self)
        self.status_timer.timeout.connect(self._poll_player)
        self.status_timer.start(500)

    def _build_ui(self) -> None:
        root = QWidget()
        self.setCentralWidget(root)
        outer = QVBoxLayout(root)
        outer.setContentsMargins(8, 8, 8, 8)
        outer.setSpacing(8)

        top = QHBoxLayout()
        self.channels_button = QPushButton("☰ Channels")
        self.channels_button.clicked.connect(self.toggle_channel_panel)
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search channels")
        self.search.textChanged.connect(self.apply_filter)
        self.group = QComboBox()
        self.group.currentTextChanged.connect(self.apply_filter)
        self.reload_button = QPushButton("Reload")
        self.reload_button.clicked.connect(self.reload_playlist)
        self.import_button = QPushButton("Import M3U")
        self.import_button.clicked.connect(self.import_playlist)

        top.addWidget(self.channels_button)
        top.addWidget(self.search, 2)
        top.addWidget(self.group, 1)
        top.addWidget(self.reload_button)
        top.addWidget(self.import_button)
        outer.addLayout(top)

        self.splitter = QSplitter(Qt.Horizontal)
        self.channel_list = QListWidget()
        self.channel_list.setMinimumWidth(270)
        self.channel_list.itemClicked.connect(self._channel_clicked)
        self.channel_list.itemActivated.connect(self._channel_clicked)
        self.splitter.addWidget(self.channel_list)

        player_side = QWidget()
        player_layout = QVBoxLayout(player_side)
        player_layout.setContentsMargins(0, 0, 0, 0)
        player_layout.setSpacing(8)

        self.video_frame = QFrame()
        self.video_frame.setFrameShape(QFrame.NoFrame)
        self.video_frame.setStyleSheet("background: black;")
        self.video_frame.setMinimumSize(320, 240)
        player_layout.addWidget(self.video_frame, 1)

        self.now_playing = QLabel("No channel selected")
        self.now_playing.setAlignment(Qt.AlignCenter)
        player_layout.addWidget(self.now_playing)

        controls = QHBoxLayout()
        self.prev_button = QPushButton("◀ Prev")
        self.play_button = QPushButton("▶ Play")
        self.next_button = QPushButton("Next ▶")
        self.fav_button = QPushButton("☆ Favorite")
        self.mute_button = QPushButton("Mute")
        self.volume = QSlider(Qt.Horizontal)
        self.volume.setRange(0, 100)
        self.volume.setValue(int(self.settings.get("volume", 70)))
        self.volume.setMinimumWidth(150)

        self.prev_button.clicked.connect(self.previous_channel)
        self.play_button.clicked.connect(self.toggle_play)
        self.next_button.clicked.connect(self.next_channel)
        self.fav_button.clicked.connect(self.toggle_favorite)
        self.mute_button.clicked.connect(self.toggle_mute)
        self.volume.valueChanged.connect(self.set_volume)

        controls.addWidget(self.prev_button)
        controls.addWidget(self.play_button)
        controls.addWidget(self.next_button)
        controls.addWidget(self.fav_button)
        controls.addWidget(self.mute_button)
        controls.addWidget(QLabel("Vol"))
        controls.addWidget(self.volume, 1)
        player_layout.addLayout(controls)

        self.status = QLabel("Ready")
        player_layout.addWidget(self.status)

        self.splitter.addWidget(player_side)
        self.splitter.setStretchFactor(1, 1)
        self.splitter.setSizes([300, 724])
        outer.addWidget(self.splitter, 1)

        self.setStyleSheet(
            """
            QWidget { font-size: 18px; background: #111; color: #f5f5f5; }
            QPushButton { min-height: 48px; padding: 4px 12px; border-radius: 8px; background: #2b2b2b; }
            QPushButton:pressed { background: #444; }
            QLineEdit, QComboBox, QListWidget { min-height: 44px; background: #1b1b1b; border: 1px solid #444; border-radius: 6px; padding: 4px; }
            QListWidget::item { min-height: 44px; padding: 4px 8px; }
            QListWidget::item:selected { background: #3a3a3a; }
            QSlider { min-height: 44px; }
            """
        )

    def _wire_shortcuts(self) -> None:
        QShortcut(QKeySequence("Space"), self, activated=self.toggle_play)
        QShortcut(QKeySequence("Right"), self, activated=self.next_channel)
        QShortcut(QKeySequence("Left"), self, activated=self.previous_channel)
        QShortcut(QKeySequence("F11"), self, activated=self.toggle_fullscreen)
        QShortcut(QKeySequence("Escape"), self, activated=self.exit_fullscreen)

    def _load_settings(self) -> dict:
        try:
            return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def _save_settings(self) -> None:
        data = {
            "playlist": str(self.playlist_path),
            "favorites": sorted(self.favorites),
            "volume": self.volume.value() if hasattr(self, "volume") else 70,
            "last_channel_url": (
                self.channels[self.current_index].url
                if self.current_index is not None and self.channels
                else ""
            ),
        }
        CONFIG_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def reload_playlist(self) -> None:
        self.channels = parse_m3u(self.playlist_path)
        self.group.blockSignals(True)
        self.group.clear()
        groups = sorted({c.group for c in self.channels})
        self.group.addItem("All groups")
        self.group.addItem("★ Favorites")
        self.group.addItems(groups)
        self.group.blockSignals(False)
        self.apply_filter()

        if not self.channels:
            self.status.setText(f"No channels found in {self.playlist_path}")
            self.now_playing.setText("Import an M3U playlist to begin")
            return

        last_url = self.settings.get("last_channel_url", "")
        index = next((i for i, c in enumerate(self.channels) if c.url == last_url), 0)
        self.current_index = index
        self._highlight_current()
        self.status.setText(f"Loaded {len(self.channels)} channels")

    def apply_filter(self) -> None:
        text = self.search.text().strip().lower()
        group = self.group.currentText()
        self.channel_list.clear()
        self.filtered_indexes = []

        for index, channel in enumerate(self.channels):
            if text and text not in channel.name.lower() and text not in channel.group.lower():
                continue
            if group == "★ Favorites" and channel.url not in self.favorites:
                continue
            if group not in ("", "All groups", "★ Favorites") and channel.group != group:
                continue
            star = "★ " if channel.url in self.favorites else ""
            item = QListWidgetItem(f"{star}{channel.name}")
            item.setToolTip(channel.group)
            item.setData(Qt.UserRole, index)
            self.channel_list.addItem(item)
            self.filtered_indexes.append(index)

        self._highlight_current()

    def _channel_clicked(self, item: QListWidgetItem) -> None:
        index = int(item.data(Qt.UserRole))
        self.play_channel(index)

    def play_channel(self, index: int, reconnecting: bool = False) -> None:
        if not 0 <= index < len(self.channels):
            return

        self.current_index = index
        self.last_playing_index = index
        if not reconnecting:
            self.retry_count = 0
        channel = self.channels[index]
        media = self.vlc_instance.media_new(channel.url)
        if channel.user_agent:
            media.add_option(f":http-user-agent={channel.user_agent}")
        if channel.referrer:
            media.add_option(f":http-referrer={channel.referrer}")
        media.add_option(":network-caching=1200")
        self.player.set_media(media)
        self._bind_video_output()
        self.player.audio_set_volume(self.volume.value())
        result = self.player.play()
        self.now_playing.setText(f"{channel.name}  •  {channel.group}")
        self.status.setText("Connecting…" if result != -1 else "Could not start VLC")
        self._highlight_current()
        self._save_settings()

    def _bind_video_output(self) -> None:
        try:
            wid = int(self.video_frame.winId())
            if sys.platform.startswith("linux"):
                self.player.set_xwindow(wid)
            elif sys.platform.startswith("win"):
                self.player.set_hwnd(wid)
            elif sys.platform == "darwin":
                self.player.set_nsobject(wid)
        except Exception as exc:
            self.status.setText(f"Video surface error: {exc}")

    def toggle_play(self) -> None:
        if not self.channels:
            return
        state = self.player.get_state()
        if state in (vlc.State.Playing, vlc.State.Buffering):
            self.player.pause()
        elif state == vlc.State.Paused:
            self.player.play()
        else:
            self.play_channel(self.current_index if self.current_index is not None else 0)

    def next_channel(self) -> None:
        if not self.channels:
            return
        start = self.current_index if self.current_index is not None else -1
        self.play_channel((start + 1) % len(self.channels))

    def previous_channel(self) -> None:
        if not self.channels:
            return
        start = self.current_index if self.current_index is not None else 0
        self.play_channel((start - 1) % len(self.channels))

    def toggle_favorite(self) -> None:
        if self.current_index is None or not self.channels:
            return
        url = self.channels[self.current_index].url
        if url in self.favorites:
            self.favorites.remove(url)
        else:
            self.favorites.add(url)
        self._save_settings()
        self.apply_filter()
        self._update_favorite_button()

    def toggle_mute(self) -> None:
        muted = bool(self.player.audio_get_mute())
        self.player.audio_set_mute(not muted)
        self.mute_button.setText("Unmute" if not muted else "Mute")

    def set_volume(self, value: int) -> None:
        self.player.audio_set_volume(int(value))
        self._save_settings()

    def import_playlist(self) -> None:
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Choose M3U playlist",
            str(Path.home()),
            "M3U playlists (*.m3u *.m3u8);;All files (*)",
        )
        if not filename:
            return
        source = Path(filename)
        destination = DEFAULT_PLAYLIST
        try:
            if source.resolve() != destination.resolve():
                shutil.copy2(source, destination)
        except OSError as exc:
            QMessageBox.critical(self, "Import failed", str(exc))
            return
        self.playlist_path = destination
        self.settings["playlist"] = str(destination)
        self._save_settings()
        self.reload_playlist()

    def _highlight_current(self) -> None:
        if self.current_index is None:
            return
        for row in range(self.channel_list.count()):
            item = self.channel_list.item(row)
            if item.data(Qt.UserRole) == self.current_index:
                self.channel_list.setCurrentRow(row)
                break
        self._update_favorite_button()

    def _update_favorite_button(self) -> None:
        if self.current_index is None or not self.channels:
            self.fav_button.setText("☆ Favorite")
            return
        url = self.channels[self.current_index].url
        self.fav_button.setText("★ Favorite" if url in self.favorites else "☆ Favorite")

    def toggle_channel_panel(self) -> None:
        self.channel_list.setVisible(not self.channel_list.isVisible())

    def toggle_fullscreen(self) -> None:
        self.showNormal() if self.isFullScreen() else self.showFullScreen()

    def exit_fullscreen(self) -> None:
        if self.isFullScreen():
            self.showNormal()

    def _poll_player(self) -> None:
        state = self.player.get_state()
        if state == vlc.State.Playing:
            self.play_button.setText("⏸ Pause")
            self.status.setText("Playing")
            self.retry_count = 0
        elif state == vlc.State.Paused:
            self.play_button.setText("▶ Play")
            self.status.setText("Paused")
        elif state == vlc.State.Buffering:
            self.play_button.setText("⏸ Pause")
            self.status.setText("Buffering…")
        elif state in (vlc.State.Error, vlc.State.Ended):
            self.play_button.setText("▶ Play")
            if self.last_playing_index is not None and self.retry_count < 3:
                self.retry_count += 1
                self.status.setText(f"Reconnecting ({self.retry_count}/3)…")
                index = self.last_playing_index
                QTimer.singleShot(1500, lambda idx=index: self.play_channel(idx, reconnecting=True))
            else:
                self.status.setText("Stream stopped — tap Play to retry")
        else:
            self.play_button.setText("▶ Play")

    def closeEvent(self, event) -> None:
        self._save_settings()
        self.player.stop()
        event.accept()


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Pocket IPTV")
    window = PocketIPTV()
    window.showFullScreen()
    return app.exec_()


if __name__ == "__main__":
    raise SystemExit(main())
