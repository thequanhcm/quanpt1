"""V7 wire v4: chuyển chain block ra ngoài khối create_task (12-space level).

Hiện block 16-space nằm trong `if create_task:` -> query thường không gán biến.
Move: cắt block (comment V7_CHAIN_WIRE .. except v7_err) + init, đặt lại ngay
trước dòng 'elapsed = round(' với indent 12 spaces.
"""
import ast
import sys
from pathlib import Path

WS = Path(__file__).resolve().parents[1]
SERVER = WS / "src" / "quan_ai_brain" / "web" / "server.py"

src = SERVER.read_text(encoding="utf-8")

START_MARKER = "                # V7_CHAIN_WIRE: chain skill kiểm tra tiến độ — chạy khi query khớp"
END_MARKER = '                    all_warnings.append(f"V7 progress chain: {str(v7_err)[:100]}")'

start = src.find(START_MARKER)
end = src.find(END_MARKER)
if start == -1 or end == -1:
    print("BLOCK MARKERS NOT FOUND — abort")
    sys.exit(1)
end += len(END_MARKER)

block_16 = src[start:end]
# Re-indent từ 16 -> 12 spaces
lines = block_16.split("\n")
new_lines = []
for ln in lines:
    if ln.startswith("    ") and not ln.strip() == "":
        new_lines.append(ln[4:])  # bỏ 4 spaces
    else:
        new_lines.append(ln)
block_12 = "\n".join(new_lines)

# Xoá block cũ (kể cả init đã ở trong đó)
src2 = src[:start] + src[end:].lstrip("\n").join(["\n", ""]) if False else src[:start] + "\n" + src[end + len(END_MARKER) + 1:] if False else src[:start] + src[end:]

# Thêm init vào đầu block_12 nếu chưa có
if "progress_check_block = None" not in block_12:
    block_12 = block_12.replace(
        "# V7_CHAIN_WIRE: chain skill kiểm tra tiến độ — chạy khi query khớp",
        "# V7_CHAIN_WIRE: chain skill kiểm tra tiến độ — chạy khi query khớp\n                progress_check_block = None",
        1,
    )
    # re-indent lại dòng init vừa thêm (16 -> đã trong block_12 nên giữ 12... làm lại):
    pass

# Đơn giản hơn: build lại block 12-space từ đầu với init
BLOCK_12_CLEAN = '''            # V7_CHAIN_WIRE: chain skill kiểm tra tiến độ — chạy khi query khớp
            # trigger của skill TASK_STATUS_RECONCILIATION (AVAILABLE). Đọc-only,
            # fail-honest, không chặn chat (lỗi chỉ append warning).
            progress_check_block = None
            try:
                from quan_ai_brain.cognition.skill_registry import SkillRegistry as _V7SR
                from quan_ai_brain.cognition.v7_skills import run_progress_check_chain as _v7_chain

                _v7_ws = _find_workspace_root()
                _v7_matches = _V7SR(_v7_ws / "data" / "skill_registry.json").find_matching_skills(query or "")
                if any(s.name == "TASK_STATUS_RECONCILIATION" for s in _v7_matches):
                    _v7_result = _v7_chain(query or "", _v7_ws)
                    progress_check_block = {
                        "chain": _v7_result["chain"],
                        "conclusion": _v7_result["reconciliation"]["conclusion"],
                        "records_matched": _v7_result["reconciliation"]["records_matched"],
                        "sources_accessed": _v7_result["reconciliation"]["sources_accessed"],
                        "sources_blocked": _v7_result["reconciliation"]["sources_blocked"],
                        "risk_summary": _v7_result["risk_summary"],
                        "report_md": _v7_result["report_md"],
                    }
            except Exception as v7_err:
                all_warnings.append(f"V7 progress chain: {str(v7_err)[:100]}")'''

# Xoá block cũ + init cũ trong vùng đó
src2 = src[:start] + "            elapsed_placeholder_keep" + src[end:]

# Tìm chỗ chèn: trước dòng 'elapsed = round(' sau vị trí đó
elapsed_pos = src2.find("elapsed = round(", start)
if elapsed_pos == -1:
    print("ELAPSED LINE NOT FOUND — abort")
    sys.exit(1)
# Đầu dòng elapsed
line_start = src2.rfind("\n", 0, elapsed_pos) + 1
src3 = src2[:line_start] + BLOCK_12_CLEAN + "\n\n" + src2[line_start:]

# Dọn placeholder
src3 = src3.replace("            elapsed_placeholder_keep\n", "")

try:
    ast.parse(src3)
except SyntaxError as exc:
    print(f"AST FAIL: {exc} — NOT writing")
    sys.exit(1)

# Sanity: chỉ 1 lần V7_CHAIN_WIRE, init ngoài create_task
assert src3.count("V7_CHAIN_WIRE") == 1, "duplicate wire marker"
assert "progress_check_block = None" in src3

SERVER.write_text(src3, encoding="utf-8")
ast.parse(SERVER.read_text(encoding="utf-8"))
print("Moved to outer scope OK + AST OK")
