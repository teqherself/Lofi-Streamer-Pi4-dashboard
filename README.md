⭐ README.md — Lofi Streamer Dashboard (Add-On for Lofi Streamer)

# 🎛️ Lofi Streamer Dashboard — Add-On for Lofi Streamer
**GENDEMIK DIGITAL • Picamera2 Edition (Pi4 / Pi5)**

A standalone dashboard that installs alongside your existing **Lofi Streamer** setup and provides real-time system status, streaming controls, camera monitoring, system metrics, and secure login. Designed for Raspberry Pi 4 or Pi 5.

---

## 🌟 Features
- **Streamer Control:** start, stop, or restart the Lofi Streamer service; restart the camera subsystem; view live service status; display “Now Playing” updates from `/tmp/current_track.txt`.
- **System Monitoring:** CPU usage, RAM usage, CPU temperature, disk usage, system uptime, stream uptime, and an auto-refreshing tail of the last 40 log lines.
- **Secure Login:** password-protected dashboard using Werkzeug SHA256 PBKDF2 hashed passwords (customisable in `dashboard.py`).
- **Web Dashboard:** lightweight auto-refreshing UI at `http://<your-pi-ip>:4455` optimized for Pi4/Pi5.
- **Standalone Add-On:** installs after the Lofi Streamer without modifying streamer files; uses systemd for always-on service and supports any Pi username.

---

## 🧰 Requirements
- Existing **Lofi Streamer** installation at `/home/<user>/LofiStream/` (install this first).
- Raspberry Pi OS (Bookworm recommended).
- Python 3 with `Flask` and `psutil`.
- `systemd` (default on Raspberry Pi OS).

---

## 🚀 Installation (One-Line Installer)
Run this from **any** directory on your Raspberry Pi:

```bash
bash <(wget -qO- https://raw.githubusercontent.com/teqherself/Lofi-Streamer-Pi4-dashboard/main/install.sh)
```

The installer will:
- Detect your Pi username.
- Verify your Lofi Streamer installation.
- Install Flask and psutil.
- Create `/home/<user>/LofiStream/Dashboard/`.
- Download `dashboard.py`, templates, CSS, and helpers.
- Create the dashboard systemd service.
- Install sudoers permissions safely.
- Start the dashboard automatically.

Once complete, the dashboard is available at `http://<pi-ip>:4455`.

To check your Pi’s IP:
```bash
hostname -I
```

---

## 📂 Installed Folder Structure
```
LofiStream/
 ├── Servers/
 │    └── lofi-streamer.py
 ├── Dashboard/
 │    ├── dashboard.py
 │    ├── system_helper.sh
 │    ├── static/
 │    │    └── style.css
 │    └── templates/
 │         ├── index.html
 │         └── login.html
 └── stream_url.txt
```

---

## 🔧 Managing the Dashboard Service
- Restart dashboard: `sudo systemctl restart lofi-dashboard`
- Check status: `sudo systemctl status lofi-dashboard`
- View dashboard logs: `journalctl -u lofi-dashboard -n 40 --no-pager`

## 🔧 Managing the Streamer Service (Terminal)
- Start: `sudo systemctl start lofi-streamer`
- Stop: `sudo systemctl stop lofi-streamer`
- Restart: `sudo systemctl restart lofi-streamer`
- Logs: `sudo journalctl -u lofi-streamer -n 40 --no-pager`

---

## 🐛 Troubleshooting
- **Dashboard shows “Streamer not running”:** verify the streamer service with `sudo systemctl status lofi-streamer`; reinstall the streamer if missing.
- **Dashboard not loading at `http://<ip>:4455`:** check service status with `sudo systemctl status lofi-dashboard`; restart with `sudo systemctl restart lofi-dashboard`.
- **Login does not work:** confirm the hashed password in `/home/<user>/LofiStream/Dashboard/dashboard.py`.
- **Buttons do nothing:** ensure the sudoers file exists: `cat /etc/sudoers.d/lofi-dashboard`.

---

## ❌ Uninstall
1. Remove dashboard folder:
   ```bash
   rm -rf ~/LofiStream/Dashboard
   ```
2. Remove systemd service:
   ```bash
   sudo rm /etc/systemd/system/lofi-dashboard.service
   sudo systemctl daemon-reload
   ```
3. Remove sudoers file:
   ```bash
   sudo rm /etc/sudoers.d/lofi-dashboard
   ```

---

## 📦 Version
Dashboard v3.4 — GENDEMIK DIGITAL  
Add-On for Lofi Streamer  
Maintained by Ms Stevie Woo (teqherself)
