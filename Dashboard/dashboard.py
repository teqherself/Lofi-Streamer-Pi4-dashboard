#!/usr/bin/env python3
"""
LOFI DASHBOARD v3.4 — Add-on for Lofi-Streamer
- Hashed password login
- Streamer status (lofi-streamer systemd unit)
- Camera status (via lsof on /dev/video* and /dev/media*)
- Now Playing from /tmp/current_track.txt
- Last 40 log lines (journalctl -u lofi-streamer)
- System info: CPU, RAM, Disk, Temp, Load, Uptime
- Controls: start/stop/restart streamer, restart camera-only, reboot (2-step)
"""

import os
import time
import socket
import subprocess
from pathlib import Path
from functools import wraps

import psutil
from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    jsonify,
    flash,
)
from werkzeug.security import check_password_hash

# ---------------- CONFIG ----------------

BASE_DIR = Path(__file__).resolve().parent.parent  # /home/<user>/LofiStream
DASH_DIR = BASE_DIR / "Dashboard"

STREAMER_SERVICE = "lofi-streamer"
CURRENT_TRACK_FILE = Path("/tmp/current_track.txt")

# Hashed password you supplied
PASSWORD_HASH = "pbkdf2:sha256:260000$U3d8BIKn15z7ql2k$34dde1620a24a98dc5adfde876dee80d399b9af4c3334f6f2f959fbd716285fd"

# Flask setup
app = Flask(__name__)
app.secret_key = "lofi-dashboard-secret-change-me-2025"  # change if you like

# ---------------- HELPERS ----------------


def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("login"))
        return f(*args, **kwargs)

    return wrapper


def run_cmd(cmd, timeout=5, use_sudo=False):
    """Run a shell command and return (ok, output)."""
    if use_sudo and cmd[0] != "sudo":
        cmd = ["sudo"] + cmd
    try:
        out = subprocess.check_output(cmd, stderr=subprocess.STDOUT, timeout=timeout)
        return True, out.decode(errors="ignore").strip()
    except subprocess.CalledProcessError as e:
        return False, e.output.decode(errors="ignore").strip()
    except Exception as e:
        return False, str(e)


def get_streamer_status():
    ok, out = run_cmd(["systemctl", "is-active", STREAMER_SERVICE])
    state = out.strip()
    active = state == "active"
    return {
        "active": active,
        "state": state or "unknown",
    }


def get_camera_status():
    # Check if anything is holding camera-related devices
    ok, out = run_cmd(
        ["lsof", "/dev/media0", "/dev/video0", "/dev/video1", "/dev/v4l-subdev0"],
        use_sudo=True,
        timeout=5,
    )
    if not ok:
        return {
            "active": False,
            "detail": "idle or unavailable",
        }

    lines = [l for l in out.splitlines() if l.strip()]
    # First line is header; any extra lines = active use
    active = len(lines) > 1
    return {
        "active": active,
        "detail": "in use" if active else "idle",
    }


def get_now_playing():
    if not CURRENT_TRACK_FILE.exists():
        return "No track info"
    try:
        txt = CURRENT_TRACK_FILE.read_text(encoding="utf-8").strip()
        return txt or "No track info"
    except Exception:
        return "No track info"


def get_logs():
    ok, out = run_cmd(
        ["journalctl", "-u", STREAMER_SERVICE, "-n", "40", "--no-pager"],
        use_sudo=True,
        timeout=5,
    )
    if not ok:
        return ["log unavailable", out]
    return out.splitlines()


def format_seconds(secs: float) -> str:
    secs = int(secs)
    d, r = divmod(secs, 86400)
    h, r = divmod(r, 3600)
    m, s = divmod(r, 60)
    parts = []
    if d:
        parts.append(f"{d}d")
    if h or d:
        parts.append(f"{h}h")
    if m or h or d:
        parts.append(f"{m}m")
    parts.append(f"{s}s")
    return " ".join(parts)


def get_system_info():
    cpu = psutil.cpu_percent(interval=0.2)
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage("/")

    try:
        load1, load5, load15 = os.getloadavg()
    except OSError:
        load1 = load5 = load15 = 0.0

    try:
        boot_time = psutil.boot_time()
        uptime = time.time() - boot_time
        uptime_str = format_seconds(uptime)
    except Exception:
        uptime_str = "unknown"

    # Temp from vcgencmd
    temp_c = "unknown"
    ok, out = run_cmd(["vcgencmd", "measure_temp"])
    if ok and "temp=" in out:
        try:
            temp_c = out.split("temp=")[1].split("'")[0] + "°C"
        except Exception:
            temp_c = out.strip()

    return {
        "cpu": f"{cpu:.1f}%",
        "ram": f"{mem.percent:.1f}%",
        "disk": f"{disk.percent:.1f}%",
        "temp": temp_c,
        "uptime": uptime_str,
        "load": f"{load1:.2f}, {load5:.2f}, {load15:.2f}",
    }


# ---------------- ROUTES ----------------


@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("logged_in"):
        return redirect(url_for("index"))

    error = None
    if request.method == "POST":
        password = request.form.get("password", "")
        if check_password_hash(PASSWORD_HASH, password):
            session["logged_in"] = True
            session["login_time"] = time.time()
            return redirect(url_for("index"))
        else:
            error = "Invalid password."

    return render_template("login.html", error=error)


@app.route("/logout", methods=["POST"])
@login_required
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/")
@login_required
def index():
    return render_template("index.html")


@app.route("/api/status")
@login_required
def api_status():
    streamer = get_streamer_status()
    camera = get_camera_status()
    now_playing = get_now_playing()
    sysinfo = get_system_info()
    logs = get_logs()

    return jsonify(
        {
            "streamer": streamer,
            "camera": camera,
            "now_playing": now_playing,
            "system": sysinfo,
            "logs": logs,
        }
    )


@app.route("/action/streamer/<cmd>", methods=["POST"])
@login_required
def action_streamer(cmd):
    if cmd not in {"start", "stop", "restart"}:
        return jsonify({"ok": False, "message": "Invalid command"}), 400

    ok, out = run_cmd(["systemctl", cmd, STREAMER_SERVICE], use_sudo=True, timeout=10)
    return jsonify({"ok": ok, "message": out or f"Streamer {cmd} requested."})


@app.route("/action/restart_camera", methods=["POST"])
@login_required
def action_restart_camera():
    helper = str(DASH_DIR / "system_helper.sh")
    ok, out = run_cmd([helper, "camera_restart"], use_sudo=True, timeout=15)
    return jsonify(
        {"ok": ok, "message": out or "Camera restart / lock clear requested."}
    )


@app.route("/reboot", methods=["GET"])
@login_required
def reboot():
    # Step 1: confirm page
    return render_template("reboot_confirm.html")


@app.route("/reboot/confirm", methods=["POST"])
@login_required
def reboot_confirm():
    helper = str(DASH_DIR / "system_helper.sh")
    # Step 2: actually reboot
    run_cmd([helper, "reboot"], use_sudo=True, timeout=2)
    return "Rebooting… you can close this window."


# ---------------- MAIN ----------------

def main():
    host_ip = "0.0.0.0"
    port = 4455
    print(
        f"🌐 Lofi Dashboard v3.4 running on http://{host_ip}:{port} (or http://<pi-ip>:{port})"
    )
    app.run(host=host_ip, port=port, debug=False)


if __name__ == "__main__":
    main()
