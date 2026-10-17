"""Run project tests and generate a safe handoff report.

The script only inventories the project folder. It does not scan sibling projects,
read environment variables, read secret files, inspect database contents, or run git mutations.
Run it only after reviewing the pending code diff, because pytest executes project tests.
"""
from __future__ import annotations

from datetime import datetime, timezone
import os
from pathlib import Path
import platform
import subprocess
import sys

# Ensure a fresh checkout can import the local package without an editable install.
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from quan_ai_brain.core.redaction import redact_text  # noqa: E402

EXCLUDED_DIRS = {
    ".git", ".venv", "venv", "env", "__pycache__", ".pytest_cache",
    ".mypy_cache", ".ruff_cache", "node_modules", "dist", "build",
    "data", "logs", "backups", "crash_dumps", ".idea", ".vscode",
}
EXCLUDED_NAMES = {
    ".env", "credentials.json", "secrets.json", "id_rsa", "id_ed25519",
}
EXCLUDED_SUFFIXES = {
    ".db", ".sqlite", ".sqlite3", ".pem", ".key", ".p12", ".pfx",
    ".log", ".pyc", ".pyd", ".dll", ".exe",
}
EXCLUDED_NAME_PARTS = ("credential", "secret", "token", "private_key")

SAFE_CONTEXT_DOCS = {
    "PROJECT_STATUS.md",
    "SYSTEM_BASELINE.md",
    "ARCHITECTURE_GAP_ANALYSIS.md",
    "NEXT_STEPS.md",
    "BAO_CAO_XAY_DUNG_HE_THONG_QUAN_AI_BRAIN.md",
    "ANTIGRAVITY_WORKFLOW.md",
    "WORKSPACE_MERGE_INSTRUCTIONS.md",
    "ANTIGRAVITY_APPLY_PROMPT.md",
    "AGENTS.md",
}


def is_sensitive_name(name: str) -> bool:
    lower = name.lower()
    if lower in EXCLUDED_NAMES or lower.endswith((".env", ".pem", ".key", ".p12", ".pfx")):
        return True
    if Path(lower).suffix in EXCLUDED_SUFFIXES:
        return True
    return any(part in lower for part in EXCLUDED_NAME_PARTS)


def safe_project_inventory() -> list[tuple[str, int]]:
    inventory: list[tuple[str, int]] = []
    for current, dirs, files in os.walk(ROOT):
        dirs[:] = sorted(d for d in dirs if d not in EXCLUDED_DIRS and not is_sensitive_name(d))
        for filename in sorted(files):
            if is_sensitive_name(filename):
                continue
            full = Path(current) / filename
            try:
                rel = full.relative_to(ROOT).as_posix()
                size = full.stat().st_size
            except (OSError, ValueError):
                continue
            # Keep generated handoff reports and arbitrary report artifacts out of the inventory.
            if rel.startswith("reports/"):
                continue
            inventory.append((rel, size))
    return inventory


def git_status() -> str:
    probe = subprocess.run(
        ["git", "-C", str(ROOT), "rev-parse", "--is-inside-work-tree"],
        capture_output=True, text=True, timeout=10, check=False,
    )
    if probe.returncode != 0 or probe.stdout.strip() != "true":
        return "Git repository chưa được khởi tạo hoặc Git không sẵn sàng."
    status = subprocess.run(
        ["git", "-C", str(ROOT), "status", "--short"],
        capture_output=True, text=True, timeout=10, check=False,
    )
    lines = []
    for line in status.stdout.splitlines():
        # Never include the names of credential-like files in a portable report.
        path_part = line[3:].strip() if len(line) > 3 else line
        if is_sensitive_name(Path(path_part.strip('"')).name):
            lines.append("[secret-like path omitted]")
        else:
            lines.append(redact_text(line))
    if status.returncode != 0:
        return "Không lấy được git status: " + redact_text(status.stderr.strip())
    return "\n".join(lines) if lines else "Working tree clean (không có thay đổi chưa commit)."


