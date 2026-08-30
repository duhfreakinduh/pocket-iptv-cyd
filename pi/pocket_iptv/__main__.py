"""Pocket IPTV service entry point."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path
import signal
import threading

from werkzeug.serving import make_server

from .config import load_config
from .m3u import load_playlist
from .player import Player
from .web import create_app


def main() -> int:
    parser = argparse.ArgumentParser(description="Pocket IPTV CYD service")
    parser.add_argument(
        "--config",
        default="/etc/pocket-iptv/config.toml",
        help="Path to config.toml",
    )
    parser.add_argument("--log-level", default="INFO")
    args = parser.parse_args()
    logging.basicConfig(
        level=getattr(logging, args.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    config = load_config(args.config)
    playlist_path = Path(config.playback.playlist)
    channels = load_playlist(playlist_path) if playlist_path.exists() else []
    player = Player(config, channels)
    player.start()

    app = create_app(player, config)
    server = make_server(
        config.server.host,
        config.server.port,
        app,
        threaded=True,
    )
    server_thread = threading.Thread(
        target=server.serve_forever, name="web-server", daemon=True
    )
    server_thread.start()
    logging.getLogger(__name__).info(
        "Control page listening on http://%s:%d",
        config.server.host,
        config.server.port,
    )

    stopped = threading.Event()

    def request_stop(_signum, _frame):
        stopped.set()

    signal.signal(signal.SIGTERM, request_stop)
    signal.signal(signal.SIGINT, request_stop)
    stopped.wait()
    server.shutdown()
    player.stop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
