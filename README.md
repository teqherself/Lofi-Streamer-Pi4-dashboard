# 🎧 Lofi Streamer + Dashboard (GENDEMIK DIGITAL)
*Maintained by **Ms Stevie Woo (GENDEMIK DIGITAL)** — Raspberry Pi 4/5 Picamera2 Edition*

<a><img src="https://img.shields.io/badge/Platform-Raspberry%20Pi-red?style=for-the-badge&logo=raspberrypi"></a>
<a><img src="https://img.shields.io/badge/Python-3.11-blue?style=for-the-badge&logo=python"></a>
<a><img src="https://img.shields.io/badge/Framework-Flask-green?style=for-the-badge&logo=flask"></a>
<a><img src="https://img.shields.io/badge/Service-systemd-orange?style=for-the-badge"></a>

The **Lofi Streamer** is a camera-first YouTube livestream engine designed for Raspberry Pi.  
The **Dashboard** is an optional add-on that provides full web-based control, monitoring, logs, and system stats.

This repo contains **the Dashboard Add-On**.

---

# 🌟 Features

### ✔️ Streamer Controls  
- Start / Stop / Restart the `lofi-streamer` service  
- Restart camera hardware (clears lockups)  

### ✔️ Streamer Monitoring  
- Shows service status  
- Shows uptime  
- Shows currently playing track from `/tmp/current_track.txt`  
- Last 40 lines of:
  - Streamer Logs  
  - Dashboard Logs  
  - Camera Lock Diagnostics  

### ✔️ System Monitoring  
- CPU usage, RAM, Disk, Load, Temperature  
- Auto-refresh  
- Clean 2×2 tile layout  
- Dedicated logs area (stacked by column)

### ✔️ Secure Login  
- PBKDF2-SHA256 hashing  
- Single password stored internally  
- Easily changeable (docs included)

---

# 📦 Installation (one-line installer)

Run this on your Raspberry Pi **after the streamer itself is installed**:

```bash
bash <(wget -qO- https://raw.githubusercontent.com/teqherself/Lofi-Streamer-Pi4-dashboard/main/install.sh)
```

This will:

- Auto-detect your Pi username  
- Install Python3 deps (Flask, psutil)  
- Create the Dashboard folder structure  
- Install & enable `lofi-dashboard.service`  
- Add the correct sudoers rules  
- Start the dashboard automatically

---

# 🌐 Usage

After install, open:

```
http://<your-pi-ip>:4455
```

Use:

```bash
hostname -I
```

to find your Pi’s IP.

Login using the hashed password configured in `dashboard.py`.

Once inside, you’ll see:

- **2×2 tiles** (system stats + controls)  
- **Three log columns**  
  - streamer log  
  - camera lock log  
  - dashboard log  

Everything updates automatically.

---

# 🔑 Password Configuration

The dashboard uses a **PBKDF2-SHA256 hash**, not a plain password.

### Generate a new password hash:

```bash
python3 - << 'EOF'
from werkzeug.security import generate_password_hash
print(generate_password_hash("YOUR_NEW_PASSWORD"))
EOF
```

Then open:

```
~/LofiStream/Dashboard/dashboard.py
```

Find:

```python
PASSWORD_HASH = "pbkdf2:sha256:...."
```

Replace it with your new hash.

Reboot dashboard:

```bash
sudo systemctl restart lofi-dashboard
```

---

# 📁 Repository Structure

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

# 🛠️ Helpful Commands

### Dashboard
```
sudo systemctl status lofi-dashboard
sudo systemctl restart lofi-dashboard
journalctl -u lofi-dashboard -n 40 --no-pager
```

### Streamer
```
sudo systemctl start lofi-streamer
sudo systemctl stop lofi-streamer
sudo systemctl restart lofi-streamer
journalctl -u lofi-streamer -n 40 --no-pager
```

---

# ❌ Uninstall

```bash
sudo systemctl stop lofi-dashboard
sudo systemctl disable lofi-dashboard
sudo rm /etc/systemd/system/lofi-dashboard.service
sudo rm /etc/sudoers.d/lofi-dashboard
rm -rf ~/LofiStream/Dashboard
sudo systemctl daemon-reload
```

---

# 🗺️ Roadmap

- Dark mode  
- OTA streamer updater  
- Inline Pi camera preview  
- Multi-stream YouTube selector  

Maintained with ❤️ by  
**Ms Stevie Woo (GENDEMIK DIGITAL)**  
Manchester, UK  
