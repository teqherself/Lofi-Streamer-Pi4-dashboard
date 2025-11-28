#!/usr/bin/env python3
"""
LOFI DASHBOARD v3.5 — GENDEMIK DIGITAL

- 2x2 tiles (controls + system info + streamer status + spacer)
- 3-column logs row:
    * Streamer log  (journalctl -u lofi-streamer -n 40)
    * Camera log    (filtered from lofi-streamer journal)
    * Dashboard log (journalctl -u lofi-dashboard -n 40)
- Login protected with PBKDF2-SHA256 hash
- Uses system_helper.sh for reboot / camera reset
"""

import os
import socket
import subprocess
from datetime import datetime
from pathlib import Path

import psutil
from flask import (
    Flask,
    render_template,
    redirect,
    url_for,
    request,
    session,
    jsonify,
)
from werkzeug.security import check_password_hash

# ---------- CONFIG ----------

BASE_DIR = Path(__file__).resolve().parent.parent  # /home/<user>/LofiStream
DASH_DIR = BASE_DIR / "Dashboard"

STREAM_SERVICE = "lofi-streamer"
DASH_SERVICE = "lofi-dashboard"

CURRENT_TRACK_FILE = Path("/tmp/current_track.txt")
SYSTEM_HELPER = DASH_DIR / "system_helper.sh"

# Your PBKDF2 hash
PASSWORD_HASH = (
    "Replace_me_with_your_password_hash_key"
)

SECRET_KEY = os.environ.get("LOFI_DASH_SECRET", "change-me-please")

LOG_LINES = 40

app = Flask(__name__, template_folder=str(DASH_DIR / "templates"),
            static_folder=str(DASH_DIR / "static"))
app.secret_key = SECRET_KEY


# ---------- HELPERS ----------

def run_cmd(cmd: list[str]) -> tuple[bool, str]:
    """Run a command and return (ok, output)."""
    try:
        out = subprocess.check_output(cmd, stderr=subprocess.STDOUT, text=True)
        return True, out
    except subprocess.CalledProcessError as e:
        return False, e.output
    except Exception as e:
        return False, str(e)


def login_required(view):
    """Simple decorator for login protection."""
    from functools import wraps

    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("login"))
        return view(*args, **kwargs)

    return wrapped


def get_system_info() -> dict:
    """Return CPU, RAM, disk, temp, uptime, host."""
    try:
        cpu = psutil.cpu_percent(interval=0.1)
        mem = psutil.virtual_memory().percent
        disk = psutil.disk_usage("/").percent
    except Exception:
        cpu = mem = disk = 0.0

    # Temperature
    temp_c = None
    ok, out = run_cmd(["vcgencmd", "measure_temp"])
    if ok and "temp=" in out:
        try:
            temp_c = float(out.strip().split("=")[1].split("'")[0])
        except Exception:
            temp_c = None

    # Uptime
    boot_ts = datetime.fromtimestamp(psutil.boot_time())
    now = datetime.now()
    delta = now - boot_ts
    days = delta.days
    hrs, rem = divmod(delta.seconds, 3600)
    mins, _ = divmod(rem, 60)
    uptime_str = f"{days}d {hrs}h {mins}m"

    hostname = socket.gethostname()

    return {
        "cpu": cpu,
        "mem": mem,
        "disk": disk,
        "temp": temp_c,
        "uptime": uptime_str,
        "hostname": hostname,
    }


