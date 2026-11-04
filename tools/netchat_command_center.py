"""NetChat Command Center — bộ định tuyến lệnh owner↔TONY (DM-only).

LỊCH SỬ (31/10/2026): file gốc bị ghi đè nhầm bằng nội dung responder trong quá
trình patch song song 2 file → KHÔI PHỤC toàn bộ từ: code đã đọc trong phiên,
hợp đồng tests (tests/test_netchat_command_center.py) và skill quan-ai-brain-ops.
Mọi intent + luật an toàn giữ nguyên: lệnh đổi trạng thái phải ĐỨNG ĐẦU câu,
câu hỏi không bao giờ kích hoạt, "giúp" chỉ là lệnh khi đứng đầu câu.

Intents điều khiển Pi5 (31/10): tony_on/off/pause/resume/status, tony_speak/face/
volume, tony_youtube/websearch/music_play/music_stop, tony_back (đóng overlay web),
tony_show_image (hiển thị ảnh DM lên màn Pi5 N giây rồi tự về avatar), pc_open/
pc_close/pc_lock/pc_screenshot, approve/status/report/tasks/knowledge/help/todo/
stop/freeze.
"""
from __future__ import annotations

import json
import re
import sqlite3
import time
from pathlib import Path
from typing import Any

WORKSPACE = Path(__file__).resolve().parent.parent

COMMAND_PATTERNS: dict[str, tuple[str, ...]] = {
    "approve": ("phê duyệt", "phe duyet", "duyệt", "duyet", "approved", "đồng ý", "dong y"),
    "status": ("trạng thái", "trang thai", "hiện trạng", "hien trang", "status", "sức khỏe", "suc khoe"),
    "report": ("báo cáo", "bao cao", "report"),
    "tasks": ("nhiệm vụ", "nhiem vu", "tasks", "backlog", "công việc", "cong viec"),
    "knowledge": ("tri thức", "tri thuc", "knowledge", "học được gì", "hoc duoc gi"),
    "help": ("giúp", "giup", "help", "lệnh", "lenh", "menu"),
    "stop": ("stop", "dừng", "dung", "dừng lại", "dung lai", "halt", "ngừng", "ngung"),
    "freeze": ("freeze", "đóng băng", "dong bang", "tạm dừng", "tam dung"),
    # Sprint 8 (a): to-do cá nhân (read-only list; thêm việc qua câu tự do
    # "nhớ giúp tôi..." xử lý ở route_message riêng)
    "todo": ("việc cần làm", "viec can lam", "todo", "to-do", "việc hôm nay", "viec hom nay"),
    # (31/10/2026) Điều khiển Pi5 mở web/YouTube — ĐẶT TRƯỚC pc_open để
    # 'tony mở youtube...' không bị nuốt thành lệnh mở app PC.
    "tony_youtube": ("tony mở youtube", "tony mo youtube", "tony bật youtube", "tony bat youtube",
                     "mở youtube", "mo youtube", "bật youtube", "bat youtube",
                     "tony mở video", "tony mo video", "xem youtube", "xem video"),
    "tony_music_play": ("tony phát nhạc", "tony phat nhac", "tony bật nhạc", "tony bat nhac",
                        "phát nhạc", "phat nhac", "bật nhạc", "bat nhac", "phát bài", "phat bai",
                        "bật bài", "bat bai", "mở bài hát", "mo bai hat", "nghe nhạc", "nghe nhac"),
    # (31/10/2026) Lệnh điều khiển TONY/Pi5 từ DM — gọi API thật /api/executive/edge/control
    "tony_on": ("bật hình thể", "bat hinh the", "mở hình thể", "mo hinh the", "kích hoạt hình thể",
                "kich hoat hinh the", "start kiosk", "bật kiosk", "bat kiosk", "dậy đi tony", "day di tony",
                # (31/10/2026) Owner không gắn màn hình — điều khiển hình thể 100% qua DM:
                "bật pi5", "bat pi5", "bật pi 5", "bat pi 5", "bật màn pi5", "bat man pi5",
                "mở giao diện pi5", "mo giao dien pi5", "bật giao diện", "bat giao dien"),
    "tony_off": ("tắt hình thể", "tat hinh the", "đóng kiosk", "dong kiosk", "close kiosk", "ngủ đi tony", "ngu di tony",
                 # (31/10/2026) 'tắt pi5' = tắt giao diện (về desktop/standby):
                 "tắt pi5", "tat pi5", "tắt pi 5", "tat pi 5", "tắt màn pi5", "tat man pi5",
                 "tắt giao diện pi5", "tat giao dien pi5", "tắt giao diện", "tat giao dien"),
"tony_hdmi_show": ("xuất hình ra hdmi", "xuat hinh ra hdmi", "chiếu ra hdmi", "chieu ra hdmi",
                   "hiển thị trên hdmi", "hien thi tren hdmi", "xuất ra màn hdmi", "xuat ra man hdmi",
                   "bật hdmi", "bat hdmi", "hdmi show", "chiếu màn hình ra tivi", "chieu man hinh ra tivi"),
"tony_hdmi_hide": ("tắt hdmi", "tat hdmi", "tắt hình hdmi", "tat hinh hdmi", "hdmi hide",
                   "ngắt hdmi", "ngat hdmi", "thu hình về màn pi", "thu hinh ve man pi"),
# (31/10/2026, owner) phê duyệt xuất hình lên HDMI sau khi bot hỏi khi cắm:
"tony_hdmi_approve": ("phê duyệt hdmi", "phe duyet hdmi", "duyệt hdmi", "duyet hdmi",
                      "có hdmi", "co hdmi", "bật hdmi lên", "bat hdmi len",
                      "xuất hình lên hdmi", "xuat hinh len hdmi", "hdmi ok"),
    # (01/11/2026, owner-ACK) 'giữ nguyên/tắt cảnh báo X' = owner đã quyết định
    # hiện trạng (vd loa TẮT là CỐ Ý) → hệ thống ngừng cảnh báo lại. STATE_CHANGING
    # không cần — chỉ ghi nhận quyết định owner vào data/alert_owner_ack.json.
    "ack_alert": ("giữ nguyên", "giu nguyen", "tắt cảnh báo", "tat canh bao",
                  "đã xác nhận cảnh báo", "da xac nhan canh bao",
                  "không cảnh báo nữa", "khong canh bao nua"),
    "tony_speak": ("tony nói", "tony noi", "kêu tony nói", "keu tony noi", "nói với anh", "noi voi anh"),
    "tony_face": ("biểu cảm", "bieu cam", "đổi biểu cảm", "doi bieu cam", "set expression", "mặt vui", "mat vui",
                  "mỉm cười", "mim cuoi", "cười lên", "cuoi len", "mắt to", "mat to", "chăm chú", "cham chu"),
    "tony_pause": ("tony nghỉ", "tony nghi", "tony nghỉ ngơi", "tony nghi ngoi", "tạm nghỉ", "tam nghi", "pause tony",
                   "tony ngủ", "tony ngu", "standby", "chế độ chờ", "che do cho", "về chế độ standby"),
    "tony_resume": ("tony làm việc", "tony lam viec", "tony hoạt động", "tony hoat dong", "resume tony", "tony dậy", "tony day"),
    "tony_status": ("hình thể", "hinh the", "pi5", "pi 5", "hình tì", "hinh ti", "edge"),
    "tony_volume": ("âm lượng", "am luong", "volume", "loa to hơn", "loa to hon", "loa nhỏ hơn", "loa nho hon"),
    # (31/10/2026) Điều khiển Pi5 mở web/YouTube/nhạc + standby từ DM
    "tony_music_stop": ("tony dừng nhạc", "tony dung nhac", "dừng nhạc", "dung nhac",
                        "tắt nhạc", "tat nhac", "stop nhạc", "stop nhac"),
    # UDC-1 (04/11/2026): điều khiển thiết bị trên Pi5 theo lệnh DM
    "device_list": ("thiết bị trên pi", "thiet bi tren pi", "liệt kê thiết bị",
                    "liet ke thiet bi", "thiết bị đang cắm", "thiet bi dang cam",
                    "danh sách thiết bị", "danh sach thiet bi", "xem thiết bị",
                    "xem thiet bi", "thiết bị pi5", "thiet bi pi5"),
    "relay_on": ("bật rơ le", "bat ro le", "bật relay", "bat relay",
                 "rơ le bật", "ro le bat", "relay on"),
    "relay_off": ("tắt rơ le", "tat ro le", "tắt relay", "tat relay",
                  "rơ le tắt", "ro le tat", "relay off"),
    "emergency_stop_device": ("dừng khẩn thiết bị", "dung khan thiet bi",
                              "emergency stop device", "ngắt nguồn thiết bị",
                              "ngat nguon thiet bi"),
    "tony_back": ("tony về", "tony ve", "về hình thể", "ve hinh the", "tắt trang web",
                  "tat trang web", "đóng trang web", "dong trang web", "tony quay lại",
                  "tony quay lai"),
    "tony_websearch": ("tony tìm", "tony tim", "tony tìm kiếm", "tony tim kiem",
                       "tìm giúp anh", "tim giup anh", "tra cứu", "tra cuu",
                       "tìm kiếm", "tim kiem"),
    # (31/10/2026) Hiển thị ảnh từ NetChat lên màn Pi5 (mặc định 15s rồi về avatar)
    "tony_show_image": ("hiển thị ảnh trên pi", "hien thi anh tren pi",
                        "hiển thị ảnh lên pi", "hien thi anh len pi",
                        "tony hiện ảnh", "tony hien anh", "tony hiển thị ảnh",
                        "tony hien thi anh", "đưa ảnh lên pi", "dua anh len pi",
                        "hiện ảnh trên pi", "hien anh tren pi",
                        # (owner) yêu cầu hiển thị LẠI ảnh vừa xem
                        "hiển thị lại ảnh", "hien thi lai anh",
                        "hiện lại ảnh", "hien lai anh",
                        "xem lại ảnh", "xem lai anh"),
    # (31/10/2026) Chụp ảnh / quay video TRỰC TIẾP từ camera Pi 5 theo lệnh DM —
    # lưu 2 bên (Pi + PC) và gửi file về DM cho owner.
    "tony_pi_photo": ("chụp ảnh từ pi", "chup anh tu pi", "chụp ảnh pi",
                      "chup anh pi", "tony chụp ảnh", "tony chup anh",
                      "chụp ảnh bằng pi", "chup anh bang pi",
                      "camera pi chụp", "camera pi chup",
                      "chụp ảnh gửi anh", "chup anh gui anh",
                      "chụp ảnh gửi em", "chụp ảnh cho anh",
                      "chụp một tấm", "chup mot tam", "chụp tấm ảnh",
                      "chụp ảnh từ camera", "chup anh tu camera",
                      "camera chụp gửi", "chụp hình gửi", "chup hinh gui",
                      "chụp ảnh màn hình pi"),
    "tony_pi_video": ("quay video từ pi", "quay video tu pi", "quay video pi",
                      "tony quay video", "quay video bằng pi",
                      "quay video bang pi", "ghi hình từ pi", "ghi hinh tu pi"),
    # (01/11/2026, owner feedback image_864dc0) 'Chụp màn hình kiosk/pi5' —
    # phải chụp MÀN HÌNH PI5 (grim qua SSH) KHÔNG phải chụp PC. ƯU TIÊN TRƯỚC
    # pc_screenshot: kiểm tra "kiosk|pi" trong câu chụp màn hình.
    "tony_pi_screenshot": ("chụp màn hình kiosk", "chup man hinh kiosk",
                           "chụp màn hình pi", "chup man hinh pi",
                           "chụp màn hình pi5", "chup man hinh pi5",
                           "screenshot kiosk", "screenshot pi",
                           "màn hình pi5 đang hiển thị gì",
                           "kiosk đang hiển thị gì"),
    # (31/10/2026) LIVE CAMERA: 'bật camera' → màn Pi5 tự sáng + hình live trực tiếp
    "tony_pi_live": ("bật camera", "bat camera", "bật camera pi5", "bat camera pi5",
                     "bật camera pi 5", "bat camera pi 5", "camera pi5 bật", "camera pi5 bat",
                     "mở camera", "mo camera", "xem camera", "camera live", "bật live",
                     "bat live", "xem hình live", "xem hinh live", "xem camera pi5",
                     "xem camera pi 5", "bật camera lên", "bat camera len"),
    "tony_pi_live_off": ("tắt camera", "tat camera", "tắt camera pi5", "tat camera pi5",
                         "tắt live", "tat live", "dừng camera", "dung camera",
                         "tắt camera lên", "tat camera len", "đóng camera", "dong camera"),
    "pc_open": ("mở", "mo", "bật", "bat", "bật lên", "khởi động", "khoi dong", "open"),
    "pc_close": ("đóng", "dong", "tắt", "tat", "tắt đi", "close", "kill"),
    "pc_lock": ("khóa máy", "khoa may", "khóa màn hình", "khoa man hinh", "lock",
                "khoá máy", "khoa may tinh", "khóa máy tính", "khoá máy tính",
                "khóa màn hình", "khoá màn hình"),
    # (31/10/2026) Chụp màn hình + gửi ảnh DM (lệnh ảnh image_273ce1)
    "pc_screenshot": ("chụp màn hình", "chup man hinh", "chụp lại màn hình",
                      "chụp ảnh màn hình", "chup anh man hinh",
                      "screenshot", "ảnh màn hình", "anh man hinh"),
}

