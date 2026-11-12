# Inventory — Secret đã chuyển về folder tập trung

Ngày tạo: 12/11/2026
Sprint: Refactor credentials tập trung

## Bảng secret

| Key | Nguồn cũ | Consumer | Trạng thái |
|---|---|---|---|
| `netmind_api_key` | `.env` | NetMind cloud API | ⏳ Chờ owner điền |
| `netchat_bot_token` | `.env.production` | NetChat DM bot | ⏳ Chờ owner điền |
| `netchat_channel_owner` | hardcode 7 file .py | DM owner (quanpt1) | ✅ Đã chuyển (giá trị public) |
| `netchat_channel_morning` | hardcode 2 file .py | Morning report channel | ✅ Đã chuyển (giá trị public) |
| `edge_shared_secret` | `edge_client/config.json` | Pi5 ↔ PC auth | ⏳ Chờ owner điền |
| `edge_hmac_secret` | `data/edge_hmac_secret.txt` | Edge HMAC signing | ⏳ Chờ owner điền |
| `app_secret_key` | `.env.production` | Flask app | ⏳ Chờ owner điền |
| `encryption_key` | `.env.production` | Data encryption | ⏳ Chờ owner điền |
| `jwt_secret` | `.env.production` | JWT signing | ⏳ Chờ owner điền |
| `smtp_password` | `.env.production` | SMTP relay | ⏳ Chờ owner điền |

## File cũ cần xử lý

| File | Hành động |
|---|---|
| `.env` | Giữ nguyên (NetMind API key) — sẽ refactor sau khi owner duyệt |
| `.env.production` | Giữ nguyên — sẽ refactor sau khi owner duyệt |
| `edge_client/config.json` | Giữ nguyên — sẽ refactor sau khi owner duyệt |
| `data/edge_hmac_secret.txt` | Giữ nguyên — sẽ refactor sau khi owner duyệt |
| `logs/dm_token2.txt` ... `dm_token5.txt` | Runtime, xóa được (token tạm) |

## File hardcode CHANNEL_ID cần refactor

| File | Line | Giá trị cũ |
|---|---|---|
| `src/quan_ai_brain/governance/netchat_approval_adapter.py` | 32 | `mwp3nk3ciprjjr4hdmcoqgk6jr` |
| `src/quan_ai_brain/governance/netchat_info_gap_adapter.py` | 36 | `mwp3nk3ciprjjr4hdmcoqgk6jr` |
| `src/quan_ai_brain/integration/netchat_bridge.py` | 43 | `mwp3nk3ciprjjr4hdmcoqgk6jr` |
| `src/quan_ai_brain/integration/netchat_bridge.py` | 44 | `mwp3nk3ciprjjr4hdmcoqgk6jr` |
| `tools/morning_report.py` | 33 | `4phc9b1mx78qjq3grxcw89u94a` |
| `tools/netchat_auto_responder.py` | 159 | `mwp3nk3ciprjjr4hdmcoqgk6jr` |
| `tools/netchat_auto_responder.py` | 163 | `mwp3nk3ciprjjr4hdmcoqgk6jr` |
| `tools/setup_netchat_integration.py` | 32 | `4phc9b1mx78ajq3grccw89u94a` |
| `tools/test_netchat_debug.py` | 8 | `4phc9b1mx78qjq3grxcw89u94a` |

## Test fixtures (KHÔNG cần chuyển — đã là test)

| File | Ghi chú |
|---|---|
| `tests/test_authenticated_verifier.py:32` | `test_owner_secret_passcode_2026` |
| `tests/test_llm_provider.py:309` | `super_secret_password` |
| `tests/test_long_term_memory.py:284` | `***` |
| `tests/test_memory.py:10` | `secret-value` |
| `tests/test_owner_signature_verifier.py:233` | `test_owner_secret_key` |
| `tests/test_redaction.py:5` | `top-secret` |
| `src/quan_ai_brain/integration/manifest.py:26` | `API_KEY = "API_KEY"` (placeholder) |

## Bước tiếp theo (sau khi owner duyệt)

1. Owner điền giá trị thật vào `secrets.env` + `secrets.local.json`
2. Refactor 9 file .py để dùng `loader.get_secret()` thay hardcode
3. Xóa hardcode CHANNEL_ID trong 9 file
4. Test E2E: gửi DM, morning report, edge auth
5. Commit refactor (KHÔNG commit file secret)
