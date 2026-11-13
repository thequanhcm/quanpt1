# User, Pass, Token — Kho tập trung

## Mục đích
Tập trung toàn bộ user, password, token, secret, API key, channel ID, HMAC key
và mọi thông tin nhạy cảm của hệ thống QUAN AI BRAIN tại một chỗ duy nhất.

## Quy tắc bất di bất dịch
1. **KHÔNG BAO GIỜ** hardcode user/token/password/secret trong code (.py, .bat, .sh, .ps1, .vbs, .yml, .json).
2. **KHÔNG BAO GIỜ** commit file chứa secret thật vào git.
3. Mọi secret phải đọc qua `loader.py` (xem bên dưới) hoặc biến môi trường.
4. Khi thêm secret mới → cập nhật `INVENTORY.md` + thêm vào `secrets.env` / `secrets.local.json`.

## Cấu trúc
| File | Mục đích |
|---|---|
| `secrets.env` | File env (KEY=value) — dùng cho shell script, docker, Task Scheduler |
| `secrets.local.json` | File JSON — dùng cho Python (dict access) |
| `loader.py` | Helper đọc secret an toàn (ưu tiên env var → fallback file) |
| `INVENTORY.md` | Danh sách secret đã chuyển + nguồn gốc + consumer |
| `README.md` | File này |

## Cách dùng

### Python
```python
from user_pass_token.loader import get_secret

# Đọc token (ưu tiên env var NETCHAT_BOT_TOKEN, fallback secrets.local.json)
token = get_secret("netchat_bot_token")

# Đọc channel ID
channel = get_secret("netchat_channel_owner")
```

### Shell / .bat
```bat
call "E:\BRAIN\user, pass, token\load_env.bat"
echo %NETCHAT_BOT_TOKEN%
```

### Task Scheduler
Trong Action → Add arguments:
```
/c "call "E:\BRAIN\user, pass, token\load_env.bat" && E:\BRAIN\.venv\Scripts\python.exe E:\BRAIN\tools\xxx.py"
```

## Backup
- File trong folder này KHÔNG được backup tự động (chứa secret).
- Owner tự backup thủ công vào nơi an toàn (USB mã hóa, password manager).
- Nếu mất file → phải rotate toàn bộ secret (đổi token, đổi password).

## Audit
- Mỗi sprint: chạy `tools/audit_secrets.py` để verify không còn hardcode.
- Mỗi khi thêm code mới: grep pattern `password|token|secret|key` trước khi commit.