# State-changing commands MUST start the message (imperative form).
# Questions like "em có thể phê duyệt qua kênh này được không?" contain the
# keyword but must NOT execute anything — they fall to conversational AI.
STATE_CHANGING = {"approve", "tony_on", "tony_pi_live", "tony_pi_live_off", "tony_off", "tony_speak", "tony_face",
                  "tony_pause", "tony_resume", "tony_volume", "tony_youtube",
                  "tony_music_play", "tony_music_stop", "tony_websearch",
                  "tony_back", "tony_show_image", "pc_open", "pc_close",
                  "pc_lock", "pc_screenshot",
                  # UDC-1 (04/11/2026): lệnh ghi thiết bị — chỉ kích hoạt khi
                  # ĐỨNG ĐẦU câu (startswith), không match giữa câu
                  "relay_on", "relay_off"}

# UDC-1: lệnh dừng khẩn thiết bị phải ĐI TRƯỚC pattern 'stop' rộng
# ('dừng khẩn thiết bị' chứa 'dừng' → bị stop nuốt) — xử lý đặc biệt
# trong detect_intent ngay đầu hàm. Động từ dừng BẮT BUỘC có mặt
# ('thiết bị trên pi' = đọc danh sách, KHÔNG phải estop); LOẠI TRỪ 'nhạc'
# ('dừng nhạc' = tony_music_stop, không phải estop).
_DEVICE_ESTOP_RE = re.compile(
    r"(?:dừng|dung|ngắt|ngat|cắt|cat|stop|emergency)[^\n]{0,14}"
    r"(?:thiết bị|thiet bi|relay|rơ\s*le|ro\s*le|device)", re.IGNORECASE)


def _is_device_estop(t: str) -> bool:
    """Estop thiết bị: khớp regex + KHÔNG phải 'dừng nhạc' (music stop)."""
    if not _DEVICE_ESTOP_RE.search(t):
        return False
    return not re.search(r"nhạc|nhac|music|bài\s+hát|bai\s+hat", t, re.IGNORECASE)


def _is_music_stop(t: str) -> bool:
    """'dừng nhạc'/'tony dừng nhạc'/'tắt nhạc' — music stop TRƯỚC stop rộng
    (pre-existing bug 04/11: 'dừng nhạc' rơi vào stop tổng — sửa kèm UDC-1)."""
    return bool(re.search(
        r"(?:dừng|dung|tắt|tat|stop|ngừng|ngung)[^\n]{0,10}(?:nhạc|nhac|music)"
        r"|(?:tony\s+)?(?:dừng|dung)\s+nhạc", t, re.IGNORECASE))

# (31/10/2026) Đối số lệnh: "tony nói <câu>" → text; "âm lượng <0-100>";
# "biểu cảm <tên>" (IDLE/LISTENING/THINKING/SPEAKING/HAPPY/SLEEPING/OFFLINE/
# SAFE_MODE/WAITING_FOR_OWNER/ERROR — khớp avatar_engine.js).
_AVATAR_STATES = {"IDLE", "LISTENING", "THINKING", "SPEAKING", "HAPPY", "SLEEPING",
                  "OFFLINE", "SAFE_MODE", "WAITING_FOR_OWNER", "ERROR"}
_EDGE_API = "http://127.0.0.1:8766/api/executive/edge/control"

# ---------------------------------------------------------------------------
# "ok" = owner confirmation of the bot's LAST question/proposal (27/10/2026).
# Yêu cầu chủ sở hữu: "khi anh gõ ok, OK có nghĩa là anh đã xác nhận; còn
# không sẽ không phản hồi hoặc không có xác nhận" + "trợ lý không hỏi lòng vòng".
# Khi bot hỏi xin phép/chờ lệnh (VD: "Anh xác nhận cho em chạy lại probe nhé?"),
# câu "ok" của anh là lệnh THỰC THI luôn — không hỏi lại lần nữa.
# ---------------------------------------------------------------------------

_OK_RE = re.compile(r"^\s*(ok|okay|okie|ok anh|oke|uk|ừ|uh)\s*[.!]?\s*$", re.IGNORECASE)

# Actions một lần chờ "ok" xác nhận. TTL 15 phút — quá hạn thì huỷ (an toàn:
# "ok" muộn không kích hoạt hành động đã lỗi thời).
_PENDING_ACTIONS: dict[str, dict[str, Any]] = {}
_PENDING_TTL_S = 15 * 60


def stage_pending_action(chat_session_id: str, label: str, action: Any) -> str:
    """Bot vừa HỎI xin phép → ghi nhận việc chờ xác nhận. Trả lời CÂU HỎI đó
    (bot không tự thực hiện trước, vì đây là việc có quyết định của anh)."""
    _PENDING_ACTIONS[chat_session_id] = {
        "label": label,
        "action": action,
        "staged_at": time.time(),
    }
    return label


def _take_pending_action(chat_session_id: str) -> dict[str, Any] | None:
    entry = _PENDING_ACTIONS.pop(chat_session_id, None)
    if entry is None:
        return None
    if time.time() - entry["staged_at"] > _PENDING_TTL_S:
        return None  # expired — stale confirmation must not fire old actions
    return entry


def run_pending_action(chat_session_id: str) -> str | None:
    """Owner đã gõ 'ok' → thực thi hành động đang chờ xác nhận, TRẢ KẾT QUẢ
    thật (không hỏi lại, không lòng vòng)."""
    entry = _take_pending_action(chat_session_id)
    if entry is None:
        return None
    action = entry.get("action")
    try:
        if callable(action):
            result = action()
            if isinstance(result, str) and result:
                return result
        # (khôi phục 31/10/2026) action dạng chuỗi probe: thực thi probe THẬT và
        # báo cáo trung thực kết quả — không trả câu chung chung "đã thực hiện".
        if action == "reprobe_pi5":
            return _reprobe_full("probe lại Pi 5")
        if action == "reprobe_full":
            return _reprobe_full("probe lại toàn hệ thống")
        return f"✅ Đã thực hiện: {entry.get('label', 'việc chờ xác nhận')}"
    except Exception as exc:
        return f"⚠️ Thực hiện thất bại: {type(exc).__name__}: {exc}"


# ---------------------------------------------------------------------------
# Tiền tố lịch sự + câu hỏi (luật nhận lệnh 31/10/2026)
# ---------------------------------------------------------------------------

_POLITE_PREFIXES = ("giúp anh", "giup anh", "giúp em", "giup em", "làm ơn", "lam on",
                    "vui lòng", "vui long", "cho anh", "cho em", "cho tôi", "cho toi",
                    "tony", "em", "bạn", "ban")


def _starts_with_any_keyword(t: str) -> bool:
    """True nếu chuỗi bắt đầu bằng 1 từ khóa lệnh thật (pattern hoặc regex có đối số)."""
    for patterns in COMMAND_PATTERNS.values():
        for p in patterns:
            if t.startswith(p):
                return True
    for _intent, kw_re in _ARG_KEYWORD_RES:
        if kw_re.match(t):
            return True
    return False


def _strip_polite_prefixes(text: str) -> str:
    """Gỡ tiền tố lịch sự ('em', 'tony', 'làm ơn'...) — CHỈ khi phần sau bắt đầu
    bằng từ khóa lệnh thật. 'Em ơi tắt hình thể' giữ nguyên (gọi thân mật, không
    phải mệnh lệnh đứng đầu) — mid-sentence tắt hình thể bị chặn an toàn."""
    t = (text or "").strip()
    if not t:
        return t
    lowered = t.lower()
    for p in sorted(_POLITE_PREFIXES, key=len, reverse=True):
        if lowered.startswith(p + " "):
            rest = t[len(p):].strip()
            if rest and _starts_with_any_keyword(rest.lower()):
                return rest
            return t  # không phải mệnh lệnh → giữ nguyên câu
    return t


def _is_question(t: str) -> bool:
    """Câu hỏi ('?'/tận cùng 'không'/'chứ'/'nào') không bao giờ kích hoạt lệnh."""
    if "?" in t:
        return True
    tt = t.rstrip("!. ").lower()
    return tt.endswith("không") or tt.endswith("chứ") or tt.endswith("nào")


def detect_intent(text: str) -> str | None:
    """Return the command intent for a message, or None for free chat.

    Rules:
    - Questions ('?'/final 'không') never trigger commands unless the
      message STARTS with the command keyword.
    - 'approve' (state-changing) only fires when the message starts with
      the keyword — never on substring matches.
    - Read-only commands fire on startswith or containment.
    - (31/10/2026) Tiền tố lịch sự 'Em ...' được bỏ trước khi khớp — owner
      ra lệnh bằng 'Em mở firefox lên' là mệnh lệnh, không phải câu hỏi.
    """
    t = _strip_polite_prefixes(text).strip().lower()
    # (01/11/2026) Làm sạch: owner lỡ gõ dấu '\\' '/' '.' '!' cuối lệnh
    # ('chụp hình\' bị rơi ra GLM) — lệnh hệ thống không chứa các ký tự này.
    t = t.strip("\\/!.?,:;")
    if not t:
        return None
    # UDC-1 (04/11/2026): dừng khẩn THIẾT BỊ — TRƯỚC pattern 'stop' rộng
    # ('dừng khẩn thiết bị' chứa 'dừng' → nếu không chặn sớm sẽ thành stop).
    if not _is_question(t) and _is_device_estop(t):
        return "emergency_stop_device"
    # (fix kèm UDC-1): 'dừng nhạc'/'tony dừng nhạc' phải là music-stop,
    # không được rơi vào 'stop' tổng (pre-existing bug, chủ bị 1 lần).
    if not _is_question(t) and _is_music_stop(t):
        return "tony_music_stop"
    # (31/10/2026) 'Tắt (cả) giao diện (Pi5)' = ngủ màn hình → standby, ƯU TIÊN
    # trước pattern rộng 'pi5' của tony_status.
    if ("tắt" in t or "tat" in t) and "giao diện" in t or ("tắt" in t or "tat" in t) and "giao dien" in t:
        return "tony_standby"
    # (31/10/2026) 'Chụp ảnh (từ) pi/ pi5' → camera Pi 5, ƯU TIÊN trước 'pi5'
    # của tony_status (pc_screenshot 'chụp màn hình' đã khớp trước đó thì để nguyên).
    if ("chụp ảnh" in t or "chup anh" in t) and ("pi" in t):
        return "tony_pi_photo"
    # (31/10/2026) 'chụp ảnh (gửi anh|cho anh|từ camera)' — không cần nhắc 'pi':
    if ("chụp ảnh" in t or "chup anh" in t or "chụp hình" in t or "chup hinh" in t) \
            and ("gửi" in t or "gui" in t or "camera" in t or "cho anh" in t):
        return "tony_pi_photo"
    # (31/10/2026 lần 2) 'Chụp ảnh' / 'Chụp hình' NGẮN ĐỨNG ĐẦU — mệnh lệnh
    # chụp camera Pi5 (owner gõ 22:02: 'Chụp ảnh', 'Chụp hình' → rơi GLM bịa
    # 'chưa có công cụ'). Loại trừ 'màn hình' (pc_screenshot xử lý bên dưới):
    _question_hit = _is_question(t)
    if not _question_hit and "màn hình" not in t and "man hinh" not in t \
            and re.match(r"^(chụp|chup)\s+(ảnh|anh|hình|hinh)(\s|$|!|\.)", t):
        return "tony_pi_photo"
    # (31/10/2026, owner) Phê duyệt HDMI ĐẶC BIỆT — TRƯỚC pattern 'phê duyệt'
    # rộng (approve consultation) để không nuốt lệnh xuất hình lên HDMI:
    _wants_hdmi = "hdmi" in t
    _says_yes = any(k in t for k in ("phê duyệt", "phe duyet", "duyệt", "duyet",
                                     "đồng ý", "dong y", "bật lên", "bat len",
                                     "xuất hình", "xuat hinh"))
    if not _is_question(t) and _wants_hdmi and _says_yes:
        return "tony_hdmi_approve"
    if _wants_hdmi and t.split() and t.split()[0] == "ok":
        return "tony_hdmi_approve"
    if ("quay video" in t or "quay video" in t) and ("pi" in t):
        return "tony_pi_video"
    if "ghi hình" in t or "ghi hinh" in t:
        return "tony_pi_video"
    # (31/10/2026) TAI: 'nghe từ pi/qua mic pi' — thu âm mic gửi DM (read-only)
    if re.search(r"(?:nghe|thu\s+âm|thu\s+am|lắng\s+nghe|lang\s+nghe)[^\n]{0,20}(?:từ|tu|qua)\s+(?:mic\s+)?pi", t):
        return "tony_pi_listen"
    question = _is_question(t)
    # (31/10/2026) chụp màn hình — biến thể 'chụp (lại) (ảnh|hình) màn hình'
    # phải bắt từ đầu câu (mệnh lệnh); câu hỏi không kích hoạt.
    # (01/11/2026, owner feedback image_864dc0) 'chụp màn hình kiosk/pi/pi5' →
    # chụp MÀN HÌNH PI5, KHÔNG phải PC — guard trước khi rơi pc_screenshot.
    if not question and re.search(r"^chụp\s+(?:lại\s+)?(?:ảnh\s+|hình\s+)?màn\s+hình", t):
        if re.search(r"\b(kiosk|pi\s*5?|pis?5)\b", t):
            return "tony_pi_screenshot"
        return "pc_screenshot"
    # (31/10/2026) 'phát câu này N lần ... : <nguyên văn>' — lệnh phát NGUYÊN VĂN
    # qua loa Pi5; phải trả intent để responder không đưa câu này cho GLM paraphrase.
    if not question and _SPEAK_VERBATIM_RE.match(t):
        return "tony_speak_verbatim"
    # (31/10/2026) 'giúp' chỉ là lệnh khi ĐỨNG ĐẦU câu — 'mở giúp anh chrome'
    # hay 'đọc giúp anh ảnh này' phải là mệnh lệnh/AI, không phải bảng help
    # (bug thật: câu chứa từ 'giúp' ở giữa bị nuốt thành help, lệch lệnh).
    for intent, patterns in COMMAND_PATTERNS.items():
        for p in patterns:
            if t.startswith(p):
                return intent
            if (not question and intent not in STATE_CHANGING
                    and intent != "help" and f" {p} " in f" {t} "):
                return intent
    return None


