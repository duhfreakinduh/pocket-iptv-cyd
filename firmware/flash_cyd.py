#!/usr/bin/env python3
"""Flash one of the prebuilt merged CYD images with esptool."""

from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import sys

IMAGES = {
    "ili9341": "cyd_ili9341.bin",
    "st7789": "cyd_st7789.bin",
    "ili9341-safe": "cyd_ili9341_safe.bin",
    "st7789-safe": "cyd_st7789_safe.bin",
}


def main() -> int:
    parser = argparse.ArgumentParser(description="Flash Pocket IPTV CYD firmware")
    parser.add_argument(
        "--variant",
        choices=IMAGES,
        default="ili9341",
        help="Display controller and serial-speed profile",
    )
    parser.add_argument(
        "--port",
        help="Optional serial port such as COM3 or /dev/ttyUSB0; auto-detect if omitted",
    )
    parser.add_argument("--baud", type=int, default=460800, help="Flashing baud rate")
    args = parser.parse_args()

    image = Path(__file__).resolve().parent / "prebuilt" / IMAGES[args.variant]
    if not image.exists():
        raise SystemExit(f"Prebuilt image is missing: {image}")

    command = [sys.executable, "-m", "esptool", "--chip", "esp32"]
    if args.port:
        command.extend(["--port", args.port])
    command.extend(
        [
            "--baud",
            str(args.baud),
            "--before",
            "default_reset",
            "--after",
            "hard_reset",
            "write_flash",
            "0x0",
            str(image),
        ]
    )
    print(f"Flashing {args.variant}: {image.name}")
    return subprocess.run(command, check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