def get_streamer_status() -> dict:
    """Return basic systemd status and now playing info."""
    status = {
        "active": False,
        "active_state": "unknown",
        "sub_state": "unknown",
        "since": "",
        "uptime": "",
    }

    ok, out = run_cmd(["systemctl", "show", STREAM_SERVICE,
                       "-p", "ActiveState", "-p", "SubState", "-p", "ActiveEnterTimestamp"])
    if ok:
        for line in out.splitlines():
            if line.startswith("ActiveState="):
                status["active_state"] = line.split("=", 1)[1].strip()
                status["active"] = status["active_state"] == "active"
            elif line.startswith("SubState="):
                status["sub_state"] = line.split("=", 1)[1].strip()
            elif line.startswith("ActiveEnterTimestamp="):
                ts = line.split("=", 1)[1].strip()
                status["since"] = ts

                # Pretty uptime
                try:
                    # systemd gives human-readable, so we just pass it through
                    status["uptime"] = ts
                except Exception:
                    pass

    # Now playing from /tmp/current_track.txt
    now_playing = ""
    if CURRENT_TRACK_FILE.exists():
        try:
            now_playing = CURRENT_TRACK_FILE.read_text(encoding="utf-8").strip()
        except Exception:
            now_playing = ""

    status["now_playing"] = now_playing

    return status


def get_journal_tail(unit: str, lines: int = LOG_LINES) -> str:
    ok, out = run_cmd(
        ["journalctl", "-u", unit, "-n", str(lines), "--no-pager", "--output", "short"]
    )
    if not ok:
        return out or "(no log data)"
    return out


def get_camera_log_from_streamer(lines: int = LOG_LINES) -> str:
    """
    Hard filter camera-related lines from lofi-streamer journal.
    C1: recommended mode (clean camera log).
    """
    raw = get_journal_tail(STREAM_SERVICE, lines * 4)  # grab more, then filter
    patterns = [
        "Camera",
        "camera",
        "Picamera2",
        "pipeline",
        "Pipeline",
        "Device or resource busy",
        "/dev/media",
        "ffmpeg",
    ]

    filtered = []
    for ln in raw.splitlines():
        if any(p in ln for p in patterns):
            filtered.append(ln)

    if not filtered:
        return "(no camera-specific entries found in streamer log)"
    # Limit to last N lines to match column
    return "\n".join(filtered[-lines:])


# ---------- ROUTES ----------

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        password = request.form.get("password", "")
        if check_password_hash(PASSWORD_HASH, password):
            session["logged_in"] = True
            return redirect(url_for("index"))
        return render_template("login.html", error="Invalid password.")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/")
@login_required
def index():
    return render_template("index.html")


# ----- API: STATUS / METRICS / LOGS -----

@app.route("/api/system")
@login_required
def api_system():
    return jsonify(get_system_info())


@app.route("/api/streamer")
@login_required
def api_streamer():
    return jsonify(get_streamer_status())


@app.route("/api/logs/streamer")
@login_required
def api_logs_streamer():
    text = get_journal_tail(STREAM_SERVICE, LOG_LINES)
    return jsonify({"log": text})


@app.route("/api/logs/camera")
@login_required
def api_logs_camera():
    text = get_camera_log_from_streamer(LOG_LINES)
    return jsonify({"log": text})


@app.route("/api/logs/dashboard")
@login_required
def api_logs_dashboard():
    text = get_journal_tail(DASH_SERVICE, LOG_LINES)
    return jsonify({"log": text})


# ----- CONTROL ENDPOINTS -----

@app.route("/control/streamer", methods=["POST"])
@login_required
def control_streamer():
    action = request.json.get("action")
    if action not in {"start", "stop", "restart"}:
        return jsonify({"ok": False, "error": "Invalid action"}), 400

    ok, out = run_cmd(["sudo", "systemctl", action, STREAM_SERVICE])
    return jsonify({"ok": ok, "output": out})


@app.route("/control/reboot", methods=["POST"])
@login_required
def control_reboot():
    # two-step confirmation could be handled client-side;
    # here we just trust the button that calls it.
    ok, out = run_cmd(["sudo", str(SYSTEM_HELPER), "reboot"])
    return jsonify({"ok": ok, "output": out})


@app.route("/control/camera", methods=["POST"])
@login_required
def control_camera():
    ok, out = run_cmd(["sudo", str(SYSTEM_HELPER), "camera_restart"])
    return jsonify({"ok": ok, "output": out})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=4455, debug=False)
