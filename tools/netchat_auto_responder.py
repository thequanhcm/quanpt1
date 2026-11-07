"""Auto-responder for QUAN AI BRAIN on NetChat.

This script:
1. Monitors the owner DM (bot <-> quanpt1) + khong con dung kenh nao khac (31/10/2026)
2. Reads new messages from the channel
3. Processes them through QUAN AI BRAIN
4. Sends responses back to the channel

Run continuously to enable 24/7 auto-response.
"""
import json
import re
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# (01/11/2026) FIX P0 ROOT-CAUSE — "Command router error: No module named
# 'tools.netchat_command_center'": khi responder được spawn thừa hưởng
# PYTHONPATH của netMind Desktop (…\netmind_desktop\netmind-agent), package
# `tools` GIẢ (của agent) được import trước và CACHE vào sys.modules → mọi
# lệnh DM (kể cả 'Chup hinh') rơi vào GLM thay vì command center. Vá gốc:
# đẩy BRAIN root lên ĐẦU sys.path + xóa cache `tools` giả TRƯỚC khi ai đó
# import nó. Phải chạy TRƯỚC mọi import dùng package `tools`.
_BRAIN_ROOT = str(Path(__file__).resolve().parent.parent)
if _BRAIN_ROOT in sys.path:
    sys.path.remove(_BRAIN_ROOT)
sys.path.insert(0, _BRAIN_ROOT)
# Dọn cache `tools` không phải của BRAIN (nếu có) — sau khi BRAIN đứng đầu path,
# import tiếp theo của `tools` sẽ luôn phân giải về BRAIN.
for _stale in [m for m in list(sys.modules) if m == "tools" or m.startswith("tools.")]:
    _mf = str(getattr(sys.modules[_stale], "__file__", "") or "")
    if _mf and not _mf.lower().startswith(_BRAIN_ROOT.lower()):
        del sys.modules[_stale]


# (29/10/2026) pythonw windowless mode: sys.stdout/sys.stderr là None khi chạy
# dưới pythonw.exe — mọi print() sẽ raise AttributeError và giết service im lặng.
# Redirect toàn bộ output ra log file.
if sys.stdout is None or sys.stderr is None:
    _LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
    try:
        _LOG_DIR.mkdir(parents=True, exist_ok=True)
        sys.stdout = open(_LOG_DIR / "netchat_auto_responder_stdout.log", "a", buffering=1, encoding="utf-8", errors="replace")
        sys.stderr = sys.stdout
    except Exception:
        pass

# (29/10/2026) pythonw: responder KHÔNG còn console cha, nên MỖI lần
# subprocess.run(python.exe netchat_bot.py read ...) (poll mỗi 5s) sẽ tạo một
# cửa sổ console riêng → cửa sổ Python nháy liên tục trên màn hình.
# Patch toàn bộ subprocess.run của process này để không bao giờ tạo cửa sổ
# (CREATE_NO_WINDOW). Bao trùm cả module import vào cùng process
# (netchat_command_center, info-gap adapter, file extraction...).
_orig_subprocess_run = subprocess.run

# (30/10/2026) FIX TỔNG LỚP LỖI UTF-8: mọi process con (netchat_bot.py banner
# tiếng Việt, learning engine, pypdf/docx extract...) chạy dưới pythonw không
# console → Windows cp1252 → UnicodeEncodeError giết im lặng toàn bộ pipeline
# (CHERRY câm từ 18:09 lúc đó — rename 07/11 TONY→CHERRY). Ép UTF-8 cho MỌI subprocess.run() của process này.
_UTF8_ENV = {"PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"}

# (06/11/2026) FIX NameError: _NO_WIN bị xóa nhầm khi patch 30/10 (17 chỗ gọi
# vẫn còn) → "Error reading dm messages: name '_NO_WIN' is not defined" CHẾT
# TOÀN BỘ poll loop — bot câm hoàn toàn dù heartbeat vẫn LIVE (loop chạy qua
# except, không crash process). Khôi phục định nghĩa.
_NO_WIN = getattr(subprocess, "CREATE_NO_WINDOW", 0)

def _subprocess_run_no_window(*args, **kwargs):
    kwargs.setdefault("creationflags", getattr(subprocess, "CREATE_NO_WINDOW", 0))
    _env = dict(os.environ)
    _env.update(_UTF8_ENV)
    kwargs.setdefault("env", _env)
    # (31/10/2026) FIX decode: process cha doc stdout/stderr cua con theo bang ma
    # locale (cp1252) → UnicodeDecodeError giet thread poll im lang khi bot
    # script in banner tieng Viet (loi that: "charmap codec can't decode byte
    # 0x81"). Ep decode UTF-8 cho MOI subprocess.run cua process nay.
    kwargs.setdefault("encoding", "utf-8")
    kwargs.setdefault("errors", "replace")
    return _orig_subprocess_run(*args, **kwargs)

subprocess.run = _subprocess_run_no_window

# 24/7 reboot-proof (27/10/2026): watchdog giám sát responder qua "heartbeat"
# — file log được touch mỗi vòng poll. Không có heartbeat => responder chết/stuck
# và watchdog (check_netchat_bot) sẽ cảnh báo. Đây là file duy nhất responder ghi.
HEARTBEAT_PATH = Path(__file__).resolve().parent.parent / "logs" / "netchat_responder_heartbeat.log"


def touch_heartbeat() -> None:
    """Update heartbeat file mtime (watchdog reads freshness from this)."""
    try:
        HEARTBEAT_PATH.parent.mkdir(parents=True, exist_ok=True)
        HEARTBEAT_PATH.touch()
    except Exception:
        pass

# 27/10/2026 (owner): "trợ lý không hỏi lòng vòng" — nếu câu trả lời AI đang
# XIN PHÉP làm việc probe CHỈ ĐỌC (an toàn tuyệt đối), responder TỰ CHẠY probe
# thật ngay và trả KẾT QUẢ thay vì câu hỏi. Không ai phải trả lời "ok" cho
# việc bot tự làm được.
_PERMISSION_ASK_RE = re.compile(
    r"(cho phép em|cho em chạy|xác nhận cho em|em chờ lệnh|chờ anh xác nhận|"
    r"anh xác nhận[^\n]*nhé\?|xin phép anh|anh cho phép)",
    re.IGNORECASE,
)
_SAFE_PROBE_RE = re.compile(r"(probe|kiểm tra|trạng thái|xác minh)", re.IGNORECASE)


def _maybe_autorun_probe(ai_response: str) -> str | None:
    """AI vừa hỏi xin phép probe chỉ-đọc? → chạy thật, trả kết quả (không hỏi lại)."""
    if not ai_response:
        return None
    if not (_PERMISSION_ASK_RE.search(ai_response) and _SAFE_PROBE_RE.search(ai_response)):
        return None
    try:
        from tools.netchat_command_center import _reprobe_full
        fresh = _reprobe_full("probe lại toàn hệ thống")
    except Exception:
        return None
    # Giữ phần phân tích của AI (trước mục 'Đề xuất'), thay phần xin phép bằng kết quả thật
    head = ai_response.split("Đề xuất")[0].strip()
    return f"{head}\n\n{fresh}" if head else fresh


def generate_memory_storage_answer() -> str:
    """Generate answer about memory storage locations."""
    return """Dạ, trí nhớ của em được lưu trữ theo 3 tầng:

**1. Trí nhớ ngắn hạn (Session Memory)** 📝
- Lưu tại: `data/brain.db` (SQLite)
- Nội dung: Cuộc trò chuyện hiện tại, context phiên làm việc
- Đặc điểm: Tạm thời, mất khi kết thúc phiên

**2. Trí nhớ dài hạn (Long-term Memory)** 🗄️
- Lưu tại: `data/vector_db` (ChromaDB vector database)
- Nội dung: 
  • 150+ kiến thức từ brain.db đã được embedding
  • Kiến thức USER_PROVIDED (anh dạy)
  • Kiến thức VERIFIED (đã xác minh)
  • Kiến thức UNVERIFIED (chờ duyệt)
- Đặc điểm: Vĩnh viễn, có semantic search
- Công nghệ: ChromaDB + BGE-M3 embeddings (1024 dims)

**3. Kiến thức chuẩn (Verified Knowledge)** ✅
- Lưu tại: Cùng vector_db nhưng với verification_status = VERIFIED hoặc USER_PROVIDED
- Nội dung: Kiến thức đã được anh duyệt, có bằng chứng xác minh
- Đặc điểm: Ưu tiên cao nhất khi retrieval

**Tiers:**
- Short-term → Long-term → Verified (priority ranking)

Anh muốn em giải thích chi tiết phần nào ạ?"""


