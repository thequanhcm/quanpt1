"""Auto-responder for QUAN AI BRAIN on NetChat.

This script:
1. Monitors the NetChat channel 4phc9b1mx78qjq3grccw89u94a
2. Reads new messages from the channel
3. Processes them through QUAN AI BRAIN
4. Sends responses back to the channel

Run continuously to enable 24/7 auto-response.
"""
import json
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

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

def _subprocess_run_no_window(*args, **kwargs):
    kwargs.setdefault("creationflags", getattr(subprocess, "CREATE_NO_WINDOW", 0))
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


CHANNEL_ID = "4phc9b1mx78qjq3grxcw89u94a"  # kênh 'Trợ lý Tony Pham' (đã sửa typo c→x)
CHANNEL_NAME = "Trợ lý Tony Pham"
BOT_USER_ID = "edojmne9d7gcxx8axu1mzas3pr"
CATCHUP_WINDOW_MIN = 45  # sau restart: chỉ trả lời tin trong N phút qua
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

NETCHAT_SCRIPT = r"C:\Users\DELL\AppData\Local\netmind_desktop\skills\bot-netchat\netchat_bot.py"
PYTHON_EXE = r"C:\Users\DELL\AppData\Local\netmind_desktop\netmind-agent\venv\Scripts\python.exe"

# ---- File attachments (27/10/2026): chủ nhân yêu cầu "bot đọc file đính kèm".
# Khi tin nhắn có file_ids: tải file về + trích xuất văn bản + gắn vào prompt AI
# như bằng chứng chỉ-đọc. Venv dự án giữ dependencies = [] (stdlib) — trích xuất
# PDF/DOCX chạy trong venv agent (có sẵn pypdf/python-docx) qua subprocess cô lập.
MAX_FILE_BYTES = 20 * 1024 * 1024   # chặn an toàn 20 MB
MAX_EXTRACT_CHARS = 18000           # giữ prompt trong biên (~6k tokens)
ATTACH_DIR = Path(__file__).resolve().parent.parent / "data" / "netchat_files"
_TEXT_EXTS = {".txt", ".md", ".csv", ".log", ".json", ".yaml", ".yml", ".xml",
              ".html", ".htm", ".py", ".js", ".ts", ".sql", ".ini", ".cfg"}

def _extract_text(path: Path) -> str:
    """Trích xuất văn bản thuần từ file đã tải về (chỉ đọc, không sửa file)."""
    ext = path.suffix.lower()
    if ext in _TEXT_EXTS or ext == "":
        return path.read_text(encoding="utf-8", errors="replace")
    if ext == ".pdf":
        # pypdf nằm trong venv agent — chạy subprocess cô lập, timeout 120s
        code = (
            "import sys;from pypdf import PdfReader;"
            "r=PdfReader(sys.argv[1]);"
            "print(chr(10).join((p.extract_text() or '') for p in r.pages))"
        )
        res = subprocess.run([PYTHON_EXE, "-c", code, str(path)],
                             capture_output=True, text=True, timeout=120)
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
                             capture_output=True, text=True, timeout=60)
        if res.returncode == 0 and res.stdout.strip():
            return res.stdout
        raise RuntimeError(res.stderr.strip()[-200:] or "DOCX rỗng")
    raise RuntimeError(f"Định dạng '{ext or 'không rõ'}' chưa hỗ trợ đọc (pdf/docx/văn bản thuần).")

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
                capture_output=True, text=True, timeout=30,
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
                    capture_output=True, text=True, timeout=120,
                )
                if dl.returncode != 0:
                    raise RuntimeError("download failed")
            text = _extract_text(dest)
            if len(text) > MAX_EXTRACT_CHARS:
                text = text[:MAX_EXTRACT_CHARS] + "\n...[trích xuất cắt tại 18.000 ký tự]"
            blocks.append(
                f"### FILE ĐÍNH KÈM: {name}\n"
                f"(file_id={fid}, {size/1024:.0f} KB — đã tải về và đọc nội dung gốc bên dưới)\n"
                f"{text}"
            )
            print(f"   📎 Extracted {name} ({len(text)} chars)")
        except Exception as e:
            blocks.append(f"### FILE ĐÍNH KÈM: {fid}\n(KHÔNG ĐỌC ĐƯỢC: {e})")
            print(f"   ⚠️ Attachment failed {fid}: {e}")
    if not blocks:
        return ""
    return ("\n\n--- TÀI LIỆU ANH ĐÍNH KÈM (nội dung gốc, chỉ đọc) ---\n\n"
            + "\n\n".join(blocks)
            + "\n\n--- HẾT TÀI LIỆU ---\n\n")


