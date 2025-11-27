 (cd "$(git rev-parse --show-toplevel)" && git apply --3way <<'EOF' 
diff --git a/README.md b/README.md
index a42386fd38c252af5e16b6b9aa2dcdee91dbb7fb..37ff99991ceef00861fa43b8154ebde7c304f95d 100644
--- a/README.md
+++ b/README.md
@@ -1,191 +1,112 @@
 ⭐ README.md — Lofi Streamer Dashboard (Add-On for Lofi Streamer)
+
 # 🎛️ Lofi Streamer Dashboard — Add-On for Lofi Streamer
-**GENDEMIK DIGITAL • Picamera2 Edition (Pi4 / Pi5)**  
-A standalone dashboard add-on that installs alongside your existing **Lofi Streamer** installation and provides real-time system status, streaming controls, camera monitoring, system metrics, and secure login.
+**GENDEMIK DIGITAL • Picamera2 Edition (Pi4 / Pi5)**
 
-Designed specifically for the **Lofi Streamer**, running on a Raspberry Pi 4 or Pi 5.
+A standalone dashboard that installs alongside your existing **Lofi Streamer** setup and provides real-time system status, streaming controls, camera monitoring, system metrics, and secure login. Designed for Raspberry Pi 4 or Pi 5.
 
 ---
 
 ## 🌟 Features
-
-### 🎥 Streamer Control
-- Start / Stop / Restart the Lofi Streamer service  
-- Restart the camera subsystem independently  
-- See live service status  
-- Displays live “Now Playing” update from `/tmp/current_track.txt`
-
-### 📊 System Monitoring
-- CPU usage (%)  
-- RAM usage (%)  
-- CPU temperature  
-- Disk usage  
-- System uptime  
-- Stream uptime  
-- Service log tail: **last 40 log lines** auto-refreshing
-
-### 🔐 Secure Login
-- Password-protected dashboard  
-- Uses **Werkzeug SHA256 PBKDF2 hashed password**  
-- Customisable in dashboard.py
-
-### 🖥️ Web Dashboard
-- Auto-refresh  
-- Clean minimal layout  
-- Fast on Pi4/Pi5  
-- Works at:  
-  **http://<your-pi-ip>:4455**
-
-### 🧩 Standalone Add-On
-- Can be installed after the Lofi Streamer  
-- Does not modify streamer files  
-- Uses systemd for always-on service  
-- Fully user-agnostic (supports any Pi username)
+- **Streamer Control:** start, stop, or restart the Lofi Streamer service; restart the camera subsystem; view live service status; display “Now Playing” updates from `/tmp/current_track.txt`.
+- **System Monitoring:** CPU usage, RAM usage, CPU temperature, disk usage, system uptime, stream uptime, and an auto-refreshing tail of the last 40 log lines.
+- **Secure Login:** password-protected dashboard using Werkzeug SHA256 PBKDF2 hashed passwords (customisable in `dashboard.py`).
+- **Web Dashboard:** lightweight auto-refreshing UI at `http://<your-pi-ip>:4455` optimized for Pi4/Pi5.
+- **Standalone Add-On:** installs after the Lofi Streamer without modifying streamer files; uses systemd for always-on service and supports any Pi username.
 
 ---
 
 ## 🧰 Requirements
-
-You **must install the Lofi Streamer first**:
-
-
-
-/home/<user>/LofiStream/
-
-
-Dashboard requires:
-- Raspberry Pi OS (Bookworm recommended)  
-- Python 3  
-- Flask  
-- psutil  
-- systemd (default on Pi OS)
+- Existing **Lofi Streamer** installation at `/home/<user>/LofiStream/` (install this first).
+- Raspberry Pi OS (Bookworm recommended).
+- Python 3 with `Flask` and `psutil`.
+- `systemd` (default on Raspberry Pi OS).
 
 ---
 
-# 🚀 Installation (One-Line Installer)
-
-Run this from ANY directory on your Raspberry Pi:
+## 🚀 Installation (One-Line Installer)
+Run this from **any** directory on your Raspberry Pi:
 
 ```bash
 bash <(wget -qO- https://raw.githubusercontent.com/teqherself/Lofi-Streamer-Pi4-dashboard/main/install.sh)
+```
 
+The installer will:
+- Detect your Pi username.
+- Verify your Lofi Streamer installation.
+- Install Flask and psutil.
+- Create `/home/<user>/LofiStream/Dashboard/`.
+- Download `dashboard.py`, templates, CSS, and helpers.
+- Create the dashboard systemd service.
+- Install sudoers permissions safely.
+- Start the dashboard automatically.
 
-This installer will:
-
-Detect your Pi username
-
-Verify your Lofi Streamer install
-
-Install Flask + psutil
-
-Create /home/<user>/LofiStream/Dashboard/
-
-Download dashboard.py, templates, CSS, helpers
-
-Create the dashboard systemd service
-
-Install sudoers permissions safely
-
-Start the dashboard automatically
-
-When complete, your dashboard is available at:
-
-http://<pi-ip>:4455
-
+Once complete, the dashboard is available at `http://<pi-ip>:4455`.
 
 To check your Pi’s IP:
-
+```bash
 hostname -I
+```
+
+---
 
-📂 Folder Structure Installed
+## 📂 Installed Folder Structure
+```
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
+```
 
-🔧 Managing the Dashboard Service
-Restart dashboard
-sudo systemctl restart lofi-dashboard
-
-Check status
-sudo systemctl status lofi-dashboard
-
-View dashboard logs
-journalctl -u lofi-dashboard -n 40 --no-pager
-
-🔧 Managing the Streamer Service (from terminal)
-Start
-sudo systemctl start lofi-streamer
-
-Stop
-sudo systemctl stop lofi-streamer
-
-Restart
-sudo systemctl restart lofi-streamer
-
-Logs
-sudo journalctl -u lofi-streamer -n 40 --no-pager
-
-🐛 Troubleshooting
-❗ Dashboard shows “Streamer not running”
-
-Verify the streamer service exists:
-
-sudo systemctl status lofi-streamer
-
-
-If missing, reinstall the streamer.
-
-❗ Dashboard not loading at http://<ip>:4455
-
-Check service:
-
-sudo systemctl status lofi-dashboard
-
-
-Restart:
-
-sudo systemctl restart lofi-dashboard
-
-❗ Login does not work
-
-Check the hashed password inside:
-
-/home/<user>/LofiStream/Dashboard/dashboard.py
-
-❗ Buttons do nothing
-
-Ensure sudoers file exists:
-
-cat /etc/sudoers.d/lofi-dashboard
-
-❌ Uninstall
-
-Remove dashboard folder:
-
-rm -rf ~/LofiStream/Dashboard
+---
 
+## 🔧 Managing the Dashboard Service
+- Restart dashboard: `sudo systemctl restart lofi-dashboard`
+- Check status: `sudo systemctl status lofi-dashboard`
+- View dashboard logs: `journalctl -u lofi-dashboard -n 40 --no-pager`
 
-Remove systemd service:
+## 🔧 Managing the Streamer Service (Terminal)
+- Start: `sudo systemctl start lofi-streamer`
+- Stop: `sudo systemctl stop lofi-streamer`
+- Restart: `sudo systemctl restart lofi-streamer`
+- Logs: `sudo journalctl -u lofi-streamer -n 40 --no-pager`
 
-sudo rm /etc/systemd/system/lofi-dashboard.service
-sudo systemctl daemon-reload
+---
 
+## 🐛 Troubleshooting
+- **Dashboard shows “Streamer not running”:** verify the streamer service with `sudo systemctl status lofi-streamer`; reinstall the streamer if missing.
+- **Dashboard not loading at `http://<ip>:4455`:** check service status with `sudo systemctl status lofi-dashboard`; restart with `sudo systemctl restart lofi-dashboard`.
+- **Login does not work:** confirm the hashed password in `/home/<user>/LofiStream/Dashboard/dashboard.py`.
+- **Buttons do nothing:** ensure the sudoers file exists: `cat /etc/sudoers.d/lofi-dashboard`.
 
-Remove sudoers file:
+---
 
-sudo rm /etc/sudoers.d/lofi-dashboard
+## ❌ Uninstall
+1. Remove dashboard folder:
+   ```bash
+   rm -rf ~/LofiStream/Dashboard
+   ```
+2. Remove systemd service:
+   ```bash
+   sudo rm /etc/systemd/system/lofi-dashboard.service
+   sudo systemctl daemon-reload
+   ```
+3. Remove sudoers file:
+   ```bash
+   sudo rm /etc/sudoers.d/lofi-dashboard
+   ```
 
-📦 Version
+---
 
-Dashboard v3.4 — GENDEMIK DIGITAL
-Add-On for Lofi Streamer
+## 📦 Version
+Dashboard v3.4 — GENDEMIK DIGITAL  
+Add-On for Lofi Streamer  
 Maintained by Ms Stevie Woo (teqherself)
 
EOF
)
