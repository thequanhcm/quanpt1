"""Loader secret tập trung cho QUAN AI BRAIN.

Đọc secret theo thứ tự ưu tiên:
1. Biến môi trường (process env → Task Scheduler env → shell env)
2. File secrets.local.json (folder user, pass, token)
3. File secrets.env (folder user, pass, token)

KHÔNG BAO GIỜ hardcode secret trong code. Luôn gọi get_secret("key_name").

Sprint 12/11/2026 — refactor từ hardcode rải rác trong 7 file .py + 2 file .env.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, Optional

# Đường dẫn tuyệt đối tới folder secret
_SECRET_DIR = Path(__file__).resolve().parent
_SECRETS_JSON = _SECRET_DIR / "secrets.local.json"
_SECRETS_ENV = _SECRET_DIR / "secrets.env"

# Cache để tránh đọc file nhiều lần
_cache: dict[str, str] = {}
_loaded = False


def _load_all() -> dict[str, str]:
    """Load toàn bộ secret từ JSON + env file vào cache."""
    global _loaded
    if _loaded:
        return _cache

    # 1. Load JSON (ưu tiên cao nhất vì có thể đặt giá trị phức tạp)
    if _SECRETS_JSON.exists():
        try:
            data = json.loads(_SECRETS_JSON.read_text(encoding="utf-8"))
            for k, v in data.items():
                _cache[k.lower()] = str(v)
        except Exception as e:
            print(f"[loader] WARN: secrets.local.json lỗi: {e}", file=sys.stderr)

    # 2. Load env file (KEY=value, comment bằng #)
    if _SECRETS_ENV.exists():
        try:
            for line in _SECRETS_ENV.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" not in line:
                    continue
                k, v = line.split("=", 1)
                k = k.strip().lower()
                v = v.strip().strip('"').strip("'")
                # JSON ưu tiên hơn env file
                if k not in _cache:
                    _cache[k] = v
        except Exception as e:
            print(f"[loader] WARN: secrets.env lỗi: {e}", file=sys.stderr)

    _loaded = True
    return _cache


def get_secret(key: str, default: Optional[str] = None) -> Optional[str]:
    """Đọc secret theo key name (case-insensitive).

    Thứ tự ưu tiên:
    1. os.environ[key.upper()] — biến môi trường
    2. secrets.local.json[key]
    3. secrets.env KEY=value
    4. default

    Args:
        key: Tên secret (vd: "netchat_bot_token", "netchat_channel_owner")
        default: Giá trị mặc định nếu không tìm thấy

    Returns:
        Giá trị secret hoặc default
    """
    # 1. Env var (uppercase)
    env_val = os.environ.get(key.upper())
    if env_val:
        return env_val

    # 2. File cache
    secrets = _load_all()
    return secrets.get(key.lower(), default)


def require_secret(key: str) -> str:
    """Đọc secret BẮT BUỘC — raise nếu không có.

    Dùng cho secret mà hệ thống không thể chạy nếu thiếu.
    """
    val = get_secret(key)
    if val is None:
        raise RuntimeError(
            f"[loader] THIẾU SECRET BẮT BUỘC: {key}\n"
            f"Thêm vào secrets.local.json hoặc secrets.env trong folder:\n"
            f"  {_SECRET_DIR}\n"
            f"Hoặc set biến môi trường {key.upper()}"
        )
    return val


def list_known_keys() -> list[str]:
    """Liệt kê tất cả key đã biết (để debug/audit)."""
    return sorted(_load_all().keys())


def reload() -> None:
    """Force reload cache (sau khi sửa file)."""
    global _loaded, _cache
    _cache = {}
    _loaded = False


if __name__ == "__main__":
    # CLI: python loader.py [key_name]
    if len(sys.argv) > 1:
        key = sys.argv[1]
        val = get_secret(key)
        if val:
            # Che giấu một phần khi in ra màn hình
            if len(val) > 8:
                masked = val[:4] + "*" * (len(val) - 8) + val[-4:]
            else:
                masked = "*" * len(val)
            print(f"{key} = {masked}")
        else:
            print(f"{key} = <MISSING>")
    else:
        print(f"Secret dir: {_SECRET_DIR}")
        print(f"Known keys: {list_known_keys()}")