def run_tests() -> tuple[int, str, str]:
    command = [sys.executable, "-m", "pytest", "-q", "tests"]
    try:
        result = subprocess.run(
            command, cwd=ROOT, capture_output=True, text=True,
            timeout=180, check=False,
        )
        output = (result.stdout or "") + ("\n" + result.stderr if result.stderr else "")
        output = redact_text(output).strip() or "(pytest không sinh output)"
        return result.returncode, " ".join(command), output
    except FileNotFoundError:
        return 127, " ".join(command), "Không tìm thấy Python hoặc pytest. Cài dependencies dev rồi chạy lại."
    except subprocess.TimeoutExpired as exc:
        partial = exc.stdout or ""
        if isinstance(partial, bytes):
            partial = partial.decode("utf-8", errors="replace")
        return 124, " ".join(command), "TEST TIMEOUT sau 180 giây. Output cuối: " + redact_text(str(partial))[-4000:]


def load_project_status() -> str:
    path = ROOT / "docs" / "PROJECT_STATUS.md"
    if not path.is_file():
        return "Không có docs/PROJECT_STATUS.md; tình trạng triển khai cần được người phụ trách cập nhật."
    # Read only this explicitly designated documentation file, never configs or secrets.
    return redact_text(path.read_text(encoding="utf-8", errors="replace").strip())


def load_safe_context_docs() -> list[tuple[str, str]]:
    """Read only allowlisted Markdown project documents; never read arbitrary files."""
    found: list[tuple[str, str]] = []
    budget = 65000
    for current, dirs, files in os.walk(ROOT):
        dirs[:] = sorted(d for d in dirs if d not in EXCLUDED_DIRS and not is_sensitive_name(d))
        for filename in sorted(files):
            if filename not in SAFE_CONTEXT_DOCS or is_sensitive_name(filename):
                continue
            path = Path(current) / filename
            try:
                relative = path.relative_to(ROOT).as_posix()
                text_value = path.read_text(encoding="utf-8", errors="replace")
            except (OSError, ValueError):
                continue
            text_value = redact_text(text_value).strip()
            if len(text_value) > 18000:
                text_value = text_value[:18000] + "\n\n[TRUNCATED: document exceeded the per-file handoff limit]"
            if budget <= 0:
                break
            if len(text_value) > budget:
                text_value = text_value[:budget] + "\n\n[TRUNCATED: total context budget reached]"
            found.append((relative, text_value))
            budget -= len(text_value)
        if budget <= 0:
            break
    return found


