"""V7 wire v3: move `progress_check_block = None` ra TRƯỚC khối try/except chứa
chain (hiện init nằm trong try — exception trước đó làm biến chưa gán).

Cụ thể: đưa init lên trước 'try:' của khối plan/pipeline (điểm vào an toàn),
hoặc đơn giản nhất: gán trong cả 2 nơi — trước khối plan và giữ nguyên trong
khối chain. An toàn nhất: gán ngay trước dòng 'try:' đầu tiên của cụm
auto-planning (marker: 'Auto-planning').
"""
import ast
import sys
from pathlib import Path

WS = Path(__file__).resolve().parents[1]
SERVER = WS / "src" / "quan_ai_brain" / "web" / "server.py"

src = SERVER.read_text(encoding="utf-8")

# Tìm dòng init hiện tại (trong khối chain) và xoá nó khỏi đó
CURRENT_INIT = '''                # V7_CHAIN_WIRE: chain skill kiểm tra tiến độ (progress_check_block = None mặc định)
                progress_check_block = None
                try:'''
MOVED = '''                # V7_CHAIN_WIRE: chain skill kiểm tra tiến độ (progress_check_block = None mặc định)
                try:'''

if CURRENT_INIT not in src:
    if MOVED in src and "progress_check_block = None" in src:
        print("Already moved — skip")
        sys.exit(0)
    print("CURRENT INIT NOT FOUND — abort")
    sys.exit(1)

src = src.replace(CURRENT_INIT, MOVED, 1)

# Gắn init ở đầu khối auto-planning (trước mọi try/except có thể chạy)
PLAN_ANCHOR = "Auto-planning"
# Tìm dòng chứa comment/khối auto-planning — quét từ vị trí V7 wire ngược lên
wire_pos = src.find("V7_CHAIN_WIRE")
plan_pos = src.rfind("Auto-planning", 0, wire_pos)
if plan_pos == -1:
    print("PLAN ANCHOR NOT FOUND — abort")
    sys.exit(1)

# Dòng chứa 'Auto-planning' — tìm đầu dòng và chèn init trước 'try:' tương ứng
# Cách an toàn: tìm '            try:' gần nhất trước plan_pos
try_line_start = src.rfind("\n            try:", 0, plan_pos)
if try_line_start == -1:
    print("TRY LINE NOT FOUND — abort")
    sys.exit(1)

insert_at = try_line_start + 1  # sau \n
src = src[:insert_at] + "            progress_check_block = None\n" + src[insert_at:]

try:
    ast.parse(src)
except SyntaxError as exc:
    print(f"AST FAIL: {exc} — NOT writing")
    sys.exit(1)

SERVER.write_text(src, encoding="utf-8")
ast.parse(SERVER.read_text(encoding="utf-8"))
print("Moved init OK + AST OK")
