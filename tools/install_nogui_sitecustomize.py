"""Cài sitecustomize_nogui vào venv E:\\BRAIN (idempotent).

Cách hoạt động: Python tự import `sitecustomize` lúc khởi động (site module).
Copy file vào <venv>/Lib/site-packages/ -> MỌI tiến trình python/pythonw của
venv này (daemon TONY 24/7, chat bridge, tool executor...) tự động thêm
CREATE_NO_WINDOW cho mọi subprocess -> không còn cửa sổ console nháy.

Idempotent: chạy lại chỉ ghi đè bản cũ. Gỡ: xóa file trong site-packages
hoặc đặt biến môi trường QAB_ALLOW_CONSOLE=1.
"""
from __future__ import annotations

import shutil
import site
import sys
from pathlib import Path

WS = Path(__file__).resolve().parents[1]
SRC = WS / "tools" / "sitecustomize_nogui.py"


def venv_site_packages() -> Path:
    """Tìm site-packages của venv .venv trong workspace."""
    venv = WS / ".venv"
    if not (venv / "Scripts" / "python.exe").exists():
        raise SystemExit("[LOI] Khong tim thay .venv tai E:\\BRAIN")
    # site-packages của venv hiện tại nếu script chạy bằng venv python
    for cand in (WS / ".venv" / "Lib" / "site-packages",):
        if cand.exists():
            return cand
    # fallback: hỏi site
    cands = [Path(p) for p in site.getsitepackages()]
    for c in cands:
        if ".venv" in str(c).lower() or str(WS).lower() in str(c).lower():
            return c
    raise SystemExit("[LOI] Khong xac dinh site-packages cua venv")


def main() -> None:
    dst_dir = venv_site_packages()
    dst = dst_dir / "sitecustomize.py"
    # Cảnh báo nếu đã có sitecustomize khác (không ghi đè mù quáng)
    if dst.exists() and "sitecustomize_nogui" not in dst.read_text(encoding="utf-8", errors="ignore"):
        print(f"[CANH BAO] {dst} da ton tai va KHONG phai ban nogui — khong ghi de.")
        print("           Kiem tra thu cong hoac dat QAB_ALLOW_CONSOLE=1 de tat patch.")
        raise SystemExit(1)
    shutil.copy(SRC, dst)
    print(f"[OK] Da cai {dst}")
    print("     Moi tien trinh pythonw/python cua venv se khong con nhay console.")
    print("     Kill-switch: QAB_ALLOW_CONSOLE=1")
    # Xác minh: import được và Popen đã được patch
    import subprocess
    r = subprocess.run([str(WS / ".venv" / "Scripts" / "pythonw.exe"), "-c",
                        "import subprocess; print('PATCHED' if subprocess.Popen.__module__ != 'subprocess' else 'NOT_PATCHED')"],
                       capture_output=True, text=True, timeout=30)
    out = (r.stdout or "").strip()
    print(f"[VERIFY] pythonw: {out or r.stderr[:200]}")


if __name__ == "__main__":
    main()