# ---------------------------------------------------------------------------
# Handlers — every handler runs REAL system logic and reports honestly
# ---------------------------------------------------------------------------


def handle_approve(payload: dict[str, Any] | None = None) -> str:
    """'phê duyệt': approve the OLDEST pending consultation ticket (FIFO) via
    the real ConsultationStore, then audit the decision.

    Honesty contract: if nothing is pending, say so — never fake success.
    Scope: this approves exactly ONE ticket per command, with its ID shown,
    so the owner always sees what was approved. Note: ConsultationStore
    seeds its own default tickets into an empty DB by design; FIFO picks
    the oldest genuinely pending ticket.
    """
    try:
        from quan_ai_brain.governance.consultation_inbox import ConsultationStore

        db = WORKSPACE / "data" / "consultations.db"
        if not db.exists():
            return "📭 Hiện không có hồ sơ phê duyệt nào (chưa có cơ sở dữ liệu tham vấn)."

        # Guard: some module-level default tickets exist only for the default
        # DB path; constructing with an explicit path keeps them out.
        store = ConsultationStore(str(db))
        tickets = store.list_tickets()
        pending = [
            t for t in tickets
            if getattr(getattr(t, "status", None), "value", "") in ("PENDING", "PENDING_REVIEW")
        ]
        if not pending:
            store.close()
            return "📭 Hiện không có hồ sơ nào chờ phê duyệt. Mọi quyết định đã được xử lý."

        pending.sort(key=lambda t: getattr(t, "created_at", "") or "")
        target = pending[0]
        store.respond_ticket(target.ticket_id, decision="APPROVE",
                             guidance="Phê duyệt qua NetChat bởi Quanpt1")
        store.close()
        _audit("netchat_command.approve", {"ticket": target.ticket_id})
        return (
            "✅ ĐÃ PHÊ DUYỆT\n"
            f"Hồ sơ: {target.ticket_id}\n"
            f"Tiêu đề: {getattr(target, 'title', '') or '(không có tiêu đề)'}\n"
            "Ghi chú: đã duyệt qua NetChat bởi Quanpt1."
        )
    except Exception as exc:
        return f"⚠️ Lỗi phê duyệt: {type(exc).__name__}: {exc}"


def _http_probe(url: str, timeout: float = 2.5) -> bool:
    try:
        import urllib.request
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            resp.read(64)
        return True
    except Exception:
        return False


def _reprobe_full(text: str = "") -> str:
    """Probe THẬT toàn hệ thống (core + Pi edge + Ollama) — báo cáo trung thực.

    Trả về text chứa trạng thái ONLINE/OFFLINE + edge IP (hoặc 'chưa xác minh
    được' khi không xác minh được Pi). Dùng cho 'trạng thái', ok-confirm
    'reprobe_full' và responder auto-run probe."""
    core_ok = _http_probe("http://127.0.0.1:8766/api/executive/edge/status")
    edge_ip = ""
    edge_state = ""
    if core_ok:
        try:
            import urllib.request
            with urllib.request.urlopen(
                    "http://127.0.0.1:8766/api/executive/edge/status",
                    timeout=3.0) as resp:
                edge = (json.loads(resp.read().decode("utf-8")) or {}).get("edge", {})
                edge_ip = str(edge.get("last_client_ip") or edge.get("ip") or "")
                edge_state = str(edge.get("state", ""))
        except Exception:
            edge_ip = ""
    ollama_ok = _http_probe("http://127.0.0.1:11434/api/tags")
    if edge_state:
        edge_line = f"Hình thể Pi 5: {_vn(edge_state)}" + (f" ({edge_ip})" if edge_ip else "")
    else:
        edge_line = "Pi 5 edge: chưa xác minh được"
    return (f"✅ Đã xác nhận — em đã kiểm tra ngay: kết quả kiểm tra: "
            f"PC chính: {_vn('ONLINE' if core_ok else 'OFFLINE')} | {edge_line} | "
            f"Ollama: {_vn('ONLINE' if ollama_ok else 'OFFLINE')}.")


def _task_counts() -> dict[str, int]:
    db = WORKSPACE / "data" / "tasks.db"
    if not db.exists():
        return {}
    conn = sqlite3.connect(str(db))
    try:
        rows = conn.execute(
            "SELECT status, COUNT(*) FROM durable_tasks GROUP BY status"
        ).fetchall()
    except sqlite3.OperationalError:
        rows = []
    finally:
        conn.close()
    return {str(s): int(c) for s, c in rows}


def handle_status(payload: dict[str, Any] | None = None) -> str:
    """'trạng thái': live probes of core server + Ollama + task summary.
    Honesty: every line reflects a REAL probe result, no cached status."""
    core_ok = _http_probe("http://127.0.0.1:8766/api/executive/edge/status")
    ollama_ok = _http_probe("http://127.0.0.1:11434/api/tags")
    ui_ok = _http_probe("http://127.0.0.1:8765/")
    counts = _task_counts()
    task_line = ", ".join(f"{s}: {c}" for s, c in sorted(counts.items())) or "chưa có tasks.db"
    lines = [
        f"{'🟢 HOẠT ĐỘNG' if core_ok else '🔴 MẤT KẾT NỐI'} — máy chủ chính (8766)",
        f"{'🟢 HOẠT ĐỘNG' if ollama_ok else '🔴 MẤT KẾT NỐI'} — trí tuệ cục bộ Ollama (11434)",
        f"{'🟢 HOẠT ĐỘNG' if ui_ok else '🔴 MẤT KẾT NỐI'} — giao diện chat (8765)",
        f"📋 Nhiệm vụ: {task_line}",
        "(🟢 HOẠT ĐỘNG = còn sống, 🔴 MẤT KẾT NỐI = không kết nối được)",
    ]
    _audit("netchat_command.status", {"core": core_ok, "ollama": ollama_ok})
    return "\n".join(lines)


def handle_tasks(payload: dict[str, Any] | None = None) -> str:
    """'nhiệm vụ': counts of durable_tasks by status (real DB, honest empty)."""
    counts = _task_counts()
    if not counts:
        return "📭 Chưa có nhiệm vụ nào trong tasks.db (bảng durable_tasks trống/thiếu)."
    lines = ["📋 NHIỆM VỤ (durable_tasks):"]
    for s, c in sorted(counts.items()):
        lines.append(f"{s}: {c}")
    _audit("netchat_command.tasks", {"counts": counts})
    return "\n".join(lines)


def handle_knowledge(payload: dict[str, Any] | None = None) -> str:
    """'tri thức': counts from data/brain.db — approved semantic, quarantined
    candidates, episodes. Real DB reads only; honest when DB missing."""
    db = WORKSPACE / "data" / "brain.db"
    if not db.exists():
        return "📭 Chưa có kho tri thức (data/brain.db chưa tạo)."
    conn = sqlite3.connect(str(db))
    try:
        sem_approved = conn.execute(
            "SELECT COUNT(*) FROM semantic_memory WHERE approved_by IS NOT NULL AND approved_by != ''"
        ).fetchone()[0]
        quarantined = conn.execute(
            "SELECT COUNT(*) FROM candidate_knowledge WHERE status = 'quarantined'"
        ).fetchone()[0]
        try:
            episodes = conn.execute("SELECT COUNT(*) FROM episodes").fetchone()[0]
        except sqlite3.OperationalError:
            episodes = 0
    except sqlite3.OperationalError as exc:
        conn.close()
        return f"⚠️ Kho tri thức đọc không được (schema lỗi): {exc}"
    finally:
        try:
            conn.close()
        except Exception:
            pass
    _audit("netchat_command.knowledge", {"approved": int(sem_approved), "quarantined": int(quarantined)})
    return (
        f"🧠 KHO TRI THỨC\n"
        f"Đã duyệt (semantic): {sem_approved}\n"
        f"Chờ duyệt (quarantined): {quarantined}\n"
        f"Episodes: {episodes}"
    )


def handle_report(payload: dict[str, Any] | None = None) -> str:
    """'báo cáo': list newest report files in 'bao cao xay dung he thong/'."""
    rdir = WORKSPACE / "bao cao xay dung he thong"
    if not rdir.exists():
        return "📭 Chưa có thư mục báo cáo (bao cao xay dung he thong/)."
    files = [f for f in rdir.iterdir() if f.is_file()]
    if not files:
        return "📭 Thư mục báo cáo trống."
    files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
    import datetime as _dt
    lines = ["📊 BÁO CÁO MỚI NHẤT:"]
    for f in files[:5]:
        ts = _dt.datetime.fromtimestamp(f.stat().st_mtime).strftime("%d/%m %H:%M")
        lines.append(f"  • {f.name} ({ts})")
    _audit("netchat_command.report", {"n": len(files)})
    return "\n".join(lines)


def handle_todo_list(payload: dict[str, Any] | None = None) -> str:
    """'việc cần làm': read-only list from data/todos.db (TodoStore)."""
    db = WORKSPACE / "data" / "todos.db"
    if not db.exists():
        return "📭 Chưa có việc nào được ghi. Thêm bằng: 'nhớ giúp tôi: <việc> (hạn mai)'."
    try:
        from quan_ai_brain.tools.todo_store import TodoStore

        store = TodoStore(str(db))
        items: list[Any] = []
        for meth in ("list_open", "list_items", "list", "all", "get_all"):
            fn = getattr(store, meth, None)
            if callable(fn):
                try:
                    items = list(fn() or [])
                    break
                except Exception:
                    continue
        try:
            store.close()
        except Exception:
            pass
        if not items:
            return "📭 Danh sách việc trống."
        lines = ["📋 VIỆC CẦN LÀM:"]
        for it in items[:10]:
            if isinstance(it, dict):
                due = it.get("due")
                lines.append(f"  • #{it.get('id')} {it.get('title')}" + (f" (hạn {due})" if due else ""))
            else:
                lines.append(f"  • {it}")
        _audit("netchat_command.todo_list", {"n": len(items)})
        return "\n".join(lines)
    except Exception as exc:
        return f"⚠️ Lỗi đọc việc cần làm: {type(exc).__name__}: {exc}"


def handle_help(payload: dict[str, Any] | None = None) -> str:
    """'giúp': bảng lệnh — chỉ hiện khi 'giúp' ĐỨNG ĐẦU câu."""
    return (
        "🤖 KÊNH LÀM VIỆC TONY (lệnh đứng đầu câu):\n"
        "• trạng thái | báo cáo | nhiệm vụ | tri thức | việc cần làm\n"
        "• phê duyệt — duyệt hồ sơ chờ (FIFO)\n"
        "• bật hình thể / tắt hình thể / tony nghỉ / tony làm việc / tony về\n"
        "• tony nói <câu> | biểu cảm <kiểu> | âm lượng <0-100>\n"
        "• tony mở youtube [từ khóa] | tony tìm <câu> | tony phát nhạc <tên> | tony dừng nhạc\n"
        "• hiển thị ảnh trên pi [N giây] — ảnh DM lên màn Pi5 rồi tự về avatar\n"
        "• mở <app> | đóng <app> | chụp màn hình | khóa máy  (PC)\n"
        "• stop — dừng khẩn cấp"
    )


