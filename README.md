🎛️ Lofi Streamer Dashboard Add-On

GENDEMIK DIGITAL • Raspberry Pi 4 / 5 • Picamera2 Edition

<a><img src="https://img.shields.io/badge/Platform-Raspberry%20Pi-red?style=for-the-badge&logo=raspberrypi"></a>
<a><img src="https://img.shields.io/badge/Python-3.11-blue?style=for-the-badge&logo=python"></a>
<a><img src="https://img.shields.io/badge/Framework-Flask-green?style=for-the-badge&logo=flask"></a>
<a><img src="https://img.shields.io/badge/Service-systemd-orange?style=for-the-badge"></a>

This repository contains the official dashboard add-on for the GENDEMIK DIGITAL Lofi Streamer.
Install the main streamer first, then install this dashboard to unlock full monitoring, system controls, service management, and health tools.

Designed for Raspberry Pi 4 / 5, running Bookworm, with Picamera2.

⭐ Features

The dashboard provides a clean, simple web interface with:

🖥️ Stream Control

Start / Stop / Restart the lofi-streamer service

Live service state (Active / Inactive / Restarting)

🎵 Stream Information

Shows the current track from /tmp/current_track.txt

Shows Pi uptime and streamer uptime

Automatically refreshes status

📊 System Monitoring

CPU usage %

RAM usage %

Disk usage

SoC temperature

Uptime

📜 Live Logs (stacked columns)

Streamer log (journalctl last 40 lines)

Dashboard log

Camera/capture log

Cleanly formatted, refreshing without reloading the page

🔐 Secure Login

PBKDF2-SHA256 hashed password (not stored in plain text)

Authentication required before any control actions

🔧 Extras

Camera lock recovery using system helper (system_helper.sh)

System reboot (double-confirmation)

Fully systemd-managed (lofi-dashboard.service)

Runs automatically on boot

🚀 Quick Install (Add-On Installer)

After installing the main Lofi Streamer, run this one command:

bash <(wget -qO- https://raw.githubusercontent.com/teqherself/Lofi-Streamer-Pi4-dashboard/main/install.sh)


This installer:

✔ Automatically detects the Pi user (no hard-coded names)
✔ Installs Flask + psutil
✔ Creates LofiStream/Dashboard/
✔ Downloads all dashboard files from this repo
✔ Creates /etc/sudoers.d/lofi-dashboard
✔ Installs lofi-dashboard.service
✔ Starts dashboard on boot

Once installed, open:

http://<pi-ip>:4455


Find your Pi IP with:

hostname -I

📁 Installed Layout
LofiStream/
├── Servers/
│   └── lofi-streamer.py
├── Dashboard/
│   ├── dashboard.py
│   ├── system_helper.sh
│   ├── static/
│   │   └── style.css
│   └── templates/
│       ├── index.html
│       └── login.html
└── stream_url.txt

🧭 Usage

Open the dashboard URL

Log in using your configured password

Use the tile controls:

Start / Stop / Restart Streamer

Refresh System Metrics

View Live Logs

Use Camera Restart if Picamera2 fails

Use System Reboot (double confirmation)

🔧 Helpful systemd commands
Dashboard
sudo systemctl restart lofi-dashboard
sudo systemctl status lofi-dashboard
journalctl -u lofi-dashboard -n 50 --no-pager

Streamer
sudo systemctl restart lofi-streamer
sudo systemctl status lofi-streamer
journalctl -u lofi-streamer -n 40 --no-pager

🛠 Troubleshooting
❌ Dashboard not loading
sudo systemctl status lofi-dashboard

❌ Buttons don’t work

Check sudoers:

cat /etc/sudoers.d/lofi-dashboard

❌ Streamer status incorrect

Check the service:

sudo systemctl status lofi-streamer

❌ No logs showing

Check journalctl permissions or missing sudoers entries.

❌ Login fails

Ensure the PBKDF2 hash in dashboard.py is correct.

🗑 Uninstall
sudo systemctl stop lofi-dashboard
sudo systemctl disable lofi-dashboard
sudo rm /etc/systemd/system/lofi-dashboard.service
sudo rm /etc/sudoers.d/lofi-dashboard
rm -rf ~/LofiStream/Dashboard
sudo systemctl daemon-reload

🧭 Roadmap

Multi-stream YouTube monitor

Camera preview (picamera2 snapshot)

Editable settings panel

OTA streamer updater

Dark mode

More detailed log filters

❤️ Support

If this dashboard improves your workflow, consider supporting the project.

Maintainer: Ms Stevie Woo
GENDEMIK DIGITAL • Manchester, UK
GitHub: https://github.com/teqherself
