"""Tái hiện bug import của responder khi chạy PATH-MODE (không -m)."""
import sys
from pathlib import Path

print("sys.path[0] ban đầu:", sys.path[0])

# Giống chính xác line 948-949 của netchat_auto_responder.py:
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
print("Sau insert, sys.path[0]:", sys.path[0])

try:
    from tools.netchat_command_center import route_message
    print("IMPORT OK — route_message sẵn sàng")
except Exception as e:
    print(f"FAIL: {type(e).__name__}: {e}")
