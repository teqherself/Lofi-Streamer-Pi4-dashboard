# Lofi Streamer Dashboard Add-On

Control and monitor your Raspberry Pi Lofi Streamer from a simple web dashboard. Install the main streamer first, then add this dashboard to get remote controls, live metrics, and quick troubleshooting tools.

## What the dashboard does
- Shows streamer status and uptime at a glance.
- Starts, stops, or restarts the `lofi-streamer` systemd service.
- Displays the currently playing track from `/tmp/current_track.txt`.
- Streams system metrics: CPU, RAM, disk, temperature, and overall uptime.
- Refreshes the latest streamer logs automatically (last 40 lines).
- Secures access with a login page and PBKDF2-SHA256 hashed password.

## Requirements
- Raspberry Pi OS Bookworm on a Raspberry Pi 4 or 5.
- Python 3.11 and systemd (standard on recent Pi OS releases).
- Picamera2 already installed via the main Lofi Streamer setup.
- Lofi Streamer installed at `/home/<user>/LofiStream/`.
- Network access to the Pi for installation and browsing the dashboard.

## Quick install
Run on the Raspberry Pi after the streamer is installed:

```bash
bash <(wget -qO- https://raw.githubusercontent.com/teqherself/Lofi-Streamer-Pi4-dashboard/main/install.sh)
```

The installer will:
- Detect your Pi username and confirm the streamer installation.
- Install Python dependencies (Flask, psutil).
- Create the `Dashboard` folder and download templates/static assets.
- Register `lofi-dashboard.service` and sudoers entries.
- Start the dashboard automatically on boot.

After installation, open the dashboard at `http://<pi-ip>:4455`. Use `hostname -I` to find the Pi’s IP address.

## Installed layout
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

## Using the dashboard
1. Open `http://<pi-ip>:4455` and log in with your password.
2. Use Start / Stop / Restart to control the streamer service.
3. Watch live logs and system metrics to verify the stream is healthy.

## Helpful systemd commands
- Restart dashboard: `sudo systemctl restart lofi-dashboard`
- Check dashboard status: `sudo systemctl status lofi-dashboard`
- Dashboard logs: `journalctl -u lofi-dashboard -n 50 --no-pager`
- Start/stop/restart streamer: `sudo systemctl [start|stop|restart] lofi-streamer`
- Streamer logs: `journalctl -u lofi-streamer -n 40 --no-pager`

## Troubleshooting
- **Dashboard won’t load**: `sudo systemctl status lofi-dashboard`
- **Login fails**: verify the password hash in `~/LofiStream/Dashboard/dashboard.py`.
- **Buttons don’t work**: check sudoers with `cat /etc/sudoers.d/lofi-dashboard`.
- **No streamer logs**: ensure the main service is running: `sudo systemctl status lofi-streamer`.

## Uninstall
```bash
sudo systemctl stop lofi-dashboard
sudo systemctl disable lofi-dashboard
sudo rm /etc/systemd/system/lofi-dashboard.service
sudo rm /etc/sudoers.d/lofi-dashboard
rm -rf ~/LofiStream/Dashboard
sudo systemctl daemon-reload
```

## Roadmap
- Multi-stream YouTube selector (testing)
- Dark mode toggle (planned)
- Inline camera preview (planned)
- On-device settings editor (in progress)
- OTA streamer updater (future consideration)

## Support
If this dashboard helps your setup, consider supporting GENDEMIK DIGITAL (add your Ko-Fi / PayPal / Patreon link here).

Maintainer: Ms Stevie Woo — GENDEMIK DIGITAL, Manchester UK  
GitHub: https://github.com/teqherself
