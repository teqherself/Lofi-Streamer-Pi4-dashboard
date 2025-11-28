# 📦 Installation Guide — Dashboard Add-On

You **must install the Lofi Streamer first**  
This dashboard is an optional add-on.

Run:

```bash
bash <(wget -qO- https://raw.githubusercontent.com/teqherself/Lofi-Streamer-Pi4-dashboard/main/install.sh)
```

This will:

- Detect Pi username
- Install Flask + psutil
- Create Dashboard folder
- Install systemd service
- Add sudoers file automatically
- Start service on port **4455**

Open:

```
http://<pi-ip>:4455
```
