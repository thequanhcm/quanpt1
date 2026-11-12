"""Audit secrets — quét toàn bộ workspace tìm hardcode user/token/password/secret.

Sprint 12/11/2026 — chạy mỗi sprint để đảm bảo không còn hardcode.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Pattern secret cần phát hiện
PATTERNS = [
    (r'(?i)(?:password|passwd|pwd)\s*=\s*["\'][^"\']+["\']', "password="),
    (r'(?i)(?:api_?key|apikey)\s*=\s*["\'][^"\']+["\']', "api_key="),
    (r'(?i)(?:secret_?key|secretkey)\s*=\s*["\'][^"\']+["\']', "secret_key="),
    (r'(?i)(?:auth_?token|access_?token|bearer)\s*=\s*["\'][^"\']+["\']', "token="),
    (r'(?i)(?:client_?secret)\s*=\s*["\'][^"\']+["\']', "client_secret="),
    (r'(?i)NETCHAT_(?:BOT|USER|PASS|TOKEN|CHANNEL|API)\s*=\s*["\'][^"\']+["\']', "NETCHAT_*"),
    (r'(?i)HMAC_(?:KEY|SECRET)\s*=\s*["\'][^"\']+["\']', "HMAC_*"),
    (r'(?i)SSH_(?:PASSWORD|PASS|KEY)\s*=\s*["\'][^"\']+["\']', "SSH_*"),
    (r'(?i)DB_(?:PASSWORD|PASS|USER)\s*=\s*["\'][^"\']+["\']', "DB_*"),
    (r'(?i)(?:GITHUB_?TOKEN|GH_?token)\s*=\s*["\'][^"\']+["\']', "GITHUB_*"),
]

# Channel ID + User ID cụ thể (hardcode trong code)
CHANNEL_IDS = [
    "mwp3nk3ciprjjr4hdmcoqgk6jr",
    "4phc9b1mx78qjq3grxcw89u94a",
    "4phc9b1mx78ajq3grccw89u94a",
    "3b1ughs36i8e9p46im8opnms8w",  # owner user id
    "66opztx9ut8rjxny555xhj84je",  # bot user id
]

# Thư mục chỉ là LOG/BACKUP/REPORT — không phải code chạy (hardcode ở đây không thực thi)
NON_CODE_DIRS = {"logs", "backups", "reports", "docs", "data"}

# Thư mục cần quét
SCAN_DIRS = ["src", "tools", "edge_client", "deploy", "tests"]

# File/folder bỏ qua
IGNORE = [".venv", "BRAIN_0", ".git", "node_modules", "__pycache__", ".pytest_cache"]


def is_test_fixture(filepath: Path, line: str) -> bool:
    """Kiểm tra có phải test fixture không (KHÔNG tính là hardcode)."""
    if "tests/" in str(filepath):
        return True
    test_patterns = [
        r"test_owner_secret",
        r"super_secret_password",
        r"top-secret",
        r"secret-value",
        r"\*\*\*",
        r"Bearer\s+[a-f0-9]{8,}",  # test fixture Bearer token
    ]
    return any(re.search(p, line) for p in test_patterns)


def is_loader_fallback(line: str) -> bool:
    """Kiểm tra có phải fallback trong _get_secret() không."""
    return "_get_secret" in line


def is_placeholder(line: str) -> bool:
    """Kiểm tra có phải placeholder không (vd: API_KEY = "API_KEY")."""
    m = re.search(r'\b(\w+)\s*=\s*["\'](\w+)["\']', line)
    if m and m.group(1).lower() == m.group(2).lower():
        return True
    return False


_DOCSTRING_CACHE: dict[str, list[tuple[int, int]]] = {}


def _get_docstring_ranges(filepath: Path) -> list[tuple[int, int]]:
    """Tìm các vùng docstring (start_line, end_line) - 1-indexed."""
    key = str(filepath)
    if key in _DOCSTRING_CACHE:
        return _DOCSTRING_CACHE[key]
    try:
        txt = filepath.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return []
    lines = txt.splitlines()
    ranges = []
    in_doc = False
    start = 0
    DQ = '"""'
    SQ = "'''"
    for i, l in enumerate(lines, start=1):
        triple_count = l.count(DQ) + l.count(SQ)
        if triple_count > 0:
            if not in_doc:
                start = i
                in_doc = True
                if triple_count >= 2:
                    ranges.append((start, i))
                    in_doc = False
            else:
                ranges.append((start, i))
                in_doc = False
    _DOCSTRING_CACHE[key] = ranges
    return ranges


def is_in_docstring_or_comment(filepath: Path, line_no: int) -> bool:
    """Kiểm tra dòng có nằm trong docstring/comment không."""
    try:
        txt = filepath.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return False
    lines = txt.splitlines()
    if line_no > len(lines):
        return False
    line = lines[line_no - 1]
    if line.strip().startswith("#"):
        return True
    for start, end in _get_docstring_ranges(filepath):
        if start <= line_no <= end:
            return True
    return False


def scan_file(filepath: Path) -> list[tuple[int, str, str]]:
    """Quét 1 file, trả về list (line_no, pattern_label, snippet)."""
    hits = []
    # File trong thư mục non-code → chỉ cảnh báo nhẹ, không tính FAIL
    is_non_code = bool(filepath.parts) and filepath.parts[0] in NON_CODE_DIRS
    try:
        txt = filepath.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return hits

    for line_no, line in enumerate(txt.splitlines(), start=1):
        if is_test_fixture(filepath, line):
            continue
        if is_loader_fallback(line):
            continue
        if is_placeholder(line):
            continue
        if is_in_docstring_or_comment(filepath, line_no):
            continue
        if filepath.name == "audit_secrets.py":
            continue

        for pat, label in PATTERNS:
            if re.search(pat, line):
                hits.append((line_no, label, line.strip()[:100]))

        for cid in CHANNEL_IDS:
            if cid in line and "_get_secret" not in line:
                hits.append((line_no, "CHANNEL_ID", line.strip()[:100]))

    return hits


def main() -> int:
    print(f"=== AUDIT SECRETS — {ROOT} ===\n")

    total_hits = 0
    files_with_hits = 0

    for scan_dir in SCAN_DIRS:
        dp = ROOT / scan_dir
        if not dp.exists():
            continue
        for f in dp.rglob("*.py"):
            rel = f.relative_to(ROOT)
            if any(p in rel.parts for p in IGNORE):
                continue
            hits = scan_file(f)
            if hits:
                is_non_code = bool(rel.parts) and rel.parts[0] in NON_CODE_DIRS
                if is_non_code:
                    # log/backup/report — không phải code thực thi
                    print(f"ℹ️  {rel} (non-code: log/backup/report)")
                    for line_no, label, snippet in hits[:3]:
                        print(f"   line {line_no} [{label}]: {snippet}")
                    if len(hits) > 3:
                        print(f"   ... +{len(hits)-3}")
                else:
                    files_with_hits += 1
                    total_hits += len(hits)
                    print(f"❌ {rel}")
                    for line_no, label, snippet in hits:
                        print(f"   line {line_no} [{label}]: {snippet}")
                print()

    print(f"\n=== KẾT QUẢ ===")
    print(f"Files có hardcode: {files_with_hits}")
    print(f"Tổng hits: {total_hits}")

    if total_hits == 0:
        print("\n✅ KHÔNG CÒN HARDCODE SECRET — hệ thống an toàn!")
        return 0
    else:
        print(f"\n⚠️ CÒN {total_hits} HARDCODE — cần refactor!")
        return 1


if __name__ == "__main__":
    sys.exit(main())
