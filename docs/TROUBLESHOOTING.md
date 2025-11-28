# 🛠️ Troubleshooting

## Dashboard not loading?
```bash
sudo systemctl status lofi-dashboard
```

## Login not working?
Check the hash:

```
~/LofiStream/Dashboard/dashboard.py
```

## Buttons not working?
Check sudoers:

```bash
cat /etc/sudoers.d/lofi-dashboard
```

## Streamer not responding?
```bash
sudo systemctl restart lofi-streamer
```

## Camera locked?
Use dashboard → Restart Camera  
or run:

```bash
sudo bash ~/LofiStream/Dashboard/system_helper.sh camera_restart
```
