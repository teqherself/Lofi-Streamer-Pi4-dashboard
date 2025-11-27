🎛️ Lofi Streamer Dashboard Add-On
GENDEMIK DIGITAL • Raspberry Pi 4 / 5 • Picamera2 Edition

<a href="#"><img src="https://img.shields.io/badge/Platform-Raspberry%20Pi-red?style=for-the-badge&logo=raspberrypi"></a>
<a href="#"><img src="https://img.shields.io/badge/Python-3.11-blue?style=for-the-badge&logo=python"></a>
<a href="#"><img src="https://img.shields.io/badge/Framework-Flask-green?style=for-the-badge&logo=flask"></a>
<a href="#"><img src="https://img.shields.io/badge/Service-systemd-orange?style=for-the-badge"></a>

This dashboard is an optional add-on for the Lofi Streamer.
Install the streamer first, then install the dashboard to gain full control, monitoring, and system tools.

🚀 What Is This?

The Lofi Streamer Dashboard gives you a professional-grade control panel for your Raspberry Pi Lofi Streamer setup.

It shows stream status, logs, system metrics, and lets you start/stop/restart your streamer without touching the terminal.

This is designed for creators, coders, musicians, and cozy-stream enthusiasts who want a reliable, always-on Pi streaming setup.

🌟 Features at a Glance
🎥 Streamer Control
Feature	Description
▶️ Start streamer	Launches lofi-streamer.service
⏹ Stop streamer	Clean stop (kills ffmpeg + Picamera2 safely)
🔄 Restart streamer	Full restart (with camera reset)
🎧 Now Playing	Reads /tmp/current_track.txt in real time
📡 Service Status	Green/Red indicator + uptime
📊 System Dashboard
Metric	Shown on Dashboard
CPU usage	Live percentage
RAM usage	Live percentage
Disk usage	/ & /home
CPU temperature	vcgencmd
System uptime	Human-friendly
Stream uptime	From systemd
Last 40 logs	Auto-refresh tail
🔐 Secure Login

PBKDF2-SHA256 hashed password

Included login page

Auto-session timeout

Hidden dashboard until logged in

🖥️ Web Interface

Accessible at:
http://<raspberry-pi-ip>:4455

Clean layout

Mobile-friendly

Fast refresh

No YouTube preview (streamers vary — keeps it safe and light)

🧩 Standalone Add-On

Installs after the streamer

Does not modify streamer files

Does not overwrite existing configs

Creates its own service:

lofi-dashboard.service

⚙️ Requirements

You must first install Lofi Streamer in:

/home/<user>/LofiStream/


Dashboard requirements:

Raspberry Pi OS Bookworm

Python 3.11

Picamera2 already installed from streamer

Internet

Systemd (default)

🔥 One-Line Easy Installer

Paste this into your Pi’s terminal:

bash <(wget -qO- https://raw.githubusercontent.com/teqherself/Lofi-Streamer-Pi4-dashboard/main/install.sh)


This installer will:

✔ Detect your Pi username
✔ Verify your Lofi Streamer install
✔ Install Flask + psutil
✔ Create Dashboard folder
✔ Download templates & static CSS
✔ Install systemd service
✔ Install sudoers commands
✔ Start dashboard automatically

Access here:

http://<your-pi-ip>:4455


Find your Pi’s IP:

hostname -I

📂 Installed File Structure
LofiStream/
 ├── Servers/
 │     └── lofi-streamer.py
 ├── Dashboard/
 │     ├── dashboard.py
 │     ├── system_helper.sh
 │     ├── static/
 │     │     └── style.css
 │     └── templates/
 │          ├── index.html
 │          └── login.html
 └── stream_url.txt

🧭 Using the Dashboard
✔ Login

Open browser → enter dashboard IP → login with your password.

✔ Stream Controls

Start / Stop / Restart → instant execution.

✔ Live Logs

Tail of last 40 lines from streamer.

✔ System Stats

Auto-refreshing CPU, RAM, temp, uptime.

🧪 Service Commands

Restart dashboard:

sudo systemctl restart lofi-dashboard


Check status:

sudo systemctl status lofi-dashboard


View logs:

journalctl -u lofi-dashboard -n 50 --no-pager


Streamer:

sudo systemctl start lofi-streamer
sudo systemctl stop lofi-streamer
sudo systemctl restart lofi-streamer
journalctl -u lofi-streamer -n 40 --no-pager

❌ Uninstall Dashboard
sudo systemctl stop lofi-dashboard
sudo systemctl disable lofi-dashboard
sudo rm /etc/systemd/system/lofi-dashboard.service
sudo rm /etc/sudoers.d/lofi-dashboard
rm -rf ~/LofiStream/Dashboard
sudo systemctl daemon-reload

🛠️ Troubleshooting
Dashboard doesn’t open?
sudo systemctl status lofi-dashboard

Login won’t accept password?

Check the hash inside:

~/LofiStream/Dashboard/dashboard.py

Buttons do nothing?

Verify sudoers:

cat /etc/sudoers.d/lofi-dashboard

Streamer not showing log?

Ensure streamer is installed:

sudo systemctl status lofi-streamer

🗺️ Roadmap
Feature	Status
Multi-stream YouTube selector	🔄 In testing
Dark mode toggle	🟧 Planned
View camera preview inside dashboard	🟧 Planned
On-device settings editor	🔄 In progress
OTA streamer updater	🟩 Possible future
❤️ Support This Project

If you like this work and want more enhancements, consider supporting GENDEMIK DIGITAL.

(Add your Ko-Fi / PayPal / Patreon link here)

👩‍💻 Maintainer / Contact

Ms Stevie Woo
GENDEMIK DIGITAL — Manchester, UK
GitHub: https://github.com/teqherself

🏁 End of README
