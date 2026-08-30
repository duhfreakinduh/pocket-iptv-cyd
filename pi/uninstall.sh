#!/usr/bin/env bash
set -Eeuo pipefail

if [[ "${EUID}" -ne 0 ]]; then
  echo "Run with: sudo bash pi/uninstall.sh" >&2
  exit 1
fi

systemctl disable --now pocket-iptv 2>/dev/null || true
rm -f /etc/systemd/system/pocket-iptv.service
rm -f /etc/udev/rules.d/99-pocket-iptv-screen.rules
rm -f /usr/local/bin/pocket-iptv-pin
rm -rf /opt/pocket-iptv
systemctl daemon-reload

echo "Pocket IPTV software was removed."
echo "Your playlist and settings remain in /etc/pocket-iptv."
echo "Remove that folder manually only if you no longer need your private playlist."
