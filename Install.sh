#!/usr/bin/env bash
set -e

echo "==============================================="
echo "   Lofi Streamer Dashboard — Add-On Installer"
echo "==============================================="

# --- Detect user --------------------------------------------------
REAL_USER="${SUDO_USER:-$USER}"
USER_HOME=$(eval echo "~$REAL_USER")
LOFISTREAM_DIR="$USER_HOME/LofiStream"
DASH_DIR="$LOFISTREAM_DIR/Dashboard"
RAW_BASE="https://raw.githubusercontent.com/teqherself/Lofi-Streamer-Pi4-dashboard/main"

echo "→ Installing for user: $REAL_USER"
echo "→ Home: $USER_HOME"
echo "→ Stream root: $LOFISTREAM_DIR"
echo "→ Dashboard dir: $DASH_DIR"
echo

# --- Verify streamer install --------------------------------------
if [ ! -d "$LOFISTREAM_DIR" ]; then
    echo "❌ ERROR: LofiStream not found at:"
    echo "   $LOFISTREAM_DIR"
    echo "Install lofi-streamer *before* running this add-on."
    exit 1
fi

if [ ! -f "$LOFISTREAM_DIR/Servers/lofi-streamer.py" ]; then
    echo "❌ ERROR: Streamer file missing. Not a valid install."
    exit 1
fi

# --- Install dependencies -----------------------------------------
echo "📦 Installing dependencies…"
sudo apt update -y
sudo apt install -y python3-flask python3-psutil curl lsof

# --- Create Dashboard layout --------------------------------------
echo "📁 Creating Dashboard directory…"
mkdir -p "$DASH_DIR/static"
mkdir -p "$DASH_DIR/templates"

# --- Download Python app ------------------------------------------
echo "⬇ Downloading dashboard.py…"
curl -fsSL "$RAW_BASE/dashboard.py" -o "$DASH_DIR/dashboard.py"

# --- Download system helper ---------------------------------------
echo "⬇ Downloading system_helper.sh…"
curl -fsSL "$RAW_BASE/system_helper.sh" -o "$DASH_DIR/system_helper.sh"
chmod +x "$DASH_DIR/system_helper.sh"

# --- Download Templates -------------------------------------------
echo "⬇ Downloading templates…"
curl -fsSL "$RAW_BASE/templates/index.html" -o "$DASH_DIR/templates/index.html"
curl -fsSL "$RAW_BASE/templates/login.html" -o "$DASH_DIR/templates/login.html"

# --- Download CSS -------------------------------------------------
echo "⬇ Downloading CSS…"
curl -fsSL "$RAW_BASE/static/style.css" -o "$DASH_DIR/static/style.css"

# --- Create Systemd service --------------------------------------
SERVICE_FILE="/etc/systemd/system/lofi-dashboard.service"

echo "🛠 Creating systemd service…"

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

# --- Reload + enable ---------------------------------------------
echo "🔄 Reloading systemd…"
sudo systemctl daemon-reload

echo "🚀 Enabling and starting dashboard…"
sudo systemctl enable lofi-dashboard
sudo systemctl restart lofi-dashboard

# --- Safe sudoers installation ------------------------------------
SUDOERS_FILE="/etc/sudoers.d/lofi-dashboard"

echo "🛡 Installing sudoers rules…"

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

echo
echo "==============================================="
echo "   🎉 Dashboard Installed Successfully!"
echo "==============================================="
echo "Access at:"
echo "   👉 http://<pi-ip>:4455"
echo
echo "To restart service:"
echo "   sudo systemctl restart lofi-dashboard"
echo
echo "Done!"
