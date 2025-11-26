#!/bin/bash
set -e

echo "--------------------------------------------------"
echo " GENDEMIK DIGITAL — LOFI STREAMER INSTALLER"
echo " Susan v3.4 Installer"
echo "--------------------------------------------------"

# -----------------------------
# Detect username automatically
# -----------------------------
if [ "$SUDO_USER" ]; then
    USERNAME="$SUDO_USER"
else
    USERNAME="$USER"
fi

USER_HOME=$(eval echo "~$USERNAME")
LOFI_DIR="$USER_HOME/LofiStream"
VENV_DIR="$LOFI_DIR/venv"

echo "📌 Installing for user: $USERNAME"
echo "📁 Home directory: $USER_HOME"
echo "📁 LofiStream dir: $LOFI_DIR"

# -----------------------------
# Install required system packages
# -----------------------------
echo "📦 Installing system dependencies..."
sudo apt update
sudo apt install -y \
    python3 python3-venv python3-pip \
    ffmpeg python3-picamera2 \
    mutagen lsof curl wget git \
    libatlas-base-dev python3-psutil

# -----------------------------
# Create project folder
# -----------------------------
echo "📁 Creating LofiStream folder structure..."
mkdir -p "$LOFI_DIR"
mkdir -p "$LOFI_DIR/Sounds"
mkdir -p "$LOFI_DIR/Logo"
mkdir -p "$LOFI_DIR/Servers"
mkdir -p "$LOFI_DIR/Dashboard/static"
mkdir -p "$LOFI_DIR/Dashboard/templates"

# -----------------------------
# Copy project files to system
# (Git clone OR placed manually)
# -----------------------------
echo "📄 Copying streamer & dashboard files..."

# These files must already be in the repo
cp Servers/lofi-streamer.py "$LOFI_DIR/Servers/"
cp Dashboard/dashboard.py "$LOFI_DIR/Dashboard/"
cp Dashboard/system_helper.sh "$LOFI_DIR/Dashboard/"
cp Dashboard/static/style.css "$LOFI_DIR/Dashboard/static/"
cp Dashboard/templates/index.html "$LOFI_DIR/Dashboard/templates/"
cp Dashboard/templates/login.html "$LOFI_DIR/Dashboard/templates/"
cp Dashboard/templates/reboot_confirm.html "$LOFI_DIR/Dashboard/templates/"

chmod +x "$LOFI_DIR/Dashboard/system_helper.sh"

# -----------------------------
# Create stream_url.txt if missing
# -----------------------------
if [ ! -f "$LOFI_DIR/stream_url.txt" ]; then
    echo "rtmp://a.rtmp.youtube.com/live2/YOUR_STREAM_KEY" > "$LOFI_DIR/stream_url.txt"
    echo "📝 Created stream_url.txt (edit with your RTMP key)"
fi

# -----------------------------
# Python venv
# -----------------------------
echo "🐍 Creating Python virtual environment..."
python3 -m venv "$VENV_DIR"
source "$VENV_DIR/bin/activate"

echo "📦 Installing Python packages..."
pip install flask mutagen werkzeug psutil

deactivate

# -----------------------------
# Systemd service — Streamer
# -----------------------------
echo "🛠️ Installing systemd service: lofi-streamer"

STREAMER_SERVICE="/etc/systemd/system/lofi-streamer.service"

sudo bash -c "cat > $STREAMER_SERVICE" <<EOF
[Unit]
Description=Lofi Streamer (GENDEMIK DIGITAL)
After=multi-user.target network-online.target

[Service]
User=$USERNAME
ExecStart=$VENV_DIR/bin/python3 $LOFI_DIR/Servers/lofi-streamer.py
Restart=always
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF

# -----------------------------
# Systemd service — Dashboard
# -----------------------------
echo "🛠️ Installing systemd service: lofi-dashboard"

DASH_SERVICE="/etc/systemd/system/lofi-dashboard.service"

sudo bash -c "cat > $DASH_SERVICE" <<EOF
[Unit]
Description=Lofi Streamer Dashboard
After=network.target

[Service]
User=$USERNAME
ExecStart=$VENV_DIR/bin/python3 $LOFI_DIR/Dashboard/dashboard.py
Restart=always
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF

# -----------------------------
# Sudoers rules
# -----------------------------
echo "🔐 Installing sudoers rules..."

SUDOERS_FILE="/etc/sudoers.d/lofi-dashboard"

sudo bash -c "cat > $SUDOERS_FILE" <<EOF
$USERNAME ALL=NOPASSWD: $LOFI_DIR/Dashboard/system_helper.sh
$USERNAME ALL=NOPASSWD: /usr/bin/systemctl start lofi-streamer
$USERNAME ALL=NOPASSWD: /usr/bin/systemctl stop lofi-streamer
$USERNAME ALL=NOPASSWD: /usr/bin/systemctl restart lofi-streamer
$USERNAME ALL=NOPASSWD: /usr/bin/systemctl status lofi-streamer
$USERNAME ALL=NOPASSWD: /usr/bin/journalctl -u lofi-streamer -n 40 --no-pager
$USERNAME ALL=NOPASSWD: /usr/bin/pkill
$USERNAME ALL=NOPASSWD: /usr/bin/lsof
$USERNAME ALL=NOPASSWD: /usr/bin/vcgencmd
$USERNAME ALL=NOPASSWD: /usr/sbin/reboot
EOF

sudo chmod 440 "$SUDOERS_FILE"

# -----------------------------
# Enable & start services
# -----------------------------
echo "🚀 Enabling services..."

sudo systemctl daemon-reload
sudo systemctl enable lofi-streamer
sudo systemctl enable lofi-dashboard

sudo systemctl restart lofi-streamer
sudo systemctl restart lofi-dashboard

echo "--------------------------------------------------"
echo " ✅ INSTALL COMPLETE!"
echo "--------------------------------------------------"
echo " Dashboard available at:"
echo "   👉 http://$(hostname -I | awk '{print $1}'):8181"
echo ""
echo " Edit RTMP stream key:"
echo "   $LOFI_DIR/stream_url.txt"
echo ""
echo " Add music to:"
echo "   $LOFI_DIR/Sounds/"
echo ""
echo " Enjoy your streaming, Stevie ❤️"
echo " Susan is always here to help."
echo "--------------------------------------------------"