# (31/10/2026) Thong nhat: chi con lai DM voi chu so huu — kenh 'Tro ly Tony Pham' da bi bo (owner yeu cau xoa cac kenh khac, chi giu DM)
CHANNEL_ID = "mwp3nk3ciprjjr4hdmcoqgk6jr"  # kênh 'Trợ lý Tony Pham' (đã sửa typo c→x)
# (31/10/2026) DM bot↔quanpt1: owner trả lời trong DM nhưng responder cũ chỉ
# đọc kênh → tin DM bị bỏ qua (sự cố 01:42: 'Chào em' trong DM không được trả lời).
# Giờ responder theo dõi CẢ HAI nguồn và trả lời đúng nơi owner nhắn.
DM_CHANNEL_ID = "mwp3nk3ciprjjr4hdmcoqgk6jr"
OWNER_USERNAME = "quanpt1"
CHANNEL_NAME = "Trợ lý Tony Pham"  # (07/11) TÊN KÊNH API THẬT trên NetChat — CHỈ đổi khi owner đổi tên kênh phía NetChat; CHERRY = tên trợ lý, không phải tên kênh.
# (02/11/2026) Thay bot_quanpt1 thanh bot_tony
BOT_USER_ID = "66opztx9ut8rjxny555xhj84je"
CATCHUP_WINDOW_MIN = 720  # (01/11/2026, owner) sau restart/treo: quét lại TẤT CẢ
# tin anh gửi trong 12 giờ qua chưa được trả lời — không bỏ lỡ tin nào.
# (27/10/2026) Chống trả lời trùng sau restart: lưu các message_id ĐÃ trả lời
# vào data/netchat_responder_state.json. Restart mới merge file này vào
# seen_ids (đơn thuần đánh dấu đã xem — không trả lời lại tin cũ).
SEEN_STATE_PATH = Path(__file__).resolve().parent.parent / "data" / "netchat_responder_state.json"

def _load_seen_state() -> set:
    try:
        data = json.loads(SEEN_STATE_PATH.read_text(encoding="utf-8"))
        ids = data.get("answered_ids", [])
        return {str(x) for x in ids} if isinstance(ids, list) else set()
    except Exception:
        return set()

def _save_seen_state(ids: set) -> None:
    try:
        SEEN_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        bounded = sorted(ids)[-2000:]  # giữ tối đa 2000 id gần nhất
        SEEN_STATE_PATH.write_text(
            json.dumps({"answered_ids": bounded}, ensure_ascii=False),
            encoding="utf-8",
        )
    except Exception:
        pass  # state persistence là best-effort; poll vẫn hoạt động bình thường

_local_appdata = Path(os.environ.get("LOCALAPPDATA", r"C:\Users\DELL\AppData\Local"))
_script_cand = [
    _local_appdata / "netmind_desktop" / "skills" / "bot-netchat" / "netchat_bot.py",
    Path(r"C:\Users\DELL\AppData\Local\netmind_desktop\skills\bot-netchat\netchat_bot.py"),
]
NETCHAT_SCRIPT = str(next((p for p in _script_cand if p.exists()), _script_cand[0]))
_py_cand = [
    _local_appdata / "netmind_desktop" / "netmind-agent" / "venv" / "Scripts" / "python.exe",
    Path(r"C:\Users\DELL\AppData\Local\netmind_desktop\netmind-agent\venv\Scripts\python.exe"),
]
PYTHON_EXE = str(next((p for p in _py_cand if p.exists()), _py_cand[0]))
BRAIN_PYTHON = str(Path(__file__).resolve().parent.parent / ".venv" / "Scripts" / "python.exe")

# (31/10/2026) Fallback DM: kenh 'Tro ly Tony Pham' dang o che do RIENG TU — bot
# doc duoc nhung gateway tu choi dang bai (403 bot_private_channel). Khi gap loi
# nay, tu dong gui phan hoi qua DM cho chu so huu thay vi cam thay vi im lang.
OWNER_USERNAME = "quanpt1"
_DM_CACHE: str | None = None


def _get_owner_dm_channel() -> str | None:
    """Resolve DM channel id voi chu so huu (cache, chi resolve 1 lan/process)."""
    global _DM_CACHE
    if _DM_CACHE:
        return _DM_CACHE
    try:
        r = subprocess.run(
            [PYTHON_EXE, NETCHAT_SCRIPT, "find_dm", OWNER_USERNAME],
            capture_output=True, creationflags=_NO_WIN, text=True, timeout=30, encoding="utf-8",
            errors="replace",
        )
        if r.returncode == 0:
            meta = _parse_json_loose(r.stdout)
            cid = meta.get("channel_id")
            if cid:
                _DM_CACHE = cid
                return cid
    except Exception as e:
        print(f"   ⚠️ find_dm failed: {e}")
    return None


def _is_private_channel_403(err_text: str) -> bool:
    return "bot_private_channel" in (err_text or "")

# ---- File attachments (27/10/2026): chủ nhân yêu cầu "bot đọc file đính kèm".
# Khi tin nhắn có file_ids: tải file về + trích xuất văn bản + gắn vào prompt AI
# như bằng chứng chỉ-đọc. Venv dự án giữ dependencies = [] (stdlib) — trích xuất
# PDF/DOCX chạy trong venv agent (có sẵn pypdf/python-docx) qua subprocess cô lập.
MAX_FILE_BYTES = 20 * 1024 * 1024   # chặn an toàn 20 MB
MAX_EXTRACT_CHARS = 18000           # giữ prompt trong biên (~6k tokens)
ATTACH_DIR = Path(__file__).resolve().parent.parent / "data" / "netchat_files"
_TEXT_EXTS = {".txt", ".md", ".csv", ".log", ".json", ".yaml", ".yml", ".xml",
              ".html", ".htm", ".py", ".js", ".ts", ".sql", ".ini", ".cfg"}
# (31/10/2026) Ảnh: OCR bằng Windows OCR qua winocr (venv netMind agent).
# Không có model vision local — Windows OCR là引擎 hệ điều hành, offline, nhẹ.
_IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"}
_OCR_LANGS = {"vi": "vi-VN", "en": "en-US"}
_OCR_MAX_CHARS = 6000               # OCR text đưa vào prompt (giữ biên guard 5000)

# (31/10/2026, owner) ÂM THANH/ghi âm DM → STT bằng faster-whisper (offline).
# Model 'small' int8 CPU: load ~55s lần đầu, ~1.5–2s/bản ghi âm ngắn.
_AUDIO_EXTS = {".m4a", ".mp3", ".wav", ".amr", ".opus", ".aac", ".ogg",
               ".webm", ".flac", ".wma", ".mp4"}
_STT_TIMEOUT = 300  # giây — bản ghi âm dài vẫn chờ

def _stt_audio(path: Path) -> str:
    """Nhận diện giọng nói file audio → text tiếng Việt (subprocess venv BRAIN)."""
    code = (
        "import sys;"
        "sys.path.insert(0, r'E:\\BRAIN');"
        "from tools.voice_stt import transcribe;"
        "print(transcribe(sys.argv[1]))"
    )
    res = subprocess.run([BRAIN_PYTHON, "-c", code, str(path)],
                         capture_output=True, creationflags=_NO_WIN, text=True, timeout=_STT_TIMEOUT)
    out = (res.stdout or "").strip()
    if res.returncode == 0 and out and not out.startswith("STT_FAIL"):
        return out
    err = (res.stderr or out or "không rõ").strip()[-200:]
    raise RuntimeError(f"nhận diện giọng nói thất bại: {err}")

def _ocr_image(path: Path) -> str:
    """OCR ảnh — chuỗi 2 tầng, không phụ thuộc mạng:

    1) RapidOCR (onnxruntime, offline, hỗ trợ tốt cả tiếng Việt có dấu) trong
       venv agent — NHANH, CHÍNH, kết quả tốt nhất hiện có.
    2) Windows OCR (winocr) dự phòng khi RapidOCR lỗi — vi-VN nếu gói đã cài,
       ngược lại en-US. Winocr recognize_pil trả IAsyncOperation → .get().
    Cả hai chạy subprocess cô lập. Raise RuntimeError nếu cả hai rỗng/lỗi
    để caller ghi chú inline (fail-honest).
    """
    # Tầng 1: RapidOCR (onnx) — chính, hỗ trợ VN
    code_rapid = (
        "import sys;"
        "from rapidocr_onnxruntime import RapidOCR;"
        "engine = RapidOCR();"
        "result, _elapse = engine(sys.argv[1]);"
        "print('\\n'.join(line[1] for line in (result or [])))"
    )
    try:
        res = subprocess.run([PYTHON_EXE, "-c", code_rapid, str(path)],
                             capture_output=True, creationflags=_NO_WIN, text=True, timeout=180)
        if res.returncode == 0 and res.stdout.strip():
            return res.stdout.strip()
    except Exception:
        pass

    # Tầng 2: Windows OCR (winocr) — dự phòng
    code_win = (
        "import sys, winocr;"
        "from PIL import Image;"
        "img=Image.open(sys.argv[1]);"
        "img.load();"
        "op=winocr.recognize_pil(img, sys.argv[2]);"
        "res=op.get();"
        "print(res.text)"
    )
    last_err = ""
    for lang in ("vi-VN", "en-US"):
        try:
            res = subprocess.run([PYTHON_EXE, "-c", code_win, str(path), lang],
                                 capture_output=True, creationflags=_NO_WIN, text=True, timeout=120)
        except Exception as exc:
            last_err = f"{type(exc).__name__}: {exc}"
            continue
        if res.returncode == 0 and res.stdout.strip():
            return res.stdout.strip()
        last_err = (res.stderr or "").strip()[-200:]
        if lang == "vi-VN":
            continue  # gói OCR tiếng Việt thường chưa cài → thử en-US
        break
    raise RuntimeError(
        "OCR trả rỗng (RapidOCR + Windows OCR đều thất bại). Ảnh có thể mờ, "
        f"không chứa chữ, hoặc thiếu model. Chi tiết tầng cuối: {last_err}"
    )

