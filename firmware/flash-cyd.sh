#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
VARIANT="${1:-ili9341}"

python3 -m pip install --disable-pip-version-check --user "esptool>=4.5,<6"
python3 "${SCRIPT_DIR}/flash_cyd.py" --variant "${VARIANT}"
