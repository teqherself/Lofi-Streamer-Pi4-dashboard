#!/usr/bin/env bash
set -e
echo "==============================================="
echo "   Lofi Streamer Dashboard — Add-On Installer"
echo "==============================================="

# --- Detect actual user -----------------------------------------
REAL_USER="${SUDO_USER:-$USER}"
USER_HOME=$(eval echo "~$REAL_USER")
LOFISTREAM_DIR="$USER_HOME/LofiStream"
DASH_DIR="$LOFISTREAM_DIR/Dashboard"

echo "→ Installing as user: $REAL_USER"
echo "→ Home directory: $USER_HOME"
echo "→ LofiStream root: $LOFISTREAM_DIR"
echo "→ Dashboard dir: $DASH_DIR"
echo

# --- Ensure streamer is already installed ------------------------
if [ ! -d "$LOFISTREAM_DIR" ]; then
    echo "❌ ERROR: LofiStream folder not found at:"
    echo "   $LOFISTREAM_DIR"
    echo "This add-on dashboard requires LofiStreamer to be installed first."
    exit 1
fi

# --- Install required packages ----------------------------------
echo "📦 Installing dependencies…"
sudo apt update -y
sudo apt install -y python3-flask python3-psutil lsof

# --- Create Dashboard folder ------------------------------------
echo "📁 Creating dashboard folder…"
mkdir -p "$DASH_DIR"
mkdir -p "$DASH_DIR/static"
mkdir -p "$DASH_DIR/templates"

# --- Copy dashboard python files --------------------------------
echo "📄 Copying dashboard files…"
cp dashboard.py "$DASH_DIR/dashboard.py"
cp system_helper.sh "$DASH_DIR/system_helper.sh"
chmod +x "$DASH_DIR/system_helper.sh"

# --- Copy templates ----------------------------------------------
cp -r templates/* "$DASH_DIR/templates/"

# --- Copy static assets ------------------------------------------
cp -r static/* "$DASH_DIR/static/"

# --- Create systemd service --------------------------------------
SERVICE_FILE="/etc/systemd/system/lofi-dashboard.service"

echo "🛠 Creating systemd service: lofi-dashboard.service"

sudo bash -c "cat > $SERVICE_FILE" <<EOF
[Unit]
Description=Lofi Streamer Dashboard
After=network-online.target

[Service]
WorkingDirectory=$DASH_DIR
ExecStart=/usr/bin/python3 $DASH_DIR/dashboard.py
User=$REAL_USER
Restart=always
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF

# --- Reload + enable service --------------------------------------
echo "🔄 Reloading systemd…"
sudo systemctl daemon-reload

echo "🚀 Enabling dashboard service…"
sudo systemctl enable lofi-dashboard

echo "▶️ Starting dashboard service…"
sudo systemctl restart lofi-dashboard

# --- Sudoers: create safe file -----------------------------------
SUDOERS_FILE="/etc/sudoers.d/lofi-dashboard"

echo "🛡 Installing sudoers rules (safe)…"

sudo bash -c "cat > $SUDOERS_FILE" <<EOF
$REAL_USER ALL=NOPASSWD: $DASH_DIR/system_helper.sh
$REAL_USER ALL=NOPASSWD: /usr/bin/systemctl start lofi-streamer
$REAL_USER ALL=NOPASSWD: /usr/bin/systemctl stop lofi-streamer
$REAL_USER ALL=NOPASSWD: /usr/bin/systemctl restart lofi-streamer
$REAL_USER ALL=NOPASSWD: /usr/bin/systemctl status lofi-streamer
$REAL_USER ALL=NOPASSWD: /usr/bin/journalctl -u lofi-streamer -n 40 --no-pager
$REAL_USER ALL=NOPASSWD: /usr/bin/pkill
$REAL_USER ALL=NOPASSWD: /usr/bin/lsof
$REAL_USER ALL=NOPASSWD: /usr/bin/vcgencmd
$REAL_USER ALL=NOPASSWD: /usr/sbin/reboot
EOF

sudo chmod 440 "$SUDOERS_FILE"

# --- Finish ------------------------------------------------------
echo
echo "==============================================="
echo "   🎉 Dashboard Installed Successfully!"
echo "==============================================="
echo "Access the dashboard at:"
echo "   👉 http://<your-raspberry-pi-ip>:4455"
echo 
echo "Service controls:"
echo "   sudo systemctl restart lofi-dashboard"
echo "   sudo systemctl status lofi-dashboard"
echo
echo "Streamer controls handled inside dashboard UI."
echo
echo "Done!"
