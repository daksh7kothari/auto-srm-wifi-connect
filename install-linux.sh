#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
root="$PWD"
.venv/bin/python -c 'import login; login.credentials()'
chmod 600 .env
mkdir -p "$HOME/.config/systemd/user"
cat > "$HOME/.config/systemd/user/srm-wifi-monitor.service" <<EOF
[Unit]
Description=SRMIST Wi-Fi login monitor
After=network-online.target

[Service]
Type=simple
WorkingDirectory="$root"
ExecStart="$root/.venv/bin/python" "$root/login.py"
Restart=on-failure
RestartSec=10

[Install]
WantedBy=default.target
EOF
systemctl --user daemon-reload
systemctl --user enable --now srm-wifi-monitor.service
echo 'SRM WiFi Monitor installed and started. It will start again at Ubuntu sign-in.'