def read_channel_messages(count=10):
    """Read recent messages from the channel."""
    try:
        result = subprocess.run(
            [PYTHON_EXE, NETCHAT_SCRIPT, "read", CHANNEL_ID, str(count)],
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode == 0:
            return json.loads(result.stdout)
    except Exception as e:
        print(f"Error reading messages: {e}")
    return []

def send_greeting_message():
    """Send welcome message when system starts or restarts."""
    greeting = f"""👋 **XIN CHÀO ANH QUANPT1!**

Em là **TONY** - Trợ lý số thông minh của anh!

**📊 Hệ thống đã khởi động thành công:**
✅ Server QUAN AI BRAIN đang chạy
✅ Watchdog giám sát hoạt động
✅ Learning engine sẵn sàng
✅ NetChat auto-responder online
✅ Dashboard phòng điều hành: http://127.0.0.1:8766/

**🧠 Trí nhớ:**
• 150+ kiến thức đã được embedding
• 2127 episodes trong brain.db
• 3-tier memory: Short-term → Long-term → Verified

**🎯 Sẵn sàng hỗ trợ:**
• Tra cứu thông tin
• Quản lý công việc
• Phân tích dữ liệu
• Tự động hóa tác vụ
• Kết nối với Digital Human Avatar

Anh cần em giúp gì hôm nay ạ? 🚀"""

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


def send_message(text, confirmed_token=None):
    """Send message to the channel."""
    def _parse(stdout):
        try:
            return json.loads(stdout)
        except (ValueError, TypeError):
            # success output may be plain text — don't crash after a real send
            return {"ok": True, "raw": (stdout or "").strip()[:200]}

    try:
        cmd = [PYTHON_EXE, NETCHAT_SCRIPT, "send", CHANNEL_ID, text, "--to-channel"]
        if confirmed_token:
            cmd.extend(["--confirmed", confirmed_token])

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

        if result.returncode == 0:
            return _parse(result.stdout)
        elif "CONFIRM-REQUIRED" in result.stdout:
            # Extract confirm token and auto-confirm
            for line in result.stdout.split("\n"):
                if line.startswith("CONFIRM-REQUIRED:"):
                    token = line.split(":", 1)[1].strip()
                    print(f"   🔄 Auto-confirming with token: {token}")
                    cmd_with_confirm = [PYTHON_EXE, NETCHAT_SCRIPT, "send", CHANNEL_ID, text, "--to-channel", "--confirmed", token]
                    result2 = subprocess.run(cmd_with_confirm, capture_output=True, text=True, timeout=30)
                    if result2.returncode == 0:
                        return _parse(result2.stdout)
                    else:
                        return {"error": f"Confirm failed: {result2.stderr or result2.stdout}"}
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


def process_message(message_text, sender_user_id="", chat_session_id="default"):
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
        if "--- TÀI LIỆU ANH ĐÍNH KÈM" in message_text:
            raise LookupError("route to AI with document context")
        intent, response = route_message(
            message_text, sender_user_id=sender_user_id, chat_session_id=chat_session_id
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
    ai_reply = process_message_with_ai(message_text)
    autorun = _maybe_autorun_probe(ai_reply)
    if autorun is not None:
        print("   🤖 AI hỏi xin phép probe chỉ-đọc → tự chạy probe thật, trả kết quả.")
        return autorun
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
            messages = read_channel_messages(count=10)

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
                    for m in messages:
                        seen_ids.add(m.get("id"))
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

                for msg in fresh:
                    msg_id = msg.get("id")
                    message_text = (msg.get("message") or "").strip()
                    has_files = bool(msg.get("file_ids"))
                    if not message_text and not has_files:
                        seen_ids.add(msg_id)
                        continue
                    timestamp = datetime.fromtimestamp(
                        msg.get("create_at", 0) / 1000, tz=timezone.utc
                    )
                    print(f"\n📩 New message at {timestamp.strftime('%H:%M:%S')}:")
                    print(f"   {message_text[:100]}")

                    # (27/10/2026) file đính kèm: tải + trích xuất TRƯỚC khi xử lý
                    file_context = ""
                    if has_files:
                        print(f"   📎 {len(msg.get('file_ids'))} file đính kèm — tải + trích xuất...")
                        file_context = extract_message_files(msg)

                    print("   🤖 Processing...")
                    response = process_message(
                        (file_context + "\n" + message_text) if file_context else message_text,
                        sender_user_id=msg.get("user_id", ""),
                        chat_session_id=CHANNEL_ID,
                    )

                    if response is None:
                        # ok_silent: xác nhận không kèm việc nào → không gửi gì
                        seen_ids.add(msg_id)
                        _save_seen_state(seen_ids)
                        continue

                    print("   📤 Sending response...")
                    result = send_message(response)
                    if "error" in result:
                        print(f"   ❌ Error: {result['error']}")
                    else:
                        print("   ✅ Response sent!")

                    seen_ids.add(msg_id)
                    _save_seen_state(seen_ids)
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
                            [r"C:/Users/DELL/AppData/Local/netmind_desktop/netmind-agent/venv/Scripts/python.exe",
                             r"C:/Users/DELL/AppData/Local/netmind_desktop/skills/bot-netchat/netchat_bot.py",
                             "send", _CH, "--to-channel", _remind],
                            capture_output=True, text=True, timeout=30,
                        )
                        print(f"   ⏰ Reminder sent: {_tid} (lần {_row['reminder_count'] + 1})")
                except Exception as _rem_err:
                    print(f"   ⚠️ reminder job error: {_rem_err}")

            time.sleep(5)

        except KeyboardInterrupt:
            print("\n\n🛑 Auto-responder stopped by user")
            break
        except Exception as e:
            print(f"\n⚠️  Error: {e}")
            import traceback
            traceback.print_exc()
            time.sleep(10)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)