# ❌ Uninstall Dashboard

```bash
sudo systemctl stop lofi-dashboard
sudo systemctl disable lofi-dashboard
sudo rm /etc/systemd/system/lofi-dashboard.service
sudo rm /etc/sudoers.d/lofi-dashboard
rm -rf ~/LofiStream/Dashboard
sudo systemctl daemon-reload
```
