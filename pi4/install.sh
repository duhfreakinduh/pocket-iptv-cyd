#!/usr/bin/env bash
set -Eeuo pipefail

if [[ "${EUID}" -eq 0 ]]; then
  echo "Run this as your normal Raspberry Pi desktop user, not with sudo:"
  echo "  bash pi4/install.sh"
  exit 1
fi

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="${HOME}/PocketIPTV"
AUTOSTART_DIR="${HOME}/.config/autostart"
DESKTOP_DIR="${HOME}/Desktop"

echo "[1/6] Checking Raspberry Pi"
if [[ -r /proc/device-tree/model ]]; then
  MODEL="$(tr -d '\0' </proc/device-tree/model)"
  echo "Detected: ${MODEL}"
  if [[ "${MODEL}" != *"Raspberry Pi 4"* ]]; then
    echo "Note: this v2 installer is tuned for a Raspberry Pi 4, but may also work on newer Pi models."
  fi
else
  echo "Could not read Pi model; continuing."
fi

echo "[2/6] Installing player packages"
sudo apt-get update
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y \
  vlc \
  python3 \
  python3-vlc \
  python3-pyqt5 \
  ffmpeg \
  ca-certificates

echo "[3/6] Installing Pocket IPTV v2"
mkdir -p "${APP_DIR}" "${AUTOSTART_DIR}"
install -m 0755 "${SCRIPT_DIR}/app.py" "${APP_DIR}/app.py"

if [[ ! -f "${APP_DIR}/channels.m3u" ]]; then
  install -m 0644 "${SCRIPT_DIR}/sample_channels.m3u" "${APP_DIR}/channels.m3u"
fi

cat >"${APP_DIR}/start-pocket-iptv.sh" <<'EOF'
#!/usr/bin/env bash
set -e
export VLC_VERBOSE=-1
exec /usr/bin/python3 "${HOME}/PocketIPTV/app.py"
EOF
chmod +x "${APP_DIR}/start-pocket-iptv.sh"

echo "[4/6] Enabling automatic startup"
cat >"${AUTOSTART_DIR}/pocket-iptv.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=Pocket IPTV
Comment=Touchscreen IPTV player
Exec=${APP_DIR}/start-pocket-iptv.sh
Terminal=false
X-GNOME-Autostart-enabled=true
EOF

echo "[5/6] Adding a desktop launcher"
if [[ -d "${DESKTOP_DIR}" ]]; then
  cat >"${DESKTOP_DIR}/Pocket IPTV.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=Pocket IPTV
Comment=Touchscreen IPTV player
Exec=${APP_DIR}/start-pocket-iptv.sh
Icon=multimedia-video-player
Terminal=false
Categories=AudioVideo;Video;
EOF
  chmod +x "${DESKTOP_DIR}/Pocket IPTV.desktop"
fi

echo "[6/6] Done"
echo
echo "Launch now:"
echo "  ${APP_DIR}/start-pocket-iptv.sh"
echo
echo "Your playlist lives at:"
echo "  ${APP_DIR}/channels.m3u"
echo
echo "Pocket IPTV will also open automatically after you log into the Raspberry Pi desktop."
echo "Use the on-screen Import M3U button to replace the sample playlist."
echo
echo "If video is black but audio works, read pi4/README.md section 'Black video / Wayland fallback'."
