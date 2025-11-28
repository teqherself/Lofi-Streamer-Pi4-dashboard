🎧 GENDEMIK DIGITAL — Lofi Streamer Dashboard Add-On

Raspberry Pi 4 / 5 • Picamera2 Edition

<p align="center"> <img src="https://img.shields.io/badge/Platform-Raspberry%20Pi-red?style=for-the-badge&logo=raspberrypi"> <img src="https://img.shields.io/badge/Python-3.11-blue?style=for-the-badge&logo=python"> <img src="https://img.shields.io/badge/Framework-Flask-black?style=for-the-badge&logo=flask"> <img src="https://img.shields.io/badge/Service-systemd-orange?style=for-the-badge"> </p>
Overview

This repository contains the GENDEMIK DIGITAL Lofi Streamer Dashboard Add-On.
It is installed after the main streamer and provides a secure web control panel with:

Start / Stop / Restart of the lofi-streamer service

CPU / RAM / Disk / Temperature metrics

“Now Playing” display from /tmp/current_track.txt

Live system uptime + streamer uptime

Three stacked log views (Streamer / Camera / Dashboard)

Camera recovery (forces release of /dev/video*, /dev/media*)

Secure login using PBKDF2-SHA256 password hashing

Installation (Add-On)

Run this after the main Lofi Streamer is already installed:

bash <(wget -qO- https://raw.githubusercontent.com/teqherself/Lofi-Streamer-Pi4-dashboard/main/install.sh)


The installer will:

Detect your Pi username automatically

Install Flask and psutil

Install dashboard files into:

~/LofiStream/Dashboard/


Install systemd service:

/etc/systemd/system/lofi-dashboard.service


Install sudoers permissions:

/etc/sudoers.d/lofi-dashboard


Start the dashboard and enable it on boot

After installation, open:

http://<pi-ip>:4455


Find your Pi’s IP:

hostname -I

Setting / Changing the Dashboard Password

The dashboard uses a hashed password stored in dashboard.py.

1. Generate your PBKDF2-SHA256 hash

Run:

python3 - << 'EOF'
from werkzeug.security import generate_password_hash
print(generate_password_hash("YOUR_PASSWORD_HERE"))
EOF


Copy the output hash.

2. Edit dashboard.py

Open the file:

nano ~/LofiStream/Dashboard/dashboard.py


Find this line:

LOGIN_PASSWORD_HASH = "CHANGE_ME"


Replace with the full hash you generated, for example:

LOGIN_PASSWORD_HASH = "pbkdf2:sha256:260000$ABC123$XYZ987..."


Save & exit.

3. Restart dashboard
sudo systemctl restart lofi-dashboard


Log in with the plain password you originally typed.

Directory Structure
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


System files installed:

/etc/systemd/system/lofi-dashboard.service
/etc/sudoers.d/lofi-dashboard

Dashboard Features (v3.5.x)
Stream Controls

Start / Stop / Restart streamer

Live status indicator

Stream Information

Current track

Stream uptime

Pi system uptime

System Metrics

CPU usage

RAM usage

Disk usage

Temperature

Logs (stacked columns)

Streamer log — journalctl -u lofi-streamer -n 40 --no-pager

Camera / capture log — same retrieval method

Dashboard log — journalctl -u lofi-dashboard -n 40 --no-pager
Each appears in its own scrollable panel.

Recovery Tools

Restart camera (kills libcamera/ffmpeg/picamera2 locks)

System reboot (two-step confirmation)

Service Commands
Dashboard
sudo systemctl status lofi-dashboard
sudo systemctl restart lofi-dashboard
journalctl -u lofi-dashboard -n 50 --no-pager

Streamer
sudo systemctl status lofi-streamer
sudo systemctl restart lofi-streamer
journalctl -u lofi-streamer -n 40 --no-pager

Troubleshooting
Dashboard loads but buttons don’t work

Check sudoers:

cat /etc/sudoers.d/lofi-dashboard


Ensure your Pi user is present.

Login always fails

Regenerate a hash and update LOGIN_PASSWORD_HASH.

Logs missing

Check if the services are actually running.

Uninstall
sudo systemctl stop lofi-dashboard
sudo systemctl disable lofi-dashboard
sudo rm /etc/systemd/system/lofi-dashboard.service
sudo rm /etc/sudoers.d/lofi-dashboard
rm -rf ~/LofiStream/Dashboard
sudo systemctl daemon-reload

Roadmap

Multi-stream YouTube selector

Dark mode

Inline camera preview

On-device settings editor

OTA streamer updater

Maintainer

Ms Stevie Woo — GENDEMIK DIGITAL (Manchester, UK)
GitHub: https://github.com/teqherself
