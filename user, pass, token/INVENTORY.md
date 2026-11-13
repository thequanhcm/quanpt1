# Inventory — Secret tập trung (rà soát lần 3, 12/11/2026 tối)

## SECRET THẬT đã copy về đây (nguồn gốc giữ nguyên — hệ thống 24/7 KHÔNG gián đoạn)

| Key | Nguồn gốc (hệ thống đang đọc) | Consumer | Giá trị |
|---|---|---|---|
| `netmind_api_key` | `.env` + HKCU\Environment registry | netmind_provider (LLM 24/7) | ✅ ĐÃ COPY (len 25) |
| `netchat_bot_token` | skill `bot-netchat/.env` | netchat_bot.py + responder fallback (DM 24/7) | ✅ ĐÃ COPY (len 26) |
| `netchat_bot_url` | skill `bot-netchat/.env` | netchat_bot.py | ✅ ĐÃ COPY |
| `edge_shared_secret` | `edge_client/config.json` | Pi5 ↔ PC HMAC auth (24/7) | ✅ ĐÃ COPY (len 64) |
| `edge_hmac_secret` | `data/edge_hmac_secret.txt` | Edge HMAC signing | ✅ ĐÃ COPY (len 64) |
| `netchat_channel_owner` | (public ID) | DM bot_tony ↔ quanpt1 | ✅ loader |
| `netchat_channel_morning` | (public ID) | Morning report 8AM | ✅ loader |
| `netchat_owner_user_id` | hardcode 1 file .py + 2 test | quanpt1 NetChat user ID | ✅ ĐÃ COPY (lần 3) |
| `netchat_bot_user_id` | hardcode 2 file .py | bot_tony user ID | ✅ ĐÃ COPY (lần 3) |

## KHÔNG phải secret thật (đã verify)

| File | Lý do |
|---|---|
| `.env.production` | Toàn bộ SECRET/KEY/PASSWORD/TOKEN là PLACEHOLDER `<...>` — chưa dùng |
| `docker-compose.yml` | Placeholder `change-me` / `admin` (Postgres/Grafana chưa deploy) |
| `tests/test_*.py` | Test fixture (mock token) |
| `tools/v42_optimize_user.ps1:12` | GUID của scheduled task Corel, không phải API key |
| `src/.../edge/models.py` | Tên constant (schema field) |
| `src/.../integration/manifest.py` | Placeholder `API_KEY = "API_KEY"` |

## Backup cũ chứa secret (khuyến nghị owner xóa sau duyệt)

| File | Nội dung |
|---|---|
| `backups/rename_cherry_20261106/config.json` | Copy cũ của edge shared_secret |
| `logs/dm_token2.txt` ... `dm_token5.txt` | DM confirm token runtime (tạm) |

## Quy tắc hoạt động 24/7 sau tập trung

1. **Consumer code KHÔNG đổi nguồn đọc** — server/responder/Pi5 đang chạy tiếp tục đọc
   từ env var + skill .env + edge config → KHÔNG cần restart, không gián đoạn.
2. Folder này là **SOURCE OF TRUTH** cho owner xem/rotate secret.
3. Khi rotate: owner đổi giá trị tại nguồn + cập nhật file ở đây trong cùng 1 lần.
4. `tools/audit_secrets.py` quét mỗi sprint — hiện **0 hardcode**.
5. Không commit file chứa giá trị (`.gitignore` đã chặn; secrets.env/secrets.local.json
   nằm ngoài git).

## Rà soát lần 3 (12/11 tối)

- Quét 2208 file (mọi ext: .py/.bat/.sh/.ps1/.json/.md/.log/.env...)
- **MỚI**: 2 user ID (owner + bot) đưa về loader + refactor 3 file .py + 2 test file
- Logs chỉ chứa message/user ID (KHÔNG có token thật — verify trực tiếp)
- `audit_secrets.py`: **0 hardcode, exit 0**
- E2E 24/7: servers 8765/8766 + LLM + responder + autonomous + Pi5 + DM — TẤT CẢ PASS
- DM xác nhận: post_id `r3kqezqmbb8of8oy49cjwpfa3w`
