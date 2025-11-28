#!/usr/bin/env python3
"""
LOFI DASHBOARD v3.5 — GENDEMIK DIGITAL
- 2x2 tiles (System, Streamer, Controls, Spare)
- 3 log columns underneath (Streamer, Camera, Dashboard)
- Last 40 lines from journalctl
- Login with PBKDF2-SHA256 hash
- Uses your existing system_helper.sh for reboot / camera restart
"""

import os
import subprocess
import socket
from pathlib import Path
from datetime import datetime

from flask import (
    Flask,
    render_template,
    redirect,
    url_for,
    request,
    session,
    flash,
)

from werkzeug.security import check_password_hash

# ---------------- CONFIG ----------------

BASE_DIR = Path(__file__).resolve().parent.parent   # /home/USER/LofiStream
DASH_DIR = BASE_DIR / "Dashboard"

# *** USE YOUR HASH HERE ***
# You gave this hash earlier:
PASSWORD_HASH = "pbkdf2:sha256:260000$U3d8BIKn15z7ql2k$34dde1620a24a98dc5adfde876dee80d399b9af4c3334f6f2f959fbd716285fd"

SECRET_KEY = os.environ.get("LOFI_DASH_SECRET", "change-me-in-prod")

STREAMER_SERVICE = "lofi-streamer"
DASH_SERVICE = "lofi-dashboard"

LOG_LINES = 40

app = Flask(__name__, template_folder=str(DASH_DIR / "templates"), static_folder=str(DASH_DIR / "static"))
app.secret_key = SECRET_KEY


# ---------------- HELPERS ----------------

def run_cmd(cmd, use_shell=False) -> str:
    """Run a command and return stdout or error string."""
    try:
        result = subprocess.run(
            cmd if not use_shell else " ".join(cmd),
            shell=use_shell,
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode != 0:
            return f"(error)\n{result.stderr.strip()}"
        return result.stdout.strip()
    except Exception as e:
        return f"(exception: {e})"


def get_streamer_status() -> dict:
    status = run_cmd(["systemctl", "is-active", STREAMER_SERVICE])
    enabled = run_cmd(["systemctl", "is-enabled", STREAMER_SERVICE])
    return {
        "status": status,
        "enabled": enabled,
    }


def get_system_stats() -> dict:
    # CPU, RAM via psutil if available
    try:
        import psutil
        cpu = psutil.cpu_percent(interval=0.5)
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
        cpu_str = f"{cpu:.0f}%"
        mem_str = f"{mem.percent:.0f}% of {mem.total // (1024**3)}GB"
        disk_str = f"{disk.percent:.0f}% of {disk.total // (1024**3)}GB"
    except Exception:
        cpu_str = "?"
        mem_str = "?"
        disk_str = "?"

    # Temp via vcgencmd if available
    temp_raw = run_cmd(["vcgencmd", "measure_temp"])
    if "temp=" in temp_raw:
        temp_val = temp_raw.split("temp=")[-1]
    else:
        temp_val = "?"

    # Uptime
    uptime = run_cmd(["uptime", "-p"])

    return {
        "cpu": cpu_str,
        "memory": mem_str,
        "disk": disk_str,
        "temp": temp_val,
        "uptime": uptime,
    }


def get_current_track() -> str:
    path = Path("/tmp/current_track.txt")
    if path.exists():
        try:
            return path.read_text(encoding="utf-8").strip()
        except Exception:
            return "(unable to read current_track.txt)"
    return "(no track data)"


def get_logs() -> dict:
    # B: use journalctl directly, last 40 lines each
    streamer_log = run_cmd(
        ["sudo", "journalctl", "-u", STREAMER_SERVICE, "-n", str(LOG_LINES), "--no-pager"]
    )

    # Camera log: filter streamer log for camera-ish lines (still 40 max)
    camera_log_cmd = (
        "journalctl -u "
        + STREAMER_SERVICE
        + " -n 120 --no-pager | grep -Ei 'camera|picam|libcamera' | tail -"
        + str(LOG_LINES)
    )
    camera_log = run_cmd(["sudo", "bash", "-lc", camera_log_cmd], use_shell=False)

    dash_log = run_cmd(
        ["sudo", "journalctl", "-u", DASH_SERVICE, "-n", str(LOG_LINES), "--no-pager"]
    )

    return {
        "streamer_log": streamer_log,
        "camera_log": camera_log,
        "dash_log": dash_log,
    }


def require_login(fn):
    from functools import wraps

    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("login"))
        return fn(*args, **kwargs)

    return wrapper


# ---------------- ROUTES ----------------

@app.route("/", methods=["GET"])
def root():
    return redirect(url_for("dashboard"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("logged_in"):
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        password = request.form.get("password", "")
        if check_password_hash(PASSWORD_HASH, password):
            session["logged_in"] = True
            flash("Logged in.", "success")
            return redirect(url_for("dashboard"))
        else:
            flash("Invalid password.", "error")

    return render_template("login.html")


@app.route("/logout", methods=["POST"])
@require_login
def logout():
    session.clear()
    flash("Logged out.", "success")
    return redirect(url_for("login"))


@app.route("/dashboard", methods=["GET"])
@require_login
def dashboard():
    system = get_system_stats()
    streamer = get_streamer_status()
    current_track = get_current_track()
    logs = get_logs()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    return render_template(
        "index.html",
        system=system,
        streamer=streamer,
        current_track=current_track,
        streamer_log=logs["streamer_log"],
        camera_log=logs["camera_log"],
        dash_log=logs["dash_log"],
        now=now,
        hostname=socket.gethostname(),
    )


@app.route("/action", methods=["POST"])
@require_login
def action():
    action = request.form.get("action", "")

    if action == "start_streamer":
        out = run_cmd(["sudo", "systemctl", "start", STREAMER_SERVICE])
        flash(f"Streamer start: {out}", "info")
    elif action == "stop_streamer":
        out = run_cmd(["sudo", "systemctl", "stop", STREAMER_SERVICE])
        flash(f"Streamer stop: {out}", "info")
    elif action == "restart_streamer":
        out = run_cmd(["sudo", "systemctl", "restart", STREAMER_SERVICE])
        flash(f"Streamer restart: {out}", "info")
    elif action == "camera_restart":
        # Use your existing system_helper with camera_restart
        helper = str(DASH_DIR / "system_helper.sh")
        out = run_cmd(["sudo", helper, "camera_restart"])
        flash(f"Camera restart: {out}", "info")
    elif action == "reboot":
        helper = str(DASH_DIR / "system_helper.sh")
        flash("System reboot requested…", "warning")
        # fire and forget
        subprocess.Popen(["sudo", helper, "reboot"])
    else:
        flash(f"Unknown action: {action}", "error")

    return redirect(url_for("dashboard"))


if __name__ == "__main__":
    # For manual testing only — normally run by systemd
    app.run(host="0.0.0.0", port=4455, debug=False)
