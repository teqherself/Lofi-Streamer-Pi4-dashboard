# 🎛️ Lofi Streamer Dashboard Add-On

GENDEMIK DIGITAL • Raspberry Pi 4 / 5 • Picamera2 Edition

<p align="left">
  <img src="https://img.shields.io/badge/Platform-Raspberry%20Pi-red?style=for-the-badge&logo=raspberrypi" alt="Platform: Raspberry Pi">
  <img src="https://img.shields.io/badge/Python-3.11-blue?style=for-the-badge&logo=python" alt="Python 3.11">
  <img src="https://img.shields.io/badge/Framework-Flask-green?style=for-the-badge&logo=flask" alt="Flask">
  <img src="https://img.shields.io/badge/Service-systemd-orange?style=for-the-badge" alt="systemd">
</p>

Official dashboard add-on for the GENDEMIK DIGITAL Lofi Streamer. Install the main streamer first, then add this dashboard to unlock monitoring, service controls, and maintenance tools for Raspberry Pi 4/5 (Bookworm, Picamera2).

---

## 📚 Table of Contents
- [Highlights](#-highlights)
- [Quick Install](#-quick-install)
- [Installed Layout](#-installed-layout)
- [Usage](#-usage)
- [Helpful systemd Commands](#-helpful-systemd-commands)
- [Troubleshooting](#-troubleshooting)
- [Uninstall](#-uninstall)
- [Roadmap](#-roadmap)
- [Support](#-support)

## ⭐ Highlights
The dashboard provides a clean, single-page interface with:

### 🖥️ Stream Control
- Start / Stop / Restart the lofi-streamer service
- Live service state (Active / Inactive / Restarting)

### 🎵 Stream Information
- Current track pulled from `/tmp/current_track.txt`
- Pi uptime and streamer uptime with auto-refresh

### 📊 System Monitoring
- CPU usage % and RAM usage %
- Disk usage and SoC temperature
- Overall uptime

### 📜 Live Logs
- Streamer log (journalctl last 40 lines)
- Dashboard log
- Camera/capture log
- Stacked columns, auto-refresh without page reloads

### 🔐 Secure Login
- PBKDF2-SHA256 hashed password (never stored in plain text)
- Authentication required before any control actions

### 🔧 Extras
- Camera lock recovery using `system_helper.sh`
- System reboot with double confirmation
- Fully systemd-managed (`lofi-dashboard.service`), auto-start on boot

---

## 🚀 Quick Install
After installing the main Lofi Streamer, run:

```bash
bash <(wget -qO- https://raw.githubusercontent.com/teqherself/Lofi-Streamer-Pi4-dashboard/main/Install.sh)
```

The installer automatically:
- Detects the Pi user (no hard-coded names)
- Installs Flask + psutil
- Creates `LofiStream/Dashboard/`
- Downloads dashboard files from this repo
- Adds `/etc/sudoers.d/lofi-dashboard`
- Installs `lofi-dashboard.service`
- Starts the dashboard on boot

Access the dashboard at:

```
http://<pi-ip>:4455
```

Find the Pi IP with `hostname -I`.

---

## 📁 Installed Layout
```
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
```

---

## 🧭 Usage
1. Open the dashboard URL and log in with your configured password.
2. Use the tiles to:
   - Start / Stop / Restart the streamer
   - Refresh system metrics
   - View live logs
   - Restart the camera if Picamera2 locks up
   - Reboot the system (double confirmation)

---

## 🔧 Helpful systemd Commands
**Dashboard**
- `sudo systemctl restart lofi-dashboard`
- `sudo systemctl status lofi-dashboard`
- `journalctl -u lofi-dashboard -n 50 --no-pager`

**Streamer**
- `sudo systemctl restart lofi-streamer`
- `sudo systemctl status lofi-streamer`
- `journalctl -u lofi-streamer -n 40 --no-pager`

---

## 🛠 Troubleshooting
- ❌ Dashboard not loading → `sudo systemctl status lofi-dashboard`
- ❌ Buttons don’t work → verify sudoers: `cat /etc/sudoers.d/lofi-dashboard`
- ❌ Streamer status incorrect → `sudo systemctl status lofi-streamer`
- ❌ No logs showing → check journalctl permissions or missing sudoers entries
- ❌ Login fails → confirm the PBKDF2 hash in `dashboard.py`

---

## 🗑 Uninstall
```bash
sudo systemctl stop lofi-dashboard
sudo systemctl disable lofi-dashboard
sudo rm /etc/systemd/system/lofi-dashboard.service
sudo rm /etc/sudoers.d/lofi-dashboard
rm -rf ~/LofiStream/Dashboard
sudo systemctl daemon-reload
```

---

## 🧭 Roadmap
- Multi-stream YouTube monitor
- Camera preview (picamera2 snapshot)
- Editable settings panel
- OTA streamer updater
- Dark mode
- More detailed log filters

---

## ❤️ Support
If this dashboard improves your workflow, consider supporting the project.

Maintainer: **Ms Stevie Woo**  
GENDEMIK DIGITAL • Manchester, UK  
GitHub: https://github.com/teqherself
