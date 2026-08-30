#!/usr/bin/env bash
set -Eeuo pipefail

if [[ "${EUID}" -ne 0 ]]; then
  echo "Run this installer with: sudo bash pi/install.sh" >&2
  exit 1
fi

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="/opt/pocket-iptv"
CONFIG_DIR="/etc/pocket-iptv"
SERVICE_USER="pocketiptv"

if [[ ! -d "${SCRIPT_DIR}/pocket_iptv" ]]; then
  echo "The pocket_iptv source folder is missing. Run this from the cloned project." >&2
  exit 1
fi

echo "[1/7] Installing Raspberry Pi packages"
apt-get update
DEBIAN_FRONTEND=noninteractive apt-get install -y \
  ffmpeg \
  python3 \
  python3-pip \
  python3-venv \
  avahi-daemon \
  ca-certificates

echo "[2/7] Creating the locked-down service account"
if ! id -u "${SERVICE_USER}" >/dev/null 2>&1; then
  useradd --system --home-dir "${INSTALL_DIR}" --shell /usr/sbin/nologin "${SERVICE_USER}"
fi
usermod -a -G dialout "${SERVICE_USER}"

echo "[3/7] Installing Pocket IPTV"
install -d -m 0755 "${INSTALL_DIR}" "${CONFIG_DIR}"
rm -rf "${INSTALL_DIR}/pocket_iptv"
cp -a "${SCRIPT_DIR}/pocket_iptv" "${INSTALL_DIR}/pocket_iptv"
cp "${SCRIPT_DIR}/requirements.txt" "${INSTALL_DIR}/requirements.txt"
python3 -m venv "${INSTALL_DIR}/venv"
"${INSTALL_DIR}/venv/bin/python" -m pip install --disable-pip-version-check --upgrade pip
"${INSTALL_DIR}/venv/bin/python" -m pip install --disable-pip-version-check -r "${INSTALL_DIR}/requirements.txt"

echo "[4/7] Creating private configuration"
NEW_PIN=""
if [[ ! -f "${CONFIG_DIR}/config.toml" ]]; then
  NEW_PIN="$(python3 -c 'import secrets; print(f"{secrets.randbelow(1000000):06d}")')"
  SECRET_KEY="$(python3 -c 'import secrets; print(secrets.token_hex(32))')"
  cp "${SCRIPT_DIR}/config.example.toml" "${CONFIG_DIR}/config.toml"
  sed -i "s/admin_pin = \"000000\"/admin_pin = \"${NEW_PIN}\"/" "${CONFIG_DIR}/config.toml"
  sed -i "s/replace-this-with-a-long-random-secret-before-use/${SECRET_KEY}/" "${CONFIG_DIR}/config.toml"
fi
if [[ ! -f "${CONFIG_DIR}/channels.m3u" ]]; then
  cp "${SCRIPT_DIR}/channels.example.m3u" "${CONFIG_DIR}/channels.m3u"
fi
chown -R "${SERVICE_USER}:${SERVICE_USER}" "${CONFIG_DIR}"
chmod 0750 "${CONFIG_DIR}"
chmod 0640 "${CONFIG_DIR}/config.toml" "${CONFIG_DIR}/channels.m3u"

echo "[5/7] Adding CYD USB permissions"
install -m 0644 /dev/stdin /etc/udev/rules.d/99-pocket-iptv-screen.rules <<'RULES'
SUBSYSTEM=="tty", ATTRS{idVendor}=="1a86", GROUP="dialout", MODE="0660"
SUBSYSTEM=="tty", ATTRS{idVendor}=="10c4", GROUP="dialout", MODE="0660"
SUBSYSTEM=="tty", ATTRS{idVendor}=="0403", GROUP="dialout", MODE="0660"
RULES
udevadm control --reload-rules
udevadm trigger

echo "[6/7] Enabling the boot service"
install -m 0644 "${SCRIPT_DIR}/systemd/pocket-iptv.service" /etc/systemd/system/pocket-iptv.service
install -m 0755 "${SCRIPT_DIR}/pocket-iptv-pin" /usr/local/bin/pocket-iptv-pin
systemctl daemon-reload
systemctl enable --now avahi-daemon
systemctl enable --now pocket-iptv

echo "[7/7] Installation complete"
HOST_NAME="$(hostname)"
echo
echo "Control page: http://${HOST_NAME}.local:8080"
if [[ -n "${NEW_PIN}" ]]; then
  echo "SAVE THIS CONTROL PIN: ${NEW_PIN}"
else
  /usr/local/bin/pocket-iptv-pin
fi
echo
echo "Next: flash the CYD, power off the Pi, and connect the CYD through the Pi USB OTG port."
echo "Logs: journalctl -u pocket-iptv -f"
