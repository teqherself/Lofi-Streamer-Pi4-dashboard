🎧 GENDEMIK DIGITAL — Lofi Streamer + Dashboard Suite
====================================================

Raspberry Pi 4 / 5 • Picamera2 • YouTube RTMP Streaming

Maintainer: **Ms Stevie Woo — Manchester, UK**  
Brand: **GENDEMIK DIGITAL**

<p align="center">
  <img src="https://img.shields.io/badge/Platform-Raspberry%20Pi-red?style=for-the-badge&logo=raspberrypi">
  <img src="https://img.shields.io/badge/Python-3.11-blue?style=for-the-badge&logo=python">
  <img src="https://img.shields.io/badge/Picamera2-Video%20First-purple?style=for-the-badge">
  <img src="https://img.shields.io/badge/Streaming-YouTube%20RTMP-yellow?style=for-the-badge&logo=youtube">
  <img src="https://img.shields.io/badge/Service-systemd-orange?style=for-the-badge">
</p>

📦 Overview
-----------

The GENDEMIK DIGITAL Lofi Streamer Suite turns a Raspberry Pi into a fully automated, self-healing YouTube livestream unit featuring:

- 📸 Picamera2 real-time video at 960×540
- 🎵 Audio playlist rotation with per-track ffmpeg sessions
- 🔊 Safe loudness protection (dynaudnorm + limiter)
- 🖼️ On-screen overlays: Now Playing, Logo, Audio Bar
- 🧠 Network watchdogs + Pi-ready checks
- 🔁 Continuous fallback-safe streaming
- 🖥️ Optional web dashboard add-on for control + monitoring

This README covers both components:

- **Lofi Streamer** (core engine)
- **Dashboard Add-On** (web controller)

✨ Features
----------

### 🎥 Lofi Streamer (Core)

- Stable Picamera2 pipeline (Video-First)
- 960×540 MJPEG capture → ffmpeg → H.264 RTMP output
- Audio playlist from `~/LofiStream/Sounds/*.mp3`
- Safe Audio Engine
  - `dynaudnorm` smoothing
  - `alimiter=limit=0.95` hard protection
- Auto-refreshed playlist (add new tracks any time)
- Now Playing text overlay
- Mini audio bar (Pi-safe)
- Logo overlay (top-right, transparent PNG)
- Network watchdog + fallback logic
- Full automatic loop streaming

### 🖥️ Dashboard Add-On (Optional)

- Password-protected login (PBKDF2 SHA-256)
- Start / Stop / Restart the streamer systemd service
- Live system metrics
- Live streamer logs (last 40 lines)
- Camera status + service status indicators
- Safe system reboot button
- Shows currently playing track
- Auto-updating interface

🧩 Installation Options
-----------------------

### ▶️ Option A — Install **only** the Streamer

Use this if you don’t want a dashboard.

```bash
bash <(wget -qO- https://raw.githubusercontent.com/teqherself/Lofi-Streamer/main/install.sh)
```

This installs:

```
~/LofiStream/
  Servers/lofi-streamer.py
  Sounds/
  Videos/
  Logo/
  stream_url.txt
```

And registers:

```
lofi-streamer.service
```

### ▶️ Option B — Install **only** the Dashboard Add-On

Use this **after** you have installed the streamer.

```bash
bash <(wget -qO- https://raw.githubusercontent.com/teqherself/Lofi-Streamer-Pi4-dashboard/main/install.sh)
```

This installs:

```
~/LofiStream/Dashboard/
  dashboard.py
  system_helper.sh
  templates/
  static/
lofi-dashboard.service
/etc/sudoers.d/lofi-dashboard
```

Dashboard opens at: `http://<Pi-IP>:4455`

### ▶️ Option C — Install **both** (Streamer first, then Dashboard)

1. Install streamer
2. Install dashboard
3. Done

📁 Directory Layout
-------------------

```
LofiStream/
├── Servers/
│   └── lofi-streamer.py
├── Sounds/
│   └── *.mp3
├── Logo/
│   └── TestLogo200.png
├── stream_url.txt
└── Dashboard/        (optional)
    ├── dashboard.py
    ├── system_helper.sh
    ├── templates/
    │   ├── index.html
    │   └── login.html
    └── static/
        └── style.css
```

⚙️ Systemd Services
-------------------

**Streamer**

```bash
sudo systemctl start lofi-streamer
sudo systemctl stop lofi-streamer
sudo systemctl restart lofi-streamer
journalctl -u lofi-streamer -n 40 --no-pager
```

**Dashboard**

```bash
sudo systemctl restart lofi-dashboard
sudo systemctl status lofi-dashboard
journalctl -u lofi-dashboard -n 50 --no-pager
```

🖥️ Using the Dashboard
----------------------

1. Open: `http://<pi-ip>:4455`
2. Log in
3. Use controls:
   - Start / Stop / Restart Streamer
   - System reboot
   - Live track
   - Live metrics
   - Recent logs
4. Monitor your stream and Pi health

🛠 Troubleshooting
-----------------

- ❌ Dashboard won’t load

  ```bash
  sudo systemctl status lofi-dashboard
  ```

- ❌ Buttons don’t work

  Check sudoers file:

  ```bash
  cat /etc/sudoers.d/lofi-dashboard
  ```

- ❌ Streamer not running

  ```bash
  sudo systemctl status lofi-streamer
  ```

- ❌ No camera

  Make sure no other program is using `/dev/media*` or `/dev/video*`:

  ```bash
  sudo lsof /dev/video* /dev/media*
  ```

🗑 Uninstall
------------

**Remove Dashboard**

```bash
sudo systemctl stop lofi-dashboard
sudo systemctl disable lofi-dashboard
sudo rm /etc/systemd/system/lofi-dashboard.service
sudo rm /etc/sudoers.d/lofi-dashboard
rm -rf ~/LofiStream/Dashboard
sudo systemctl daemon-reload
```

**Remove Streamer**

```bash
sudo systemctl stop lofi-streamer
sudo systemctl disable lofi-streamer
sudo rm /etc/systemd/system/lofi-streamer.service
rm -rf ~/LofiStream
sudo systemctl daemon-reload
```

🧭 Roadmap
----------

- Multi-stream YouTube channel selector
- Dark mode dashboard
- Camera preview tile
- On-Pi settings editor (no SSH needed)
- Over-the-air streamer updater
- Remote config sync
- Touch-friendly control mode

❤️ Support
----------

If this project helps you, consider supporting **GENDEMIK DIGITAL**.
