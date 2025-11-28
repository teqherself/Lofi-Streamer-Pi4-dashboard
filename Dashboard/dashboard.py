#!/usr/bin/env python3
import os
import subprocess
import psutil
from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.security import check_password_hash

app = Flask(__name__)
app.secret_key = "lofi-dashboard-secret"

# ✔ PBKDF2 hashed password (replace with your hash if needed)
PASSWORD_HASH = "Replace_me_with_your_password_hash_key"

BASE = os.path.expanduser("~/LofiStream")


# ------------- AUTH -------------
def logged_in():
    return session.get("logged_in", False)


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        pw = request.form.get("password", "")
        if check_password_hash(PASSWORD_HASH, pw):
            session["logged_in"] = True
            return redirect(url_for("dashboard"))
        return render_template("login.html", error="Invalid password")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ------------- HELPERS -------------
def get_service_status():
    try:
        out = subprocess.check_output(
            ["systemctl", "is-active", "lofi-streamer"],
            text=True
        ).strip()
        return out
    except:
        return "unknown"


def get_uptime():
    try:
        raw = subprocess.check_output("uptime -p", shell=True, text=True)
        return raw.replace("up ", "").strip()
    except:
        return "unknown"


def get_track():
    f = "/tmp/current_track.txt"
    if os.path.exists(f):
        try:
            return open(f).read().strip()
        except:
            return "unavailable"
    return "no track"


def get_sysinfo():
    cpu = psutil.cpu_percent()
    ram = psutil.virtual_memory().percent
    disk = psutil.disk_usage("/").percent
    # temperature
    try:
        t = subprocess.check_output(["vcgencmd", "measure_temp"], text=True)
        temp = t.replace("temp=", "").replace("'C", "")
    except:
        temp = "N/A"
    return cpu, ram, disk, temp


def get_logs(service):
    try:
        out = subprocess.check_output(
            ["journalctl", "-u", service, "-n", "40", "--no-pager"],
            text=True
        )
        return out
    except:
        return "No logs"


# ------------- ROUTES -------------
@app.route("/")
def dashboard():
    if not logged_in():
        return redirect(url_for("login"))

    status = get_service_status()
    uptime = get_uptime()
    track = get_track()
    cpu, ram, disk, temp = get_sysinfo()

    streamer_logs = get_logs("lofi-streamer")
    dashboard_logs = get_logs("lofi-dashboard")

    # camera logs = streamer logs (recommended)
    camera_logs = streamer_logs

    return render_template(
        "index.html",
        status=status,
        uptime=uptime,
        track=track,
        cpu=cpu,
        ram=ram,
        disk=disk,
        temp=temp,
        streamer_logs=streamer_logs,
        camera_logs=camera_logs,
        dashboard_logs=dashboard_logs
    )


@app.route("/action/<cmd>")
def action(cmd):
    if not logged_in():
        return redirect(url_for("login"))

    if cmd == "start":
        os.system("sudo systemctl start lofi-streamer")
    elif cmd == "stop":
        os.system("sudo systemctl stop lofi-streamer")
    elif cmd == "restart":
        os.system("sudo systemctl restart lofi-streamer")
    elif cmd == "camrestart":
        os.system("sudo /home/$USER/LofiStream/Dashboard/system_helper.sh camera_restart")
    elif cmd == "reboot":
        os.system("sudo /home/$USER/LofiStream/Dashboard/system_helper.sh reboot")

    return redirect(url_for("dashboard"))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=4455)
