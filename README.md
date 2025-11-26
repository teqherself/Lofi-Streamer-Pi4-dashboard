 (cd "$(git rev-parse --show-toplevel)" && git apply --3way <<'EOF' 
diff --git a/README.md b/README.md
new file mode 100644
index 0000000000000000000000000000000000000000..9c86eadd8b10c6c10852abca1c7347de9868ff04
--- /dev/null
+++ b/README.md
@@ -0,0 +1,51 @@
+# Lofi Streamer Dashboard
+
+A lightweight Flask dashboard for monitoring and controlling the "lofi-streamer" service on a Raspberry Pi. The app exposes a password-protected web UI with service controls, temperature reporting, camera lock detection, and access to recent journal logs.
+
+## Requirements
+- Python 3
+- Flask, Werkzeug, and psutil Python packages
+- System utilities used by the dashboard: `systemctl`, `journalctl`, `lsof`, and `vcgencmd` (for CPU temperature on Raspberry Pi)
+- A systemd-managed service named `lofi-streamer` (provided by the main streamer project)
+
+## Quick start (development)
+1. Create and activate a virtual environment:
+   ```bash
+   python3 -m venv .venv
+   source .venv/bin/activate
+   ```
+2. Install dependencies:
+   ```bash
+   pip install flask werkzeug psutil
+   ```
+3. Run the dashboard:
+   ```bash
+   python dashboard.py
+   ```
+4. Visit `http://localhost:4455` in your browser and log in with the configured password hash.
+
+> **Note:** Service controls rely on `systemd`, journal access, and camera utilities that are normally available on the target Raspberry Pi. When running on a different platform, those features may return `unknown` until the supporting tools are present.
+
+## Installation on Raspberry Pi
+A convenience installer provisions system dependencies, virtual environment, sudoers entries, and systemd services for both the streamer and dashboard:
+
+```bash
+chmod +x Install-Lofi-Streamer-Pi4-Dashboard.sh
+sudo ./Install-Lofi-Streamer-Pi4-Dashboard.sh
+```
+
+The installer expects the streamer and dashboard files to be present relative to the script and will:
+- Copy server and dashboard files into `~/LofiStream`
+- Create and populate a Python virtual environment
+- Install and enable `lofi-streamer` and `lofi-dashboard` systemd services
+- Add sudoers rules needed for system commands (service control, logs, camera checks, and reboot)
+
+## Configuration notes
+- The allowed username and password hash are defined near the top of `dashboard.py`. Update `ALLOWED_USER` and `PASSWORD_HASH` to match your credentials before deployment.
+- The dashboard listens on port `4455` by default; adjust `app.run()` in `dashboard.py` if you need a different port.
+- System status information is read from `lofi-streamer` logs and service status; ensure the service name matches your deployment.
+
+## Repository layout
+- `dashboard.py` — Flask application powering the dashboard UI
+- `Install-Lofi-Streamer-Pi4-Dashboard.sh` — installer for Raspberry Pi
+- `index.html`, `login.html`, `reboot_confirm.html`, `style.css` — dashboard templates and styling
 
EOF
)
