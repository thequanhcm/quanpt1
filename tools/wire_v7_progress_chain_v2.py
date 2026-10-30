"""V7 wire v2: sửa block V7_CHAIN_WIRE — dùng biến progress_check_block thay
response_data (không tồn tại), và thêm trường vào _send_json cuối handler.

Idempotent qua marker; AST check trước khi ghi.
"""
import ast
import sys
from pathlib import Path

WS = Path(__file__).resolve().parents[1]
SERVER = WS / "src" / "quan_ai_brain" / "web" / "server.py"

src = SERVER.read_text(encoding="utf-8")

OLD_ASSIGN = 'response_data["progress_check"] = {'
NEW_ASSIGN = 'progress_check_block = {'
OLD_TAIL = '''                "persistence": persistence_info,
                "durable_task": durable_task_dict,
                "external_lookup": ext_lookup_info,
            })'''
NEW_TAIL = '''                "persistence": persistence_info,
                "durable_task": durable_task_dict,
                "external_lookup": ext_lookup_info,
                "progress_check": progress_check_block,
            })'''

if OLD_ASSIGN not in src:
    if 'progress_check_block' in src and 'V7_CHAIN_WIRE' in src:
        print("Already fixed — skip")
        sys.exit(0)
    print("OLD ASSIGN NOT FOUND — abort")
    sys.exit(1)

new_src = src.replace(OLD_ASSIGN, NEW_ASSIGN, 1)

# Init biến trước block (phòng khi exception trước khi gán) — đặt ngay sau comment V7_CHAIN_WIRE
new_src = new_src.replace(
    "# V7_CHAIN_WIRE: chain skill kiểm tra tiến độ",
    "# V7_CHAIN_WIRE: chain skill kiểm tra tiến độ (progress_check_block = None mặc định)",
    1,
)

# Thêm init rõ ràng ngay trước try của chain
INIT_ANCHOR = '''                # V7_CHAIN_WIRE: chain skill kiểm tra tiến độ (progress_check_block = None mặc định)
                try:'''
INIT_BLOCK = '''                # V7_CHAIN_WIRE: chain skill kiểm tra tiến độ (progress_check_block = None mặc định)
                progress_check_block = None
                try:'''
new_src = new_src.replace(INIT_ANCHOR, INIT_BLOCK, 1)

# Thêm trường vào _send_json
if OLD_TAIL not in new_src:
    print("OLD TAIL NOT FOUND — abort")
    sys.exit(1)
new_src = new_src.replace(OLD_TAIL, NEW_TAIL, 1)

try:
    ast.parse(new_src)
except SyntaxError as exc:
    print(f"AST FAIL: {exc} — NOT writing")
    sys.exit(1)

SERVER.write_text(new_src, encoding="utf-8")
ast.parse(SERVER.read_text(encoding="utf-8"))
print("Fixed OK + AST OK")