def handle_stop(payload: dict[str, Any] | None = None) -> str:
    """'stop': DỪNG TẤT CẢ tác vụ đang chạy (emergency halt).

    Đây là lệnh khẩn cấp - dừng mọi tác vụ không quan trọng.
    An toàn: không dừng services cốt lõi (server, watchdog).
    """
    stopped: list[str] = []
    ok, msg = _edge_control({"action": "emergency_stop"})
    if ok:
        stopped.append("hình thể Pi5 (emergency_stop)")
    _audit("netchat_command.stop", {"edge_ok": ok, "stopped": stopped})
    body = ", ".join(stopped) if stopped else "không có tác vụ nền nào đang chạy"
    return (f"🛑 STOP — đã dừng: {body}.\n"
            "(An toàn: server, watchdog, responder cốt lõi KHÔNG bị dừng.)")


def handle_freeze(payload: dict[str, Any] | None = None) -> str:
    """'freeze': tạm dừng hình thể (pause) — 'tony làm việc' để dậy lại."""
    ok, msg = _edge_control({"action": "pause"})
    _audit("netchat_command.freeze", {"success": ok})
    return "🧊 Đã tạm dừng (freeze) hình thể TONY — anh nói 'tony làm việc' để em dậy lại ạ." if ok \
        else f"⚠️ Không tạm dừng được: {_vn_err(msg)}"


