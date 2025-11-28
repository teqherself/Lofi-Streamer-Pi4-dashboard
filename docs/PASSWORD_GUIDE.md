# 🔑 Password Guide (Dashboard Login)
The Dashboard uses a **PBKDF2-SHA256 hashed password**, not plain text.

---

## 🔹 Generate a password hash

Run this:

```bash
python3 - << 'EOF'
from werkzeug.security import generate_password_hash
print(generate_password_hash("YOUR_NEW_PASSWORD"))
EOF
```

Copy the output, then open:

```
~/LofiStream/Dashboard/dashboard.py
```

Replace:

```python
PASSWORD_HASH = "Replace_me_with_your_password_hash_key"
```

Restart dashboard:

```bash
sudo systemctl restart lofi-dashboard
```