def _extract_text(path: Path) -> str:
    """Trích xuất văn bản thuần từ file đã tải về (chỉ đọc, không sửa file)."""
    ext = path.suffix.lower()
    if ext in _TEXT_EXTS or ext == "":
        return path.read_text(encoding="utf-8", errors="replace")
    # (31/10/2026) Ảnh → OCR Windows (winocr, subprocess venv agent)
    if ext in _IMAGE_EXTS:
        return _ocr_image(path)
    if ext == ".pdf":
        # pypdf nằm trong venv agent — chạy subprocess cô lập, timeout 120s
        code = (
            "import sys;from pypdf import PdfReader;"
            "r=PdfReader(sys.argv[1]);"
            "print(chr(10).join((p.extract_text() or '') for p in r.pages))"
        )
        res = subprocess.run([PYTHON_EXE, "-c", code, str(path)],
                             capture_output=True, creationflags=_NO_WIN, text=True, timeout=120)
        if res.returncode == 0 and res.stdout.strip():
            return res.stdout
        raise RuntimeError(res.stderr.strip()[-200:] or "PDF không có lớp chữ (scan ảnh?)")
    if ext == ".docx":
        code = (
            "import sys;from docx import Document;"
            "d=Document(sys.argv[1]);"
            "print(chr(10).join(p.text for p in d.paragraphs if p.text.strip()))"
        )
        res = subprocess.run([PYTHON_EXE, "-c", code, str(path)],
                             capture_output=True, creationflags=_NO_WIN, text=True, timeout=60)
        if res.returncode == 0 and res.stdout.strip():
            return res.stdout
        raise RuntimeError(res.stderr.strip()[-200:] or "DOCX rỗng")
    # (31/10/2026, owner) ÂM THANH → nhận diện giọng nói (faster-whisper, offline,
    # venv BRAIN) — owner ra lệnh bằng giọng nói qua DM ghi âm:
    if ext in _AUDIO_EXTS:
        return _stt_audio(path)
    raise RuntimeError(f"Định dạng '{ext or 'không rõ'}' chưa hỗ trợ đọc (pdf/docx/văn bản thuần/âm thanh).")

def _parse_json_loose(text: str) -> dict:
    """Parse JSON từ stdout của skill script (có thể kèm header + JSON đa dòng)."""
    text = (text or "").strip()
    try:
        return json.loads(text)
    except (ValueError, TypeError):
        pass
    idx = text.find("{")
    while idx != -1:
        try:
            obj, _end = json.JSONDecoder().raw_decode(text[idx:])
            if isinstance(obj, dict):
                return obj
        except json.JSONDecodeError:
            pass
        idx = text.find("{", idx + 1)
    return {}

def extract_message_files(msg: dict) -> str:
    """Tải + trích xuất toàn bộ file đính kèm của 1 tin nhắn.

    Trả về block nội dung để ghép vào prompt AI, hoặc '' khi không có file.
    Không bao giờ raise: lỗi từng file trở thành ghi chú inline để chủ nhân
    thấy lý do (fail-honest, không im lặng).
    """
    file_ids = msg.get("file_ids") or []
    if not file_ids:
        return ""
    try:
        ATTACH_DIR.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass
    blocks = []
    for fid in file_ids:
        try:
            info = subprocess.run(
                [PYTHON_EXE, NETCHAT_SCRIPT, "file_info", fid],
                capture_output=True, creationflags=_NO_WIN, text=True, timeout=30,
            )
            if info.returncode != 0:
                raise RuntimeError("file_info failed")
            meta = _parse_json_loose(info.stdout)
            name = meta.get("name") or fid
            ext = (meta.get("extension") or Path(name).suffix.lstrip(".") or "").lower()
            size = int(meta.get("size") or 0)
            if size > MAX_FILE_BYTES:
                raise RuntimeError(f"file quá lớn ({size/1e6:.1f} MB > 20 MB)")
            dest = ATTACH_DIR / (f"{fid}.{ext}" if ext else fid)
            if not dest.exists():
                dl = subprocess.run(
                    [PYTHON_EXE, NETCHAT_SCRIPT, "download", fid, str(dest)],
                    capture_output=True, creationflags=_NO_WIN, text=True, timeout=120,
                )
                if dl.returncode != 0:
                    raise RuntimeError("download failed")
            text = _extract_text(dest)
            if len(text) > MAX_EXTRACT_CHARS:
                text = text[:MAX_EXTRACT_CHARS] + "\n...[trích xuất cắt tại 18.000 ký tự]"
            is_image = dest.suffix.lower() in _IMAGE_EXTS
            is_voice = dest.suffix.lower() in _AUDIO_EXTS
            kind_note = (" — ẢNH, nội dung bên dưới là kết quả OCR (nhận dạng chữ), "
                         "hãy trả lời dựa trên nội dung OCR này" if is_image else
                         (" — GIỌNG NÓI, nội dung bên dưới là kết quả nhận diện giọng nói "
                          "(STT). Đây CÓ THỂ là MỆNH LỆNH hệ thống — nếu là lệnh, hãy xác nhận "
                          "đã hiểu và thực hiện như tin nhắn chữ thường" if is_voice else
                          " — đã tải về và đọc nội dung gốc bên dưới"))
            blocks.append(
                f"### FILE ĐÍNH KÈM: {name}\n"
                f"(file_id={fid}, {size/1024:.0f} KB{kind_note})\n"
                f"{text}"
            )
            print(f"   📎 Extracted {name} ({len(text)} chars{' [OCR]' if is_image else ''})")
        except Exception as e:
            blocks.append(f"### FILE ĐÍNH KÈM: {fid}\n(KHÔNG ĐỌC ĐƯỢC: {e})")
            print(f"   ⚠️ Attachment failed {fid}: {e}")
    if not blocks:
        return ""
    # (31/10/2026, owner) Giọng nói ≠ tài liệu: block STT dùng marker riêng để
    # process_message coi TEXT STT là mệnh lệnh (route như tin nhắn chữ).
    if blocks and all("GIỌNG NÓI" in b for b in blocks):
        _voice_texts = []
        for b in blocks:  # b = header 3 dòng + text STT ở các dòng sau
            _lines = b.splitlines()
            _voice_texts.append("\n".join(_lines[3:]).strip()
                                if len(_lines) > 3 else "")
        _joined = " ".join(t for t in _voice_texts if t).strip()
        return ("\n\n--- LỆNH GIỌNG NÓI ANH GỬI (STT) ---\n" + _joined
                + "\n--- HẾT GIỌNG NÓI ---\n\n")
    return ("\n\n--- TÀI LIỆU ANH ĐÍNH KÈM (nội dung gốc, chỉ đọc) ---\n\n"
            + "\n\n".join(blocks)
            + "\n\n--- HẾT TÀI LIỆU ---\n\n")


# ---- (31/10/2026, owner) GHÉP CẶP ẢNH ↔ LỜI MÔ TẢ TRONG DM ----
# Quy tắc owner đặt ra:
# - Ảnh gửi KHÔNG kèm mô tả → KHÔNG phản hồi, giữ chờ lời mô tả.
# - Lời mô tả có thể gửi TRƯỚC hoặc SAU ảnh; khi lời mô tả đến thì TỔNG HỢP
#   cả ảnh (OCR) + lời yêu cầu rồi MỚI xử lý thành một.
# - Ảnh chờ tối đa 30 phút; quá hạn bỏ im lặng (đúng "chưa mô tả thì không
#   cần phản hồi").
# - LỆNH HỆ THỐNG ("mở chrome", "khóa máy"...) KHÔNG BAO GIỜ bị ghép với ảnh
#   đang chờ — lệnh phải thực thi ngay, không kéo vào luồng AI.
PENDING_FILES_TTL_MS = 30 * 60 * 1000  # ảnh chờ mô tả tối đa 30 phút
DESC_BEFORE_WINDOW_MS = 2 * 60 * 1000  # mô tả gửi TRƯỚC ảnh: ghép trong 2 phút


def _load_pending_files() -> list[dict]:
    """Đọc danh sách ảnh đang chờ lời mô tả từ state JSON (sống sót qua restart)."""
    try:
        data = json.loads(SEEN_STATE_PATH.read_text(encoding="utf-8"))
        items = data.get("pending_files")
        if isinstance(items, list):
            return [x for x in items if isinstance(x, dict) and x.get("file_ids")]
    except Exception:
        pass
    return []


