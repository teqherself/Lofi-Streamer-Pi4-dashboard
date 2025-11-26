# Lofi Streamer Dashboard ADD-ON

A lightweight Flask dashboard for controlling and monitoring the `lofi-streamer` service on Raspberry Pi. The password-protected web UI provides start/stop/restart controls, shows recent journal logs, reports CPU temperature, checks whether the camera device is locked, and displays the currently playing track from `/tmp/current_track.txt`.

## Requirements
- Python 3
- Python packages: `flask`, `werkzeug`, `psutil`
- System utilities: `systemctl`, `journalctl`, `lsof`, and `vcgencmd` (for Raspberry Pi CPU temperature)
- A systemd-managed service named `lofi-streamer`

## Development quick start
1. Create and activate a virtual environment:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```
2. Install dependencies:
   ```bash
   pip install flask werkzeug psutil
   ```
3. Launch the dashboard locally:
   ```bash
   python dashboard.py
   ```
4. Open `http://localhost:4455` and log in using the password that matches `PASSWORD_HASH` in `dashboard.py`.

> Service controls, log viewing, camera checks, and temperature readings rely on Raspberry Pi tooling and systemd. When running on other platforms those values may return `unknown` until the utilities are available.

## Raspberry Pi installation (with the provided script)
The `Install-Lofi-Streamer-Pi4-Dashboard.sh` script provisions dependencies, a Python virtual environment, sudoers rules, and systemd services for both the streamer and the dashboard.

### Obtain and run the installer
1. Download this repository onto your Raspberry Pi. Two common options:
   - Clone it (replace `<REPO-URL>` with wherever you host this repo, for example `https://github.com/<org>/Lofi-Streamer-Pi4-dashboard.git`):
     ```bash
     git clone <REPO-URL>
     cd Lofi-Streamer-Pi4-dashboard
     ```
   - Download an archive (if you prefer not to use git) and extract it, then `cd` into the folder that contains `Install-Lofi-Streamer-Pi4-Dashboard.sh`.
2. Make the installer executable and launch it with sudo (it needs to create services and sudoers entries):
   ```bash
   chmod +x Install-Lofi-Streamer-Pi4-Dashboard.sh
   sudo ./Install-Lofi-Streamer-Pi4-Dashboard.sh
   ```
3. When the script finishes it reports the dashboard URL (default `http://<pi-ip>:8181`). Use that address to sign in with the password that matches `PASSWORD_HASH` in `dashboard.py`. If you need to rerun or troubleshoot the services after installation:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable --now lofi-streamer.service lofi-dashboard.service
   sudo systemctl status lofi-dashboard.service lofi-streamer.service
   ```

What the script does:
- Detects the target user and creates `~/LofiStream` with subfolders for `Servers` and `Dashboard`
- Copies streamer and dashboard files into the new directory tree and makes `system_helper.sh` executable
- Creates `~/LofiStream/stream_url.txt` (if missing) with a placeholder RTMP key
- Sets up a virtual environment at `~/LofiStream/venv` and installs Python packages
- Registers `lofi-streamer.service` and `lofi-dashboard.service` systemd units and enables them
- Adds sudoers entries that allow the dashboard to run system commands without prompting for a password

When complete, the script prints the dashboard URL, which defaults to the host's IP on port `8181`. You can change the port by editing `app.run(..., port=4455)` in `dashboard.py` (and adjusting the installer output if desired).

## Configuration
- Update `ALLOWED_USER` and `PASSWORD_HASH` near the top of `dashboard.py` to set your credentials. The provided hash corresponds to the password `G1mp(())`.
- The dashboard binds to `0.0.0.0` on port `4455` by default. Modify `app.run` for a different port.
- Service names and log collection assume the systemd unit is called `lofi-streamer`. Adjust `STREAMER_SERVICE` in `dashboard.py` if your service name differs.

## Repository layout
- `dashboard.py` — Flask application powering the dashboard UI
- `index.html`, `login.html`, `reboot_confirm.html`, `style.css` — templates and styling
- `Install-Lofi-Streamer-Pi4-Dashboard.sh` — installer for Raspberry Pi that configures services, virtualenv, and sudoers