def build_report(exit_code: int, command: str, test_output: str) -> str:
    now = datetime.now(timezone.utc)
    inventory = safe_project_inventory()
    package_dirs = ["core", "governance", "memory", "planning", "tools", "clae", "daemon"]
    module_state = []
    for module in package_dirs:
        exists = (ROOT / "src" / "quan_ai_brain" / module).is_dir()
        module_state.append(f"- `{module}`: {'directory exists' if exists else 'missing'}")

    test_verdict = "PASS" if exit_code == 0 else f"FAIL / NEEDS ATTENTION (exit code {exit_code})"
    lines = [
        "# QUAN AI BRAIN — Automated Handoff Report",
        "",
        "> Báo cáo được tạo tự động bởi `tools/validate_and_report.py`. Đây là trạng thái đọc được từ workspace tại thời điểm chạy; không đại diện cho việc xác minh hệ thống ngoại vi nếu chưa có test tích hợp.",
        "",
        "## 1. Phiên báo cáo",
        f"- UTC timestamp: `{now.isoformat()}`",
        f"- Workspace: `{ROOT}`",
        f"- Python: `{sys.version.split()[0]}`",
        f"- OS: `{platform.platform()}`",
        "- Report generator: `tools/validate_and_report.py`",
        "",
        "## 2. Kết quả kiểm thử",
        f"- Verdict: **{test_verdict}**",
        f"- Command: `{command}`",
        "```text",
        test_output[-12000:],
        "```",
        "",
        "## 3. Git status",
        "```text",
        redact_text(git_status())[-6000:],
        "```",
        "",
        "## 4. Cấu trúc module đã kiểm tra",
        *module_state,
        "",
        "## 5. Danh mục tệp an toàn trong workspace",
        "> Chỉ liệt kê đường dẫn tương đối và kích thước. Tệp bí mật, DB, log, dữ liệu runtime và thư mục build bị loại khỏi báo cáo.",
    ]
    if inventory:
        lines.extend(f"- `{path}` — {size} bytes" for path, size in inventory[:500])
        if len(inventory) > 500:
            lines.append(f"- ... còn {len(inventory) - 500} tệp bị lược bớt vì giới hạn báo cáo")
    else:
        lines.append("- Không tìm thấy tệp an toàn để liệt kê.")
    lines.extend([
        "",
        "## 6. Trạng thái dự án được người phát triển khai báo",
        load_project_status(),
        "",
        "## 7. Tài liệu dự án được đưa vào gói bàn giao",
        "> Chỉ các tài liệu Markdown có tên nằm trong danh sách cho phép mới được đính kèm. Tài liệu được lọc mẫu bí mật phổ biến; tuyệt đối không lưu token hoặc mật khẩu trong tài liệu dự án.",
    ])
    context_docs = load_safe_context_docs()
    if context_docs:
        for doc_path, doc_text in context_docs:
            lines.extend(["", f"### Source document: `{doc_path}`", "", doc_text])
    else:
        lines.append("Không tìm thấy tài liệu nguồn nằm trong danh sách cho phép.")
    lines.extend([
        "",
        "## 8. Ranh giới xác minh",
        "- Báo cáo này không quét ngoài workspace và không đọc `.env`, key/certificate, token, database hay biến môi trường.",
        "- Việc tệp hoặc thư mục tồn tại không chứng minh rằng tính năng đã hoạt động.",
        "- Chỉ coi phần có test output tương ứng là đã kiểm thử; chưa có test tích hợp nghĩa là tích hợp chưa được xác minh.",
        "- Tài liệu nguồn được lọc bằng redaction cơ bản; kiểm tra báo cáo trước khi chia sẻ, đặc biệt nếu tài liệu được viết thủ công.",
        "- Thông tin về Kernel L3, DC-COMMAND, SKILL_BAT_AI, Battery AI V4, VDCIM và NetChat cần được bổ sung bằng bằng chứng tích hợp riêng.",
        "",
        "## 9. Công việc tiếp theo",
        "1. Đọc kết quả test và xử lý mọi lỗi trước khi mở rộng tính năng.",
        "2. Kiểm tra `git diff` và xác nhận không có thay đổi ngoài ý muốn.",
        "3. Cập nhật `docs/PROJECT_STATUS.md` chỉ khi có bằng chứng mới.",
        "4. Gửi `reports/HANDOFF_LATEST.md` cho phiên hỗ trợ tiếp theo để tiếp tục từ trạng thái này.",
        "",
        "---",
        "Báo cáo này chứa danh mục và kết quả kiểm thử, không chứa mã nguồn đầy đủ. Nếu cần review một lỗi cụ thể, gửi thêm diff hoặc các tệp liên quan đã loại bỏ bí mật.",
        "",
    ])
    return "\n".join(lines)


def main() -> int:
    reports_dir = ROOT / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    exit_code, command, output = run_tests()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report = build_report(exit_code, command, output)
    latest = reports_dir / "HANDOFF_LATEST.md"
    archived = reports_dir / f"HANDOFF_{timestamp}.md"
    latest.write_text(report, encoding="utf-8")
    archived.write_text(report, encoding="utf-8")
    test_log = reports_dir / "TEST_RUN_LATEST.txt"
    test_log.write_text(
        f"Exit code: {exit_code}\nCommand: {command}\n\n{output}\n",
        encoding="utf-8",
    )
    print(f"Test exit code: {exit_code}")
    print(f"Handoff report: {latest}")
    print(f"Archived report: {archived}")
    print(f"Test log: {test_log}")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