def _edge_control(data: dict[str, Any], timeout: float = 8.0) -> tuple[bool, str]:
    """POST 1 action tới edge control API của server (8766) — trả (ok, message)."""
    try:
        import urllib.request
        req = urllib.request.Request(
            _EDGE_API,
            data=json.dumps(data).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            out = json.loads(resp.read().decode("utf-8"))
        if out.get("success"):
            return True, str(out.get("message") or "xong")
        return False, _vn_err(out.get("error") or out)
    except Exception as exc:
        return False, f"{type(exc).__name__}: {exc}"


def handle_tony_on(payload: dict[str, Any] | None = None) -> str:
    ok, msg = _edge_control({"action": "start_kiosk"})
    _audit("netchat_command.tony_on", {"success": ok})
    return "🤖 Đã bật hình thể TONY trên Pi 5 (màn sáng + giao diện kiosk)." if ok \
        else f"⚠️ Không bật được hình thể: {_vn_err(msg)}"


def handle_tony_off(payload: dict[str, Any] | None = None) -> str:
    ok, msg = _edge_control({"action": "close_kiosk"})
    _audit("netchat_command.tony_off", {"success": ok})
    return "🌙 Đã tắt hình thể — Pi 5 vào chế độ nghỉ (anh gọi 'TONY ơi' là em dậy ạ)." if ok \
        else f"⚠️ Không tắt được hình thể: {_vn_err(msg)}"




def handle_tony_hdmi_show(text: str = "", payload: dict[str, Any] | None = None) -> str:
    """'xuất hình ra hdmi' / 'chiếu ra màn hdmi' — mirror kiosk ra cổng HDMI Pi5."""
    ok, msg = _edge_control({"action": "hdmi_show"})
    _audit("netchat_command.tony_hdmi_show", {"success": ok})
    if ok:
        return ("🖥️ Đã bật mirror kiosk ra cổng HDMI của Pi 5 — avatar TONY hiển thị "
                "đồng thời trên màn DSI 7\" và màn HDMI (tự phát hiện độ phân giải).")
    return ("⚠️ Chưa thấy màn hình nào cắm vào cổng HDMI của Pi 5 — anh cắm dây HDMI "
            "vào rồi nói lại 'xuất hình ra hdmi' nhé (hệ thống cũng tự bật khi phát hiện cắm).")


def handle_tony_hdmi_hide(text: str = "", payload: dict[str, Any] | None = None) -> str:
    """'tắt hdmi' — đóng mirror trên HDMI (DSI giữ nguyên)."""
    ok, msg = _edge_control({"action": "hdmi_hide"})
    _audit("netchat_command.tony_hdmi_hide", {"success": ok})
    return "🌙 Đã tắt hình trên màn HDMI (màn DSI 7\" giữ nguyên)." if ok \
        else "⚠️ Không tắt được mirror HDMI — xem log daemon."


def handle_tony_hdmi_approve(text: str = "", payload: dict[str, Any] | None = None) -> str:
    """'phê duyệt hdmi' — owner CHẤP THUẬN xuất hình thể lên HDMI (khi cắm màn
    hệ thống hỏi). Bật mirror LIÊN TỤC cho đến khi owner 'tắt hdmi'.

    Fail-honest: Pi5 trả 'HDMI chưa cắm màn' → báo thẳng, KHÔNG xác nhận suông."""
    ok, msg = _edge_control({"action": "hdmi_show"})
    _audit("netchat_command.tony_hdmi_approve", {"success": ok})
    _detail = str(msg or "").strip()
    if ok and "chưa cắm" not in _detail and "không bật được" not in _detail:
        return ("🖥️ Đã phê duyệt — em xuất hình thể lên màn HDMI NGAY và hiển thị "
                "LIÊN TỤC cho đến khi anh nhắn 'tắt hdmi'. Hình vẫn song song trên "
                "màn Pi 5.")
    if "chưa cắm" in _detail or "không bật được" in _detail:
        return ("⚠️ Anh phê duyệt rồi nhưng em chưa thấy màn hình nào cắm vào cổng "
                "HDMI của Pi 5. Anh kiểm tra dây/cổng HDMI cắm chắc rồi nhắn lại "
                "'phê duyệt hdmi' — em sẽ bật ngay.")
    return f"⚠️ Pi 5 từ chối lệnh HDMI: {_detail or 'không rõ nguyên nhân'}"


def handle_ack_alert(text: str = "", payload: dict[str, Any] | None = None) -> str:
    """'giữ nguyên [loa]/tắt cảnh báo [X]' (01/11/2026) — owner xác nhận hiện
    trạng là CỐ Ý → hệ thống ngừng cảnh báo lại check liên quan.

    Map từ khóa trong câu → check_id thật:
      loa/bluetooth/bt → bt_speaker_connected; mic → pi5_audio_input;
      nhiệt độ/temp → soc_temp_c; cpu → cpu.used_pct; ram → ram_mb.used_pct;
      đĩa/disk → disk_root.used_pct. Không khớp → ack check nhắc đến gần nhất
      trong cảnh báo gần đây (ít ràng buộc nhất cho owner).
    """
    from quan_ai_brain.monitoring.alert_engine import save_owner_ack, load_owner_acks

    t = (text or "").lower()
    _MAP = {
        "bt_speaker_connected": ("loa", "bluetooth", "bt ", "speaker", "âm thanh", "am thanh"),
        "pi5_audio_input": ("mic", "micro"),
        "soc_temp_c": ("nhiệt", "nhiet", "temp"),
        "cpu.used_pct": ("cpu",),
        "ram_mb.used_pct": ("ram", "bộ nhớ", "bo nho"),
        "disk_root.used_pct": ("đĩa", "dia", "disk", "ổ cứng", "o cung"),
    }
    targets: list[str] = []
    for check_id, kws in _MAP.items():
        if any(k in t for k in kws):
            targets.append(check_id)
    if not targets:
        # Không nói rõ → ack mọi cảnh báo WARNING/CRITICAL đang hoạt động
        # (owner nói 'giữ nguyên' tổng quát = tôn trọng toàn bộ quyết định).
        try:
            from quan_ai_brain.monitoring.alert_engine import load_owner_acks as _loa
        except Exception:
            pass
        targets = ["*"]
    for cid in targets:
        save_owner_ack(WORKSPACE, cid,
                       f"owner ack qua DM: {(text or '').strip()[:120]}")
    acks = load_owner_acks(WORKSPACE)
    _audit("netchat_command.ack_alert", {"targets": targets, "text": (text or "")[:120]})
    nice = ", ".join(targets)
    return (f"✅ Đã ghi nhận quyết định của anh ({nice}). Từ giờ em không cảnh "
            f"báo lại các mục này nữa — vẫn theo dõi ngầm, nếu tình trạng THAY ĐỔI "
            f"thật sự (vd loa được bật) em sẽ báo anh. Hiện có {len(acks)} cảnh "
            f"báo đã được anh xác nhận giữ nguyên.")


def handle_tony_status(payload: dict[str, Any] | None = None) -> str:
    try:
        import urllib.request
        with urllib.request.urlopen("http://127.0.0.1:8766/api/executive/edge/status",
                                    timeout=6) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        edge = data.get("edge") or {}
        state = str(edge.get("state") or "?")
        paired = edge.get("paired")
        hb = edge.get("last_heartbeat_epoch") or 0
        age = f"{max(0.0, time.time() - float(hb)):.0f}s trước" if hb else "?"
        kiosk = edge.get("kiosk_running")
        _audit("netchat_command.tony_status", {"state": state})
        return (f"🧭 Hình thể Pi 5: {_vn(state)} | ghép nối: {_vn_bool(paired)} | "
                f"tim đập (heartbeat): {age} | "
                f"kiosk: {'đang bật' if kiosk else 'đang tắt'}")
    except Exception as exc:
        return f"🔴 Pi5 không trả lời: {type(exc).__name__}: {exc}"


def handle_tony_pause(payload: dict[str, Any] | None = None) -> str:
    ok, msg = _edge_control({"action": "pause"})
    _audit("netchat_command.tony_pause", {"success": ok})
    return "😴 TONY tạm nghỉ — màn Pi 5 tắt, tự dậy khi có lệnh hoặc giọng 'TONY ơi'." if ok \
        else f"⚠️ Không pause được: {msg}"


def handle_tony_resume(payload: dict[str, Any] | None = None) -> str:
    ok, msg = _edge_control({"action": "resume"})
    _audit("netchat_command.tony_resume", {"success": ok})
    return "☀️ TONY dậy làm việc — màn hình Pi 5 sáng lại." if ok \
        else f"⚠️ Không resume được: {msg}"


def handle_tony_speak(text: str, payload: dict[str, Any] | None = None) -> str:
    """'tony nói <câu>' — TTS trên loa Pi 5 (BT SRS-XB33 phải bật nguồn)."""
    q = (text or "").strip()
    if not q:
        return "🗣️ Anh muốn TONY nói gì? Cú pháp: 'tony nói Chào anh Quân'"
    ok, msg = _edge_control({"action": "speak", "text": q[:500]})
    _audit("netchat_command.tony_speak", {"success": ok, "len": len(q)})
    return f"🗣️ TONY đang nói: \"{q[:120]}\"" if ok else f"⚠️ TONY không nói được: {msg}"


# (31/10/2026) PHÁT NGUYÊN VĂN — chống GLM paraphrase:
# 'em phát câu này 2 lần trên loa pi5: <nguyên văn>' → text đưa vào TTS giữ
# 100% nguyên văn câu sau dấu ':', phát đúng N lần (1..5), không cắt/không diễn giải.
_SPEAK_VERBATIM_RE = re.compile(
    r"^\s*(?:em\s+|tony\s+)?phát(?:\s+câu\s+này|\s+nguyên\s+văn|\s+đúng)?\s*"
    r"(?:(\d+)\s*lần|\s+hai\s+lần|\s+2\s+lần)?\s*(?:trên\s+)?(?:loa\s+)?(?:pi\s*5|pi5)?\s*"
    r"(?:giọng\s+(nữ|nam))?\s*[:：]\s*(.+)$",
    re.IGNORECASE,
)


def handle_tony_speak_verbatim(text: str, payload: dict[str, Any] | None = None) -> str:
    """'phát [câu này] [N lần] [trên loa pi5] [giọng nữ/nam]: <nguyên văn>'.

    Khác 'tony nói': KHÔNG cho GLM diễn giải — chuỗi sau ':' được đưa thẳng
    vào Edge-TTS nguyên xi (giữ dấu, dấu câu, độ dài ≤600).
    """
    q = (text or "").strip()
    m = _SPEAK_VERBATIM_RE.match(q)
    if not m:
        return ("🗣️ Cú pháp: 'phát câu này 2 lần trên loa pi5: <nội dung nguyên văn>'")
    repeat = 1
    if m.group(1):
        repeat = max(1, min(5, int(m.group(1))))
    elif re.search(r"\bhai\s+lần\b|\b2\s+lần\b", q, re.IGNORECASE):
        repeat = 2
    voice = "vi-VN-NamMinhNeural" if (m.group(2) or "").lower() == "nam" else "vi-VN-HoaiMyNeural"
    verbatim = m.group(3).strip()
    if not verbatim:
        return "⚠️ Anh chưa ghi nội dung cần phát sau dấu ':'."
    if len(verbatim) > 600:
        return (f"⚠️ Nội dung {len(verbatim)} ký tự vượt giới hạn TTS 600 — "
                f"anh tách thành 2 câu giúp em nhé.")
    # Synth NGAY tại PC (tránh server synth đồng bộ gây timeout 8s) rồi đẩy
    # audio sang — server chỉ forward (<1s/lần):
    audio_b64 = ""
    try:
        import base64 as _b64
        from quan_ai_brain.voice.tts_config import TTSManager as _TTSManager

        _mgr = _TTSManager()
        for _attempt in range(3):
            audio_bytes, _err = _mgr.synthesize_audio(verbatim, voice_id=voice)
            if audio_bytes:
                audio_b64 = _b64.b64encode(audio_bytes).decode("ascii")
                break
            time.sleep(1.0)
    except Exception as exc:  # synth fail → fallback server synth
        audio_b64 = ""

    ok_all, errs = True, []
    duration_ms = max(2000, len(verbatim) * 130)
    for i in range(repeat):
        payload_edge: dict[str, Any] = {"action": "speak", "text": verbatim,
                                        "duration_ms": duration_ms,
                                        "force_hardware": True}
        if audio_b64:
            payload_edge["audio_base64"] = audio_b64
        else:
            payload_edge["voice_id"] = voice
        ok, msg = _edge_control(payload_edge, timeout=25.0)
        if not ok:
            ok_all = False
            errs.append(msg)
        time.sleep(1.0 if i < repeat - 1 else 0.0)
    _audit("netchat_command.tony_speak_verbatim",
           {"success": ok_all, "len": len(verbatim), "repeat": repeat, "voice": voice})
    if ok_all:
        preview = verbatim if len(verbatim) <= 160 else verbatim[:157] + "..."
        return (f"🗣️ Đã phát NGUYÊN VĂN {repeat} lần (giọng {'nữ HoàiMy' if 'HoaiMy' in voice else 'nam NamMinh'}):\n"
                f"«{preview}»")
    return f"⚠️ Phát lỗi: {'; '.join(errs)[:200]}"


def handle_tony_face(text: str, payload: dict[str, Any] | None = None) -> str:
    """'biểu cảm <kiểu>' — set_expression trên avatar Pi 5."""
    expr = (text or "").strip().upper().replace(" ", "_")
    if expr not in _AVATAR_STATES:
        expr = "HAPPY"
    ok, msg = _edge_control({"action": "set_expression", "expression": expr})
    _audit("netchat_command.tony_face", {"success": ok, "expression": expr})
    return f"😊 Đã đổi biểu cảm TONY: {expr}" if ok else f"⚠️ Không đổi được biểu cảm: {msg}"


def handle_pc_screenshot(payload: dict[str, Any] | None = None) -> str:
    """'chụp màn hình' — chụp PC + gửi ảnh DM (qua action executor)."""
    try:
        from tools.netchat_action_executor import screenshot_to_dm

        ok, msg = screenshot_to_dm()
        _audit("netchat_command.pc_screenshot", {"success": ok})
        return f"📸 {msg}" if ok else f"⚠️ {msg}"
    except Exception as exc:
        return f"⚠️ Lỗi chụp màn hình: {type(exc).__name__}: {exc}"


def show_image_on_pi5(image_path: str, duration_sec: float = 15.0) -> tuple[bool, str]:
    """Gửi lệnh show_image qua edge control — server PC tự upload ảnh lên Pi."""
    try:
        import urllib.request
        req = urllib.request.Request(
            _EDGE_API,
            data=json.dumps({"action": "show_image", "url": image_path,
                             "duration_sec": duration_sec}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=25) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        if data.get("success"):
            return True, str(data.get("url", ""))
        return False, str(data.get("error", "không rõ"))[:200]
    except Exception as exc:
        return False, f"{type(exc).__name__}: {exc}"


def handle_tony_show_image(text: str = "", payload: dict[str, Any] | None = None) -> str:
    """'hiển thị ảnh trên pi' / 'hiển thị lại ảnh' — ảnh = đính kèm DM đang xử
    lý (payload['file_paths']) HOẶC ảnh DM mới nhất trong data/netchat_files.
    Mặc định hiển thị 15 giây rồi Pi5 tự về avatar; '...20 giây' đổi thời gian."""
    from pathlib import Path as _Path

    m_dur = re.search(r"(\d{1,3})\s*(?:giây|s)\b", (text or "").lower())
    duration = max(3.0, min(600.0, float(m_dur.group(1)))) if m_dur else 15.0

    paths: list[str] = list((payload or {}).get("file_paths") or [])
    if not paths:
        attach = WORKSPACE / "data" / "netchat_files"
        imgs = [f for f in attach.iterdir()
                if f.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"}
                ] if attach.exists() else []
        if not imgs:
            return "⚠️ Chưa có ảnh nào từ DM để hiển thị. Anh gửi ảnh vào DM rồi lệnh lại nhé."
        paths = [str(max(imgs, key=lambda f: f.stat().st_mtime))]

    ok, info = show_image_on_pi5(paths[0], duration)
    _audit("netchat_command.tony_show_image",
           {"ok": ok, "file": _Path(paths[0]).name, "duration": duration})
    if ok:
        return (f"🖼️ Đang hiển thị ảnh trên màn Pi 5 trong {duration:.0f} giây — "
                f"hết thời gian tự về avatar TONY. Muốn hiện lại: nhắn 'hiển thị lại ảnh'.")
    return f"⚠️ Không hiển thị được ảnh lên Pi 5: {info}"


def _pi_media_capture(kind: str, duration_sec: float = 5.0,
                      mic_kind: str = "auto") -> tuple[bool, dict]:
    """Gọi server PC action 'pi_media_capture' — Pi chụp/quay + PC tải file về."""
    try:
        import urllib.request
        req = urllib.request.Request(
            _EDGE_API,
            data=json.dumps({"action": "pi_media_capture", "kind": kind,
                             "duration_sec": duration_sec,
                             "mic_kind": mic_kind}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        timeout = 90.0 if kind == "video" else 45.0
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        if data.get("success"):
            return True, data
        return False, {"error": str(data.get("error", "không rõ"))[:200]}
    except Exception as exc:
        return False, {"error": f"{type(exc).__name__}: {exc}"}


def handle_tony_pi_screenshot(text: str = "", payload: dict[str, Any] | None = None) -> str:
    """(01/11/2026, owner feedback image_864dc0) 'chụp màn hình kiosk/pi5' —

    Chụp MÀN HÌNH PI5 thật (không phải PC): SSH → wlopm --on nếu màn đang ngủ
    (swayidle timeout 600s làm DSI-2 off — grim sẽ 'failed to copy output') →
    grim (wlr-screencopy, TFT 800x480) → scp về PC → gửi ảnh DM.
    Fail-honest: lỗi SSH/grim trả thông báo rõ, không bịa ảnh.
    """
    import subprocess as _sp
    from pathlib import Path as _P
    from tools.netchat_action_executor import send_file_to_dm

    PI = "quanpt1@100.100.83.59"
    ts = time.strftime("%Y%m%d_%H%M%S")
    remote_png = f"/tmp/kiosk_shot_{ts}.png"
    pc_dir = _P(__file__).resolve().parent.parent / "data" / "netchat_files"
    pc_dir.mkdir(parents=True, exist_ok=True)
    pc_path = pc_dir / f"kiosk_{ts}.png"
    try:
        # 1) Bật màn hình nếu đang off (swayidle ngủ sau 10 phút)
        _sp.run(["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=8", PI,
                 "WAYLAND_DISPLAY=wayland-0 XDG_RUNTIME_DIR=/run/user/1000 "
                 "wlopm --on '*' >/dev/null 2>&1; sleep 1"],
                capture_output=True, timeout=25)
        # 2) grim chụp Wayland output TFT
        r = _sp.run(["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=8", PI,
                     f"WAYLAND_DISPLAY=wayland-0 XDG_RUNTIME_DIR=/run/user/1000 "
                     f"grim {remote_png} 2>&1 && test -s {remote_png}"],
                    capture_output=True, text=True, timeout=30)
        if r.returncode != 0:
            _audit("netchat_command.tony_pi_screenshot", {"ok": False, "err": r.stdout[:120]})
            return ("⚠️ Không chụp được màn hình Pi 5 (grim lỗi: "
                    f"{(r.stdout or r.stderr).strip()[:120]}). Anh thử lại nhé.")
        # 3) Kéo về PC
        r2 = _sp.run(["scp", "-o", "BatchMode=yes",
                      f"{PI}:{remote_png}", str(pc_path)],
                     capture_output=True, text=True, timeout=30)
        if r2.returncode != 0 or not pc_path.exists() or pc_path.stat().st_size < 2000:
            _audit("netchat_command.tony_pi_screenshot", {"ok": False, "err": "scp fail"})
            return "⚠️ Đã chụp trên Pi nhưng tải ảnh về PC thất bại."
        _sp.run(["ssh", "-o", "BatchMode=yes", PI, f"rm -f {remote_png}"],
                capture_output=True, timeout=15)
        size_kb = pc_path.stat().st_size / 1024
        # 4) Gửi ảnh DM
        sent, sent_msg = send_file_to_dm(
            str(pc_path),
            f"🖥️ Ảnh màn hình kiosk Pi 5 (TFT 800x480) lúc "
            f"{time.strftime('%H:%M:%S %d/%m')} (TONY chụp theo lệnh DM)")
        _audit("netchat_command.tony_pi_screenshot",
               {"ok": True, "size_kb": round(size_kb, 1), "dm_sent": sent})
        dm_note = " — đã gửi ảnh vào DM cho anh" if sent else f" (gửi DM lỗi: {sent_msg})"
        return (f"🖥️ Đã chụp màn hình kiosk Pi 5 ({size_kb:.0f} KB){dm_note}.")
    except Exception as exc:
        _audit("netchat_command.tony_pi_screenshot", {"ok": False, "err": type(exc).__name__})
        return f"⚠️ Lỗi chụp màn hình Pi 5: {type(exc).__name__}: {exc}"


def handle_tony_pi_photo(text: str = "", payload: dict[str, Any] | None = None) -> str:
    """'chụp ảnh từ pi' — Pi5 chụp ảnh camera, lưu Pi + PC, gửi ảnh về DM."""
    from tools.netchat_action_executor import send_file_to_dm

    ok, data = _pi_media_capture("photo")
    if not ok:
        _audit("netchat_command.tony_pi_photo", {"ok": False, "error": data.get("error", "")})
        return f"⚠️ Không chụp được ảnh từ Pi 5: {_vn_err(data.get('error', ''))}"
    fname = str(data.get("filename", ""))
    pc_path = str(data.get("pc_path", ""))
    size_kb = int(data.get("size_bytes", 0)) / 1024
    _audit("netchat_command.tony_pi_photo",
           {"ok": True, "file": fname, "size_kb": round(size_kb, 1)})

    # Gửi file vào DM cho owner xem ngay:
    dm_note = ""
    if pc_path and not pc_path.startswith("("):
        from pathlib import Path as _P
        sent, sent_msg = send_file_to_dm(
            pc_path, f"📷 Ảnh chụp từ camera Pi 5 lúc "
                     f"{time.strftime('%H:%M:%S %d/%m')} (TONY chụp theo lệnh DM)")
        dm_note = " và đã gửi ảnh vào DM cho anh" if sent else (
            f" (gửi DM lỗi: {sent_msg})")
    return (f"📷 Đã chụp ảnh từ camera Pi 5: {fname} ({size_kb:.0f} KB) — "
            f"đã lưu trên Pi 5 lẫn máy tính{dm_note}.")


def handle_tony_pi_video(text: str = "", payload: dict[str, Any] | None = None) -> str:
    """'quay video từ pi [N giây]' — Pi5 quay video + ghi mic, lưu 2 bên, gửi DM."""
    from tools.netchat_action_executor import send_file_to_dm

    import re as _re
    m_dur = _re.search(r"(\d{1,2})\s*(?:giây|s)\b", (text or "").lower())
    duration = max(3.0, min(30.0, float(m_dur.group(1)))) if m_dur else 5.0

    ok, data = _pi_media_capture("video", duration)
    if not ok:
        _audit("netchat_command.tony_pi_video", {"ok": False, "error": data.get("error", "")})
        return f"⚠️ Không quay được video từ Pi 5: {_vn_err(data.get('error', ''))}"
    fname = str(data.get("filename", ""))
    pc_path = str(data.get("pc_path", ""))
    size_kb = int(data.get("size_bytes", 0)) / 1024
    has_audio = bool(data.get("has_audio"))
    _audit("netchat_command.tony_pi_video",
           {"ok": True, "file": fname, "size_kb": round(size_kb, 1),
            "duration": duration, "has_audio": has_audio})

    dm_note = ""
    if pc_path and not pc_path.startswith("("):
        from pathlib import Path as _P
        sent, sent_msg = send_file_to_dm(
            pc_path, f"🎬 Video {duration:.0f}s{' kèm tiếng' if has_audio else '(câm)'} "
                     f"từ camera Pi 5 lúc {time.strftime('%H:%M:%S %d/%m')} "
                     f"(TONY quay theo lệnh DM)")
        dm_note = " và đã gửi video vào DM cho anh" if sent else (
            f" (gửi DM lỗi: {sent_msg})")
    audio_note = "kèm tiếng mic" if has_audio else "video câm (mic không ghi được)"
    return (f"🎬 Đã quay video {duration:.0f}s từ Pi 5 ({audio_note}): {fname} "
            f"({size_kb:.0f} KB) — đã lưu trên Pi 5 lẫn máy tính{dm_note}.")


def handle_tony_pi_listen(text: str = "", payload: dict[str, Any] | None = None) -> str:
    """'nghe từ pi [N giây] [bằng mic usb|mic loa]' — TAI của TONY: thu âm N giây.

    Mặc định: mic USB Jieli (ưu tiên); 'mic loa'/'mic bluetooth' → mic tích hợp
    trong loa SRS-XB33 (bluez_input) — nhạy tiếng ồn lớn, nền sạch.
    """
    from tools.netchat_action_executor import send_file_to_dm

    import re as _re
    m_dur = _re.search(r"(\d{1,2})\s*(?:giây|s)\b", (text or "").lower())
    duration = max(3.0, min(30.0, float(m_dur.group(1)))) if m_dur else 5.0
    t_low = (text or "").lower()
    if re.search(r"mic\s*(loa|bluetooth|bt)\b|bằng\s+mic\s+loa", t_low):
        mic_kind = "bt"
    elif re.search(r"mic\s*usb\b", t_low):
        mic_kind = "usb"
    else:
        mic_kind = "auto"

    ok, data = _pi_media_capture("audio", duration, mic_kind=mic_kind)
    if not ok:
        _audit("netchat_command.tony_pi_listen", {"ok": False, "error": data.get("error", "")})
        return f"⚠️ Không thu âm được từ mic Pi 5: {_vn_err(data.get('error', ''))}"
    fname = str(data.get("filename", ""))
    pc_path = str(data.get("pc_path", ""))
    size_kb = int(data.get("size_bytes", 0)) / 1024
    _audit("netchat_command.tony_pi_listen",
           {"ok": True, "file": fname, "size_kb": round(size_kb, 1), "duration": duration})

    dm_note = ""
    if pc_path and not pc_path.startswith("("):
        sent, sent_msg = send_file_to_dm(
            pc_path, f"🎙️ Thu âm {duration:.0f}s từ mic Pi 5 lúc "
                     f"{time.strftime('%H:%M:%S %d/%m')} (tai TONY nghe theo lệnh DM)")
        dm_note = " và đã gửi file âm thanh vào DM cho anh" if sent else (
            f" (gửi DM lỗi: {sent_msg})")
    mic_label = {"usb": "mic USB", "bt": "mic loa (SRS-XB33)", "auto": "mic tự chọn (USB ưu tiên)"}.get(mic_kind, "mic")
    return (f"🎙️ Đã thu âm {duration:.0f}s ({mic_label}): {fname} ({size_kb:.0f} KB) — "
            f"đã lưu trên Pi 5 lẫn máy tính{dm_note}.")


def handle_tony_youtube(text: str, payload: dict[str, Any] | None = None) -> str:
    """'tony mở youtube [từ khóa]' — không từ khóa: mở trang chủ YouTube;
    có từ khóa: tìm kiếm và mở trang kết quả YouTube trên màn Pi 5."""
    q = (text or "").strip()
    if q:
        try:
            from quan_ai_brain.media.youtube_music import search_youtube_music
            results = search_youtube_music(q, max_results=3)
        except Exception as exc:
            results = []
            _audit("netchat_command.tony_youtube_search_error", {"error": str(exc)[:150]})
        if results:
            top = results[0]
            ok, info = _open_url_on_pi5(top["url"])
            _audit("netchat_command.tony_youtube", {"ok": ok, "video": top.get("video_id"), "q": q[:60]})
            if ok:
                extra = ""
                if len(results) > 1:
                    alt = " | ".join(f"{r['title'][:40]} ({r['duration']})" for r in results[1:3])
                    extra = f"\nCác video khác: {alt}"
                return (f"▶️ Đang mở trên màn Pi 5: “{top['title'][:90]}” "
                        f"({top.get('channel') or 'YouTube'}{', ' + top['duration'] if top.get('duration') else ''})"
                        f"{extra}")
            return f"⚠️ Không mở được YouTube trên Pi 5: {info}\n(Kiểm tra: gõ 'hình thể')"
        return (f"🔍 Không tìm thấy video nào cho “{q[:60]}”. "
                f"Thử từ khóa khác, ví dụ: 'tony mở youtube nhac thieu nhi vui nhon'")
    ok, info = _open_url_on_pi5("https://www.youtube.com/")
    _audit("netchat_command.tony_youtube", {"ok": ok, "home": True})
    if ok:
        return "▶️ Đã mở YouTube trên màn Pi 5 — anh xem trực tiếp nhé!"
    return f"⚠️ Không mở được YouTube trên Pi 5: {info}\n(Kiểm tra: gõ 'hình thể')"


def _open_url_on_pi5(url: str) -> tuple[bool, str]:
    """Gửi lệnh open_url qua edge control API → kiosk Pi 5 điều hướng thật."""
    try:
        import urllib.request
        req = urllib.request.Request(
            _EDGE_API,
            data=json.dumps({"action": "open_url", "url": url}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return bool(data.get("success")), str(data.get("url", url))
    except Exception as exc:
        return False, f"{type(exc).__name__}: {exc}"


def handle_tony_websearch(text: str, payload: dict[str, Any] | None = None) -> str:
    """'tony tìm <câu>' / 'tìm kiếm <câu>' — mở Google search kết quả trên màn
    Pi 5 (anh đọc trực tiếp) — không cần AI tổng hợp."""
    q = (text or "").strip()
    if not q:
        return "🔍 Anh muốn em tìm gì? Cú pháp: 'tony tìm thời tiết hôm nay'"
    import urllib.parse
    url = "https://www.google.com/search?q=" + urllib.parse.quote(q)
    ok, info = _open_url_on_pi5(url)
    _audit("netchat_command.tony_websearch", {"ok": ok, "q": q[:60]})
    if ok:
        return f"🔍 Đã mở Google Search “{q[:60]}” trên màn Pi 5 — anh xem kết quả nhé!"
    return f"⚠️ Không mở được tìm kiếm trên Pi 5: {info}\n(Kiểm tra: gõ 'hình thể')"


def handle_tony_music_play(text: str, payload: dict[str, Any] | None = None) -> str:
    """'tony phát nhạc <tên>' / 'bật nhạc <tên>' — dùng engine YouTube Music
    có sẵn (search + play trên loa Pi 5)."""
    q = (text or "").strip()
    if not q:
        return "🎵 Anh muốn nghe bài gì? Cú pháp: 'tony phát nhạc bolero trữ tình'"
    try:
        import urllib.request
        req = urllib.request.Request(
            "http://127.0.0.1:8766/api/music/play",
            data=json.dumps({"query": q}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        if data.get("success"):
            title = str(data.get("title", ""))[:80]
            return f"🎵 Đang phát trên loa Pi 5: “{title}” (LƯU Ý: loa BT phải đang bật nguồn)"
        return f"⚠️ Không phát được: {_vn_err(data.get('error', 'không rõ'), 120)}"
    except Exception as exc:
        return f"⚠️ Lỗi phát nhạc: {type(exc).__name__}: {exc}"


def handle_tony_music_stop(payload: dict[str, Any] | None = None) -> str:
    """'tony dừng nhạc' — stop music trên Pi 5."""
    try:
        import urllib.request
        req = urllib.request.Request(
            "http://127.0.0.1:8766/api/music/stop",
            data=json.dumps({}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        _audit("netchat_command.tony_music_stop", {"success": bool(data.get("success"))})
        return "⏹️ Đã dừng nhạc trên Pi 5."
    except Exception as exc:
        return f"⚠️ Không dừng được nhạc: {type(exc).__name__}: {exc}"


# ---------------------------------------------------------------------------
# UDC-1 (04/11/2026): điều khiển/khống chế thiết bị Pi5 theo DM của quanpt1
# — gọi edge control API thật (server 8766 → kiosk 8768 → DeviceControlService).
# Write ops (relay/joint) đi qua stage_pending_action: owner gõ 'ok' mới thực thi.
# ---------------------------------------------------------------------------
def _device_control_api(body: dict[str, Any], timeout: float = 8.0) -> dict[str, Any]:
    try:
        import urllib.request
        req = urllib.request.Request(
            "http://127.0.0.1:8766/api/executive/edge/control",
            data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as exc:
        return {"success": False, "error": f"{type(exc).__name__}: {exc}"}


def handle_device_list(payload: dict[str, Any] | None = None) -> str:
    """'thiết bị trên pi' — liệt kê thiết bị Pi5 đang thấy (read-only)."""
    out = _device_control_api({"action": "device", "op": "list_devices"})
    if not out.get("success"):
        pi = out.get("pi5_result", out)
        reason = pi.get("reason") or pi.get("error") or "Pi5 offline/cổng đóng"
        return f"⚠️ Không đọc được thiết bị Pi5: {reason}"
    data = (out.get("pi5_result") or {}).get("data", {})
    devs = data.get("devices", [])
    if not devs:
        return "📭 Pi5 chưa thấy thiết bị nào (snapshot đầu chưa chạy hoặc máy trống)."
    by_bus = data.get("by_bus", {})
    bus_line = " | ".join(f"{k}: {v}" for k, v in sorted(by_bus.items()) if v)
    lines = [f"🔌 Pi5 đang thấy {data.get('total', len(devs))} thiết bị"
             + (f" ({bus_line})" if bus_line else ""), ""]
    for d in devs[:15]:
        lines.append(f"  • [{d.get('bus', '?')}] {d.get('name') or d.get('dev_id')}")
    if len(devs) > 15:
        lines.append(f"  … và {len(devs) - 15} thiết bị khác")
    return "\n".join(lines)


def _parse_relay_target(text: str) -> str:
    """'rơ le 3' / 'relay 3' / 'rơ le chân 3' → relay_3; không số → relay_1."""
    m = re.search(r"\b(\d{1})\b", text or "")
    return f"relay_{m.group(1)}" if m else "relay_1"


def _relay_set_response(text: str, state: str, chat_session_id: str) -> str:
    """Stage lệnh relay + câu hỏi chờ 'ok' (không tự thực hiện lệnh ghi).

    Token do PI cấp (stage_write) ngay lúc stage — lúc owner gõ 'ok', lambda
    sẽ gửi lệnh ghi kèm token đó; token gắn đúng (op, target, value), TTL
    10 phút, một-lần. Pi5 offline → stage thất bại, không hứa suông.
    """
    target = _parse_relay_target(text)
    staged = _device_control_api(
        {"action": "device", "op": "stage_write", "write_op": "relay_set",
         "target": target, "value": state}, timeout=8.0)
    pi = staged.get("pi5_result") or staged
    token = str(pi.get("token", ""))
    if not staged.get("success") or not token:
        reason = pi.get("reason") or staged.get("error") or "Pi5 offline/cổng đóng"
        return (f"⚠️ Chưa đặt được lệnh {state} {target}: {reason}.\n"
                f"Anh kiểm tra Pi5 đang chạy (service quan_ai_edge) rồi lệnh lại.")
    label = (f"⚙️ Chờ anh xác nhận: {state} {target} trên Pi5"
             f" — gõ 'ok' để thực hiện, gõ lệnh khác để bỏ.")
    stage_pending_action(chat_session_id, label,
                         action=lambda: _device_control_api(
                             {"action": "device", "op": "relay_set",
                              "target": target, "value": state,
                              "confirm_token": token}))
    return label


def handle_relay_on(text: str = "", payload: dict[str, Any] | None = None) -> str:
    """'bật rơ le 3' — stage relay_set OPEN, chờ owner 'ok'."""
    return _relay_set_response(text, "OPEN", (payload or {}).get("chat_session_id", "default"))


def handle_relay_off(text: str = "", payload: dict[str, Any] | None = None) -> str:
    """'tắt rơ le 3' — stage relay_set CLOSED, chờ owner 'ok'."""
    return _relay_set_response(text, "CLOSED", (payload or {}).get("chat_session_id", "default"))


def handle_emergency_stop_device(payload: dict[str, Any] | None = None) -> str:
    """'dừng khẩn thiết bị' — emergency_all_stop CHẠY NGAY (an toàn, không chờ ok)."""
    out = _device_control_api({"action": "device", "op": "emergency_stop"})
    pi = out.get("pi5_result") or {}
    if out.get("success") and pi.get("success", True):
        _audit("netchat_command.device_estop", {"success": True})
        return "🛑 Đã DỪNG KHẨN toàn bộ relay/khớp trên Pi5 (an toàn)."
    reason = pi.get("reason") or out.get("error") or "Pi5 offline"
    return f"⚠️ Không dừng khẩn được: {reason}"


def handle_tony_back(payload: dict[str, Any] | None = None) -> str:
    """'tony về' — đóng overlay web trên Pi 5, hình thể TONY hiển thị lại."""
    try:
        import urllib.request
        req = urllib.request.Request(
            _EDGE_API,
            data=json.dumps({"action": "close_web_overlay"}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        _audit("netchat_command.tony_back", {"success": bool(data.get("success"))})
        return "🤖 Đã đóng trang web — hình thể TONY hiển thị lại trên Pi 5."
    except Exception as exc:
        return f"⚠️ Không đóng được overlay: {type(exc).__name__}: {exc}"


def handle_tony_volume(text: str, payload: dict[str, Any] | None = None) -> str:
    """'âm lượng 90' / 'loa to hơn' / 'loa nhỏ hơn' → set_volume 0-100."""
    m = re.search(r"\b(\d{1,3})\b", (text or ""))
    if m:
        vol = max(0, min(100, int(m.group(1))))
    elif "to hơn" in (text or "").lower() or "to hon" in (text or "").lower():
        vol = 95
    elif "nhỏ hơn" in (text or "").lower() or "nho hon" in (text or "").lower():
        vol = 50
    else:
        vol = 85
    ok, msg = _edge_control({"action": "set_volume", "volume": vol})
    _audit("netchat_command.tony_volume", {"success": ok, "volume": vol})
    if ok:
        return f"🔊 Đã đặt âm lượng loa Pi 5 = {vol}%"
    return f"⚠️ Không đặt được âm lượng: {msg}"


def handle_pc_open(text: str, payload: dict[str, Any] | None = None) -> str:
    """'mở ultraviewer' / 'mở chrome' — mở app trong allowlist trên PC."""
    # (31/10/2026) Lệnh hình thể Pi5 ("bật pi5"/"bật màn pi5"/"bật giao diện")
    # ĐỨNG TRƯỚC pc_open — không phải mở app PC. detect_intent là nguồn chuẩn
    # cho các cụm này (đã đưa vào COMMAND_PATTERNS tony_on).
    _pi = detect_intent(text)
    if _pi in ("tony_on", "tony_off", "tony_standby", "tony_status",
               "tony_pi_live", "tony_pi_live_off"):
        return HANDLERS[_pi]()
    try:
        from tools.netchat_action_executor import find_app_in_text, open_app, list_capabilities

        app_key = find_app_in_text(text)
        if app_key is None:
            return (
                "🤔 Anh muốn mở ứng dụng nào? Em mở được:\n"
                + list_capabilities()
                + "\n\nCú pháp: 'mở <tên app>' (VD: 'mở ultraviewer')"
            )
        ok, msg = open_app(app_key)
        return f"✅ {msg}" if ok else f"⚠️ {msg}"
    except Exception as exc:
        return f"⚠️ Lỗi mở app: {type(exc).__name__}: {exc}"


def handle_pc_close(text: str, payload: dict[str, Any] | None = None) -> str:
    """'đóng chrome' / 'tắt zalo' — đóng app trong allowlist (taskkill)."""
    # (31/10/2026) Lệnh hình thể Pi5 ("tắt pi5"/"tắt màn pi5"/"tắt giao diện")
    # ĐỨNG TRƯỚC pc_close — không phải đóng app PC.
    _pi = detect_intent(text)
    if _pi in ("tony_on", "tony_off", "tony_standby", "tony_status",
               "tony_pi_live", "tony_pi_live_off"):
        return HANDLERS[_pi]()
    try:
        from tools.netchat_action_executor import find_app_in_text, close_app, list_capabilities

        app_key = find_app_in_text(text)
        if app_key is None:
            return (
                "🤔 Anh muốn đóng ứng dụng nào? Em đóng được:\n"
                + list_capabilities()
                + "\n\nCú pháp: 'đóng <tên app>'"
            )
        ok, msg = close_app(app_key)
        return f"✅ {msg}" if ok else f"⚠️ {msg}"
    except Exception as exc:
        return f"⚠️ Lỗi đóng app: {type(exc).__name__}: {exc}"


_CAMERA_API = "http://127.0.0.1:8766/api/executive/edge/camera/control"


def _camera_control(data: dict[str, Any], timeout: float = 8.0) -> tuple[bool, str]:
    """POST 1 action tới camera control API của server (8766) — trả (ok, message)."""
    try:
        import urllib.request
        req = urllib.request.Request(
            _CAMERA_API,
            data=json.dumps(data).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            out = json.loads(resp.read().decode("utf-8"))
        if out.get("success"):
            return True, str(out.get("message") or out.get("status") or "OK")
        return False, _vn_err(out.get("error") or out)
    except Exception as exc:
        return False, f"{type(exc).__name__}: {exc}"


def handle_tony_pi_live(payload: dict[str, Any] | None = None) -> str:
    """'bật camera' — Pi5 bật màn hình + hiển thị hình LIVE trực tiếp từ camera."""
    try:
        ok, msg = _camera_control({"action": "start_live", "source": "netchat"})
        if not ok:
            return f"⚠️ Không bật được camera live: {msg}"
        _audit("netchat_command.tony_pi_live", {})
        return ("📹 ĐÃ BẬT CAMERA LIVE trên màn Pi 5 — màn hình tự sáng, "
                "hình trực tiếp từ Camera Module 3. Nhắn 'tắt camera' để tắt.")
    except Exception as exc:
        return f"⚠️ Lỗi bật camera live: {type(exc).__name__}: {exc}"


def handle_tony_pi_live_off(payload: dict[str, Any] | None = None) -> str:
    """'tắt camera' — dừng live, màn Pi5 về avatar TONY."""
    try:
        ok, msg = _camera_control({"action": "stop_live", "source": "netchat"})
        if not ok:
            return f"⚠️ Không tắt được camera live: {msg}"
        _audit("netchat_command.tony_pi_live_off", {})
        return "✅ Đã TẮT camera live — màn Pi 5 trở về hình thể TONY."
    except Exception as exc:
        return f"⚠️ Lỗi tắt camera live: {type(exc).__name__}: {exc}"


def handle_pc_lock(payload: dict[str, Any] | None = None) -> str:
    """'khóa máy' — khóa màn hình Windows (an toàn, anh mở bằng mật khẩu)."""
    try:
        from tools.netchat_action_executor import lock_pc

        ok, msg = lock_pc()
        return f"🔒 {msg}" if ok else f"⚠️ {msg}"
    except Exception as exc:
        return f"⚠️ Lỗi khóa máy: {type(exc).__name__}: {exc}"


HANDLERS = {
    "approve": handle_approve,
    "status": handle_status,
    "report": handle_report,
    "tasks": handle_tasks,
    "knowledge": handle_knowledge,
    "help": handle_help,
    "todo": handle_todo_list,
    "stop": handle_stop,
    "freeze": handle_freeze,
    # (31/10/2026) Điều khiển hình thể TONY/Pi5 qua DM — gọi edge control API thật
    "tony_on": handle_tony_on,
    "tony_off": handle_tony_off,
"tony_hdmi_show": handle_tony_hdmi_show,
"tony_hdmi_hide": handle_tony_hdmi_hide,
"tony_hdmi_approve": handle_tony_hdmi_approve,
    "tony_status": handle_tony_status,
    "tony_pause": handle_tony_pause,
    "tony_resume": handle_tony_resume,
    # tony_speak / tony_face / tony_volume cần đối số → xử lý riêng ở route_message
    # pc_open / pc_close cần đối số (tên app) → xử lý riêng ở route_message
    "pc_screenshot": handle_pc_screenshot,
    # (31/10/2026) Pi5 web/nhạc — music_stop không cần đối số
    "tony_music_stop": handle_tony_music_stop,
    # UDC-1 (04/11/2026): thiết bị/khống chế theo DM — relay_on/off cần text
    # → xử lý riêng ở route_message; list + emergency không cần đối số
    "device_list": handle_device_list,
    "emergency_stop_device": handle_emergency_stop_device,
    "tony_back": handle_tony_back,
    "tony_show_image": handle_tony_show_image,
    "tony_pi_photo": handle_tony_pi_photo,
    "tony_pi_screenshot": handle_tony_pi_screenshot,
    "tony_pi_live": handle_tony_pi_live,
    "tony_pi_live_off": handle_tony_pi_live_off,
    "tony_pi_video": handle_tony_pi_video,
    # (01/11/2026, owner-ACK) 'giữ nguyên/tắt cảnh báo' — ghi nhận quyết định
    "ack_alert": handle_ack_alert,
}

# Intent cần đối số (text sau từ khóa)
_ARG_INTENTS = {"tony_speak": "speak", "tony_face": "face", "tony_volume": "volume",
                "tony_youtube": "youtube", "tony_websearch": "websearch",
                "tony_music_play": "music_play"}

# Từ khóa dẫn lệnh có đối số — tách phần còn lại làm đối số
_ARG_KEYWORD_RES: list[tuple[str, re.Pattern[str]]] = [
    # (31/10/2026) phát NGUYÊN VĂN qua loa — phải đứng TRƯỚC tony_speak/pc_open:
    ("tony_speak_verbatim", _SPEAK_VERBATIM_RE),
    ("tony_speak", re.compile(r"^\s*(?:tony\s+nói|tony\s+noi|kêu\s+tony\s+nói|keu\s+tony\s+noi)\s+(?:với\s+anh|voi\s+anh)?\s*[:：]?\s*(.+)$", re.IGNORECASE)),
    # UDC-1 (04/11/2026): relay on/off — PHẢI đứng TRƯỚC pc_open/pc_close vì
    # động từ 'bật/tắt' trùng ('bật rơ le 3' ≠ 'bật <app>')
    ("relay_on", re.compile(r"^\s*(?:bật|bat)\s+(?:rơ\s*le|ro\s*le|relay)\b(.*)$", re.IGNORECASE)),
    ("relay_off", re.compile(r"^\s*(?:tắt|tat)\s+(?:rơ\s*le|ro\s*le|relay)\b(.*)$", re.IGNORECASE)),
    ("tony_face", re.compile(r"^\s*(?:biểu\s+cảm|bieu\s+cam|đổi\s+biểu\s+cảm|doi\s+bieu\s+cam|set\s+expression)\s*[:：]?\s*(.*)$", re.IGNORECASE)),
    ("tony_volume", re.compile(r"^\s*(?:âm\s+lượng|am\s+luong|volume)\s*[:：]?\s*(.*)$", re.IGNORECASE)),
    ("pc_open", re.compile(r"^\s*(?:mở|mo|bật|bat|bật\s+lên|bat\s+len|khởi\s+động|khoi\s+dong|open)\s+(.+)$", re.IGNORECASE)),
    ("pc_close", re.compile(r"^\s*(?:đóng|dong|tắt|tat|tắt\s+đi|tat\s+di|close|kill)\s+(.+)$", re.IGNORECASE)),
    # (31/10/2026) Pi5: youtube/tìm kiếm/phát nhạc có đối số
    ("tony_youtube", re.compile(r"^\s*(?:tony\s+)?(?:mở|mo|bật|bat|xem)\s+(?:youtube|video)\s*[:：]?\s*(.*)$", re.IGNORECASE)),
    ("tony_websearch", re.compile(r"^\s*(?:tony\s+)?(?:tìm|tim|tra\s+cứu|tra\s+cuu|tìm\s+kiếm|tim\s+kiem)(?:\s+kiếm|\s+giúp\s+anh)?\s*[:：]?\s*(.+)$", re.IGNORECASE)),
    ("tony_music_play", re.compile(r"^\s*(?:tony\s+)?(?:phát|phat|bật|bat|mở|mo|nghe)\s+(?:nhạc|nhac|bài|bai|bài\s+hát|bai\s+hat)\s*[:：]?\s*(.+)$", re.IGNORECASE)),
    # (31/10/2026) hiển thị ảnh lên Pi5 — 'N giây' là phần đối số
    ("tony_show_image", re.compile(r"^\s*(?:hiển\s+thị|hien\s+thi)\s+(?:lại\s+|lai\s+)?(?:ảnh|anh)\b.*?\bpi(?:\s*5)?\s*[:：]?\s*(.*)$", re.IGNORECASE)),
    # (31/10/2026) TAI: 'nghe từ pi [N giây]' — thu âm mic Pi5 gửi DM
    ("tony_pi_listen", re.compile(r"^\s*(?:tony\s+)?(?:nghe|thu\s+âm|thu\s+am|ghi\s+âm|ghi\s+am|lắng\s+nghe|lang\s+nghe)\s+(?:từ|tu|qua)\s+(?:mic\s+)?pi(?:\s*5)?\b(.*)$", re.IGNORECASE)),
]


def _parse_todo_add(text: str) -> tuple[str, str] | None:
    """'nhớ giúp tôi: <việc> (hạn mai)' → (title, due|None). None nếu không khớp."""
    m = re.match(r"^\s*nhớ\s+(?:giúp\s+)?(?:tôi|anh|em)\b\s*[:：]\s*(.+)$",
                 (text or "").strip(), re.IGNORECASE)
    if not m:
        # biến thể KHÔNG dấu ':' phải có nội dung theo sau ngay (vd 'nhớ tôi họp'):
        m = re.match(r"^\s*nhớ\s+(?:giúp\s+)?(?:tôi|anh|em)\b\s+(?![:：])(.+)$",
                     (text or "").strip(), re.IGNORECASE)
    if not m:
        return None
    body = m.group(1).strip()
    if not body:
        return None
    due = ""
    m_due = re.search(r"\b(?:hạn|deadline)\s+(hôm nay|mai|mốt|thứ\s+\w+|ngày\s+\d{1,2}[/-]\d{1,2}"
                      r"|\d{4}-\d{2}-\d{2})\b",
                      body, re.IGNORECASE)
    if m_due:
        due = m_due.group(1).lower()
        body = body[:m_due.start()].strip(" -–—,.")
        if not body:
            return None
    return (body, due)


def route_message(text: str, *, sender_user_id: str = "", chat_session_id: str = "default", payload: dict[str, Any] | None = None) -> tuple[str | None, str]:
    """Route an incoming channel message.

    Returns (intent, response). intent=None + response='' means: fall back
    to AI conversational processing in the responder.

    Sprint 2 (V3): approval intents go through NetChatApprovalAdapter —
    persistent Approval Cards + formal ApprovalGate + SPECIFIC explanations
    (duyệt gì, vì sao, trạng thái, bước tiếp theo). The old consultation-FIFO
    handler stays as a fallback for legacy tickets not bound to task codes.

    27/10/2026 (yêu cầu chủ sở hữu): "ok" = XÁC NHẬN việc bot vừa hỏi → thực
    thi NGAY; nếu không có việc nào chờ xác nhận → KHÔNG PHẢN HỒI (im lặng).
    """
    t = (text or "").strip()

    # (31/10/2026) Bỏ tiền tố lịch sự 'Em ...' — owner ra lệnh 'Em mở firefox lên'
    # ≡ 'mở firefox lên'. _strip_polite_prefixes chỉ strip khi phần còn lại
    # bắt đầu bằng từ khóa lệnh thật.
    t_stripped = _strip_polite_prefixes(t)
    t_for_args = t_stripped

    # 0) "ok" — xác nhận nhanh, PHẢI đứng trước adapter (regex của adapter
    #    bắt cả 'ok' thành lệnh duyệt hồ sơ → lòng vòng, sai ý).
    if _OK_RE.match(t):
        result = run_pending_action(chat_session_id)
        if result is not None:
            _audit("netchat_command.ok_confirmed", {"session": chat_session_id})
            return "ok_confirm", result
        # Không có việc nào chờ xác nhận → im lặng (không lòng vòng).
        return "ok_silent", ""

    # 1) Approval-card commands (DUYỆT/TỪ CHỐI/SỬA/CHI TIẾT TASK-xxxx,
    #    or a plain 'Duyệt'/'Từ chối'/'Chi tiết') — giữ priority như V3.
    try:
        from quan_ai_brain.governance.netchat_approval_adapter import NetChatApprovalAdapter

        adapter = NetChatApprovalAdapter()
        reply = adapter.handle_owner_message(text, sender_user_id=sender_user_id, post=False)
        if reply:
            _audit("netchat_command.approval_card", {"matched": True, "sender": sender_user_id})
            return "approval_card", reply
    except Exception as exc:  # adapter failure must not break other commands
        _audit("netchat_command.approval_adapter_error", {"error": str(exc)[:200]})

    # 0.5) V3 Sprint 3: owner trả lời yêu cầu bổ sung thông tin (TASK-xxxx +
    #      không khớp lệnh duyệt ở trên) → cập nhật trạng thái chờ (V3 §8.1).
    #      Trả lời ≠ phê duyệt — approval đã xử lý ở bước 1 với priority cao hơn.
    try:
        from quan_ai_brain.governance.netchat_info_gap_adapter import (
            handle_owner_info_reply,
        )

        info_reply = handle_owner_info_reply(text, sender_user_id=sender_user_id)
        if info_reply:
            _audit("netchat_command.info_gap_reply", {"session": chat_session_id})
            return "info_gap_reply", info_reply
    except Exception as exc:  # không phá các lệnh khác
        _audit("netchat_command.info_gap_adapter_error", {"error": str(exc)[:200]})

    # 2) Sprint 8 (a): "nhớ giúp tôi: ..." → thêm to-do — chạy TRƯỚC detect_intent
    #    để "nhớ giúp tôi: giúp anh Hùng sửa camera hạn mai" không bị nuốt vào help.
    #    Lệnh đổi trạng thái mức thấp (chỉ ghi việc) — đứng SAU approval/info-gap.
    todo_add = _parse_todo_add(text)
    if todo_add is not None:
        try:
            from quan_ai_brain.tools.todo_store import TodoStore

            store = TodoStore(WORKSPACE / "data" / "todos.db")
            title, due = todo_add
            item = store.add(title=title, due=due)
            due_note = f" (hạn {due})" if due else ""
            _audit("netchat_command.todo_add", {"id": item["id"]})
            return "todo_add", f"✅ Đã ghi việc: {item['title']}{due_note}"
        except Exception as exc:
            return "todo_add", f"⚠️ Lỗi thêm việc: {type(exc).__name__}: {exc}"

    # 2.2) (02/11/2026) SEC-S1: lệnh An ninh (an ninh / giữ <pid> / thả <pid> /
    #      hạ <pid> / giao nhiệm vụ cho ...) — TRƯỚC detect_intent Pi5 & app PC
    #      để 'hạ 1234' không bị nuốt thành lệnh khác.
    try:
        from tools.netchat_security_center import route_security_command

        sec = route_security_command(text)
        if sec is not None:
            _audit("netchat_command.security", {"intent": sec[0]})
            return sec
    except Exception as exc:  # hỏng module an ninh không được phá luồng khác
        _audit("netchat_command.security_error", {"error": str(exc)[:200]})

    # 2.5) (31/10/2026) Lệnh hình thể Pi5 ưu tiên cao hơn lệnh app PC —
    #    'bật pi5'/'tắt pi5' phải là tony_on/off, KHÔNG rơi vào pc_open/pc_close.
    _pi_intent = detect_intent(t_for_args)
    if _pi_intent in ("tony_on", "tony_off", "tony_standby", "tony_status",
                      "tony_pi_live", "tony_pi_live_off",
                      # (31/10/2026, owner) HDMI: 'tắt hdmi' KHÔNG phải đóng app PC
                      "tony_hdmi_hide", "tony_hdmi_approve"):
        try:
            return _pi_intent, HANDLERS[_pi_intent]()
        except Exception as exc:
            return _pi_intent, f"⚠️ Lỗi thực thi lệnh '{_pi_intent}': {type(exc).__name__}: {exc}"

    # 3) Lệnh có đối số (tony nói/biểu cảm/âm lượng/mở-đóng app) — khớp regex trước intent thường
    for intent_arg, kw_re in _ARG_KEYWORD_RES:
        m_arg = kw_re.match(t_for_args)
        if m_arg:
            arg_text = (m_arg.group(1) or "").strip()
            try:
                if intent_arg == "tony_speak_verbatim":
                    # (31/10) handler tự parse số lần/giọng/nguyên văn từ CÂU ĐẦY ĐỦ
                    return intent_arg, handle_tony_speak_verbatim(t_for_args)
                if intent_arg == "tony_speak":
                    return intent_arg, handle_tony_speak(arg_text)
                if intent_arg == "tony_face":
                    return intent_arg, handle_tony_face(arg_text)
                if intent_arg == "tony_volume":
                    return intent_arg, handle_tony_volume(arg_text)
                if intent_arg == "pc_open":
                    return intent_arg, handle_pc_open(arg_text)
                if intent_arg == "pc_close":
                    return intent_arg, handle_pc_close(arg_text)
                if intent_arg == "tony_youtube":
                    return intent_arg, handle_tony_youtube(arg_text)
                if intent_arg == "tony_websearch":
                    return intent_arg, handle_tony_websearch(arg_text)
                if intent_arg == "tony_music_play":
                    return intent_arg, handle_tony_music_play(arg_text)
                if intent_arg == "tony_show_image":
                    return intent_arg, handle_tony_show_image(arg_text, payload=payload)
                if intent_arg == "tony_pi_photo":
                    return intent_arg, handle_tony_pi_photo(arg_text, payload=payload)
                if intent_arg == "tony_pi_screenshot":
                    return intent_arg, handle_tony_pi_screenshot(arg_text, payload=payload)
                if intent_arg == "tony_pi_video":
                    return intent_arg, handle_tony_pi_video(arg_text, payload=payload)
                if intent_arg == "tony_pi_listen":
                    return intent_arg, handle_tony_pi_listen(arg_text, payload=payload)
                if intent_arg == "relay_on":
                    return intent_arg, handle_relay_on(arg_text, payload=payload)
                if intent_arg == "relay_off":
                    return intent_arg, handle_relay_off(arg_text, payload=payload)
            except Exception as exc:
                return intent_arg, f"⚠️ Lỗi lệnh '{intent_arg}': {type(exc).__name__}: {exc}"

    # 3.5) Khóa máy (không cần đối số)
    if detect_intent(t_for_args) == "pc_lock":
        try:
            return "pc_lock", handle_pc_lock()
        except Exception as exc:
            return "pc_lock", f"⚠️ Lỗi khóa máy: {type(exc).__name__}: {exc}"

    # 4) System commands (trạng thái/báo cáo/nhiệm vụ/tri thức/giúp/phê duyệt/hình thể)
    intent = detect_intent(text)
    if intent is not None:
        handler = HANDLERS.get(intent)
        if handler is None:
            return intent, f"⚠️ Lệnh '{intent}' chưa có handler (lỗi cấu hình)."
        try:
            return intent, handler()
        except Exception as exc:
            return intent, f"⚠️ Lỗi thực thi lệnh '{intent}': {type(exc).__name__}: {exc}"

    return None, ""


def _audit(event_type: str, details: dict[str, Any]) -> None:
    try:
        from quan_ai_brain.core.audit import AuditLogger

        AuditLogger(WORKSPACE).record(event_type, details)
    except Exception:
        pass  # audit phải không bao giờ làm hỏng lệnh chính


# (01/11/2026, owner yêu cầu) CHUẨN HOÁ NGÔN NGỮ DM = TIẾNG VIỆT: mọi trạng thái
# kỹ thuật gửi owner đều dịch sang tiếng Việt (kèm giá trị gốc trong ngoặc khi
# cần tra cứu log). Không dịch tên riêng (Pi 5, Ollama, GLM...).
_VN_STATE_MAP = {
    "READY": "SẴN SÀNG",
    "RUNNING": "ĐANG CHẠY",
    "IDLE": "NGHỈ",
    "SLEEPING": "ĐANG NGỦ",
    "PAUSED": "TẠM DỪNG",
    "STOPPED": "ĐÃ DỪNG",
    "OFFLINE": "MẤT KẾT NỐI",
    "ONLINE": "HOẠT ĐỘNG",
}


def _vn(value: Any, default: str = "không rõ") -> str:
    """Trạng thái kỹ thuật → tiếng Việt (fallback giữ giá trị gốc)."""
    s = str(value or "").strip().upper()
    if not s:
        return default
    return _VN_STATE_MAP.get(s, str(value))


def _vn_bool(v: Any, true_w: str = "rồi", false_w: str = "chưa") -> str:
    return true_w if v else false_w


_ERR_VN_MAP = {
    "timeout": "quá thời gian chờ",
    "timed out": "quá thời gian chờ",
    "connection refused": "từ chối kết nối",
    "connection error": "lỗi kết nối",
    "not found": "không tìm thấy",
    "not running": "chưa chạy",
    "camera busy": "camera đang bận",
    "permission denied": "không có quyền",
    "no such file": "không có file",
    "failed": "thất bại",
    "error": "lỗi",
    "invalid": "không hợp lệ",
    "unsupported": "không được hỗ trợ",
    "busy": "đang bận",
}


def _vn_err(msg: Any, limit: int = 200) -> str:
    """Lỗi kỹ thuật từ server → tiếng Việt dễ hiểu (giữ chi tiết gốc khi lạ)."""
    s = str(msg or "").strip()
    if not s:
        return "không rõ"
    low = s.lower()
    for en, vi in _ERR_VN_MAP.items():
        if en in low:
            return f"{vi} ({s[:limit]})"
    return s[:limit]
