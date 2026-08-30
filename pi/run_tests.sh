#!/usr/bin/env bash
set -Eeuo pipefail
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PYTHONPATH="${SCRIPT_DIR}" python3 -m unittest discover -s "${SCRIPT_DIR}/tests" -v
