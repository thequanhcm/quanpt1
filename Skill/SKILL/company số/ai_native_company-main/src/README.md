# Scripts và Công cụ

---

## install.sh (macOS / Linux)

Cài đặt tự động skills cho Claude Code, Antigravity, OpenClaw, hoặc Codex.

```bash
# Tương tác — chọn ứng dụng:
bash src/install.sh

# Chỉ định ứng dụng:
bash src/install.sh --app claude-code
bash src/install.sh --app antigravity
bash src/install.sh --app openclaw
bash src/install.sh --app codex
```

---

## install.ps1 (Windows)

Cài đặt tự động skills trên Windows qua PowerShell.

```powershell
# Tương tác — chọn ứng dụng:
powershell -ExecutionPolicy Bypass -File src\install.ps1

# Chỉ định ứng dụng:
powershell -ExecutionPolicy Bypass -File src\install.ps1 -App claude-code
powershell -ExecutionPolicy Bypass -File src\install.ps1 -App antigravity
powershell -ExecutionPolicy Bypass -File src\install.ps1 -App openclaw
powershell -ExecutionPolicy Bypass -File src\install.ps1 -App codex
```

---

## install-skills.sh

Cài đặt nhanh skills vào Claude Code (legacy).

```bash
bash src/install-skills.sh
# Hoặc chỉ định đường dẫn repo:
bash src/install-skills.sh /path/to/community_version
```

---

## create-sop-folder.sh

Tạo cấu trúc folder chuẩn cho SOP mới.

```bash
bash src/create-sop-folder.sh [org-root] [department] [sop-name]

# Ví dụ:
bash src/create-sop-folder.sh /path/to/company marketing create-linkedin-content
```

---

## archive-sop-run.sh

Archive output/ sang archive/[YYYY-MM]/ sau khi SOP run hoàn thành.

```bash
bash src/archive-sop-run.sh [sop-path]

# Ví dụ:
bash src/archive-sop-run.sh /path/to/company/marketing/create-linkedin-content
```

---

## migrate-existing-sop.sh

Chuyển đổi SOP folder cũ sang cấu trúc State Machine mới.

```bash
bash src/migrate-existing-sop.sh [sop-path]

# Hoặc migrate toàn bộ department:
for sop in /path/to/company/marketing/*/; do
  bash src/migrate-existing-sop.sh "$sop"
done
```
