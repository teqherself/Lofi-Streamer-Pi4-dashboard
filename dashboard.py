#!/usr/bin/env python3
import os
import subprocess
import psutil
from flask import Flask, render_template, request, redirect, session, url_for
from werkzeug.security import check_password_hash

app = Flask(__name__)
app.secret_key = "streamer-dashboard-secret"

# ----------------------------
#   CONFIG
# ----------------------------
STREAMER_SERVICE = "lofi-streamer"
CURRENT_TRACK_FILE = "/tmp/current_track.txt"
ALLOWED_USER = "woo"

# Password hash for:  G1mp(())
PASSWORD_HASH = "pbkdf2:sha256:600000$L8vsw6W2$8cb897b4b2ad367d8b488ac632ae4ed17e680c8576cb12f4c752d335c9c93224"

# ----------------------------
#   AUTH
# ----------------------------
def login_required(func):
    def wrapper(*args, **kwargs):
        if "user" not in session:
            return redirect(url_for("login"))
        return func(*args, **kwargs)
    wrapper.__name__ = func.__name__
    return wrapper


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        pwd = request.form.get("password", "")
        if check_password_hash(PASSWORD_HASH, pwd):
            session["user"] = ALLOWED_USER
            return redirect(url_for("index"))
        return render_template("login.html", error="Wrong password")
    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    session.clear()
    return redirect(url_for("login"))

# ----------------------------
#   HELPERS
# ----------------------------
def get_streamer_status():
    try:
        out = subprocess.check_output(
            ["systemctl", "is-active", STREAMER_SERVICE], text=True
        ).strip()
        return out
    except Exception:
        return "unknown"


def get_recent_logs():
    try:
        logs = subprocess.check_output(
            ["journalctl", "-u", STREAMER_SERVICE, "-n", "40", "--no-pager"],
            text=True
        )
        return logs
    except Exception as e:
        return f"Error reading logs: {e}"


def get_cpu_temp():
    try:
        out = subprocess.check_output(["vcgencmd", "measure_temp"], text=True)
        return out.replace("temp=", "").strip()
    except:
        return "unknown"


def get_now_playing():
    if os.path.exists(CURRENT_TRACK_FILE):
        return open(CURRENT_TRACK_FILE).read().strip()
    return "—"


def camera_locked():
    try:
        out = subprocess.check_output(
            ["lsof", "/dev/media0"], stderr=subprocess.DEVNULL, text=True
        )
        return "Yes" if out.strip() else "No"
    except:
        return "Unknown"


# ----------------------------
#   STREAM CONTROL ACTIONS
# ----------------------------
@app.route("/action/<cmd>")
@login_required
def action(cmd):

    if cmd == "start":
        os.system("sudo systemctl start lofi-streamer")

    elif cmd == "stop":
        os.system("sudo systemctl stop lofi-streamer")

    elif cmd == "restart":
        os.system("sudo systemctl restart lofi-streamer")

    elif cmd == "reboot-confirm":
        return render_template("reboot_confirm.html")

    elif cmd == "reboot-now":
        os.system("sudo reboot")

    return redirect(url_for("index"))

# ----------------------------
#   MAIN DASHBOARD
# ----------------------------
@app.route("/")
@login_required
def index():
    status = get_streamer_status()
    logs = get_recent_logs()
    temp = get_cpu_temp()
    camera = camera_locked()
    nowp = get_now_playing()

    return render_template(
        "index.html",
        status=status,
        logs=logs,
        temp=temp,
        camera=camera,
        nowp=nowp
    )


# ----------------------------
#   RUN
# ----------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=4455, debug=False)