def _save_state_files(answered: set, pending: list[dict] | None = None) -> None:
    """Ghi seen-state + danh sách ảnh đang chờ mô tả vào 1 file JSON.

    pending=None → giữ nguyên pending đang có trên đĩa (chỉ cập nhật answered).
    """
    try:
        SEEN_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        if pending is None:
            pending = _load_pending_files()
        bounded = sorted(answered)[-2000:]
        SEEN_STATE_PATH.write_text(
            json.dumps(
                {"answered_ids": bounded, "pending_files": pending[-20:]},
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
    except Exception:
        pass  # state persistence là best-effort; poll vẫn hoạt động bình thường


def _prune_pending(pending: list[dict], now_ms: int | None = None) -> list[dict]:
    """Bỏ ảnh chờ quá TTL — im lặng theo đúng yêu cầu owner (không nhắc)."""
    if now_ms is None:
        now_ms = int(time.time() * 1000)
    return [
        p for p in (pending or [])
        if now_ms - (p.get("create_at") or 0) <= PENDING_FILES_TTL_MS
    ]


def _msg_files_are_images(msg: dict) -> bool:
    """Kiểm tra TẤT CẢ file của tin có phải ảnh không (qua file_info thật)."""
    fids = msg.get("file_ids") or []
    if not fids:
        return False
    for fid in fids:
        try:
            info = subprocess.run(
                [PYTHON_EXE, NETCHAT_SCRIPT, "file_info", fid],
                capture_output=True, creationflags=_NO_WIN, text=True, timeout=30,
            )
            if info.returncode != 0:
                return False
            meta = _parse_json_loose(info.stdout)
            ext = (meta.get("extension")
                   or Path(meta.get("name") or "").suffix.lstrip(".")
                   or "").lower()
            if f".{ext}" not in _IMAGE_EXTS:
                return False
        except Exception:
            return False
    return True


def _plan_batch(
    fresh: list[dict],
    pending: list[dict],
    now_ms: int | None = None,
    image_check=None,
) -> tuple[list[dict], list[dict]]:
    """Lập kế hoạch xử lý cho CẢ LÔ tin mới (31/10/2026 — yêu cầu owner).

    Thiết kế 2 pha để mọi ảnh chỉ được dùng đúng MỘT lần:
      Pha 1 (CLAIM): duyệt tin cũ→mới. Ảnh-đơn không chữ → CLAIM làm "mô tả
      chuẩn bị" cho tin CHỮ GẦN NHẤT gửi TRƯỚC trong 2 phút (không phải lệnh
      hệ thống) — đúng luật "mô tả trước ảnh". Không tìm thấy → HOLD chờ mô
      tả đến sau. File không phải ảnh → việc xử lý ngay như cũ.
      Pha 2 (WORK): lần 2 cũ→mới. Ảnh đã claim → việc {mô tả chuẩn bị, file}.
      Tin CHỮ chưa dùng → gộp TẤT CẢ ảnh đang chờ (pending cũ + mới) thành
      MỘT việc (đúng luật "tổng hợp cả ảnh và lời yêu cầu"). Lệnh hệ thống →
      việc riêng chạy ngay, không bao giờ ghép ảnh. Chữ trơ trọi khác → việc
      AI bình thường.

    Trả về (danh sách việc, pending còn lại). Mỗi việc:
      {"msg": tin gốc (giữ _src/_chan để trả lời đúng nơi),
       "text": lời mô tả dùng để xử lý,
       "file_ids": file cần OCR/đọc}
    """
    if now_ms is None:
        now_ms = int(time.time() * 1000)
    if image_check is None:
        image_check = _msg_files_are_images
    try:
        from tools.netchat_command_center import detect_intent
    except Exception:
        detect_intent = None

    def _is_cmd(m: dict) -> bool:
        t = (m.get("message") or "").strip()
        return bool(t and detect_intent and detect_intent(t))

    pending = [p for p in (pending or []) if p.get("file_ids")]
    sorted_msgs = sorted(fresh, key=lambda m: (m.get("create_at", 0), str(m.get("id"))))

    # ---------- PHA 1: CLAIM — ảnh đơn tìm mô tả gửi TRƯỚC ----------
    claimed_by: dict[str, str] = {}     # image_msg_id -> text_msg_id
    text_used: set[str] = set()         # tin chữ đã bị claim làm mô tả chuẩn bị
    for idx, msg in enumerate(sorted_msgs):
        text = (msg.get("message") or "").strip()
        fids = [f for f in (msg.get("file_ids") or []) if f]
        if not (fids and not text) or _is_cmd(msg) or not image_check(msg):
            continue  # chỉ xét ảnh-đơn không chữ
        # tin chữ gần NHẤT gửi trước ảnh trong 2 phút, chưa dùng, không lệnh
        best_idx, best_cat = None, None
        for j in range(idx - 1, -1, -1):
            cand = sorted_msgs[j]
            ctext = (cand.get("message") or "").strip()
            if not ctext or _is_cmd(cand) or cand.get("id") in text_used:
                continue
            gap = msg.get("create_at", 0) - cand.get("create_at", 0)
            if 0 <= gap <= DESC_BEFORE_WINDOW_MS:
                if best_cat is None or cand.get("create_at", 0) > best_cat:
                    best_idx, best_cat = j, cand.get("create_at", 0)
        if best_idx is not None:
            claimed_by[msg.get("id")] = sorted_msgs[best_idx].get("id")
            text_used.add(sorted_msgs[best_idx].get("id"))

    # ---------- PHA 2: WORK — dựng các việc theo thứ tự thời gian ----------
    work: list[dict] = []
    for msg in sorted_msgs:
        text = (msg.get("message") or "").strip()
        fids = [f for f in (msg.get("file_ids") or []) if f]
        is_cmd = _is_cmd(msg)

        # (1) Ảnh-đơn không chữ
        if fids and not text:
            if is_cmd or not image_check(msg):
                # file thường (PDF/DOCX...) → hành vi cũ: xử lý ngay
                work.append({"msg": msg, "text": "", "file_ids": fids})
                continue
            desc_id = claimed_by.get(msg.get("id"))
            if desc_id:
                desc_text = next(
                    ((m.get("message") or "").strip() for m in sorted_msgs
                     if m.get("id") == desc_id), "")
                work.append({"msg": msg, "text": desc_text, "file_ids": fids})
            else:
                pending.append({"msg_id": msg.get("id"), "file_ids": fids,
                                "create_at": msg.get("create_at", 0) or now_ms})
            continue

        # (2) Tin CÓ CHỮ
        if text:
            if msg.get("id") in text_used:
                continue  # đã làm mô tả chuẩn bị cho 1 ảnh — không tạo việc riêng
            if is_cmd:
                # lệnh hệ thống: chạy ngay, KHÔNG ghép ảnh đang chờ
                work.append({"msg": msg, "text": text, "file_ids": fids})
                continue
            if pending:
                # mô tả gửi SAU: gộp TẤT CẢ ảnh đang chờ + chữ thành MỘT việc
                all_fids: list[str] = []
                for p in pending:
                    all_fids.extend(p.get("file_ids", []))
                work.append({"msg": msg, "text": text, "file_ids": all_fids})
                pending = []
                continue
            work.append({"msg": msg, "text": text, "file_ids": fids})
            continue

        # (3) Tin chỉ file (đã xử lý ở nhánh ảnh) — rơi xuống đây không làm gì

    return work, pending


def _fetch_reply_context(post_id: str) -> str:
    """(07/11/2026) Lấy nội dung tin gốc khi owner REPLY-quote.

    NetChat (Mattermost fork) gói tin được reply vào `props.reply_post` của
    post raw — nhưng `netchat_bot.py read` chỉ trả id/user_id/message/
    file_ids/create_at nên responder mất ngữ cảnh quote (sự cố 17:32:
    owner reply tin cảnh báo LIÊN BANG hỏi "Sao báo lỗi này" → bot bảo
    "chưa thấy lỗi nào"). Hàm này GET /api/v4/posts/{id} trực tiếp với
    token bot (đọc từ .env của skill, in-memory — KHÔNG log giá trị),
    trả về message của tin gốc hoặc "" nếu không có/không lấy được.
    """
    if not post_id:
        return ""
    token = ""
    try:
        _env = Path(__file__).resolve().parent.parent / "config" / "netchat.env"
        if not _env.exists():
            _env = Path(r"C:\Users\DELL\AppData\Local\netmind_desktop"
                        r"\skills\bot-netchat\.env")
        if _env.exists():
            for _line in _env.read_text(encoding="utf-8", errors="replace").splitlines():
                _line = _line.strip()
                if _line.startswith("NETCHAT_BOT_TOKEN="):
                    token = _line.split("=", 1)[1].strip()
                    break
    except Exception:
        return ""
    if not token:
        return ""
    try:
        import urllib.request as _ur
        import ssl as _ssl
        _req = _ur.Request(
            f"https://netchat.viettel.vn/api/v4/posts/{post_id}",
            headers={"Authorization": f"Bearer {token}"})
        with _ur.urlopen(_req, timeout=10, context=_ssl.create_default_context()) as _resp:
            _post = json.loads(_resp.read().decode("utf-8", "replace"))
        _rp = (_post.get("props") or {}).get("reply_post") or {}
        return (_rp.get("message") or "").strip()
    except Exception:
        return ""


def read_channel_messages(count=10):
    """Read recent messages from BOTH the channel and the owner DM.

    (31/10/2026) Mỗi tin được gắn thêm '_src' = 'channel' | 'dm' để bước
    trả lời biết phải gửi phản hồi về đúng nơi owner đã nhắn.
    """
    sources = [("channel", CHANNEL_ID), ("dm", DM_CHANNEL_ID)]
    all_msgs = []
    for src, cid in sources:
        try:
            result = subprocess.run(
                [PYTHON_EXE, NETCHAT_SCRIPT, "read", cid, str(count)],
                capture_output=True, creationflags=_NO_WIN,
                text=True,
                timeout=30,
            )
            if result.returncode == 0:
                msgs = json.loads(result.stdout)
                for m in msgs if isinstance(msgs, list) else []:
                    m["_src"] = src
                    m["_chan"] = cid
                all_msgs.extend(msgs if isinstance(msgs, list) else [])
        except Exception as e:
            print(f"Error reading {src} messages: {e}")
    return all_msgs


def _target_channel_for(msg):
    """Trả về channel id đích cho tin nhắn (đúng nơi owner nhắn)."""
    return msg.get("_chan") or CHANNEL_ID

def send_greeting_message():
    """Send welcome message when system starts or restarts.

    (06/11/2026, owner): bản tin rút gọn — CHỈ 2 dòng:
    "XIN CHÀO ANH QUANPT1! / Em là Cherry - Trợ lý số thông minh của anh!"
    (cũ: bảng trạng thái dài multi-section — bỏ theo lệnh owner)
    """
    greeting = """XIN CHÀO ANH QUANPT1!
Em là Cherry - Trợ lý số thông minh của anh!"""

    print("\n" + "="*60)
    print("👋 Sending greeting message to NetChat...")
    print("="*60)
    
    result = send_message(greeting)
    if "error" in result:
        print(f"   ❌ Error sending greeting: {result['error']}")
        return False
    else:
        print("   ✅ Greeting message sent successfully!")
        return True


# ---------------------------------------------------------------------------
# (02/11/2026, owner yêu cầu) VN-LANG tầng cuối — chuẩn hoá tiếng Việt cho
# mọi tin rời responder. Reuse bộ map của command center + bổ sung mật ngữ.
# ---------------------------------------------------------------------------
try:
    from tools.netchat_command_center import _VN_STATE_MAP as _CC_VN_MAP, _ERR_VN_MAP as _CC_ERR_MAP
except Exception:  # fail-honest: không có command center → map nội bộ tối thiểu
    _CC_VN_MAP, _CC_ERR_MAP = {}, {}

_VN_DM_STATUS = {
    "CRITICAL": "NGHIÊM TRỌNG", "WARNING": "CẢNH BÁO", "NORMAL": "BÌNH THƯỜNG",
    "UNKNOWN": "KHÔNG RÕ", "ONLINE": "HOẠT ĐỘNG", "OFFLINE": "MẤT KẾT NỐI",
    "READY": "SẴN SÀNG", "RUNNING": "ĐANG CHẠY", "STOPPED": "ĐÃ DỪNG",
    "PAUSED": "TẠM DỪNG", "OK": "BÌNH THƯỜNG", "FAILED": "THẤT BẠI",
    "DOWN": "MẤT KẾT NỐI", "HEALTHY": "KHỎE MẠNH", "BLOCKED": "BỊ CHẶN",
    "PENDING": "CHỜ XỬ LÝ", "APPROVED": "ĐÃ DUYỆT", "COMPLETED": "HOÀN THÀNH",
    "IN_PROGRESS": "ĐANG LÀM", "WAITING_APPROVAL": "CHỜ DUYỆT",
    "ERROR": "LỖI", "CONNECTED": "ĐÃ KẾT NỐI", "DISCONNECTED": "MẤT KẾT NỐI",
    "TIMEOUT": "QUÁ THỜI GIAN CHỜ",
}
_VN_DM_COMPONENTS = {
    "pc_host": "máy chính", "pi5_edge": "Pi 5", "selfcare_engine": "tự chăm sóc",
    "ram_percent": "RAM", "disk_percent": "ổ đĩa", "cpu_percent": "CPU",
    "connectivity": "kết nối", "response_time": "thời gian phản hồi",
}
_VN_DM_STATUS.update(_CC_VN_MAP)


def _vn_normalize_dm(text):
    """Chuẩn hoá 1 tin DM → tiếng Việt (giữ số liệu, ID, tên riêng)."""
    out = str(text or "")
    if not out:
        return out
    for en, vi in _VN_DM_COMPONENTS.items():
        out = out.replace(en, vi)
    for en, vi in _VN_DM_STATUS.items():
        out = out.replace(f" {en}", f" {vi}").replace(f"→ {en}", f"→ {vi}")
    return out


def send_message(text, confirmed_token=None, target_channel=None, root_id=None):
    """Send message to the channel (hoặc DM nếu tin gốc đến từ DM).

    (31/10/2026) target_channel: nếu tin gốc của owner đến từ DM thì truyền
    DM_CHANNEL_ID vào đây — phản hồi đi đúng nơi owner nhắn, không còn tình
    trạng trả lời trôi sang kênh khác.
    (01/11/2026, owner) root_id: id tin gốc — phản hồi thành REPLY trong
    thread của tin đó, anh thấy ngay em đang trả lời về mục nào.
    (02/11/2026, owner) VN-LANG: chuẩn hoá tiếng Việt TẦNG CUỐI — mọi tin rời
    responder đều tiếng Việt (trạng thái/mật ngữ → tiếng Việt, số liệu + tên
    riêng giữ nguyên).
    """
    text = _vn_normalize_dm(text)
    def _parse(stdout):
        try:
            return json.loads(stdout)
        except (ValueError, TypeError):
            # success output may be plain text — don't crash after a real send
            return {"ok": True, "raw": (stdout or "").strip()[:200]}

    dest = target_channel or CHANNEL_ID
    is_dm = (dest == DM_CHANNEL_ID)

    try:
        # DM: netchat_bot.py send <dm_channel_id> <text> (không cần --to-channel)
        # Channel: cần --to-channel
        cmd = [PYTHON_EXE, NETCHAT_SCRIPT, "send", dest, text]
        if root_id:
            cmd.extend(["--root-id", root_id])
        if not is_dm:
            cmd.append("--to-channel")
        if confirmed_token:
            cmd.extend(["--confirmed", confirmed_token])

        result = subprocess.run(cmd, capture_output=True, creationflags=_NO_WIN, text=True, timeout=30)

        if result.returncode == 0:
            return _parse(result.stdout)
        elif "CONFIRM-REQUIRED" in result.stdout:
            # Extract confirm token and auto-confirm
            for line in result.stdout.split("\n"):
                if line.startswith("CONFIRM-REQUIRED:"):
                    token = line.split(":", 1)[1].strip()
                    print(f"   🔄 Auto-confirming with token: {token}")
                    cmd_with_confirm = [PYTHON_EXE, NETCHAT_SCRIPT, "send", dest, text]
                    if root_id:
                        cmd_with_confirm.extend(["--root-id", root_id])
                    if not is_dm:
                        cmd_with_confirm.append("--to-channel")
                    cmd_with_confirm.extend(["--confirmed", token])
                    result2 = subprocess.run(cmd_with_confirm, capture_output=True, creationflags=_NO_WIN, text=True, timeout=30)
                    if result2.returncode == 0:
                        return _parse(result2.stdout)
                    # (31/10/2026) 403 bot_private_channel → fallback DM chủ sở hữu
                    err2 = (result2.stderr or "") + (result2.stdout or "")
                    if _is_private_channel_403(err2):
                        dm = _get_owner_dm_channel()
                        if dm:
                            print("   📨 Kênh riêng tư → gửi qua DM chủ sở hữu thay thế")
                            r3 = subprocess.run(
                                [PYTHON_EXE, NETCHAT_SCRIPT, "send", dm, text],
                                capture_output=True, creationflags=_NO_WIN, text=True, timeout=30,
                                encoding="utf-8", errors="replace",
                            )
                            out3 = (r3.stdout or "") + (r3.stderr or "")
                            if r3.returncode == 0:
                                return _parse(r3.stdout)
                            m3 = re.search(r"CONFIRM-REQUIRED:\s*([a-f0-9]+)", out3)
                            if m3:
                                r4 = subprocess.run(
                                    [PYTHON_EXE, NETCHAT_SCRIPT, "send", dm, text,
                                     "--confirmed", m3.group(1)],
                                    capture_output=True, creationflags=_NO_WIN, text=True, timeout=30,
                                    encoding="utf-8", errors="replace",
                                )
                                if r4.returncode == 0:
                                    return _parse(r4.stdout)
                                return {"error": (r4.stderr or r4.stdout)[:200]}
                            return {"error": out3[:200]}
                    return {"error": f"Confirm failed: {result2.stderr or result2.stdout}"}
        # (31/10/2026) 403 riêng tư ngay từ lần gửi đầu (không qua confirm)
        err_all = (result.stderr or "") + (result.stdout or "")
        if _is_private_channel_403(err_all):
            dm = _get_owner_dm_channel()
            if dm:
                print("   📨 Kênh riêng tư → gửi qua DM chủ sở hữu thay thế")
                rd = subprocess.run(
                    [PYTHON_EXE, NETCHAT_SCRIPT, "send", dm, text],
                    capture_output=True, creationflags=_NO_WIN, text=True, timeout=30,
                    encoding="utf-8", errors="replace",
                )
                outd = (rd.stdout or "") + (rd.stderr or "")
                if rd.returncode == 0:
                    return _parse(rd.stdout)
                md = re.search(r"CONFIRM-REQUIRED:\s*([a-f0-9]+)", outd)
                if md:
                    rd2 = subprocess.run(
                        [PYTHON_EXE, NETCHAT_SCRIPT, "send", dm, text,
                         "--confirmed", md.group(1)],
                        capture_output=True, creationflags=_NO_WIN, text=True, timeout=30,
                        encoding="utf-8", errors="replace",
                    )
                    if rd2.returncode == 0:
                        return _parse(rd2.stdout)
                    return {"error": (rd2.stderr or rd2.stdout)[:200]}
                return {"error": outd[:200]}
        return {"error": result.stderr if result.stderr else result.stdout}
    except Exception as e:
        return {"error": str(e)}

def process_message_with_ai(message_text):
    """Process message through QUAN AI BRAIN and get response."""
    try:
        # Call QUAN AI BRAIN API using urllib (no requests dependency)
        import urllib.request
        import urllib.error
        import json

        data = json.dumps({
            "query": message_text,
            "session_id": "netchat_auto_responder",
            "model": "zai-org/GLM-5.3-Flash",
            "reasoning_effort": "low",  # CRITICAL: GLM-5.3-Flash requires this!
        }).encode('utf-8')

        req = urllib.request.Request(
            "http://127.0.0.1:8765/api/chat",
            data=data,
            headers={"Content-Type": "application/json"}
        )

        with urllib.request.urlopen(req, timeout=120) as response:
            result = json.loads(response.read().decode('utf-8'))
            return result.get("answer", "Xin lỗi, em chưa xử lý được yêu cầu này.")
    except urllib.error.HTTPError as e:
        return f"⚠️ Lỗi HTTP {e.code}: {e.reason}"
    except urllib.error.URLError as e:
        return f"⚠️ Không kết nối được server: {e.reason}. Vui lòng kiểm tra server QUAN AI BRAIN đang chạy."
    except Exception as e:
        return f"⚠️ Lỗi xử lý: {str(e)}"


def _split_parts(text: str, limit: int = 4300) -> list[str]:
    """Chia text thành các phần ≤ limit ký tự, ưu tiên cắt tại xuống dòng."""
    parts: list[str] = []
    buf: list[str] = []
    size = 0
    for line in text.splitlines(keepends=True):
        # dòng đơn vượt limit → cắt cứng theo ký tự
        while len(line) > limit:
            if buf:
                parts.append("".join(buf))
                buf, size = [], 0
            parts.append(line[:limit])
            line = line[limit:]
        if size + len(line) > limit and buf:
            parts.append("".join(buf))
            buf, size = [], 0
        buf.append(line)
        size += len(line)
    if buf:
        parts.append("".join(buf))
    return parts


def _summarize_via_map_reduce(message_text: str) -> str:
    """Đọc tài liệu >5000 ký tự bằng map-reduce qua /api/chat.

    Câu hỏi thật của chủ nhân nằm cuối message (sau block tài liệu). Mỗi phần
    tài liệu ≤4300 ký tự (biên guard 5000). Map: tóm tắt tuần tự, phần sau
    được kèm tóm tắt dồn của các phần trước. Reduce: tổng hợp + trả lời câu
    hỏi thật. Bỏ hạn chế: đoạn header tối đa 150 ký tự mỗi phần để LLM biết
    ngữ cảnh đang ở giữa tài liệu.
    """
    marker = "--- TÀI LIỆU ANH ĐÍNH KÈM"
    head, _, tail = message_text.partition(marker)
    owner_question = tail.rsplit("--- HẾT TÀI LIỆU", 1)[-1].strip()
    owner_question = owner_question.lstrip("-").strip() or "Tóm tắt tài liệu này."
    doc_body = tail.rsplit("--- HẾT TÀI LIỆU", 1)[0]
    parts = _split_parts(doc_body)
    print(f"   🗂️ map-reduce: {len(parts)} phần × ≤4300 ký tự; câu hỏi: {owner_question[:60]!r}")

    running = ""
    for i, part in enumerate(parts, 1):
        # Ngân sách động: tổng prompt phải ≤ ~4900 (< guard 5000). Tóm tắt dồn
        # càng dài thì phần tài liệu trong bước đó càng bị cắt ngắn.
        budget = 4800 - 300 - len(running)
        if budget < 500:
            budget = 500
        if len(part) > budget:
            part = part[:budget] + "…[cắt giữa phần]"
        prompt = (
            f"Đang đọc phần {i}/{len(parts)} của một tài liệu anh chủ nhân gửi "
            f"(các phần trước đã tóm tắt dồn bên dưới nếu có).\n\n"
            f"TÓM TẮT DỒN TỪ CÁC PHẦN TRƯỚC:\n{running or '(đây là phần đầu)'}\n\n"
            f"NỘI DUNG PHẦN {i}:\n{part}\n\n"
            f"Cập nhật tóm tắt dồn (tối đa 10 gạch đầu dòng, ngắn gọn, giữ số "
            f"liệu, tên đơn vị, mốc thời gian):"
        )
        running = process_message_with_ai(prompt)
        if running.startswith("⚠️"):
            raise RuntimeError(f"map step {i} failed: {running[:120]}")
        print(f"   🗂️ map {i}/{len(parts)} OK ({len(running)} chars)")

    # Reduce: kẹp tổng prompt cuối ≤ ~4900 ký tự (guard 5000)
    summary = running
    if len(summary) > 3800:
        summary = summary[:1800] + "\n…[lược giữa]…\n" + summary[-1800:]
    final_prompt = (
        f"Anh chủ nhân gửi một tài liệu (đã chia {len(parts)} phần, em đã đọc "
        f"hết) và hỏi.\n\nTÓM TẮT TOÀN BỘ TÀI LIỆU:\n{summary}\n\n"
        f"CÂU HỎI CỦA ANH: {owner_question}\n\n"
        f"Trả lời dựa trên tóm tắt trên. Xưng 'em', gọi 'anh', giọng tự nhiên "
        f"miền Bắc. Không bịa số liệu không có trong tóm tắt."
    )
    answer = process_message_with_ai(final_prompt)
    if answer.startswith("⚠️"):
        raise RuntimeError(f"reduce failed: {answer[:120]}")
    return answer


def detect_intent_safe(text: str):
    """detect_intent không bao giờ ném — dùng cho check nhanh trước khi route."""
    try:
        from tools.netchat_command_center import detect_intent
        return detect_intent(text)
    except Exception:
        return None


def process_message(message_text, sender_user_id="", chat_session_id="default", payload=None):
    """Route: ok-confirm → system commands → approval cards → AI fallback.

    The channel is a dedicated owner<->assistant command center — no @bot
    needed. Commands like 'phê duyệt' execute real system actions; other
    messages fall through to the conversational AI. sender_user_id enables
    owner-identity verification in the approval adapter (V3 Section 5.2).

    27/10/2026 (owner): intent 'ok_silent' = anh xác nhận nhưng không có việc
    chờ → KHÔNG gửi gì cả (không lòng vòng). 'ok_confirm' = đã thực thi việc
    chờ xác nhận.
    
    28/10/2026: Fix prompt card parsing - extract actual question from card text.
    """
    # (28/10/2026) Fix: Extract actual question from prompt card
    # NetChat prompt cards may send text like "Trả lời câu hỏi này" after the question
    # We need to extract the actual question before such phrases
    import re
    question_extract_re = re.compile(r'^(.+?)(?:\s*[.-]\s*Trả lời|Trả lời câu|Gửi câu hỏi|Nhấn để)', re.IGNORECASE)
    match = question_extract_re.match(message_text.strip())
    if match:
        extracted_question = match.group(1).strip()
        if extracted_question and len(extracted_question) > 3:
            print(f"   📝 Extracted question from prompt card: '{extracted_question[:50]}...'")
            message_text = extracted_question
    
    # Handle common prompt card patterns
    if "Trí nhớ" in message_text or "memory" in message_text.lower():
        if "lưu trữ" in message_text or "ở đâu" in message_text:
            # Direct question about memory storage - bypass router
            print(f"   📚 Memory storage question detected")
            return generate_memory_storage_answer()
    
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
        from tools.netchat_command_center import route_message
        # (27/10/2026) Có tài liệu đính kèm → bỏ qua router lệnh (lệnh hệ thống
        # không bao giờ đi kèm file), đi thẳng AI với ngữ cảnh tài liệu.
        # Dùng 'in' (không startswith) vì block tài liệu đứng sau 2 xuống dòng.
        # (31/10/2026) NGOẠI LỆ: lệnh hiển thị ảnh lên Pi5 ĐI KÈM ảnh — ảnh là
        # ĐỐI TƯỢNG của lệnh, phải route vào command center (file đã nằm ở
        # data/netchat_files, handler tự lấy ảnh mới nhất).
        _no_doc_text = message_text.split("--- TÀI LIỆU ANH ĐÍNH KÈM")[0].strip()
        if ("--- TÀI LIỆU ANH ĐÍNH KÈM" in message_text
                and _no_doc_text
                and detect_intent_safe(_no_doc_text) == "tony_show_image"):
            message_text = _no_doc_text  # bỏ block tài liệu → route lệnh bình thường
        elif "--- TÀI LIỆU ANH ĐÍNH KÈM" in message_text:
            raise LookupError("route to AI with document context")
        # (31/10/2026, owner) LỆNH GIỌNG NÓI: tin ghi âm DM → STT → coi như
        # tin nhắn chữ, route bình thường (lệnh hệ thống chạy thật):
        if "--- LỆNH GIỌNG NÓI ANH GỬI" in message_text:
            try:
                _voice_text = (message_text
                               .split("--- LỆNH GIỌNG NÓI ANH GỬI (STT) ---", 1)[1]
                               .split("--- HẾT GIỌNG NÓI", 1)[0]
                               .strip())
            except IndexError:
                _voice_text = ""
            if _voice_text:
                message_text = _voice_text  # text STT thay thế → route như lệnh chữ
        # (06/11/2026) FIX session mismatch: route_message KHÔNG tự inject
        # chat_session_id vào payload → handle_relay_on/off đọc payload['chat_session_id']
        # = 'default' → pending rơi vào key 'default' dù owner đang ở DM thật →
        # 'ok' sau đó run_pending_action(chat_session_id thật) KHÔNG thấy gì → im lặng.
        # Inject ở đây (responder là entry point chính) — caller truyền đủ thì giữ nguyên.
        if payload is None:
            payload = {"chat_session_id": chat_session_id}
        elif "chat_session_id" not in payload:
            payload = {**payload, "chat_session_id": chat_session_id}
        intent, response = route_message(
            message_text, sender_user_id=sender_user_id, chat_session_id=chat_session_id,
            payload=payload,
        )
        if intent == "ok_silent":
            print("   🔇 'ok' nhưng không có việc chờ xác nhận → im lặng (không spam).")
            return None  # responder sẽ không gửi gì
        if intent is not None:
            print(f"   ⚡ System command: {intent}")
            return response
    except LookupError:
        pass
    except Exception as e:
        print(f"   ⚠️ Command router error: {e}")
    # (01/11/2026, M4-C ĐÃ DUYỆT) Self-Q&A wired: câu hỏi về bản thân CHERRY
    # ("em là ai", "em làm được gì", "hệ thống khỏe không"...) → trả lời TỪ DỮ
    # LIỆU SỐNG (SelfQA: self model + learning checkpoints + candidates + health)
    # thay vì để GLM bịa. Không khớp → None, đi tiếp GLM như cũ.
    try:
        from quan_ai_brain.cognition.self_qa import SelfQA
        _self_reply = SelfQA(_BRAIN_ROOT).answer(message_text)
        if _self_reply:
            print("   🪞 Self-Q&A (M4-C): trả lời từ dữ liệu sống.")
            return _self_reply
    except Exception as _e:
        print(f"   ⚠️ SelfQA error (bỏ qua, đi tiếp): {_e}")

    # (27/10/2026) Nếu prompt có tài liệu đính kèm: AI phải trả lời DỰA TRÊN
    # tài liệu, không được bảo "chưa có file" (bug thật ngày 27/10: bot trả
    # "Anh chưa đính kèm file nào" dù file đã vào prompt).
    if "--- TÀI LIỆU ANH ĐÍNH KÈM" in message_text:
        # (27/10/2026) Server guard: /api/chat chặn query > 5000 ký tự
        # ("Query exceeds maximum allowed length"). Tài liệu 18K ký tự không thể
        # gửi trực tiếp → tóm tắt map-reduce: chia phần ≤4300 ký tự, tóm tắt
        # tuần tự (mỗi lần kèm tóm tắt trước), tổng hợp cuối bằng chính /api/chat
        # — vẫn trong biên an toàn của server, không đụng guard nào.
        try:
            return _summarize_via_map_reduce(message_text)
        except Exception as e:
            print(f"   ⚠️ map-reduce failed: {e}")
            return (
                "⚠️ Em đã tải và đọc được tài liệu nhưng chưa tổng hợp nổi câu trả "
                "lời (lỗi xử lý nội bộ). Anh thử lại giúp em nhé."
            )
    # (01/11/2026, M5-C ĐÃ DUYỆT) Multi-turn DM: câu có đại từ ("nó", "vậy", "cái đó"...)
    # → bọc ngữ cảnh lượt trước để GLM hiểu liền mạch (cùng cơ chế kênh voice M5 P1).
    _dm_query = message_text
    try:
        from quan_ai_brain.cognition.conversation_state import ConversationStateManager
        _conv = ConversationStateManager(_BRAIN_ROOT)
        _dm_query = _conv.build_contextualized_query("dm", message_text)
        if _dm_query != message_text:
            print("   💬 M5-C: bọc ngữ cảnh lượt trước cho câu hỏi nối (anaphora).")
    except Exception as _e:
        print(f"   ⚠️ M5-C context wrap error (đi tiếp): {_e}")

    ai_reply = process_message_with_ai(_dm_query)
    autorun = _maybe_autorun_probe(ai_reply)
    if autorun is not None:
        print("   🤖 AI hỏi xin phép probe chỉ-đọc → tự chạy probe thật, trả kết quả.")
        return autorun
    # (01/11/2026, M5-C ĐÃ DUYỆT) Ghi state hội thoại DM (fire-and-forget, fail-honest)
    try:
        from quan_ai_brain.cognition.conversation_state import ConversationStateManager
        ConversationStateManager(_BRAIN_ROOT).update("dm", message_text, ai_reply)
    except Exception:
        pass
    return ai_reply

def main():
    """Main auto-responder loop.

    Message tracking: a bounded set of seen message IDs. On startup, all
    existing messages are marked seen EXCEPT the newest ones (within
    CATCHUP_WINDOW_MIN) which are answered — so a restart never replays the
    whole history but still responds to fresh unanswered owner messages.
    """
    print("=" * 70)
    print("QUAN AI BRAIN — NetChat Auto-Responder (Command Center 2 chiều)")
    print("=" * 70)
    print(f"Channel: {CHANNEL_NAME} ({CHANNEL_ID})")
    print(f"Started: {datetime.now(timezone.utc).isoformat()}")
    print("=" * 70)
    print("\nMonitoring for new messages... (Ctrl+C to stop)\n")
    
    # Send greeting message on startup/restart
    print("🚀 System starting up...")
    send_greeting_message()
    print()

    seen_ids: set[str] = set()
    answered_state = _load_seen_state()
    seen_ids |= answered_state
    if answered_state:
        print(f"[STATE] Nạp {len(answered_state)} message_id đã trả lời từ lần chạy trước (chống trùng lặp).")
    first_poll = True
    iteration = 0
    catchup_window_ms = CATCHUP_WINDOW_MIN * 60 * 1000

    while True:
        iteration += 1
        touch_heartbeat()
        try:
            messages = read_channel_messages(count=60)

            if messages:
                # oldest first so replies land in chronological order
                messages.sort(key=lambda x: x.get("create_at", 0))

                if first_poll:
                    now_ms = time.time() * 1000
                    # (29/10/2026) FIX bug catch-up: phải lọc fresh (kể cả loại
                    # tin đã trả lời ở lần chạy trước) TRƯỚC khi mark-all-seen.
                    # Code cũ mark TẤT CẢ seen trước → 100% tin mới bị loại ở
                    # bước seen-filter sau đó → catch-up sau restart KHÔNG BAO GIỜ
                    # trả lời tin nào (sự cố 29/10: 3 tin "Chào em" bị bỏ qua).
                    fresh = [
                        m for m in messages
                        if m.get("user_id") != BOT_USER_ID
                        and now_ms - m.get("create_at", 0) <= catchup_window_ms
                        and m.get("id") not in seen_ids
                    ]
                    # (01/11/2026, owner) KHÔNG mark-all-seen ở startup nữa:
                    # seen_ids chỉ cộng dồn khi TIN ĐƯỢC TRẢ LỜI THÀNH CÔNG
                    # (hoặc ok_silent). Nếu responder treo giữa chừng, tin
                    # chưa trả lời KHÔNG bị đánh dấu → lần chạy sau quét lại
                    # và phản hồi đúng ý anh. Chỉ mark ngay: tin bot, tin đã
                    # answered (trong seen_state), tin quá cũ (>12h).
                    for m in messages:
                        _mid = m.get("id")
                        if (m.get("user_id") == BOT_USER_ID
                                or _mid in seen_ids
                                or now_ms - m.get("create_at", 0) > catchup_window_ms):
                            seen_ids.add(_mid)
                    first_poll = False
                    # trùng nội dung trong catch-up (vd "Chào em" x3): trả lời
                    # 1 tin MỚI NHẤT duy nhất; tin không có text (file) không dedupe
                    dedup: dict[str, dict] = {}
                    for m in fresh:
                        _key = (m.get("message") or "").strip() or m.get("id", "")
                        dedup[_key] = m
                    fresh = list(dedup.values())
                    # answer at most the 5 newest fresh messages after restart
                    fresh = sorted(fresh, key=lambda x: x.get("create_at", 0))[-5:]
                    if fresh:
                        print(f"[STARTUP] {len(fresh)} tin nhắn mới trong {CATCHUP_WINDOW_MIN} phút qua — sẽ trả lời.")
                    else:
                        print("[STARTUP] Không có tin mới nào cần trả lời.")
                else:
                    fresh = [
                        m for m in messages
                        if m.get("id") not in seen_ids and m.get("user_id") != BOT_USER_ID
                    ]
                    # (29/10/2026) trùng nội dung trong cùng 1 vòng poll → trả
                    # lời 1 lần (tin mới nhất); tin file (không text) giữ nguyên
                    if len(fresh) > 1:
                        _dedup: dict[str, dict] = {}
                        for m in fresh:
                            _key = (m.get("message") or "").strip() or m.get("id", "")
                            _dedup[_key] = m
                        fresh = sorted(_dedup.values(), key=lambda x: x.get("create_at", 0))

                # ---- (31/10/2026, owner) GHÉP CẶP ẢNH ↔ LỜI MÔ TẢ ----
                # Lập kế hoạch CẢ LÔ trước khi xử lý: ảnh-đơn không chữ được
                # HOLD chờ mô tả (tối đa 30 phút); lời mô tả gửi trước/sau ảnh
                # đều được ghép; lệnh hệ thống vẫn chạy ngay; file thường giữ
                # hành vi cũ. Sau đó mới xử lý lần lượt từng việc.
                _batch_pending = _prune_pending(_load_pending_files())
                _work, _batch_pending = _plan_batch(fresh, _batch_pending)
                _save_state_files(seen_ids, _batch_pending)

                for item in _work:
                    msg = item["msg"]
                    msg_id = msg.get("id")
                    message_text = item["text"]
                    has_files = bool(item["file_ids"])
                    if has_files:
                        msg = dict(msg, file_ids=item["file_ids"])
                    timestamp = datetime.fromtimestamp(
                        msg.get("create_at", 0) / 1000, tz=timezone.utc
                    )
                    print(f"\n📩 New message at {timestamp.strftime('%H:%M:%S')}:")
                    print(f"   {message_text[:100]}")
                    if has_files and message_text:
                        print("   🔗 Ảnh + lời mô tả đã TỔNG HỢP — xử lý cùng lúc.")

                    # (27/10/2026) file đính kèm: tải + trích xuất TRƯỚC khi xử lý
                    file_context = ""
                    if has_files:
                        print(f"   📎 {len(msg.get('file_ids'))} file đính kèm — tải + trích xuất...")
                        file_context = extract_message_files(msg)

                    # (31/10/2026) local paths của file đã tải — truyền vào route
                    # cho lệnh 'hiển thị ảnh trên pi' (handler hiển thị đúng file
                    # của tin nhắn hiện tại, không đoán 'ảnh mới nhất').
                    _attach_dir = ATTACH_DIR
                    _local_paths = []
                    try:
                        for _fid in (item.get("file_ids") or []):
                            for _f in _attach_dir.iterdir():
                                if _fid in _f.name and _f.suffix.lower() in _IMAGE_EXTS:
                                    _local_paths.append(str(_f))
                                    break
                    except Exception:
                        _local_paths = []

                    print("   🤖 Processing...")
                    # (07/11/2026, owner: "khi anh reply lại nội dung tin nhắn, Cherry
                    # cần đọc để biết anh reply gì") — NetChat UI gói tin gốc vào
                    # props.reply_post (đã E2E: GET /posts/{id} → props.reply_post.message)
                    # nhưng netchat_bot.py read không trả field props → mất ngữ cảnh.
                    # Responder tự fetch raw post khi message không đủ ngữ cảnh.
                    reply_ctx = ""
                    _rp = ((msg.get("props") or {}).get("reply_post") or {})
                    if not _rp:
                        try:
                            reply_ctx = _fetch_reply_context(msg.get("id"))
                        except Exception:
                            reply_ctx = ""
                    else:
                        _rq = (_rp.get("message") or "").strip()
                        if _rq:
                            reply_ctx = _rq
                    _ai_text = (file_context + "\n" + message_text) if file_context else message_text
                    if reply_ctx:
                        _ai_text = f'[Anh QUANPT1 đang REPLY trích dẫn tin CHERRY gửi trước: "{reply_ctx}"]\nCâu hỏi của anh: {_ai_text}'
                    response = process_message(
                        _ai_text,
                        sender_user_id=msg.get("user_id", ""),
                        chat_session_id=CHANNEL_ID,
                        payload={"file_paths": _local_paths} if _local_paths else None,
                    )

                    if response is None or not str(response).strip():
                        # ok_silent / handler trả rỗng (vd 'chụp hình' đã gửi ảnh DM,
                        # metadata gộp caption): không gửi tin text rỗng/spam.
                        seen_ids.add(msg_id)
                        _save_seen_state(seen_ids)
                        _save_state_files(seen_ids, _batch_pending)
                        continue

                    print("   📤 Sending response...")
                    # (01/11/2026, owner) REPLY RÕ MỤC: gateway bot NetChat
                    # bỏ root_id (đã thử E2E — API trả root_id="") → dùng
                    # PREFIX trích dẫn tin gốc: anh thấy ngay em đang trả
                    # lời tin nào, chi tiết nào.
                    _orig_text = (msg.get("message") or "").strip()
                    _quote = " ".join(_orig_text.split())[:60]
                    _when = datetime.fromtimestamp(
                        msg.get("create_at", 0) / 1000, tz=timezone.utc
                    ).astimezone().strftime("%H:%M")
                    _prefixed = f"↩️ Trả lời tin \"{_quote}\" ({_when}):\n{response}"
                    result = send_message(_prefixed, target_channel=_target_channel_for(msg))
                    if "error" in result:
                        print(f"   ❌ Error: {result['error']}")
                    else:
                        print("   ✅ Response sent!")
                        # mark 'đã trả lời' CHỈ KHI gửi thành công — tin gửi
                        # lỗi sẽ được quét lại ở vòng sau (không mất tin).
                        seen_ids.add(msg_id)
                    _save_seen_state(seen_ids)
                    _save_state_files(seen_ids, _batch_pending)
                    # NetChat rate limit (HTTP 429) khi gửi dồn — nghỉ giữa các reply
                    time.sleep(3)

                # keep the seen set bounded
                if len(seen_ids) > 500:
                    seen_ids = set(sorted(seen_ids)[-200:])

            # V3 Sprint 4 (b): auto-reminder info-gap — mỗi ~12 vòng (≈1 phút)
            # quét task chờ quá hạn → gửi nhắc theo chính sách should_send_reminder
            # (≤5 lần, cách 12h; im lặng của anh KHÔNG đồng ý — chỉ nhắc, không tự làm)
            if iteration % 12 == 0:
                try:
                    from quan_ai_brain.governance.netchat_info_gap_adapter import (
                        get_analyzer, CHANNEL_ID as _CH,
                    )
                    import subprocess as _sp

                    _ana = get_analyzer()
                    for _row in _ana.list_waiting():
                        _tid = _row["task_id"]
                        if not _ana.should_send_reminder(_tid):
                            continue
                        _spec = json.loads(_row["spec_json"])
                        _open = [q for q in _spec.get("questions", []) if q.get("status") == "OPEN"]
                        if not _open:
                            continue
                        _remind = (
                            f"🔔 Nhắc việc (lần {_row['reminder_count'] + 1}/5) — {_tid}: "
                            + " ".join(q["question"] for q in _open[:2])
                            + "\nTrạng thái: ĐANG CHỜ ANH QUANPT1 CUNG CẤP THÔNG TIN HOẶC CHỈ ĐẠO. CHƯA THỰC HIỆN HÀNH ĐỘNG NGHIỆP VỤ."
                        )
                        _ana.note_reminder_sent(_tid)
                        _sp.run(
                            [PYTHON_EXE,
                             NETCHAT_SCRIPT,
                             "send", _CH, "--to-channel", _remind],
                            capture_output=True, text=True, timeout=30,
                        )
                        print(f"   ⏰ Reminder sent: {_tid} (lần {_row['reminder_count'] + 1})")
                except Exception as _rem_err:
                    print(f"   ⚠️ reminder job error: {_rem_err}")

            time.sleep(2)  # (01/11/2026, owner) 5s→2s — phản hồi nhanh hơn

        except KeyboardInterrupt:
            print("\n\n🛑 Auto-responder stopped by user")
            break
        except Exception as e:
            print(f"\n⚠️  Error: {e}")
            import traceback
            traceback.print_exc()
            # (31/10/2026) 429 rate limit/suspended: nghỉ ĐỦ LÂU theo yêu cầu
            # server (retry_after) hoặc tối thiểu 90s — tránh tàn phá hạn mức
            # gateway (sự cố 01:07: poll 5s + poll lỗi 10s + tab Cockpit 10s
            # → bot bị suspended 15 phút vì rate_limit_violation).
            err_txt = str(e)
            backoff = 90
            m = re.search(r"suspended_until[\"':\s]+(\d{13})", err_txt)
            if m:
                _wait_s = int(m.group(1)) / 1000 - time.time()
                if _wait_s > backoff:
                    backoff = min(int(_wait_s) + 5, 3600)
                    print(f"   ⏳ Bot suspended — ngủ {backoff}s đến khi hết hình phạt.")
            else:
                m2 = re.search(r"retry_after[\"':\s]+(\d+)", err_txt)
                if m2:
                    backoff = max(backoff, min(int(m2.group(1)) + 2, 3600))
            time.sleep(backoff)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        # (02/11/2026) VN-LANG: pythonw windowless — stdout có thể là console
        # cp1252 gây UnicodeEncodeError khi in lỗi tiếng Việt. Ghi file UTF-8
        # thay vì print ra console (fail-honest: lỗi không biến mất).
        try:
            (Path(__file__).resolve().parent.parent / "logs").mkdir(exist_ok=True)
            with open(Path(__file__).resolve().parent.parent / "logs" / "netchat_responder_fatal.log", "a", encoding="utf-8", errors="replace") as fh:
                fh.write(f"{datetime.now(timezone.utc).isoformat()} Fatal: {e}\n")
        except Exception:
            pass
        sys.exit(1)
