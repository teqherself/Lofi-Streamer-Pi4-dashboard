#!/bin/bash
set -e
clear
echo "============================================"
echo "  GENDEMIK DIGITAL — LOFI STREAMER INSTALL  "
echo "             Susan v3.4 Installer           "
echo "============================================"
sleep 1

PI_USER="woo"
BASE_DIR="/home/$PI_USER/LofiStream"
VENV="$BASE_DIR/venv"

echo "→ Creating folder structure…"
mkdir -p $BASE_DIR/{Servers,Dashboard,Logo,Sounds}
mkdir -p $BASE_DIR/Dashboard/{templates,static}

echo "→ Updating system + installing dependencies…"
sudo apt update
sudo apt install -y \
    python3 python3-venv python3-pip \
    ffmpeg python3-picamera2 \
    libatlas-base-dev mutagen \
    lsof curl wget git \
    python3-flask python3-werkzeug \
    python3-psutil

echo "→ Creating Python venv…"
python3 -m venv $VENV
source $VENV/bin/activate
pip install flask mutagen werkzeug psutil

echo "→ Downloading Lofi Streamer + Dashboard files…"

# These three lines must be changed to your GitHub repo paths
REPO="https://raw.githubusercontent.com/yourusername/yourrepo/main"

curl -L "$REPO/Servers/lofi-streamer.py" -o "$BASE_DIR/Servers/lofi-streamer.py"
curl -L "$REPO/Dashboard/dashboard.py" -o "$BASE_DIR/Dashboard/dashboard.py"
curl -L "$REPO/Dashboard/system_helper.sh" -o "$BASE_DIR/Dashboard/system_helper.sh"

# Templates
curl -L "$REPO/Dashboard/templates/index.html" -o "$BASE_DIR/Dashboard/templates/index.html"
curl -L "$REPO/Dashboard/templates/login.html" -o "$BASE_DIR/Dashboard/templates/login.html"
curl -L "$REPO/Dashboard/templates/reboot_confirm.html" -o "$BASE_DIR/Dashboard/templates/reboot_confirm.html"

# CSS
curl -L "$REPO/Dashboard/static/style.css" -o "$BASE_DIR/Dashboard/static/style.css"

chmod +x "$BASE_DIR/Dashboard/system_helper.sh"

echo "→ Creating stream_url.txt if missing…"
if [ ! -f "$BASE_DIR/stream_url.txt" ]; then
    echo "rtmp://a.rtmp.youtube.com/live2/YOURKEYHERE" > "$BASE_DIR/stream_url.txt"
    echo "⚠️ Edit your RTMP key inside:  $BASE_DIR/stream_url.txt"
fi

echo "→ Installing sudoers rules…"
sudo bash -c "cat >/etc/sudoers.d/lofi-dashboard" <<EOF
$PI_USER ALL=NOPASSWD: $BASE_DIR/Dashboard/system_helper.sh
$PI_USER ALL=NOPASSWD: /usr/bin/systemctl start lofi-streamer
$PI_USER ALL=NOPASSWD: /usr/bin/systemctl stop lofi-streamer
$PI_USER ALL=NOPASSWD: /usr/bin/systemctl restart lofi-streamer
$PI_USER ALL=NOPASSWD: /usr/bin/systemctl status lofi-streamer
$PI_USER ALL=NOPASSWD: /usr/bin/journalctl -u lofi-streamer -n 40 --no-pager
$PI_USER ALL=NOPASSWD: /usr/bin/pkill
$PI_USER ALL=NOPASSWD: /usr/bin/lsof
$PI_USER ALL=NOPASSWD: /usr/bin/vcgencmd
$PI_USER ALL=NOPASSWD: /usr/sbin/reboot
EOF

chmod 440 /etc/sudoers.d/lofi-dashboard

echo "→ Installing systemd service: lofi-streamer…"
sudo bash -c "cat >/etc/systemd/system/lofi-streamer.service" <<EOF
[Unit]
Description=Lofi Streamer (GENDEMIK DIGITAL)
After=multi-user.target network-online.target

[Service]
User=$PI_USER
ExecStart=$VENV/bin/python3 $BASE_DIR/Servers/lofi-streamer.py
Restart=always

[Install]
WantedBy=multi-user.target
EOF

echo "→ Installing systemd service: lofi-dashboard…"
sudo bash -c "cat >/etc/systemd/system/lofi-dashboard.service" <<EOF
[Unit]
Description=Lofi Streamer Dashboard
After=network.target

[Service]
User=$PI_USER
ExecStart=$VENV/bin/python3 $BASE_DIR/Dashboard/dashboard.py
Restart=always

[Install]
WantedBy=multi-user.target
EOF

echo "→ Reloading systemd + enabling services…"
sudo systemctl daemon-reload
sudo systemctl enable lofi-streamer
sudo systemctl enable lofi-dashboard
sudo systemctl start lofi-streamer
sudo systemctl start lofi-dashboard

echo ""
echo "============================================"
echo "  INSTALL COMPLETE — GENDEMIK DIGITAL ❤️"
echo "============================================"
echo ""
echo "Dashboard:  http://$(hostname -I | cut -d' ' -f1):8181"
echo "Streamer running under systemd."
echo ""
echo "Edit stream key:"
echo "  nano $BASE_DIR/stream_url.txt"
echo ""
echo "Reboot recommended. Do it now? (y/n)"
read confirm

if [[ "$confirm" =~ ^[Yy]$ ]]; then
    sudo reboot
fi
