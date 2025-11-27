⭐ README.md — Lofi Streamer Dashboard (Add-On for Lofi Streamer)
# 🎛️ Lofi Streamer Dashboard — Add-On for Lofi Streamer
**GENDEMIK DIGITAL • Picamera2 Edition (Pi4 / Pi5)**  
A standalone dashboard add-on that installs alongside your existing **Lofi Streamer** installation and provides real-time system status, streaming controls, camera monitoring, system metrics, and secure login.

Designed specifically for the **Lofi Streamer**, running on a Raspberry Pi 4 or Pi 5.

---

## 🌟 Features

### 🎥 Streamer Control
- Start / Stop / Restart the Lofi Streamer service  
- Restart the camera subsystem independently  
- See live service status  
- Displays live “Now Playing” update from `/tmp/current_track.txt`

### 📊 System Monitoring
- CPU usage (%)  
- RAM usage (%)  
- CPU temperature  
- Disk usage  
- System uptime  
- Stream uptime  
- Service log tail: **last 40 log lines** auto-refreshing

### 🔐 Secure Login
- Password-protected dashboard  
- Uses **Werkzeug SHA256 PBKDF2 hashed password**  
- Customisable in dashboard.py

### 🖥️ Web Dashboard
- Auto-refresh  
- Clean minimal layout  
- Fast on Pi4/Pi5  
- Works at:  
  **http://<your-pi-ip>:4455**

### 🧩 Standalone Add-On
- Can be installed after the Lofi Streamer  
- Does not modify streamer files  
- Uses systemd for always-on service  
- Fully user-agnostic (supports any Pi username)

---

## 🧰 Requirements

You **must install the Lofi Streamer first**:



/home/<user>/LofiStream/


Dashboard requires:
- Raspberry Pi OS (Bookworm recommended)  
- Python 3  
- Flask  
- psutil  
- systemd (default on Pi OS)

---

# 🚀 Installation (One-Line Installer)

Run this from ANY directory on your Raspberry Pi:

```bash
bash <(wget -qO- https://raw.githubusercontent.com/teqherself/Lofi-Streamer-Pi4-dashboard/main/install.sh)


This installer will:

Detect your Pi username

Verify your Lofi Streamer install

Install Flask + psutil

Create /home/<user>/LofiStream/Dashboard/

Download dashboard.py, templates, CSS, helpers

Create the dashboard systemd service

Install sudoers permissions safely

Start the dashboard automatically

When complete, your dashboard is available at:

http://<pi-ip>:4455


To check your Pi’s IP:

hostname -I

📂 Folder Structure Installed
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

🔧 Managing the Dashboard Service
Restart dashboard
sudo systemctl restart lofi-dashboard

Check status
sudo systemctl status lofi-dashboard

View dashboard logs
journalctl -u lofi-dashboard -n 40 --no-pager

🔧 Managing the Streamer Service (from terminal)
Start
sudo systemctl start lofi-streamer

Stop
sudo systemctl stop lofi-streamer

Restart
sudo systemctl restart lofi-streamer

Logs
sudo journalctl -u lofi-streamer -n 40 --no-pager

🐛 Troubleshooting
❗ Dashboard shows “Streamer not running”

Verify the streamer service exists:

sudo systemctl status lofi-streamer


If missing, reinstall the streamer.

❗ Dashboard not loading at http://<ip>:4455

Check service:

sudo systemctl status lofi-dashboard


Restart:

sudo systemctl restart lofi-dashboard

❗ Login does not work

Check the hashed password inside:

/home/<user>/LofiStream/Dashboard/dashboard.py

❗ Buttons do nothing

Ensure sudoers file exists:

cat /etc/sudoers.d/lofi-dashboard

❌ Uninstall

Remove dashboard folder:

rm -rf ~/LofiStream/Dashboard


Remove systemd service:

sudo rm /etc/systemd/system/lofi-dashboard.service
sudo systemctl daemon-reload


Remove sudoers file:

sudo rm /etc/sudoers.d/lofi-dashboard

📦 Version

Dashboard v3.4 — GENDEMIK DIGITAL
Add-On for Lofi Streamer
Maintained by Ms Stevie Woo (teqherself)
