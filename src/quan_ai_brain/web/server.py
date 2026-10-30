"""Lightweight, standard-library HTTP server for QUAN AI BRAIN Local Web UI."""
from __future__ import annotations

import base64
import http.server
import json
import mimetypes
import os
from datetime import datetime, timezone
from pathlib import Path
import socket
import socketserver
import sys
import threading
import time
import urllib.parse
import urllib.request
import webbrowser

from quan_ai_brain.cognition import (
    CapabilityRegistry,
    CognitiveRetriever,
    ExecutivePersona,
    GLOBAL_AUTONOMOUS_MIND,
    MemoryQuery,
    PromptContextBuilder,
)
from quan_ai_brain.cognition.session_memory import SessionMemoryManager
from quan_ai_brain.core.autonomic import GLOBAL_AUTONOMIC_SYSTEM
from quan_ai_brain.core.guardrails import OutputGuardrails
from quan_ai_brain.core.redaction import redact_text
from quan_ai_brain.daemon.health import health_as_dict
from quan_ai_brain.governance.consultation_inbox import (
    ConsultationCategory,
    ConsultationStore,
    ConsultationTicket,
    TicketStatus,
)
from quan_ai_brain.learning.periodic_reporter import PeriodicLearningReporter
from quan_ai_brain.llm import FallbackMode, LLMProvider, LLMRequest
from quan_ai_brain.llm.netmind_provider import NetMindProvider
from quan_ai_brain.llm.router import LLMRouter
from quan_ai_brain.memory.sqlite_store import MemoryStore


def _build_llm_provider(fallback_mode: FallbackMode = FallbackMode.NEVER) -> LLMProvider:
    """LLMProvider with NetMind cloud attached (policy/key gates stay fail-closed
    inside the provider itself — attaching costs nothing when disabled)."""
    return LLMProvider(fallback_mode=fallback_mode, netmind=NetMindProvider())


# Sprint 2: NetMind availability TTL cache (120s — increased from 60s for better performance)
# Optimized 2026-10-25: longer cache reduces GET /models round-trips per chat request.
_NETMIND_AVAIL_CACHE: dict[str, Any] = {"models": None, "expires": 0.0}
_NETMIND_AVAIL_TTL_SECONDS = 120.0


def _netmind_available_models(netmind: NetMindProvider) -> list[str]:
    """Cached catalog read for routing (readiness check included in the TTL)."""
    now = time.time()
    if _NETMIND_AVAIL_CACHE["models"] is not None and now < _NETMIND_AVAIL_CACHE["expires"]:
        return list(_NETMIND_AVAIL_CACHE["models"])
    try:
        if netmind.health(timeout=2.0).get("status") != "READY":
            return []
        names = [m.name for m in netmind.list_models(timeout=3.0)]
    except Exception:
        return []
    _NETMIND_AVAIL_CACHE["models"] = names
    _NETMIND_AVAIL_CACHE["expires"] = now + _NETMIND_AVAIL_TTL_SECONDS
    return names


from quan_ai_brain.cognition.role_orchestrator import (
    ExecutiveRole,
    ExecutiveRoleOrchestrator,
    ROLE_METADATA,
)
from quan_ai_brain.edge.models import (
    DataClassification,
    DeviceIdentity,
    ReleaseManifest,
    TransferChunk,
    TransferDirection,
    TransferManifest,
    TransferStatus,
)
from quan_ai_brain.edge.release_manager import EdgeReleaseManager
from quan_ai_brain.edge.transfer_service import EdgeTransferService
from quan_ai_brain.voice import VoiceState, WakeWordConfig
from quan_ai_brain.voice.mouth_sync import MouthSyncEngine
from quan_ai_brain.voice.tts_config import (
    GLOBAL_TTS_MANAGER,
    TTSStatus,
    normalize_text_for_vietnamese_tts,
)
from quan_ai_brain.media.youtube_music import (
    search_youtube_music,
    looks_like_music_request,
    dispatch_play_music_to_pi5,
    dispatch_stop_music_to_pi5,
)
from quan_ai_brain.voice.voice_pipeline import XiaoZhiVoicePipeline
from quan_ai_brain.web.edge_monitor import (
    EdgeAlertCode,
    EdgeConnectionMonitor,
    EdgeConnectionState,
)

STATIC_DIR = Path(__file__).resolve().parent / "static"
_GLOBAL_WAKE_CONFIG = WakeWordConfig(enabled=False)
_GLOBAL_EDGE_PAIRING_PIN = "888666"
_GLOBAL_PAIRED_EDGE_DEVICES: dict[str, dict[str, Any]] = {}
_GLOBAL_EDGE_MONITOR = EdgeConnectionMonitor(heartbeat_timeout_sec=4.0)
_GLOBAL_MOUTH_SYNC = MouthSyncEngine(frame_interval_ms=50)
_GLOBAL_EDGE_TELEMETRY: dict[str, Any] = {
    "packets_in": 0,
    "packets_out": 0,
    "rtt_history": [11.0, 11.2, 10.8, 11.5, 12.0, 11.0],
    "edge_ip": "192.168.1.21",
    "edge_port": 8768,
    "last_telemetry": {},
    "pending_commands": [],
    "target_avatar_state": "IDLE",
    "transcript": "Chào Anh Quanpt1! Em đang sẵn sàng hỗ trợ.",
    "face_only_mode": False,
}
_GLOBAL_ROLE_ORCHESTRATOR = ExecutiveRoleOrchestrator(edge_telemetry=_GLOBAL_EDGE_TELEMETRY)
_GLOBAL_VOICE_PIPELINE = XiaoZhiVoicePipeline(
    role_orchestrator=_GLOBAL_ROLE_ORCHESTRATOR,
    mouth_sync=_GLOBAL_MOUTH_SYNC,
    wake_config=_GLOBAL_WAKE_CONFIG,
)
_GLOBAL_TRANSFER_SERVICE = EdgeTransferService()
_GLOBAL_RELEASE_MANAGER = EdgeReleaseManager()
_GLOBAL_SUPERVISOR = None


def _get_global_supervisor():
    global _GLOBAL_SUPERVISOR
    if _GLOBAL_SUPERVISOR is None:
        workspace = _find_workspace_root()
        tasks_db = workspace / "data" / "tasks.db"
        gov_db = workspace / "data" / "governance.db"
        from quan_ai_brain.orchestration.task_registry import DurableTaskRegistry
        from quan_ai_brain.governance.state_store import GovernanceStateStore
        from quan_ai_brain.orchestration.supervisor import ContinuousAutonomySupervisor
        registry = DurableTaskRegistry(tasks_db, workspace=workspace)
        gov_store = GovernanceStateStore(gov_db, workspace=workspace)
        _GLOBAL_SUPERVISOR = ContinuousAutonomySupervisor(
            workspace=workspace,
            task_registry=registry,
            governance_store=gov_store,
        )
    return _GLOBAL_SUPERVISOR


def _send_edge_request(path: str, method: str = "GET", data: dict | None = None, timeout: float = 3.0) -> dict:
    """Send an HTTP request to the Raspberry Pi 5 Kiosk Daemon over Wi-Fi with resilient timeout."""
    edge_ip = _GLOBAL_EDGE_TELEMETRY.get("edge_ip", "192.168.1.21")
    edge_port = _GLOBAL_EDGE_TELEMETRY.get("edge_port", 8768)

    # Fast non-blocking pre-check of TCP socket before urllib to prevent Windows 21s SYN stall
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(min(timeout, 1.0))
        res = sock.connect_ex((edge_ip, edge_port))
        sock.close()
        if res != 0:
            return {"success": False, "error": f"Port {edge_port} not reachable", "offline": True}
    except Exception as e:
        return {"success": False, "error": str(e), "offline": True}

    url = f"http://{edge_ip}:{edge_port}{path}"
    try:
        body_bytes = json.dumps(data).encode("utf-8") if data is not None else None
        req = urllib.request.Request(url, data=body_bytes, method=method)
        req.add_header("Content-Type", "application/json")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw)
    except urllib.error.HTTPError as he:
        try:
            raw_err = he.read().decode("utf-8")
            err_data = json.loads(raw_err)
            if isinstance(err_data, dict):
                err_data.setdefault("offline", False)
                return err_data
        except Exception:
            pass
        return {"success": False, "error": f"HTTP {he.code}: {he.reason}", "offline": False}
    except Exception as exc:
        return {"success": False, "error": str(exc), "offline": True}


def get_local_lan_ip() -> str:
    """Detect local Wi-Fi / LAN IP address for Raspberry Pi 5 discovery."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return str(s.getsockname()[0])
    except Exception:
        return "127.0.0.1"


def push_avatar_expression(state: str, transcript: str = "", timeout: float = 1.5) -> bool:
    """Đẩy biểu cảm xuống avatar Pi 5 (kiosk daemon) — đồng bộ biểu cảm khi giao tiếp.

    Owner requirement 27/10: "thay đổi trạng thái biểu cảm khi anh chat, hỏi đáp,
    tùy theo các câu hỏi, hoặc trạng thái trợ lý suy nghĩ... đồng bộ cùng hiển thị
    trên giao diện Pi5".
    Gọi POST /api/kiosk/control {action:"set_expression", state, transcript} trên
    Pi 5 daemon. Fire-and-forget an toàn: mọi lỗi → False, không bao giờ làm chết
    luồng chat. Trạng thái hợp lệ khớp kiosk.js: IDLE/LISTENING/THINKING/SPEAKING/
    RESEARCHING/LEARNING/WAITING/BLOCKED/SAFE/OFFLINE.
    QUAN TRỌNG: cũng cập nhật _GLOBAL_EDGE_TELEMETRY — heartbeat loop của Pi 5
    định kỳ pull target_avatar_state+transcript từ PC; nếu không cập nhật,
    heartbeat sẽ ĐÈ state/transcript cũ ngược lại Pi 5.
    """
    try:
        _GLOBAL_EDGE_TELEMETRY["target_avatar_state"] = state
        if transcript:
            _GLOBAL_EDGE_TELEMETRY["transcript"] = transcript[:300]
        resp = _send_edge_request(
            "/api/kiosk/control",
            method="POST",
            data={"action": "set_expression", "state": state,
                  "transcript": transcript[:300]},
            timeout=timeout,
        )
        return bool(resp.get("success"))
    except Exception:
        return False


def push_avatar_speech(text: str, duration_ms: int | None = None, timeout: float = 3.0, synthesize_tts: bool = True) -> bool:
    """Đẩy lời thoại hiển thị + âm thanh Edge-TTS + biểu cảm SPEAKING xuống Pi 5 (auto-reset IDLE phía daemon).

    Cập nhật cả telemetry transcript/state để heartbeat không đè bằng giá trị cũ.
    Sau duration_ms, PC tự đặt IDLE vào telemetry (daemon tự reset phía Pi).
    """
    try:
        _GLOBAL_EDGE_TELEMETRY["target_avatar_state"] = "SPEAKING"
        _GLOBAL_EDGE_TELEMETRY["transcript"] = text[:300]

        audio_b64 = None
        if synthesize_tts and text:
            try:
                import base64
                clean_speech = re.sub(r"[\*#_`]", "", text[:300]).strip()
                audio_bytes, _ = GLOBAL_TTS_MANAGER.synthesize_audio(clean_speech, voice_id="vi-VN-HoaiMyNeural")
                if audio_bytes:
                    audio_b64 = base64.b64encode(audio_bytes).decode("ascii")
            except Exception:
                pass

        def _reset_after_speech() -> None:
            import time as _time

            _time.sleep(max(1.0, (duration_ms or 3000) / 1000.0))
            if _GLOBAL_EDGE_TELEMETRY.get("target_avatar_state") == "SPEAKING":
                _GLOBAL_EDGE_TELEMETRY["target_avatar_state"] = "IDLE"

        import threading as _threading

        _threading.Thread(target=_reset_after_speech, daemon=True).start()

        data: dict[str, Any] = {
            "action": "speak",
            "text": text[:600],
            "state": "SPEAKING",
            "force_hardware": True,
        }
        if audio_b64:
            data["audio_base64"] = audio_b64
        if duration_ms:
            data["duration_ms"] = int(duration_ms)
        resp = _send_edge_request(
            "/api/kiosk/control", method="POST", data=data, timeout=timeout,
        )
        return bool(resp.get("success"))
    except Exception:
        return False


def push_avatar_thinking(context_note: str = "") -> None:
    """Đặt THINKING ngay khi nhận câu hỏi; kèm transcript ngắn gọn ngữ cảnh."""
    push_avatar_expression("THINKING", transcript=context_note or "Đang suy nghĩ...")


def _find_workspace_root() -> Path:
    # V6 hotfix (27/10/2026): env override cho test isolation — không cho
    # test suite ghi task thật vào data/tasks.db của production (nguồn gốc
    # 294 task trùng lặp 'năng lượng' — daemon chạy pytest mỗi cycle).
    override = os.environ.get("QUAN_AI_BRAIN_WORKSPACE", "").strip()
    if override:
        candidate = Path(override).resolve()
        if candidate.exists():
            return candidate
    current = Path.cwd().resolve()
    if (current / "src" / "quan_ai_brain").exists():
        return current
    anchor = Path(__file__).resolve().parents[3]
    if (anchor / "src" / "quan_ai_brain").exists():
        return anchor
    return current


def _table_has(con, column: str) -> bool:
    """Sprint 9 (A): kiểm cột tồn tại trong bảng đầu tiên của schema — dùng cho
    đếm thô an toàn (DB cũ thiếu cột thì bỏ qua chứ không chết)."""
    try:
        row = con.execute("SELECT name FROM sqlite_master WHERE type='table' LIMIT 1").fetchone()
        if not row:
            return False
        cols = [r[1] for r in con.execute(f"PRAGMA table_info({row[0]})").fetchall()]
        return column in cols
    except Exception:
        return False


class BrainAPIHandler(http.server.BaseHTTPRequestHandler):
    """Handles static files and JSON REST API for QUAN AI BRAIN."""

    server_version = "QuanAIBrainWeb/1.0"

    def log_message(self, format: str, *args: object) -> None:
        # Keep console output clean
        try:
            if sys.stdout:
                sys.stdout.write(f"[{time.strftime('%H:%M:%S')}] {self.address_string()} - {format % args}\n")
                sys.stdout.flush()
        except Exception:
            pass

    def _send_json(self, data: object, status: int = 200) -> None:
        payload = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(payload)

    def _send_error_json(self, message: str, status: int = 400) -> None:
        self._send_json({"error": message, "success": False}, status=status)

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        port = self.server.server_address[1] if hasattr(self.server, "server_address") else 8765

        if path in ("/", "/index.html"):
            if port == 8766:
                self._serve_file(STATIC_DIR / "executive.html")
            else:
                self._serve_file(STATIC_DIR / "index.html")
            return

        if path in ("/executive", "/executive.html"):
            self._serve_file(STATIC_DIR / "executive.html")
            return

        if path.startswith("/static/"):
            rel = path[len("/static/"):]
            target = (STATIC_DIR / rel).resolve()
            if not str(target).startswith(str(STATIC_DIR.resolve())):
                self.send_error(403, "Forbidden")
                return
            self._serve_file(target)
            return

        if path == "/api/status":
            self._handle_api_status()
            return

        if path == "/api/health":
            self._handle_api_health()
            return

        if path == "/api/memories":
            self._handle_api_list_memories()
            return

        if path == "/api/executive/overview":
            self._handle_api_executive_overview()
            return

        if path == "/api/executive/netchat/status":
            self._handle_api_executive_netchat_status()
            return

        if path == "/api/executive/netchat/messages":
            self._handle_api_executive_netchat_messages(parsed.query)
            return

        if path == "/api/executive/persona":
            self._handle_api_executive_persona()
            return

        if path == "/api/executive/capabilities":
            self._handle_api_executive_capabilities()
            return

        # V6: Skill Registry — read-only listing (GET)
        if path == "/api/skills":
            self._handle_api_skills()
            return

        if path == "/api/executive/consultations":
            self._handle_api_executive_consultations(parsed.query)
            return

        if path == "/api/executive/learning/reports":
            self._handle_api_executive_learning_reports()
            return

        if path == "/api/executive/tasks":
            self._handle_api_executive_tasks()
            return

        if path == "/api/executive/tasks/detail":
            self._handle_api_executive_task_detail(parsed.query)
            return

        # Sprint 15 (b): evidence traceability — cognitive state của task (GET, read-only)
        if path == "/api/executive/tasks/cognitive-state":
            self._handle_api_task_cognitive_state(parsed.query)
            return
        
        # CLO V1: Continuous Learning API endpoints
        if path == "/api/learning/status":
            self._handle_api_learning_status()
            return
        elif path == "/api/learning/start":
            self._handle_api_learning_start(parsed.query)
            return
        elif path == "/api/learning/stop":
            self._handle_api_learning_stop(parsed.query)
            return
        elif path == "/api/learning/pause":
            self._handle_api_learning_pause(parsed.query)
            return
        elif path == "/api/learning/resume":
            self._handle_api_learning_resume()
            return

        # Sprint 15 (d): session coordination — detect duplicate goals (GET, read-only)
        if path == "/api/executive/tasks/duplicates":
            self._handle_api_executive_task_duplicates()
            return

        if path == "/api/executive/supervisor":
            self._handle_api_executive_supervisor()
            return

        if path == "/api/executive/edge/alerts":
            self._handle_api_edge_alerts()
            return

        if path == "/api/executive/edge/status":
            self._handle_api_edge_status()
            return

        if path == "/api/executive/edge/telemetry":
            self._handle_api_edge_telemetry()
            return

        if path == "/api/executive/edge/files":
            self._handle_api_edge_list_files()
            return

        if path == "/api/executive/edge/audio/status":
            self._handle_api_edge_audio_status()
            return

        if path == "/api/executive/edge/camera/status":
            self._handle_api_edge_camera_status()
            return

        if path == "/api/executive/edge/camera/snapshot":
            self._handle_api_edge_camera_snapshot()
            return

        if path == "/api/executive/edge/camera/stream":
            self._handle_api_edge_camera_stream()
            return

        if path == "/api/executive/edge/camera/library":
            self._handle_api_edge_camera_library(parsed.query)
            return

        if path == "/api/executive/edge/camera/image":
            self._handle_api_edge_camera_serve_image(parsed.query)
            return

        if path == "/api/executive/roles":
            self._handle_api_executive_roles()
            return

        if path == "/api/executive/edge/transfer/status":
            self._handle_api_edge_transfer_status(parsed.query)
            return

        if path == "/api/executive/edge/transfer/history":
            self._handle_api_edge_transfer_history(parsed.query)
            return

        if path == "/api/executive/edge/release/list":
            self._handle_api_edge_release_list()
            return

        if path == "/api/voice/wake-config":
            self._handle_api_voice_get_config()
            return

        if path == "/api/voice/tts-config":
            self._handle_api_voice_get_tts_config()
            return

        if path == "/api/voice/tts-voices":
            self._handle_api_voice_get_tts_voices()
            return

        if path == "/api/chat/history":
            self._handle_api_chat_history(parsed.query)
            return

        if path == "/api/autonomic/status":
            self._handle_api_autonomic_status()
            return

        if path == "/api/mind/state":
            self._handle_api_mind_state()
            return

        if path == "/api/mind/thoughts":
            self._handle_api_mind_thoughts(parsed.query)
            return

        if path == "/api/supervisor/state":
            self._handle_api_supervisor_state()
            return

        # Sprint 8 (c): Approval Center — danh sách cards đọc-only
        if path == "/api/approvals":
            self._handle_api_approvals_list()
            return

        # Sprint 8 (a): To-do — danh sách việc cần làm (đọc-only)
        if path == "/api/todos":
            self._handle_api_todos_list()
            return

        if path == "/api/music/status":
            self._handle_api_music_status()
            return

        # Sprint 9 (A): Workbench overview — tổng hợp thật, fail-honest
        if path == "/api/workbench/overview":
            self._handle_api_workbench_overview()
            return

        # Sprint 9 (B): danh sách nhiệm vụ thật + filter ?status=&limit=
        if path == "/api/workbench/tasks":
            self._handle_api_workbench_tasks(parsed.query)
            return

        # Sprint 9 (C): email intake — list + sync (mock connector; Vmail BLOCKED)
        if path == "/api/email/intake":
            self._handle_api_email_intake_list(parsed.query)
            return

        # Sprint 10 (c): email intelligence — đề xuất xử lý email (GET, đọc-only)
        if path == "/api/email/proposals":
            self._handle_api_email_proposals_list(parsed.query)
            return

        # Sprint 11 (b): experience lessons — list (GET, đọc-only)
        if path == "/api/experience/lessons":
            self._handle_api_experience_lessons_list(parsed.query)
            return

        # Sprint 12 (b): web read-only — search/page/rss (GET, localhost-only)
        if path == "/api/web/search":
            self._handle_api_web_search(parsed.query)
            return

        if path == "/api/web/page":
            self._handle_api_web_page(parsed.query)
            return

        if path == "/api/web/rss":
            self._handle_api_web_rss(parsed.query)
            return

        # Sprint 13 (b): improvement report (GET, localhost-only)
        if path == "/api/improvement/report":
            self._handle_api_improvement_report(parsed.query)
            return

        # Sprint 14 (c): semantic search kinh nghiệm (GET, localhost-only, read-only)
        if path == "/api/experience/search":
            self._handle_api_experience_search(parsed.query)
            return

        if path.startswith("/edge_client/"):
            workspace = _find_workspace_root()
            rel = path.lstrip("/").replace("edge_client/", "")
            target = (workspace / "edge_client" / rel).resolve()
            base = (workspace / "edge_client").resolve()
            try:
                target.relative_to(base)
                if target.exists() and target.is_file():
                    self._serve_file(target)
                    return
            except ValueError:
                pass

        # Fallback to static file if exists
        target = STATIC_DIR / path.lstrip("/")
        if target.exists() and target.is_file():
            self._serve_file(target)
            return

        self.send_error(404, "Not Found")

    def do_POST(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        content_length = int(self.headers.get("Content-Length", 0))
        if content_length > 10_000_000:
            self._send_error_json("Payload too large", 413)
            return

        body_raw = self.rfile.read(content_length).decode("utf-8", errors="replace")
        try:
            body = json.loads(body_raw) if body_raw else {}
        except json.JSONDecodeError:
            self._send_error_json("Invalid JSON body", 400)
            return

        if path == "/api/chat":
            self._handle_api_chat(body)
            return

        if path == "/api/chat/stream":
            self._handle_api_chat_stream(body)
            return

        if path == "/api/memories":
            self._handle_api_add_memory(body)
            return

        if path == "/api/plan":
            self._handle_api_plan(body)
            return

        if path == "/api/learning":
            self._handle_api_learning(body)
            return

        if path == "/api/executive/persona":
            self._handle_api_executive_persona_update(body)
            return

        if path == "/api/executive/netchat/send":
            self._handle_api_executive_netchat_send(body)
            return

        if path == "/api/executive/netchat/command":
            self._handle_api_executive_netchat_command(body)
            return

        if path == "/api/executive/consultations/respond":
            self._handle_api_executive_consultation_respond(body)
            return

        if path == "/api/executive/consultations/create":
            self._handle_api_executive_consultation_create(body)
            return

        if path == "/api/executive/learning/trigger":
            self._handle_api_executive_learning_trigger(body)
            return

        if path == "/api/executive/tasks/create":
            self._handle_api_executive_task_create(body)
            return

        if path == "/api/executive/tasks/execute":
            self._handle_api_executive_task_execute(body)
            return

        if path == "/api/executive/tasks/cancel":
            self._handle_api_executive_task_cancel(body)
            return

        # Sprint 8 (a): To-do — thêm / hoàn thành việc
        if path == "/api/todos/add":
            self._handle_api_todos_add(body)
            return

        if path == "/api/todos/done":
            self._handle_api_todos_done(body)
            return

        # Sprint 8 (c): Approval Center — duyệt/từ chối card (localhost-only)
        if path == "/api/approvals/decide":
            self._handle_api_approvals_decide(body)
            return

        # Sprint 11 (b): experience memory — consolidate + promote (POST, localhost-only)
        if path == "/api/experience/consolidate":
            self._handle_api_experience_consolidate(body)
            return

        if path == "/api/experience/lessons/promote":
            self._handle_api_experience_lessons_promote(body)
            return

        # Sprint 13 (b): xuất báo cáo tự đánh giá .md (POST — R2, owner bấm)
        if path == "/api/improvement/export":
            self._handle_api_improvement_export(body)
            return

        # Sprint 10 (c): email intelligence — tạo nhiệm vụ ứng viên (POST)
        if path == "/api/email/task/create":
            self._handle_api_email_task_create(body)
            return

        # Sprint 9 (C): email intake sync (mock connector; Vmail BLOCKED giữ nguyên)
        if path == "/api/email/intake/sync":
            self._handle_api_email_intake_sync(body)
            return

        if path == "/api/executive/emergency":
            self._handle_api_executive_emergency(body)
            return

        if path == "/api/voice/wake-config":
            self._handle_api_voice_set_config(body)
            return

        if path == "/api/voice/tts-config":
            self._handle_api_voice_set_tts_config(body)
            return

        if path == "/api/voice/tts-synthesize":
            self._handle_api_voice_tts_synthesize(body)
            return

        if path == "/api/voice/telemetry":
            self._handle_api_voice_telemetry(body)
            return

        if path == "/api/autonomic/selftest":
            self._handle_api_autonomic_selftest(body)
            return

        if path == "/api/autonomic/vocalize":
            self._handle_api_autonomic_vocalize(body)
            return

        if path == "/api/mind/cogitate":
            self._handle_api_mind_cogitate(body)
            return

        if path == "/api/supervisor/tick":
            self._handle_api_supervisor_tick(body)
            return

        if path == "/api/edge/pair":
            self._handle_api_edge_pair(body)
            return

        if path == "/api/executive/edge/heartbeat":
            self._handle_api_edge_heartbeat(body)
            return

        # V41: Edge Agent gửi events tự thu thập lên Brain
        if path == "/api/executive/edge/events":
            self._handle_api_edge_events(body)
            return

        if path == "/api/executive/edge/mouth-sync":
            self._handle_api_edge_mouth_sync(body)
            return

        if path == "/api/executive/edge/control":
            self._handle_api_edge_control(body)
            return

        if path == "/api/executive/edge/startup-sequence":
            self._handle_api_edge_startup_sequence(body)
            return

        if path == "/api/executive/edge/files/upload":
            self._handle_api_edge_upload_file(body)
            return

        if path == "/api/executive/edge/files/sync-all":
            self._handle_api_edge_sync_all_assets()
            return

        if path == "/api/executive/edge/files/delete":
            self._handle_api_edge_delete_file(body)
            return

        if path == "/api/executive/edge/action":
            self._handle_api_edge_remote_action(body)
            return

        if path == "/api/executive/edge/audio/control":
            self._handle_api_edge_audio_control(body)
            return

        if path == "/api/executive/edge/camera/control":
            self._handle_api_edge_camera_control(body)
            return

        if path == "/api/executive/edge/camera/save":
            self._handle_api_edge_camera_save(body)
            return

        if path == "/api/executive/edge/camera/delete":
            self._handle_api_edge_camera_delete(body)
            return

        if path == "/api/voice/interact":
            self._handle_api_voice_interact(body)
            return

        if path == "/api/voice/barge-in":
            self._handle_api_voice_barge_in(body)
            return

        if path == "/api/executive/edge/transfer/initiate":
            self._handle_api_edge_transfer_initiate(body)
            return

        if path == "/api/executive/edge/transfer/chunk":
            self._handle_api_edge_transfer_chunk(body)
            return

        if path == "/api/executive/edge/transfer/ack":
            self._handle_api_edge_transfer_ack(body)
            return

        if path == "/api/executive/edge/release/create":
            self._handle_api_edge_release_create(body)
            return

        if path == "/api/executive/edge/release/stage":
            self._handle_api_edge_release_stage(body)
            return

        if path == "/api/executive/edge/release/activate":
            self._handle_api_edge_release_activate(body)
            return

        if path == "/api/executive/edge/release/rollback":
            self._handle_api_edge_release_rollback(body)
            return

        if path == "/api/music/search":
            self._handle_api_music_search(body)
            return

        if path == "/api/music/play":
            self._handle_api_music_play(body)
            return

        if path == "/api/music/stop":
            self._handle_api_music_stop()
            return

        self.send_error(404, "Endpoint not found")

    def _serve_file(self, file_path: Path) -> None:
        if not file_path.exists() or not file_path.is_file():
            self.send_error(404, "File not found")
            return

        mime_type, _ = mimetypes.guess_type(str(file_path))
        if not mime_type:
            mime_type = "application/octet-stream"

        try:
            with open(file_path, "rb") as f:
                content = f.read()
        except OSError as exc:
            self.send_error(500, f"Failed to read file: {exc}")
            return

        self.send_response(200)
        self.send_header("Content-Type", f"{mime_type}; charset=utf-8" if "text" in mime_type or "json" in mime_type or "javascript" in mime_type else mime_type)
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.end_headers()
        self.wfile.write(content)

    def _handle_api_health(self) -> None:
        """Sprint A-fix (GAP-R4): canonical health endpoint per Digital
        Employee Brain design — every component reports evidence-based state
        from live probes, never from configuration presence."""
        components: list[dict[str, object]] = []
        now_utc = datetime.now(timezone.utc).isoformat()

        def _add(component_id: str, observed: object, status: str, source: str,
                 evidence_ref: str, verification: str = "VERIFIED_LIVE") -> None:
            components.append({
                "component_id": component_id,
                "observed_value": observed,
                "status": status,
                "observed_at": now_utc,
                "source": source,
                "evidence_ref": evidence_ref,
                "verification_status": verification,
                "last_verified_at": now_utc,
            })

        # 1. HTTP server itself (we are serving this request => HEALTHY)
        _add("core_server", True, "HEALTHY", "http_handler",
             f"http_request:{self.path}")

        # 2. Ollama daemon — live TCP probe, UNKNOWN on probe infrastructure error
        ollama_alive = False
        probe_error: str | None = None
        try:
            ollama_alive = socket.create_connection(("127.0.0.1", 11434), timeout=1.5) is not None
        except Exception as exc:
            probe_error = type(exc).__name__
        _add("ollama_daemon", ollama_alive,
             "HEALTHY" if ollama_alive else "OFFLINE",
             "tcp_probe:127.0.0.1:11434",
             f"tcp_probe_result:{ollama_alive}" + (f":{probe_error}" if probe_error else ""))

        # 3. brain.db — real row counts, not configuration claims
        try:
            workspace = _find_workspace_root()
            db_path = workspace / "data" / "brain.db"
            import sqlite3 as _sq
            if db_path.exists():
                conn = _sq.connect(str(db_path))
                try:
                    episodes = conn.execute("SELECT COUNT(*) FROM episodes").fetchone()[0]
                    semantic = conn.execute("SELECT COUNT(*) FROM semantic_memory").fetchone()[0]
                finally:
                    conn.close()
                _add("brain_db", {"episodes": episodes, "semantic_memory": semantic},
                     "HEALTHY", "sqlite:data/brain.db", f"row_counts:{episodes}/{semantic}")
            else:
                _add("brain_db", None, "OFFLINE", "sqlite:data/brain.db", "db_file_missing")
        except Exception as exc:
            _add("brain_db", None, "UNKNOWN", "sqlite:data/brain.db",
                 f"probe_error:{type(exc).__name__}")

        # 4. Task registry backlog — real PENDING count from tasks.db
        try:
            workspace = _find_workspace_root()
            tasks_db = workspace / "data" / "tasks.db"
            import sqlite3 as _sq
            if tasks_db.exists():
                conn = _sq.connect(str(tasks_db))
                try:
                    pending = conn.execute(
                        "SELECT COUNT(*) FROM durable_tasks WHERE status='PENDING'"
                    ).fetchone()[0]
                finally:
                    conn.close()
                _add("task_registry", {"pending": pending},
                     "HEALTHY" if pending < 500 else "DEGRADED",
                     "sqlite:data/tasks.db", f"pending_count:{pending}")
            else:
                _add("task_registry", None, "OFFLINE", "sqlite:data/tasks.db", "db_file_missing")
        except Exception as exc:
            _add("task_registry", None, "UNKNOWN", "sqlite:data/tasks.db",
                 f"probe_error:{type(exc).__name__}")

        overall = "HEALTHY" if all(
            c["status"] in ("HEALTHY",) for c in components
        ) else "DEGRADED"
        self._send_json({
            "success": True,
            "overall_status": overall,
            "components": components,
        })

    def _handle_api_status(self) -> None:
        try:
            provider = _build_llm_provider()  # gắn NetMind cloud — health phải phản ánh đúng
            health = provider.health()
        except Exception as exc:
            health = {"ollama_online": False, "error": str(exc)}

        health["reachable"] = bool(health.get("ollama_online"))
        health["model"] = health.get("default_model", "qwen2.5:7b")
        # Model THẬT đang phục vụ chat: NetMind cloud nếu READY, không thì local/mock.
        # UI dùng trường này để hiển thị trung thực (tránh claim "local" sai).
        netmind_state = (health.get("netmind") or {}).get("status", "")
        if netmind_state == "READY":
            health["active_model"] = "zai-org/GLM-5.3-Flash"
            health["active_provider_label"] = "NetMind Cloud (GLM-5.3-Flash)"
        elif health.get("ollama_online"):
            health["active_model"] = health.get("default_model", "qwen2.5:7b")
            health["active_provider_label"] = f"Ollama local ({health['active_model']})"
        else:
            health["active_model"] = "mock"
            health["active_provider_label"] = "MOCK (không có provider thật — trả lời mẫu)"

        mem_count = 0
        try:
            workspace = _find_workspace_root()
            db_path = workspace / "data" / "brain.db"
            if db_path.exists():
                with MemoryStore(db_path, workspace=workspace) as store:
                    mem_count = len(store.list_episodes(limit=500))
        except Exception:
            pass

        sys_health = health_as_dict()
        self._send_json({
            "success": True,
            "llm": health,
            "system": sys_health,
            "memories": {"count": mem_count},
        })

    def _handle_api_list_memories(self) -> None:
        workspace = _find_workspace_root()
        db_path = workspace / "data" / "brain.db"
        try:
            with MemoryStore(db_path, workspace=workspace) as store:
                episodes = store.list_episodes(limit=100)
            self._send_json({"success": True, "memories": episodes})
        except Exception as exc:
            self._send_error_json(f"Database error: {exc}", 500)

    def _handle_api_add_memory(self, body: dict) -> None:
        summary = str(body.get("summary", "")).strip()
        if not summary:
            self._send_error_json("Summary is required", 400)
            return

        kind = str(body.get("kind", "user_note")).strip()
        workspace = _find_workspace_root()
        db_path = workspace / "data" / "brain.db"
        try:
            with MemoryStore(db_path, workspace=workspace) as store:
                record_id = store.add_episode(
                    summary=summary,
                    kind=kind,
                    source_ref="web_ui",
                    metadata={"client": "web_chat_ui"},
                )
            self._send_json({"success": True, "record_id": record_id})
        except Exception as exc:
            self._send_error_json(f"Failed to record memory: {exc}", 500)

    def _handle_api_chat_history(self, query_str: str) -> None:
        params = urllib.parse.parse_qs(query_str)
        session_id = params.get("session_id", ["default_executive_session"])[0]
        limit = int(params.get("limit", [10])[0])
        workspace = _find_workspace_root()
        db_path = workspace / "data" / "brain.db"
        try:
            with MemoryStore(db_path, workspace=workspace) as store:
                session_mgr = SessionMemoryManager(store)
                history = session_mgr.get_recent_session_history(session_id, limit=limit)
            self._send_json({"success": True, "session_id": session_id, "history": history})
        except Exception as exc:
            self._send_error_json(f"Error fetching session history: {exc}", 500)

    def _handle_api_autonomic_status(self) -> None:
        """Return the latest autonomic health report, active pains, and hardware organ audits."""
        try:
            report = GLOBAL_AUTONOMIC_SYSTEM.get_last_report()
            self._send_json({"success": True, "report": report.to_dict()})
        except Exception as exc:
            self._send_error_json(f"Failed to fetch autonomic status: {exc}", 500)

    def _handle_api_autonomic_selftest(self, body: dict) -> None:
        """Trigger an on-demand self-test across all organ systems and return results."""
        try:
            report = GLOBAL_AUTONOMIC_SYSTEM.run_self_test()
            vocalize = bool(body.get("vocalize", False))
            if vocalize and report.vocal_summary:
                _GLOBAL_EDGE_TELEMETRY["transcript"] = report.vocal_summary
                target_state = "IDLE" if report.is_healthy else "THINKING"
                _GLOBAL_EDGE_TELEMETRY["target_avatar_state"] = target_state
            self._send_json({"success": True, "report": report.to_dict()})
        except Exception as exc:
            self._send_error_json(f"Failed to execute self-test: {exc}", 500)

    def _handle_api_autonomic_vocalize(self, body: dict) -> None:
        """Trigger the assistant to vocalize its current health or pain condition."""
        try:
            report = GLOBAL_AUTONOMIC_SYSTEM.get_last_report()
            speech_text = report.vocal_summary
            _GLOBAL_EDGE_TELEMETRY["transcript"] = speech_text
            _GLOBAL_EDGE_TELEMETRY["target_avatar_state"] = "SPEAKING" if not report.is_healthy else "HAPPY"
            try:
                _send_edge_request("/api/avatar/action", method="POST", data={
                    "action": "speak",
                    "text": speech_text,
                    "expression": "sad" if not report.is_healthy else "happy",
                }, timeout=1.0)
            except Exception:
                pass
            self._send_json({
                "success": True,
                "vocal_text": speech_text,
                "pain_level": report.overall_pain_level.value,
                "health_score": report.health_score,
            })
        except Exception as exc:
            self._send_error_json(f"Failed to vocalize pain: {exc}", 500)

    def _handle_api_mind_state(self) -> None:
        """Return the current autonomous mind state and mental focus."""
        try:
            state = GLOBAL_AUTONOMOUS_MIND.get_state()
            self._send_json({"success": True, "state": state})
        except Exception as exc:
            self._send_error_json(f"Failed to fetch mind state: {exc}", 500)

    def _handle_api_mind_thoughts(self, query_str: str) -> None:
        """Return the stream of consciousness / internal thoughts."""
        try:
            params = urllib.parse.parse_qs(query_str)
            limit = int(params.get("limit", [10])[0])
            thoughts = GLOBAL_AUTONOMOUS_MIND.get_recent_thoughts(limit=limit)
            self._send_json({"success": True, "thoughts": thoughts})
        except Exception as exc:
            self._send_error_json(f"Failed to fetch thoughts: {exc}", 500)

    def _handle_api_mind_cogitate(self, body: dict) -> None:
        """Execute one cycle of autonomous thinking on demand."""
        try:
            trigger = str(body.get("trigger", "IDLE_REFLECTION"))
            topic = str(body.get("topic", "")).strip() or None
            notes = str(body.get("notes", "")).strip()
            thought = GLOBAL_AUTONOMOUS_MIND.cogitate(
                trigger=trigger,
                topic_override=topic,
                context_notes=notes,
            )
            _GLOBAL_EDGE_TELEMETRY["target_avatar_state"] = "THINKING"
            self._send_json({"success": True, "thought": thought.to_dict()})
        except Exception as exc:
            self._send_error_json(f"Failed to execute cogitation: {exc}", 500)

    def _handle_api_chat(self, body: dict) -> None:
        query = str(body.get("query") or body.get("message", "")).strip()
        if not query:
            self._send_error_json("Query cannot be empty", 400)
            return

        session_id = str(body.get("session_id", "default_executive_session")).strip() or "default_executive_session"
        allow_fallback = bool(body.get("fallback", False))
        scope = body.get("scope") or None
        timeout = float(body.get("timeout", 120.0))
        explicit_model = str(body.get("model", "")).strip() or None

        workspace = _find_workspace_root()
        db_path = workspace / "data" / "brain.db"

        start_time = time.perf_counter()
        try:
            # 1. Routing Model — include NetMind cloud models when the gateway is READY
            # (policy allowed + key present + catalog reachable); router then prefers
            # GLM-5.3-Flash and falls back to local models only if the cloud is absent.
            router = LLMRouter()
            mode = FallbackMode.ON_ERROR if allow_fallback else FallbackMode.NEVER
            provider = _build_llm_provider(mode)
            avail_models: list[str] = []
            if provider.netmind is not None:
                try:
                    avail_models.extend(_netmind_available_models(provider.netmind))
                except Exception:
                    pass
            if provider.is_online(timeout=1.0):
                try:
                    avail_models = [m.name for m in provider.list_models(allow_fallback=True)] + avail_models
                except Exception:
                    avail_models = []

            decision = router.route(
                query,
                task_hint="chat",
                explicit_model=explicit_model,
                available_models=avail_models,
            )
            selected_model = decision.model

            # 2.0 Owner teach detection — "anh đào tạo, em nhớ" persists FIRST
            teach_note: str | None = None
            try:
                from quan_ai_brain.core.audit import AuditLogger
                from quan_ai_brain.cognition.teach_pipeline import detect_teaching, persist_taught_memory

                def _audit(event: str, details: dict[str, Any]) -> None:
                    try:
                        AuditLogger(workspace).record(event, details)
                    except Exception:
                        pass

                with MemoryStore(db_path, workspace=workspace) as t_store:
                    teach = detect_teaching(query)
                    if teach.is_teaching:
                        saved = persist_taught_memory(
                            t_store, teach.content, teach.memory_type, session_id=session_id,
                        )
                        teach_note = (
                            f"✅ Em đã NHỚ vào trí nhớ dài hạn (ID {saved['id']}, loại {saved['memory_type']}, "
                            f"nguồn: chủ sở hữu dạy trực tiếp). Nội dung: \"{teach.content[:200]}\""
                        )
                        _audit("owner_teach.persisted", {"memory_id": saved["id"], "type": saved["memory_type"], "chars": len(teach.content)})
            except Exception as teach_exc:
                try:
                    AuditLogger(workspace).record("owner_teach.error", {"error": str(teach_exc)[:200]})
                except Exception:
                    pass

            # 2. Memory Retrieval & Session History
            with MemoryStore(db_path, workspace=workspace) as store:
                session_mgr = SessionMemoryManager(store)
                recent_history = session_mgr.get_recent_session_history(session_id, limit=3)

                retriever = CognitiveRetriever(store)
                m_query = MemoryQuery(
                    query=query,
                    project_scope=scope,
                    top_k=5,
                    max_chars=6000,
                )
                retrieval = retriever.retrieve(m_query)
                builder = PromptContextBuilder(default_max_chars=6000)
                context = builder.build(
                    user_query=query,
                    retrieval=retrieval,
                    max_chars=6000,
                    project_scope=scope,
                    conversation_history=recent_history,
                )

            # 2.5 Living Grounding Facts — probe thật, ép bot nói đúng về bản thân
            try:
                from quan_ai_brain.cognition.grounding_facts import collect_grounding_facts, render_grounding_block

                grounding_block = render_grounding_block(collect_grounding_facts(current_model=selected_model))
                context.system_instructions = grounding_block + "\n\n" + context.system_instructions
            except Exception as ground_exc:
                _audit("grounding_facts.error", {"error": str(ground_exc)[:200]})

            # 2.55 Avatar: THINKING ngay khi nhận câu hỏi (trước tra cứu — owner thấy
            # phản ứng tức thì), rồi RESEARCHING nếu có tra cứu ngoài.
            try:
                push_avatar_thinking()
            except Exception:
                pass

            # 2.6 External lookup evidence — câu hỏi tin tức/tra cứu ngoài → tự tra cứu
            # (Gemini search → Google News RSS + Gemini tổng hợp). Fail-closed, chỉ
            # kích hoạt với câu hỏi thời sự (should_lookup_external); key chỉ đọc env.
            ext_lookup_info: dict[str, Any] = {"attempted": False}
            try:
                from quan_ai_brain.tools.external_lookup import (
                    collect_external_evidence,
                    should_lookup_external,
                )

                if should_lookup_external(query):
                    ext_lookup_info["attempted"] = True
                    _GLOBAL_EDGE_TELEMETRY["target_avatar_state"] = "RESEARCHING"
                    push_avatar_expression("RESEARCHING",
                                           transcript="Đang tra cứu thông tin ngoài...")
                    _ev = collect_external_evidence(query, timeout=20.0)
                    _ev_block = _ev.render_block()
                    ext_lookup_info.update({
                        "layer": _ev.source_layer, "sources": len(_ev.sources),
                        "summary": bool(_ev.summary), "block_len": len(_ev_block),
                        "note": _ev.note[:120],
                    })
                    if _ev_block:
                        context.system_instructions = context.system_instructions + "\n" + _ev_block
            except Exception as _ev_exc:
                ext_lookup_info["error"] = str(_ev_exc)[:160]

            # 2.7 TTNS lookup (Sprint 6-GOP mục 4) — câu hỏi nhân sự/lịch họp nội bộ
            # → bọc skill ttns-meeting-lookup (read-only), đưa kết quả vào context.
            # Fail-closed: lỗi → không evidence, chat vẫn chạy; KHÔNG cache DB.
            ttns_info: dict[str, Any] = {"attempted": False}
            try:
                from quan_ai_brain.tools.ttns_lookup import (
                    looks_like_ttns_query,
                    ttns_lookup,
                )

                if looks_like_ttns_query(query):
                    ttns_info["attempted"] = True
                    _ttns = ttns_lookup(query)
                    if _ttns and _ttns.get("answer"):
                        ttns_info["answer_len"] = len(_ttns["answer"])
                        _ttns_block = (
                            "[EVIDENCE TTNS NỘI BỘ — nguồn tra cứu chính thức công ty, "
                            "CHỈ TRA CỨU. Dùng thông tin này để trả lời; nếu không đủ, "
                            "nói thiếu]\n" + _ttns["answer"][:6000]
                        )
                        context.system_instructions = (
                            context.system_instructions + "\n" + _ttns_block
                        )
                    else:
                        ttns_info["note"] = "lookup trả rỗng/lỗi — fail-closed"
            except Exception as _ttns_exc:
                ttns_info["error"] = str(_ttns_exc)[:160]

            # 2.8 Document RAG evidence (Sprint 6-GOP mục 1) — câu hỏi về quy trình/
            # sổ tay nội bộ → retrieve từ kho tài liệu (index riêng), đưa bằng chứng
            # có citation vào context. Fail-closed: lỗi/không đủ → không evidence.
            doc_rag_info: dict[str, Any] = {"attempted": False}
            try:
                from quan_ai_brain.cognition.document_rag import DocumentRAG

                _rag = DocumentRAG(workspace=str(workspace))
                if _rag.count_chunks() > 0:
                    _rr = _rag.retrieve(query)
                    doc_rag_info["attempted"] = True
                    if _rr.has_evidence:
                        doc_rag_info["chunks"] = len(_rr.chunks)
                        doc_rag_info["best_score"] = _rr.chunks[0].score
                        _rag_block = _rr.render_evidence_block()
                        context.system_instructions = (
                            context.system_instructions + "\n" + _rag_block
                        )
                    else:
                        doc_rag_info["note"] = "không tìm thấy bằng chứng đủ tốt"
            except Exception as _rag_exc:
                doc_rag_info["error"] = str(_rag_exc)[:160]

            # 2.85 YouTube Music detection & Pi 5 streaming dispatch
            music_info: dict[str, Any] = {"requested": False}
            try:
                is_music, song_target = looks_like_music_request(query)
                if is_music:
                    music_info["requested"] = True
                    edge_ip = _GLOBAL_EDGE_TELEMETRY.get("edge_ip", "192.168.1.21")
                    edge_port = _GLOBAL_EDGE_TELEMETRY.get("edge_port", 8768)
                    if song_target == "STOP":
                        dispatch_stop_music_to_pi5(edge_ip=edge_ip, edge_port=edge_port)
                        music_info["action"] = "stop"
                        music_block = "[EVIDENCE ÂM NHẠC: Đã gửi lệnh DỪNG PHÁT NHẠC trên loa Raspberry Pi 5 theo yêu cầu của Anh. Hãy thông báo ngắn gọn, xác nhận đã dừng bài hát.]"
                        context.system_instructions = context.system_instructions + "\n" + music_block
                    else:
                        music_info["action"] = "play"
                        music_info["song_query"] = song_target
                        yt_results = search_youtube_music(song_target, max_results=3)
                        if yt_results:
                            top_track = yt_results[0]
                            dispatch_play_music_to_pi5(
                                video_id=top_track["video_id"],
                                title=top_track["title"],
                                url=top_track["url"],
                                edge_ip=edge_ip,
                                edge_port=edge_port,
                            )
                            music_info["track"] = top_track
                            music_info["playing"] = True
                            music_block = (
                                f"[EVIDENCE ÂM NHẠC YOUTUBE — ĐÃ TÌM THẤY VÀ KÍCH HOẠT PHÁT TRÊN PI 5:\n"
                                f"- Tên bài hát/video: {top_track['title']}\n"
                                f"- Kênh: {top_track.get('channel', 'YouTube')}\n"
                                f"- Thời lượng: {top_track.get('duration', '')}\n"
                                f"- URL: {top_track['url']}\n"
                                f"- Trạng thái: Lệnh phát nhạc đã gửi tới loa Raspberry Pi 5 thành công qua Wi-Fi.\n"
                                f"HÃY BÁO CÁO VUI VẺ, LỊCH SỰ XÁC NHẬN BÀI HÁT ĐANG PHÁT TRÊN LOA PI 5 ĐỂ ANH VÀ CHỊ THƯỞNG THỨC.]"
                            )
                            context.system_instructions = context.system_instructions + "\n" + music_block
            except Exception as _m_err:
                music_info["error"] = str(_m_err)[:120]

            # 3. LLM Generation
            req = LLMRequest(
                prompt=context.rendered_context,
                system_prompt=context.system_instructions,
                model=selected_model,
                timeout_seconds=timeout,
            )
            resp = provider.generate(req)

            # 4. Output Guardrails & Grounding Analysis
            sanitized_reply, guardrail_warnings = OutputGuardrails.sanitize(resp.text)
            grounding_analysis = OutputGuardrails.analyze_grounding(sanitized_reply, context=context)

            # 5. Continuous Session & Memory Persistence
            persistence_info: dict[str, Any] = {}
            if resp.success and sanitized_reply:
                with MemoryStore(db_path, workspace=workspace) as store:
                    session_mgr = SessionMemoryManager(store)
                    persistence_info = session_mgr.persist_chat_turn(
                                            session_id=session_id,
                                            user_query=query,
                                            assistant_reply=sanitized_reply,
                                            model_used=resp.model,
                                            used_memory_ids=[m.memory_id for m in context.used_memories],
                                            project_scope=scope or "general",
                                            # system_prompt NOT passed (Sprint 16 memory hygiene — do not store raw system instructions)
                                        )

            all_warnings: list[str] = []
            if resp.warning:
                all_warnings.append(resp.warning)
            if guardrail_warnings:
                all_warnings.extend(guardrail_warnings)

            # 6. Task Plan & Durable Registration if requested
            durable_task_dict: dict[str, Any] | None = None
            if resp.success and bool(body.get("create_task", False)):
                try:
                    from quan_ai_brain.governance.policy import PolicyEngine
                    from quan_ai_brain.planning import ExecutiveCoordinator
                    from quan_ai_brain.orchestration.plan_orchestrator import PlanOrchestrator
                    from quan_ai_brain.orchestration.task_registry import DurableTaskRegistry
                    from quan_ai_brain.governance.state_store import GovernanceStateStore
                    from quan_ai_brain.governance.consultation_inbox import ConsultationStore

                    with MemoryStore(db_path, workspace=workspace) as plan_mem:
                        p_retriever = CognitiveRetriever(plan_mem)
                        p_builder = PromptContextBuilder()
                        p_policy = PolicyEngine(workspace)
                        p_coord = ExecutiveCoordinator(
                            workspace=workspace,
                            llm_provider=provider,
                            policy_engine=p_policy,
                            retriever=p_retriever,
                            context_builder=p_builder,
                        )
                        task_plan = p_coord.plan(goal=query, project_scope=scope, model=selected_model, fallback=allow_fallback)

                    tasks_db = workspace / "data" / "tasks.db"
                    gov_db = workspace / "data" / "governance.db"
                    cst_db = workspace / "data" / "consultations.db"
                    t_reg = DurableTaskRegistry(tasks_db, workspace=workspace)
                    g_store = GovernanceStateStore(gov_db, workspace=workspace)
                    c_store = ConsultationStore(cst_db)

                    t_orch = PlanOrchestrator(task_registry=t_reg, workspace=workspace, governance_store=g_store, consultation_store=c_store)
                    task_rec = t_orch.submit_plan(task_plan)
                    # Sprint 15 (c): plan warnings (stale/adversarial/metacognitive)
                    # phải tới owner — trước đây bị nuốt vì TaskRecord không chứa warnings.
                    for _pw in (getattr(task_plan, "warnings", None) or []):
                        if _pw and _pw not in all_warnings:
                            all_warnings.append(f"Plan: {_pw}")
                    durable_task_dict = task_rec.to_dict()
                    plan_note = f"\n\n📋 *Nhiệm vụ đã được tự động phân rã và đăng ký bền vững vào DurableTaskRegistry: `{task_rec.task_id}` (Rủi ro: {task_rec.risk_level}, Tiến trình: {len(task_rec.approved_scope)} bước DAG).* "
                    sanitized_reply += plan_note
                    
                    # CLO V1: Trigger learning session when task created
                    try:
                        from quan_ai_brain.cognition.continuous_learning_engine import ContinuousLearningEngine
                        
                        # Check if CLO is enabled
                        with MemoryStore(db_path, workspace=workspace) as clo_store:
                            clo_engine = ContinuousLearningEngine(clo_store, workspace=workspace)
                            if clo_engine.session_manager.is_clo_enabled():
                                # End current session if running, create next session
                                current_session = clo_engine.session_manager.get_current_session()
                                if current_session and current_session.status.value in ["RUNNING", "PLANNING", "EVALUATING"]:
                                    # End current session with task info
                                    next_plan = {
                                        "objectives": ["Continue learning from task execution"],
                                        "source_manifest": {"task_id": task_rec.task_id, "source": "chat_task"}
                                    }
                                    ended_session = clo_engine.end_session(
                                        session_id=current_session.session_id,
                                        evaluation_result={"task_created": True, "task_id": task_rec.task_id},
                                        unresolved_questions=[],
                                        next_plan=next_plan
                                    )
                                    learning_session_info = {
                                        "session_ended": current_session.session_id,
                                        "next_session": ended_session.session_id if ended_session.session_id != current_session.session_id else None,
                                        "cycle_number": ended_session.cycle_number
                                    }
                    except Exception as clo_err:
                        # Non-blocking: log but don't fail the request
                        all_warnings.append(f"CLO session trigger: {str(clo_err)[:100]}")

                    # V6: TaskPipeline evidence trail — pipeline gắn với task vừa đăng ký
                    try:
                        from quan_ai_brain.cognition.task_pipeline import (
                            TaskPipelineEngine,
                            PipelineStage,
                        )

                        _tp_engine = TaskPipelineEngine()
                        _tp = _tp_engine.create_pipeline(
                            owner_request=query,
                            task_goal=task_rec.goal if hasattr(task_rec, "goal") else query,
                            acceptance_criteria=[
                                "Task đã đăng ký vào DurableTaskRegistry với task_id hợp lệ",
                            ],
                            risk_level=str(task_rec.risk_level),
                        )
                        _tp_engine.advance(
                            _tp, PipelineStage.DECOMPOSE,
                            notes=f"Decomposed by ExecutiveCoordinator.plan() ({len(task_rec.approved_scope)} DAG steps)",
                            evidence_refs=[f"task_id:{task_rec.task_id}"],
                        )
                        _tp_engine.advance(
                            _tp, PipelineStage.DISCOVER,
                            notes="Existing tools reused: ExecutiveCoordinator, PlanOrchestrator, DurableTaskRegistry",
                            evidence_refs=[f"task_id:{task_rec.task_id}"],
                        )
                        _tp_engine.advance(
                            _tp, PipelineStage.PLAN,
                            notes=f"Plan registered with risk {task_rec.risk_level}",
                            evidence_refs=[f"task_id:{task_rec.task_id}"],
                        )
                        for _s in (PipelineStage.LEARN, PipelineStage.BUILD, PipelineStage.TEST):
                            _tp_engine.advance(_tp, _s, notes="", skipped_reason="registration path — execution handled by durable task runner")
                        _tp_engine.advance(
                            _tp, PipelineStage.ANALYZE,
                            notes=f"Task {task_rec.task_id} registered; awaiting execution evidence",
                            evidence_refs=[f"task_id:{task_rec.task_id}"],
                        )
                        # VERIFY fail-honest: chưa có bằng chứng thực thi → NOT_VERIFIED
                        _crit = _tp.spec.acceptance_criteria[0]
                        _tp_engine.advance(
                            _tp, PipelineStage.VERIFY,
                            notes="Task registered but not yet executed — honest not_verified",
                            validation={"criteria": {
                                _crit: {"passed": False, "not_verified": True,
                                        "reason": "durable task execution pending"},
                            }},
                            evidence_refs=[f"task_id:{task_rec.task_id}"],
                        )
                        # ADVISE + REUSE — ghi khuyến nghị trung thực
                        _tp_engine.advance(
                            _tp, PipelineStage.ADVISE,
                            notes=f"Task {task_rec.task_id} chờ thực thi theo DAG đã duyệt; theo dõi tại /api/executive/tasks",
                        )
                        _tp_engine.advance(
                            _tp, PipelineStage.REUSE,
                            notes="", skipped_reason="no reusable asset generated at registration time",
                        )
                        # Gắn pipeline vào response (truy vết bằng chứng)
                        if isinstance(durable_task_dict, dict):
                            durable_task_dict["task_pipeline"] = {
                                "pipeline_id": _tp.pipeline_id,
                                "stages_completed": len(_tp.stage_history),
                                "final_recommendation": _tp.final_recommendation,
                                "verify_status": "NOT_VERIFIED (execution pending)",
                            }
                    except Exception as tp_err:
                        # Non-blocking: pipeline chỉ là evidence trail, không chặn chat
                        all_warnings.append(f"TaskPipeline trail: {str(tp_err)[:100]}")
                except Exception as plan_err:
                    all_warnings.append(f"Auto-planning registration: {plan_err}")

                # V7 Cấp 2: chain skill kiểm tra tiến độ — chạy khi query khớp
                # trigger của skill TASK_STATUS_RECONCILIATION (AVAILABLE). Đọc-only,
                # fail-honest, không chặn chat (lỗi chỉ append warning).
                try:
                    from quan_ai_brain.cognition.skill_registry import SkillRegistry as _V7SR
                    from quan_ai_brain.cognition.v7_skills import run_progress_check_chain as _v7_chain

                    _v7_ws = _find_workspace_root()
                    _v7_matches = _V7SR(_v7_ws / "data" / "skill_registry.json").find_matching_skills(query or "")
                    if any(s.name == "TASK_STATUS_RECONCILIATION" for s in _v7_matches):
                        _v7_result = _v7_chain(query or "", _v7_ws)
                        response_data["progress_check"] = {
                            "chain": _v7_result["chain"],
                            "conclusion": _v7_result["reconciliation"]["conclusion"],
                            "records_matched": _v7_result["reconciliation"]["records_matched"],
                            "sources_accessed": _v7_result["reconciliation"]["sources_accessed"],
                            "sources_blocked": _v7_result["reconciliation"]["sources_blocked"],
                            "risk_summary": _v7_result["risk_summary"],
                            "report_md": _v7_result["report_md"],
                        }
                except Exception as v7_err:
                    all_warnings.append(f"V7 progress chain: {str(v7_err)[:100]}")

            elapsed = round((time.perf_counter() - start_time) * 1000, 2)
            warning_out = "; ".join(all_warnings) if all_warnings else None

            # 4.5 Avatar expression sync — SPEAKING + lời thoại hiển thị trên Pi 5.
            # Daemon phía Pi tự reset về IDLE sau duration_ms (đọc xong) — PC không cần dọn.
            try:
                if resp.success and sanitized_reply:
                    speak_ms = max(2500, min(15000, len(sanitized_reply) * 90))
                    push_avatar_speech(sanitized_reply, duration_ms=speak_ms)
                    _GLOBAL_EDGE_TELEMETRY["target_avatar_state"] = "SPEAKING"
                elif not resp.success:
                    push_avatar_expression("BLOCKED", transcript="Có lỗi khi xử lý câu hỏi")
                    _GLOBAL_EDGE_TELEMETRY["target_avatar_state"] = "BLOCKED"
            except Exception:
                pass

            # Owner teach confirmation — hiển thị ngay trong reply
            if teach_note:
                sanitized_reply = teach_note + "\n\n" + sanitized_reply

            self._send_json({
                "success": resp.success,
                "answer": sanitized_reply,
                "reply": sanitized_reply,
                "teach_note": teach_note,
                "model": resp.model,
                "provider": resp.provider,
                "is_mock": resp.is_mock,
                "warning": warning_out,
                "error_message": resp.error_message,
                "elapsed_ms": elapsed,
                "used_memory_ids": [m.memory_id for m in context.used_memories],
                "used_memories": [
                    {
                        "id": getattr(m, "memory_id", str(getattr(m, "id", ""))),
                        "summary": getattr(m, "summary", getattr(m, "content", str(m))),
                        "content": getattr(m, "content", ""),
                        "type": str(getattr(getattr(m, "memory_type", None), "value", getattr(m, "memory_type", "SEMANTIC"))),
                    }
                    for m in context.used_memories
                ],
                "grounding": grounding_analysis.to_dict(),
                "session_id": session_id,
                "routing": {
                    "tier": decision.tier,
                    "reason": decision.reason,
                    "model": decision.model,
                    "is_fallback": decision.is_fallback,
                },
                "persistence": persistence_info,
                "durable_task": durable_task_dict,
                "external_lookup": ext_lookup_info,
                "music_playback": music_info.get("track") if music_info.get("playing") else ({"action": "stop", "playing": False} if music_info.get("action") == "stop" else None),
            })
        except Exception as exc:
            self._send_error_json(f"Chat execution error: {exc}", 500)

    def _handle_api_chat_stream(self, body: dict) -> None:
        """SSE streaming chat endpoint (Sprint 2, owner-approved 2026-10-25).

        POST /api/chat/stream  body: same fields as /api/chat.
        Emits text/event-stream frames of JSON dicts:
          {"type":"meta","model":...} — model chosen after routing + gates
          {"type":"delta","text":...} — incremental GLM tokens
          {"type":"final", ...}       — full reply persisted AFTER completion
          {"type":"error","code":...} — fail-closed; never a mock masquerade
        Mock fallback is emitted ONLY when the caller explicitly passes
        fallback=true, tagged with an explicit is_mock/warning provenance.
        """
        query = str(body.get("query") or body.get("message", "")).strip()
        session_id = str(body.get("session_id", "default_executive_session")).strip() or "default_executive_session"
        allow_fallback = bool(body.get("fallback", False))
        scope = body.get("scope") or None
        timeout = float(body.get("timeout", 120.0))
        explicit_model = str(body.get("model", "")).strip() or None

        def _sse(event: dict) -> bytes:
            return f"data: {json.dumps(event, ensure_ascii=False)}\n\n".encode("utf-8")

        # Header validation errors must still be SSE-shaped for the client.
        if not query:
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream; charset=utf-8")
            self.end_headers()
            self.wfile.write(_sse({"type": "error", "code": "EMPTY_QUERY", "message": "Query cannot be empty"}))
            return

        workspace = _find_workspace_root()
        db_path = workspace / "data" / "brain.db"

        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "close")
        self.end_headers()

        try:
            # 1. Routing (same heuristics as /api/chat; deep tier included).
            # Include NetMind cloud models when READY (same logic as /api/chat).
            router = LLMRouter()
            mode = FallbackMode.ON_ERROR if allow_fallback else FallbackMode.NEVER
            provider = _build_llm_provider(mode)
            avail_models: list[str] = []
            if provider.netmind is not None:
                try:
                    avail_models.extend(_netmind_available_models(provider.netmind))
                except Exception:
                    pass
            if provider.is_online(timeout=1.0):
                try:
                    avail_models = [m.name for m in provider.list_models(allow_fallback=True)] + avail_models
                except Exception:
                    avail_models = []
            decision = router.route(
                query,
                task_hint="chat",
                explicit_model=explicit_model,
                available_models=avail_models,
            )
            selected_model = decision.model
            self.wfile.write(_sse({"type": "meta", "model": selected_model, "tier": decision.tier}))

            # 1.5 Owner teach detection (V8 parity)
            teach_note = None
            try:
                from quan_ai_brain.cognition.owner_teach import detect_teaching
                teach = detect_teaching(query)
                if teach:
                    teach_note = f"Đã ghi nhận kiến thức dạy từ Anh ({teach.content[:80]})."
            except Exception:
                pass

            # 2. Memory retrieval & session history.
            with MemoryStore(db_path, workspace=workspace) as store:
                session_mgr = SessionMemoryManager(store)
                recent_history = session_mgr.get_recent_session_history(session_id, limit=6)
                retriever = CognitiveRetriever(store)
                m_query = MemoryQuery(query=query, project_scope=scope, top_k=5, max_chars=4000)
                retrieval = retriever.retrieve(m_query)
                builder = PromptContextBuilder(default_max_chars=4000)
                context = builder.build(
                    user_query=query,
                    retrieval=retrieval,
                    max_chars=4000,
                    project_scope=scope,
                    conversation_history=recent_history,
                )

            # 2.5 Living Grounding Facts (V8 parity)
            try:
                from quan_ai_brain.cognition.grounding_facts import collect_grounding_facts, render_grounding_block
                grounding_block = render_grounding_block(collect_grounding_facts(current_model=selected_model))
                context.system_instructions = grounding_block + "\n\n" + context.system_instructions
            except Exception:
                pass

            # 2.55 Avatar: THINKING ngay khi nhận câu hỏi (stream path).
            try:
                push_avatar_thinking()
            except Exception:
                pass

            # 2.6 External lookup evidence — như /api/chat (câu hỏi thời sự mới tra;
            # fail-closed, không bao giờ làm chết stream).
            _stream_researching = False
            try:
                from quan_ai_brain.tools.external_lookup import collect_external_evidence

                _ev = collect_external_evidence(query, timeout=20.0)
                _ev_block = _ev.render_block()
                if _ev_block:
                    context.system_instructions = context.system_instructions + "\n" + _ev_block
                    _stream_researching = True
                    _GLOBAL_EDGE_TELEMETRY["target_avatar_state"] = "RESEARCHING"
                    push_avatar_expression("RESEARCHING", transcript="Đang tra cứu thông tin ngoài...")
            except Exception:
                pass

            # 2.7 TTNS lookup (V8 parity)
            try:
                from quan_ai_brain.tools.ttns_lookup import looks_like_ttns_query, ttns_lookup
                if looks_like_ttns_query(query):
                    _ttns = ttns_lookup(query)
                    if _ttns and _ttns.get("answer"):
                        context.system_instructions += "\n[EVIDENCE TTNS NỘI BỘ]\n" + _ttns["answer"][:6000]
            except Exception:
                pass

            # 2.8 Document RAG evidence (V8 parity)
            try:
                from quan_ai_brain.cognition.document_rag import DocumentRAG
                _rag = DocumentRAG(workspace=str(workspace))
                if _rag.count_chunks() > 0:
                    _rr = _rag.retrieve(query)
                    if _rr.has_evidence:
                        context.system_instructions += "\n" + _rr.render_evidence_block()
            except Exception:
                pass

            # 2.85 YouTube Music detection & Pi 5 streaming dispatch (stream path)
            music_info_stream: dict[str, Any] = {"requested": False}
            try:
                is_music, song_target = looks_like_music_request(query)
                if is_music:
                    music_info_stream["requested"] = True
                    edge_ip = _GLOBAL_EDGE_TELEMETRY.get("edge_ip", "192.168.1.21")
                    edge_port = _GLOBAL_EDGE_TELEMETRY.get("edge_port", 8768)
                    if song_target == "STOP":
                        dispatch_stop_music_to_pi5(edge_ip=edge_ip, edge_port=edge_port)
                        music_info_stream["action"] = "stop"
                        music_block = "[EVIDENCE ÂM NHẠC: Đã gửi lệnh DỪNG PHÁT NHẠC trên loa Raspberry Pi 5 theo yêu cầu của Anh. Hãy thông báo ngắn gọn, xác nhận đã dừng bài hát.]"
                        context.system_instructions = context.system_instructions + "\n" + music_block
                    else:
                        music_info_stream["action"] = "play"
                        music_info_stream["song_query"] = song_target
                        yt_results = search_youtube_music(song_target, max_results=3)
                        if yt_results:
                            top_track = yt_results[0]
                            dispatch_play_music_to_pi5(
                                video_id=top_track["video_id"],
                                title=top_track["title"],
                                url=top_track["url"],
                                edge_ip=edge_ip,
                                edge_port=edge_port,
                            )
                            music_info_stream["track"] = top_track
                            music_info_stream["playing"] = True
                            music_block = (
                                f"[EVIDENCE ÂM NHẠC YOUTUBE — ĐÃ TÌM THẤY VÀ KÍCH HOẠT PHÁT TRÊN PI 5:\n"
                                f"- Tên bài hát/video: {top_track['title']}\n"
                                f"- Kênh: {top_track.get('channel', 'YouTube')}\n"
                                f"- Thời lượng: {top_track.get('duration', '')}\n"
                                f"- URL: {top_track['url']}\n"
                                f"- Trạng thái: Lệnh phát nhạc đã gửi tới loa Raspberry Pi 5 thành công qua Wi-Fi.\n"
                                f"HÃY BÁO CÁO VUI VẺ, LỊCH SỰ XÁC NHẬN BÀI HÁT ĐANG PHÁT TRÊN LOA PI 5 ĐỂ ANH VÀ CHỊ THƯỞNG THỨC.]"
                            )
                            context.system_instructions = context.system_instructions + "\n" + music_block
            except Exception as _m_err:
                music_info_stream["error"] = str(_m_err)[:120]

            # 3. Streamed generation (NetMind SSE) — deltas forwarded as they come.
            req = LLMRequest(
                prompt=context.rendered_context,
                system_prompt=context.system_instructions,
                model=selected_model,
                timeout_seconds=timeout,
            )
            parts: list[str] = []
            final_event: dict = {}
            for event in provider.stream(req):
                if event["type"] == "delta":
                    parts.append(event["text"])
                    self.wfile.write(_sse(event))
                    self.wfile.flush()
                elif event["type"] == "final":
                    final_event = event
                elif event["type"] == "error":
                    # Fail-closed: no mock masquerade unless caller opted in.
                    if allow_fallback:
                        mock_resp = provider.mock.generate(req)
                        warning = (
                            f"MOCK FALLBACK — [{event.get('code')}] {event.get('message', '')} "
                            "Mock provider used. NO REAL LLM INFERENCE."
                        )
                        self.wfile.write(_sse({"type": "delta", "text": mock_resp.text}))
                        self.wfile.write(_sse({"type": "final", "model": "mock", "elapsed_ms": 0.0,
                                               "completion_tokens": None, "finish_reason": "stop",
                                               "is_mock": True, "warning": warning}))
                    else:
                        self.wfile.write(_sse(event))
                    self.wfile.flush()
                    return

            full_text = OutputGuardrails.sanitize("".join(parts))[0]
            if teach_note:
                full_text = (teach_note + "\n\n" + full_text)
            grounding_analysis = OutputGuardrails.analyze_grounding(full_text, context=context)

            # 4. Persist the COMPLETE answer only after stream completion.
            persistence_info: dict[str, Any] = {}
            if full_text:
                with MemoryStore(db_path, workspace=workspace) as store:
                    session_mgr = SessionMemoryManager(store)
                    persistence_info = session_mgr.persist_chat_turn(
                        session_id=session_id,
                        user_query=query,
                        assistant_reply=full_text,
                        model_used=final_event.get("model", selected_model),
                        used_memory_ids=[m.memory_id for m in context.used_memories],
                        project_scope=scope or "general",
                    )

            final_event.setdefault("type", "final")
            final_event.update({
                "reply": full_text,
                "grounding": grounding_analysis.to_dict(),
                "session_id": session_id,
                "routing": {"tier": decision.tier, "model": decision.model, "is_fallback": decision.is_fallback},
                "persistence": persistence_info,
                "music_playback": music_info_stream.get("track") if music_info_stream.get("playing") else ({"action": "stop", "playing": False} if music_info_stream.get("action") == "stop" else None),
            })
            self.wfile.write(_sse(final_event))
            self.wfile.flush()

            # 4.5 Avatar expression sync — SPEAKING sau khi stream xong (Pi tự về IDLE).
            try:
                if full_text:
                    speak_ms = max(2500, min(15000, len(full_text) * 90))
                    push_avatar_speech(full_text, duration_ms=speak_ms)
                    _GLOBAL_EDGE_TELEMETRY["target_avatar_state"] = "SPEAKING"
            except Exception:
                pass
        except (BrokenPipeError, ConnectionResetError):
            return  # client disconnected mid-stream — nothing to write
        except Exception as exc:  # noqa: BLE001 — endpoint must not crash the server
            try:
                self.wfile.write(_sse({"type": "error", "code": "STREAM_HANDLER_ERROR", "message": str(exc)}))
            except Exception:  # noqa: BLE001
                pass

    def _handle_api_plan(self, body: dict) -> None:
        goal = str(body.get("goal", "")).strip()
        if not goal:
            self._send_error_json("Goal is required", 400)
            return

        model = str(body.get("model", "qwen2.5:7b")).strip()
        fallback_val = body.get("fallback")
        if fallback_val is None:
            fallback_val = body.get("allow_fallback", True)
        allow_fallback = bool(fallback_val)
        scope = body.get("scope") or None

        workspace = _find_workspace_root()
        db_path = workspace / "data" / "brain.db"
        try:
            from quan_ai_brain.governance.policy import PolicyEngine
            from quan_ai_brain.planning import ExecutiveCoordinator

            with MemoryStore(db_path, workspace=workspace) as store:
                retriever = CognitiveRetriever(store)
                builder = PromptContextBuilder()
                policy = PolicyEngine(workspace)
                mode = FallbackMode.ON_ERROR if allow_fallback else FallbackMode.NEVER
                provider = LLMProvider(fallback_mode=mode, default_model=model)

                coordinator = ExecutiveCoordinator(
                    workspace=workspace,
                    llm_provider=provider,
                    policy_engine=policy,
                    retriever=retriever,
                    context_builder=builder,
                )
                plan = coordinator.plan(
                    goal=goal,
                    project_scope=scope,
                    model=model,
                    fallback=allow_fallback,
                )

            # Persist and register task into DurableTaskRegistry via PlanOrchestrator
            task_record_dict = None
            if plan.status.value != "failed":
                try:
                    from quan_ai_brain.orchestration.plan_orchestrator import PlanOrchestrator
                    from quan_ai_brain.orchestration.task_registry import DurableTaskRegistry
                    from quan_ai_brain.governance.state_store import GovernanceStateStore

                    tasks_db = workspace / "data" / "tasks.db"
                    gov_db = workspace / "data" / "governance.db"
                    task_reg = DurableTaskRegistry(tasks_db, workspace=workspace)
                    gov_store = GovernanceStateStore(gov_db, workspace=workspace)
                    orchestrator = PlanOrchestrator(task_registry=task_reg, workspace=workspace, governance_store=gov_store)
                    task_rec = orchestrator.submit_plan(plan)
                    task_record_dict = task_rec.to_dict()
                except Exception as orch_err:
                    plan.warning = f"Plan created but orchestration registration deferred: {orch_err}"

            self._send_json({
                "success": plan.status.value != "failed",
                "plan": plan.to_dict(),
                "explanation": plan.explain(),
                "durable_task": task_record_dict,
            })
        except Exception as exc:
            self._send_error_json(f"Planning error: {exc}", 500)

    def _handle_api_learning(self, body: dict) -> None:
        scope = str(body.get("scope", "general")).strip()
        workspace = _find_workspace_root()
        db_path = workspace / "data" / "learning_sandbox.db"
        try:
            import uuid
            from quan_ai_brain.contract.models import EvidenceRecord, TaskOutcome, TaskState
            from quan_ai_brain.learning.engine import SelfLearningEngine

            with MemoryStore(db_path, workspace=workspace) as store:
                engine = SelfLearningEngine(workspace=workspace, memory_store=store)

                error_desc = str(body.get("error") or "Simulated capability gap: Local Ollama daemon unreachable at 127.0.0.1:11434 (Connection refused).")
                outcome = TaskOutcome(
                    task_id=f"task_{uuid.uuid4().hex[:8]}",
                    correlation_id=f"corr_{uuid.uuid4().hex[:8]}",
                    state=TaskState.FAILED,
                    error_message=error_desc,
                    evidence=[
                        EvidenceRecord(
                            evidence_id=f"ev_{uuid.uuid4().hex[:8]}",
                            source_type="local_system_probe",
                            description="Observed execution failure or capability bottleneck",
                            evidence_payload={"error": error_desc, "scope": scope},
                        )
                    ],
                    is_outcome_certain=False,
                )

                gap = engine.observe_task(outcome)
                if gap is None:
                    self._send_json({"success": True, "status": "no_gap"})
                    return

                authorized_sources = [
                    {"title": "System Baseline", "path": "docs/SYSTEM_BASELINE.md", "type": "architecture_doc"},
                    {"title": "Local LLM Client", "path": "src/quan_ai_brain/llm/client.py", "type": "source_code"},
                    {"title": "Python Standard Library Specification", "path": "stdlib", "type": "standard_library"},
                ]
                dossier = engine.research_gap(
                    gap=gap,
                    question=f"How to address: {gap.description} with standard-library code?",
                    authorized_sources=authorized_sources,
                    findings="Use standard library pre-flight socket probing with bounded timeout (<=50ms) to detect offline dependencies instantly.",
                    candidate_statement="Fast TCP socket pre-flight probing enables instant offline detection without thread blocking.",
                    confidence_score=0.88,
                )

                cand_rec = engine.quarantine_candidate(dossier)
                diff_sample = """--- a/src/quan_ai_brain/llm/client.py\n+++ b/src/quan_ai_brain/llm/client.py\n@@ -35,6 +35,14 @@\n+    def is_daemon_online(self) -> bool:\n+        \"\"\"Pre-flight TCP check to detect offline daemon without HTTP latency.\"\"\"\n+        import socket\n+        try:\n+            with socket.create_connection((self.host, self.port), timeout=0.05):\n+                return True\n+        except OSError:\n+            return False\n"""
                proposal = engine.create_upgrade_proposal(
                    problem_statement=gap.description,
                    target_goal="Detect offline status within <=50ms and fail fast to fallback without worker thread stall.",
                    proposed_solution="Implement standard-library pre-flight socket probe before attempting HTTP calls.",
                    unified_diff=diff_sample,
                    pros=["Instant fail-fast", "Eliminates UI freeze", "Standard library only"],
                    cons=["Adds 1 extra loopback socket handshake (<0.1ms)"],
                    risk_assessment="Low: only probes loopback address, does not change core parsing.",
                    files_to_modify=["src/quan_ai_brain/llm/client.py"],
                    new_candidate_ids=[cand_rec.memory_id],
                )

            self._send_json({
                "success": True,
                "gap": gap.to_dict(),
                "dossier": dossier.to_dict(),
                "proposal": proposal.to_dict(),
                "explanation": proposal.explain(),
            })
        except Exception as exc:
            self._send_error_json(f"Learning cycle error: {exc}", 500)

    def _handle_api_executive_overview(self) -> None:
        workspace = _find_workspace_root()
        persona = ExecutivePersona()
        caps = CapabilityRegistry().list_capabilities()
        cst_store = ConsultationStore(workspace / "data" / "consultations.db")
        try:
            pending_count = cst_store.count_pending()
        finally:
            cst_store.close()
        reporter = PeriodicLearningReporter(workspace)
        try:
            latest_rep = reporter.get_latest_report()
        finally:
            reporter.close()
        self._send_json({
            "success": True,
            "persona": persona.to_dict(),
            "capability_count": len(caps),
            "pending_consultations": pending_count,
            "latest_report": latest_rep.to_dict() if latest_rep else None,
        })

    def _handle_api_executive_netchat_status(self) -> None:
        try:
            from quan_ai_brain.integration.netchat_bridge import get_status

            self._send_json(get_status())
        except Exception as exc:
            self._send_error_json(f"NetChat status error: {exc}", 502)

    def _handle_api_executive_netchat_messages(self, query_str: str) -> None:
        try:
            from quan_ai_brain.integration.netchat_bridge import (
                DEFAULT_CHANNEL_ID,
                get_messages,
            )

            params = urllib.parse.parse_qs(query_str)
            channel_id = params.get("channel_id", [DEFAULT_CHANNEL_ID])[0]
            count = int(params.get("count", ["20"])[0])
            self._send_json(get_messages(channel_id, count))
        except Exception as exc:
            self._send_error_json(f"NetChat messages error: {exc}", 502)

    def _handle_api_executive_netchat_send(self, body: dict) -> None:
        try:
            from quan_ai_brain.integration.netchat_bridge import (
                DEFAULT_CHANNEL_ID,
                send_message,
            )

            text = str(body.get("message", "")).strip()
            channel_id = str(body.get("channel_id", DEFAULT_CHANNEL_ID)).strip() or DEFAULT_CHANNEL_ID
            self._send_json(send_message(channel_id, text))
        except Exception as exc:
            self._send_error_json(f"NetChat send error: {exc}", 502)

    def _handle_api_executive_netchat_command(self, body: dict) -> None:
        try:
            from quan_ai_brain.integration.netchat_bridge import run_command

            self._send_json(run_command(str(body.get("command", ""))))
        except Exception as exc:
            self._send_error_json(f"NetChat command error: {exc}", 502)

    def _handle_api_executive_persona(self) -> None:
        persona = ExecutivePersona()
        self._send_json(persona.to_dict())

    def _handle_api_executive_persona_update(self, body: dict) -> None:
        approved = bool(body.get("approved_by_owner", False))
        approver = str(body.get("approver", "")).strip()
        if not approved or approver != "Quanpt1":
            self._send_error_json(
                "Sửa đổi cấu hình Persona bị từ chối: Bắt buộc phải có phê duyệt hợp lệ từ Anh Quân (Quanpt1).",
                403,
            )
            return
        self._send_json({"success": True, "message": "Persona updated with verified owner approval."})

    def _handle_api_executive_capabilities(self) -> None:
        caps = CapabilityRegistry().list_capabilities()
        self._send_json({"success": True, "capabilities": [c.to_dict() for c in caps]})

    def _handle_api_skills(self) -> None:
        """V6: GET /api/skills — danh sách Skill trong registry (read-only)."""
        try:
            from quan_ai_brain.cognition.skill_registry import SkillRegistry

            workspace = _find_workspace_root()
            registry = SkillRegistry(workspace / "data" / "skill_registry.json")
            skills = registry.list_skills()
            self._send_json({
                "success": True,
                "total": len(skills),
                "skills": [s.to_dict() for s in skills],
            })
        except Exception as exc:
            self._send_json({"success": False, "error": str(exc)[:200]})

    def _handle_api_executive_consultations(self, query_str: str) -> None:
        workspace = _find_workspace_root()
        params = urllib.parse.parse_qs(query_str)
        status_filter = params.get("status", [None])[0]
        if status_filter == "ALL":
            status_filter = None
        store = ConsultationStore(workspace / "data" / "consultations.db")
        try:
            tickets = store.list_tickets(status=status_filter)
            self._send_json({"success": True, "tickets": [t.to_dict() for t in tickets]})
        finally:
            store.close()

    def _handle_api_executive_consultation_respond(self, body: dict) -> None:
        ticket_id = str(body.get("ticket_id", "")).strip()
        decision = str(body.get("decision", "DIRECT")).strip()
        guidance = str(body.get("guidance", "")).strip()
        if not ticket_id:
            self._send_error_json("ticket_id is required", 400)
            return
        workspace = _find_workspace_root()
        store = ConsultationStore(workspace / "data" / "consultations.db")
        try:
            updated = store.respond_ticket(ticket_id, decision=decision, guidance=guidance)
            self._send_json({"success": True, "ticket": updated.to_dict()})
        except Exception as exc:
            self._send_error_json(f"Error responding to ticket: {exc}", 500)
        finally:
            store.close()

    def _handle_api_executive_consultation_create(self, body: dict) -> None:
        title = str(body.get("title", "")).strip()
        if not title:
            self._send_error_json("Title is required", 400)
            return
        category_str = str(body.get("category", "STRATEGIC_DIRECTION")).strip()
        category = (
            ConsultationCategory(category_str)
            if category_str in ConsultationCategory._value2member_map_
            else ConsultationCategory.STRATEGIC_DIRECTION
        )
        ticket = ConsultationTicket(
            ticket_id=str(body.get("ticket_id", "")).strip(),
            title=title,
            category=category,
            priority=str(body.get("priority", "MEDIUM")).strip(),
            context_summary=str(body.get("context_summary", "")).strip(),
            proposed_action=str(body.get("proposed_action", "")).strip(),
            options=body.get("options", []),
            evidence_notes=str(body.get("evidence_notes", "")).strip(),
        )
        workspace = _find_workspace_root()
        store = ConsultationStore(workspace / "data" / "consultations.db")
        try:
            tid = store.create_ticket(ticket)
            self._send_json({"success": True, "ticket_id": tid})
        finally:
            store.close()

    def _handle_api_executive_learning_reports(self) -> None:
        workspace = _find_workspace_root()
        reporter = PeriodicLearningReporter(workspace)
        try:
            reports = reporter.list_reports()
            self._send_json({"success": True, "reports": [r.to_dict() for r in reports]})
        finally:
            reporter.close()

    def _handle_api_executive_learning_trigger(self, body: dict) -> None:
        reason = str(body.get("trigger_reason", "manual_desk_trigger")).strip()
        workspace = _find_workspace_root()
        reporter = PeriodicLearningReporter(workspace)
        try:
            report = reporter.trigger_learning_cycle(trigger_reason=reason)
            self._send_json({"success": True, "report": report.to_dict()})
        except Exception as exc:
            self._send_error_json(f"Error triggering learning cycle: {exc}", 500)
        finally:
            reporter.close()

    def _handle_api_executive_task_create(self, body: dict) -> None:
        goal = str(body.get("goal", "")).strip()
        if not goal:
            self._send_error_json("Goal is required", 400)
            return
        autonomy_str = str(body.get("autonomy_level", "LEVEL_A")).strip()
        model = str(body.get("model", "qwen2.5:7b")).strip()
        allow_fallback = bool(body.get("allow_fallback", True))
        scope = body.get("scope") or None

        workspace = _find_workspace_root()
        db_path = workspace / "data" / "brain.db"
        try:
            from quan_ai_brain.governance.policy import PolicyEngine
            from quan_ai_brain.planning import ExecutiveCoordinator
            from quan_ai_brain.orchestration.plan_orchestrator import PlanOrchestrator
            from quan_ai_brain.orchestration.task_registry import DurableTaskRegistry
            from quan_ai_brain.orchestration.models import AutonomyLevel
            from quan_ai_brain.governance.state_store import GovernanceStateStore
            from quan_ai_brain.governance.consultation_inbox import ConsultationStore

            with MemoryStore(db_path, workspace=workspace) as store:
                retriever = CognitiveRetriever(store)
                builder = PromptContextBuilder()
                policy = PolicyEngine(workspace)
                mode = FallbackMode.ALWAYS_MOCK if model == "mock" else (FallbackMode.ON_ERROR if allow_fallback else FallbackMode.NEVER)
                provider = LLMProvider(fallback_mode=mode, default_model=model)

                coordinator = ExecutiveCoordinator(
                    workspace=workspace,
                    llm_provider=provider,
                    policy_engine=policy,
                    retriever=retriever,
                    context_builder=builder,
                )
                plan = coordinator.plan(
                    goal=goal,
                    project_scope=scope,
                    model=model,
                    fallback=allow_fallback,
                )

            tasks_db = workspace / "data" / "tasks.db"
            gov_db = workspace / "data" / "governance.db"
            cst_db = workspace / "data" / "consultations.db"
            task_reg = DurableTaskRegistry(tasks_db, workspace=workspace)
            gov_store = GovernanceStateStore(gov_db, workspace=workspace)
            cst_store = ConsultationStore(cst_db)

            autonomy = AutonomyLevel(autonomy_str) if autonomy_str in AutonomyLevel._value2member_map_ else AutonomyLevel.LEVEL_A

            orchestrator = PlanOrchestrator(
                task_registry=task_reg,
                workspace=workspace,
                governance_store=gov_store,
                consultation_store=cst_store,
            )
            task_rec = orchestrator.submit_plan(plan, autonomy_level=autonomy)

            self._send_json({
                "success": True,
                "task": task_rec.to_dict(),
                "plan": plan.to_dict(),
                "message": f"Nhiệm vụ '{task_rec.task_id}' đã được khởi tạo và ghi nhận bền vững vào DurableTaskRegistry.",
            })
        except Exception as exc:
            self._send_error_json(f"Lỗi khởi tạo nhiệm vụ: {exc}", 500)

    def _handle_api_executive_tasks(self) -> None:
            workspace = _find_workspace_root()
            task_list = []
            try:
                from quan_ai_brain.orchestration.task_registry import DurableTaskRegistry
                registry = DurableTaskRegistry(workspace / "data" / "tasks.db", workspace=workspace)
                tasks = registry.list_tasks(limit=50)
                for t in tasks:
                    t_dict = t.to_dict()
                    steps = registry.list_steps_for_task(t.task_id)
                    completed_steps = sum(1 for s in steps if str(getattr(s.status, "value", s.status)).upper() == "COMPLETED")
                    total_steps = len(steps)
                    is_task_done = str(getattr(t.status, "value", t.status)).upper() == "COMPLETED"
                    pct = round((completed_steps / total_steps * 100), 1) if total_steps > 0 else (100.0 if is_task_done else 0.0)
                    t_dict["steps_count"] = total_steps
                    t_dict["completed_steps_count"] = completed_steps
                    t_dict["progress_pct"] = pct
                    t_dict["steps"] = [s.to_dict() for s in steps]
                    task_list.append(t_dict)
            except Exception as e:
                import traceback
                traceback.print_exc()
                pass

            self._send_json({
                "success": True,
                "orchestration_mode": "DAG_SAFE_PLANNING",
                "active_tasks": task_list,
                "total_tasks": len(task_list),
                "governance_bounds": {
                    "R0": "Active",
                    "R1": "Active",
                    "R2": "Active",
                    "R3": "Quarantined",
                    "R4": "Approval-Gated",
                    "R5": "Hard-Blocked",
                },
            })

    def _handle_api_executive_task_detail(self, query_str: str) -> None:
        params = urllib.parse.parse_qs(query_str)
        task_id = params.get("task_id", [None])[0]
        if not task_id:
            self._send_error_json("task_id is required", 400)
            return
        workspace = _find_workspace_root()
        try:
            from quan_ai_brain.orchestration.task_registry import DurableTaskRegistry

            registry = DurableTaskRegistry(workspace / "data" / "tasks.db", workspace=workspace)
            task = registry.get_task(task_id)
            if not task:
                self._send_error_json(f"Task '{task_id}' not found", 404)
                return
            steps = registry.list_steps_for_task(task_id)
            self._send_json({
                "success": True,
                "task": task.to_dict(),
                "steps": [s.to_dict() for s in steps],
            })
        except Exception as exc:
            self._send_error_json(f"Error fetching task detail: {exc}", 500)

    def _handle_api_executive_task_execute(self, body: dict) -> None:
        task_id = str(body.get("task_id", "")).strip()
        if not task_id:
            self._send_error_json("task_id is required", 400)
            return
        dry_run = bool(body.get("dry_run", True))
        workspace = _find_workspace_root()
        try:
            from quan_ai_brain.governance.consultation_inbox import ConsultationStore
            from quan_ai_brain.governance.state_store import GovernanceStateStore
            from quan_ai_brain.orchestration.plan_orchestrator import PlanOrchestrator
            from quan_ai_brain.orchestration.task_registry import DurableTaskRegistry

            registry = DurableTaskRegistry(workspace / "data" / "tasks.db", workspace=workspace)
            gov_store = GovernanceStateStore(workspace / "data" / "governance.db", workspace=workspace)
            cst_store = ConsultationStore(workspace / "data" / "consultations.db")
            orchestrator = PlanOrchestrator(
                task_registry=registry,
                workspace=workspace,
                governance_store=gov_store,
                consultation_store=cst_store,
            )
            outcome = orchestrator.execute_lifecycle(task_id, dry_run=dry_run)
            task = registry.get_task(task_id)
            steps = registry.list_steps_for_task(task_id)

            # Sprint 11 (d): consolidation — task kết thúc (COMPLETED/FAILED) tự sinh
            # lesson candidate vào Experience Memory (fail-closed: lỗi không phá response)
            lesson_note = None
            try:
                task_status = str(getattr(getattr(task, "status", None), "value", getattr(task, "status", ""))).upper()
                if task_status in ("COMPLETED", "FAILED"):
                    from quan_ai_brain.memory.experience_consolidation import extract_candidate_lesson
                    from quan_ai_brain.memory.sqlite_store import MemoryStore

                    mem_store = MemoryStore(workspace / "data" / "brain.db", workspace=workspace)
                    lesson = extract_candidate_lesson(
                        mem_store,
                        task_id,
                        str(getattr(task, "goal", "") or ""),
                        task_status,
                        result_summary=str(getattr(outcome, "summary", "") or ""),
                        source_ref=f"execute:{task_id}",
                    )
                    lesson_note = lesson.to_dict()
            except Exception as lesson_exc:
                lesson_note = {"created": False, "reason": f"consolidation lỗi (không chặn execute): {lesson_exc}"}

            self._send_json({
                "success": True,
                "outcome": outcome.to_dict(),
                "task": task.to_dict() if task else None,
                "steps": [s.to_dict() for s in steps],
                "experience_lesson": lesson_note,
            })
        except Exception as exc:
            self._send_error_json(f"Error executing task lifecycle: {exc}", 500)

    def _handle_api_executive_task_cancel(self, body: dict) -> None:
        task_id = str(body.get("task_id", "")).strip()
        reason = str(body.get("reason", "Cancelled by owner via Executive Desk")).strip()
        if not task_id:
            self._send_error_json("task_id is required", 400)
            return
        workspace = _find_workspace_root()
        try:
            from quan_ai_brain.governance.consultation_inbox import ConsultationStore
            from quan_ai_brain.governance.state_store import GovernanceStateStore
            from quan_ai_brain.orchestration.plan_orchestrator import PlanOrchestrator
            from quan_ai_brain.orchestration.task_registry import DurableTaskRegistry

            registry = DurableTaskRegistry(workspace / "data" / "tasks.db", workspace=workspace)
            gov_store = GovernanceStateStore(workspace / "data" / "governance.db", workspace=workspace)
            cst_store = ConsultationStore(workspace / "data" / "consultations.db")
            orchestrator = PlanOrchestrator(
                task_registry=registry,
                workspace=workspace,
                governance_store=gov_store,
                consultation_store=cst_store,
            )
            updated = orchestrator.cancel_task(task_id, reason=reason)
            self._send_json({
                "success": True,
                "task": updated.to_dict(),
                "message": f"Task '{task_id}' cancelled successfully.",
            })
        except Exception as exc:
            self._send_error_json(f"Error cancelling task: {exc}", 500)


    def _handle_api_executive_task_duplicates(self) -> None:
        """List tasks with duplicate goals (read-only, localhost-only). Sprint 15 (d)."""
        client_ip = self.client_address[0] if self.client_address else ""
        if client_ip not in ("127.0.0.1", "::1", "localhost"):
            self._send_error_json("Chỉ truy cập được từ máy chủ (localhost)", 403)
            return
        
        workspace = _find_workspace_root()
        try:
            from quan_ai_brain.orchestration.task_registry import DurableTaskRegistry
            
            registry = DurableTaskRegistry(workspace / "data" / "tasks.db", workspace=workspace)
            tasks = registry.list_tasks(limit=200)
            
            # Group by goal
            goal_map = {}
            for t in tasks:
                goal = t.goal.strip()
                if not goal:
                    continue
                if goal not in goal_map:
                    goal_map[goal] = []
                goal_map[goal].append({
                    "task_id": t.task_id,
                    "status": t.status.value,
                    "created_at_utc": t.created_at_utc,
                    "correlation_id": t.correlation_id,
                    "idempotency_key": t.idempotency_key,
                })
            
            # Filter goals with >1 task
            duplicates = {
                goal: task_list
                for goal, task_list in goal_map.items()
                if len(task_list) > 1
            }
            
            # Sort by count descending
            sorted_duplicates = sorted(
                duplicates.items(),
                key=lambda x: len(x[1]),
                reverse=True
            )
            
            self._send_json({
                "success": True,
                "total_tasks": len(tasks),
                "unique_goals": len(goal_map),
                "duplicate_goals": len(duplicates),
                "duplicates": [
                    {
                        "goal": goal,
                        "count": len(task_list),
                        "tasks": task_list
                    }
                    for goal, task_list in sorted_duplicates
                ]
            })
        except Exception as e:
            import traceback
            traceback.print_exc()
            self._send_error_json(f"Lỗi: {e}", 500)

    def _handle_api_executive_supervisor(self) -> None:
        workspace = _find_workspace_root()
        state = "READY"
        emergency_state = "normal"
        try:
            from quan_ai_brain.governance.state_store import GovernanceStateStore
            gov_store = GovernanceStateStore(workspace / "data" / "governance.db", workspace=workspace)
            emergency = gov_store.get_emergency_state()
            emergency_state = emergency.state
            if emergency.state == "stop":
                state = "STOPPED"
            elif emergency.state == "freeze":
                state = "SAFE_MODE"
        except Exception:
            pass

        # Check if request comes from Edge device or Cockpit UI
        device_hdr = (
            self.headers.get("X-QuanAI-Device")
            or self.headers.get("X-Quan-Device-Id")
            or self.headers.get("X-QuanAI-Device-Id")
        )
        if device_hdr:
            _GLOBAL_EDGE_TELEMETRY["packets_in"] += 1
            if hasattr(self, "client_address") and self.client_address:
                _GLOBAL_EDGE_TELEMETRY["edge_ip"] = self.client_address[0]
            rtt_val = 15.0
            try:
                rtt_val = float(self.headers.get("X-QuanAI-RTT-Ms", 15.0))
            except Exception:
                pass
            _GLOBAL_EDGE_TELEMETRY["rtt_history"].append(rtt_val)
            if len(_GLOBAL_EDGE_TELEMETRY["rtt_history"]) > 30:
                _GLOBAL_EDGE_TELEMETRY["rtt_history"].pop(0)

            if not _GLOBAL_EDGE_MONITOR.paired:
                _GLOBAL_EDGE_MONITOR.record_pairing(device_hdr, "Raspberry Pi 5 Digital Avatar")
            _GLOBAL_EDGE_MONITOR.record_heartbeat(device_hdr, rtt_ms=rtt_val)
        else:
            _GLOBAL_EDGE_MONITOR.check_deadline()

        edge_status = _GLOBAL_EDGE_MONITOR.get_status()
        edge_info = {
            "device_id": edge_status["device_id"],
            "device_label": edge_status["device_label"],
            "status": edge_status["state"],
            "paired": edge_status["paired"],
            "lan_ip": get_local_lan_ip(),
            "pairing_pin": _GLOBAL_EDGE_PAIRING_PIN,
            "last_heartbeat_utc": edge_status["last_heartbeat_utc"],
            "seconds_since_heartbeat": edge_status["seconds_since_heartbeat"],
            "rtt_ms": edge_status["rtt_ms"],
            "active_alert_count": edge_status["active_alert_count"],
            "active_alerts": edge_status["active_alerts"],
        }

        _GLOBAL_EDGE_TELEMETRY["packets_out"] += 1
        cmd = None
        if device_hdr:
            cmd = _GLOBAL_EDGE_TELEMETRY["pending_commands"].pop(0) if _GLOBAL_EDGE_TELEMETRY["pending_commands"] else None

        # Current Task for Cockpit Hero & Telemetry
        current_task_info = None
        try:
            from quan_ai_brain.orchestration.task_registry import DurableTaskRegistry
            registry = DurableTaskRegistry(workspace / "data" / "tasks.db", workspace=workspace)
            tasks = registry.list_tasks(limit=10)
            active_tasks = [t for t in tasks if str(getattr(t.status, "value", t.status)).upper() in ("IN_PROGRESS", "PENDING", "WAITING_APPROVAL")]
            candidate = active_tasks[0] if active_tasks else (tasks[0] if tasks else None)
            if candidate:
                steps = registry.list_steps_for_task(candidate.task_id)
                completed_steps = sum(1 for s in steps if str(getattr(s.status, "value", s.status)).upper() == "COMPLETED")
                total_steps = len(steps)
                is_task_done = str(getattr(candidate.status, "value", candidate.status)).upper() == "COMPLETED"
                current_step_name = steps[completed_steps].name if completed_steps < total_steps else ("Đã hoàn thành" if is_task_done else "Đang khởi tạo")
                pct = round((completed_steps / total_steps * 100), 1) if total_steps > 0 else (100.0 if is_task_done else 0.0)
                current_task_info = {
                    "task_id": candidate.task_id,
                    "goal": candidate.goal,
                    "status": candidate.status.value,
                    "risk_level": candidate.risk_level,
                    "autonomy_level": candidate.autonomy_level.value,
                    "total_steps": total_steps,
                    "completed_steps": completed_steps,
                    "current_step_name": current_step_name,
                    "progress_pct": pct,
                }
        except Exception:
            pass

        self._send_json({
            "success": True,
            "state": state,
            "emergency_state": emergency_state,
            "active_model": "qwen2.5:7b",
            "edge_device": edge_info,
            "current_task": current_task_info,
            "target_avatar_state": _GLOBAL_EDGE_TELEMETRY.get("target_avatar_state", "IDLE"),
            "transcript": _GLOBAL_EDGE_TELEMETRY.get("transcript", ""),
            "face_only_mode": _GLOBAL_EDGE_TELEMETRY.get("face_only_mode", True),
            "remote_command": cmd,
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        })

    def _handle_api_edge_status(self) -> None:
        _GLOBAL_EDGE_MONITOR.check_deadline()
        self._send_json({
            "success": True,
            "edge": _GLOBAL_EDGE_MONITOR.get_status(),
        })

    def _handle_api_edge_telemetry(self) -> None:
        _GLOBAL_EDGE_MONITOR.check_deadline()
        edge_status = _GLOBAL_EDGE_MONITOR.get_status()
        self._send_json({
            "success": True,
            "core_ip": f"{get_local_lan_ip()}:8766",
            "edge_ip": f"{_GLOBAL_EDGE_TELEMETRY.get('edge_ip', '192.168.1.21')}:8768",
            "edge_status": edge_status,
            "packets_in": _GLOBAL_EDGE_TELEMETRY.get("packets_in", 0),
            "packets_out": _GLOBAL_EDGE_TELEMETRY.get("packets_out", 0),
            "rtt_ms": edge_status["rtt_ms"],
            "rtt_history": _GLOBAL_EDGE_TELEMETRY.get("rtt_history", []),
            "target_avatar_state": _GLOBAL_EDGE_TELEMETRY.get("target_avatar_state", "IDLE"),
            "transcript": _GLOBAL_EDGE_TELEMETRY.get("transcript", ""),
            "face_only_mode": _GLOBAL_EDGE_TELEMETRY.get("face_only_mode", True),
            "last_telemetry": _GLOBAL_EDGE_TELEMETRY.get("last_telemetry", {}),
        })

    def _handle_api_edge_control(self, body: dict) -> None:
        try:
            action = str(body.get("action", "")).strip().lower()
            if action == "set_expression":
                state = str(body.get("state", "IDLE")).strip().upper()
                transcript = str(body.get("transcript", "")).strip()
                _GLOBAL_EDGE_TELEMETRY["target_avatar_state"] = state
                if transcript:
                    _GLOBAL_EDGE_TELEMETRY["transcript"] = transcript
                _GLOBAL_EDGE_TELEMETRY["pending_commands"].append({
                    "action": "set_expression",
                    "state": state,
                    "transcript": transcript,
                })
                _send_edge_request("/api/kiosk/control", method="POST", data={"action": "set_expression", "state": state, "transcript": transcript})
                self._send_json({"success": True, "action": action, "state": state, "transcript": transcript})
                return

            if action == "speak":
                text = str(body.get("text", "")).strip()
                state = str(body.get("state", "SPEAKING")).strip().upper()
                duration_ms = int(body.get("duration_ms", max(1200, len(text) * 110)))
                audio_base64 = body.get("audio_base64")
                timeline_dict = body.get("timeline")

                # If no audio provided, synthesize via Core TTS engine
                if not audio_base64 and text:
                    try:
                        import base64
                        voice_id = str(body.get("voice_id", "vi-VN-HoaiMyNeural"))
                        audio_bytes, _ = GLOBAL_TTS_MANAGER.synthesize_audio(text, voice_id=voice_id)
                        if audio_bytes:
                            audio_base64 = base64.b64encode(audio_bytes).decode("ascii")
                    except Exception as exc:
                        pass

                if not timeline_dict:
                    timeline = _GLOBAL_MOUTH_SYNC.generate_timeline(
                        utterance_id=f"utt_ctrl_{int(time.time()*1000)}",
                        text=text,
                        target_duration_ms=duration_ms,
                    )
                    timeline_dict = timeline.to_dict()

                _GLOBAL_EDGE_TELEMETRY["target_avatar_state"] = state
                _GLOBAL_EDGE_TELEMETRY["transcript"] = text
                cmd_data = {
                    "action": "speak",
                    "text": text,
                    "state": state,
                    "timeline": timeline_dict,
                    "duration_ms": duration_ms,
                }
                if audio_base64:
                    cmd_data["audio_base64"] = audio_base64

                _GLOBAL_EDGE_TELEMETRY["pending_commands"].append(cmd_data)
                threading.Thread(
                    target=_send_edge_request,
                    args=("/api/kiosk/control", "POST", cmd_data, 10.0),
                    daemon=True,
                ).start()
                self._send_json({
                    "success": True,
                    "action": action,
                    "text": text,
                    "timeline": timeline_dict,
                    "has_audio": bool(audio_base64),
                })
                return

            if action == "toggle_face_only":
                cur = _GLOBAL_EDGE_TELEMETRY.get("face_only_mode", True)
                _GLOBAL_EDGE_TELEMETRY["face_only_mode"] = not cur
                _send_edge_request("/api/kiosk/control", method="POST", data={"action": "set_face_only", "face_only": _GLOBAL_EDGE_TELEMETRY["face_only_mode"]})
                self._send_json({"success": True, "face_only_mode": _GLOBAL_EDGE_TELEMETRY["face_only_mode"]})
                return

            if action == "reload_ui":
                resp = _send_edge_request("/api/kiosk/control", method="POST", data={"action": "reload_ui"})
                _GLOBAL_EDGE_TELEMETRY["pending_commands"].append({"action": "reload_ui"})
                self._send_json({"success": True, "action": action, "pi5_result": resp, "message": "Đã gửi tín hiệu tải lại giao diện Kiosk trên Pi 5."})
                return

            if action == "pause":
                _GLOBAL_EDGE_TELEMETRY["target_avatar_state"] = "SLEEPING"
                _GLOBAL_EDGE_TELEMETRY["transcript"] = "Trợ lý đang tạm nghỉ ngơi theo chỉ đạo của Anh."
                _GLOBAL_EDGE_TELEMETRY["pending_commands"].append({
                    "action": "pause",
                    "state": "SLEEPING",
                    "transcript": "Trợ lý đang tạm nghỉ ngơi theo chỉ đạo của Anh.",
                })
                _send_edge_request("/api/kiosk/control", method="POST", data={"action": "pause"})
                self._send_json({"success": True, "action": "pause", "state": "SLEEPING", "message": "Đã chuyển trợ lý Pi 5 sang chế độ tạm nghỉ ngơi."})
                return

            if action == "resume":
                _GLOBAL_EDGE_TELEMETRY["target_avatar_state"] = "IDLE"
                _GLOBAL_EDGE_TELEMETRY["transcript"] = "Chào Anh Quanpt1! Em đã sẵn sàng tiếp tục công việc."
                _GLOBAL_EDGE_TELEMETRY["pending_commands"].append({
                    "action": "resume",
                    "state": "IDLE",
                    "transcript": "Chào Anh Quanpt1! Em đã sẵn sàng tiếp tục công việc.",
                })
                _send_edge_request("/api/kiosk/control", method="POST", data={"action": "resume"})
                self._send_json({"success": True, "action": "resume", "state": "IDLE", "message": "Đã kích hoạt trợ lý Pi 5 hoạt động bình thường."})
                return

            if action == "set_volume":
                vol = max(0, min(100, int(body.get("volume", 85))))
                resp = _send_edge_request("/api/kiosk/control", method="POST", data={"action": "set_volume", "volume": vol})
                self._send_json({"success": True, "action": action, "volume": vol, "pi5_result": resp})
                return

            if action in ("start_kiosk", "launch_kiosk", "open_kiosk"):
                _GLOBAL_EDGE_TELEMETRY["target_avatar_state"] = "IDLE"
                _GLOBAL_EDGE_TELEMETRY["transcript"] = "Giao diện hình thể đã được khởi động theo lệnh của Anh."
                resp = _send_edge_request("/api/kiosk/control", method="POST", data={"action": "start_kiosk"})
                self._send_json({"success": True, "action": action, "pi5_result": resp, "message": "Đã gửi lệnh bật giao diện hình thể Kiosk trên Pi 5."})
                return

            if action == "close_kiosk":
                _GLOBAL_EDGE_TELEMETRY["target_avatar_state"] = "OFFLINE"
                _GLOBAL_EDGE_TELEMETRY["transcript"] = "Giao diện hình thể đã đóng theo lệnh của Anh."
                resp = _send_edge_request("/api/kiosk/control", method="POST", data={"action": "close_kiosk"})
                self._send_json({"success": True, "action": action, "pi5_result": resp, "message": "Đã gửi lệnh tắt hẳn giao diện Kiosk trên Pi 5."})
                return

            if action == "poweroff_pi":
                _GLOBAL_EDGE_TELEMETRY["target_avatar_state"] = "OFFLINE"
                _GLOBAL_EDGE_TELEMETRY["transcript"] = "Đang tắt nguồn an toàn thiết bị Raspberry Pi 5..."
                resp = _send_edge_request("/api/kiosk/control", method="POST", data={"action": "poweroff_pi"})
                self._send_json({"success": True, "action": action, "pi5_result": resp, "message": "Đang thực hiện tắt nguồn an toàn Raspberry Pi 5..."})
                return

            if action in ("auto_configure_audio", "setup_audio"):
                resp = _send_edge_request("/api/kiosk/control", method="POST", data={"action": "auto_configure_audio"})
                self._send_json({"success": True, "action": action, "pi5_result": resp, "message": "Đã gửi lệnh tự động định tuyến âm thanh USB trên Pi 5."})
                return

            if action in ("startup_sequence", "test_and_greet"):
                self._handle_api_edge_startup_sequence(body)
                return

            self._send_error_json(f"Unknown control action: {action}", 400)

        except Exception as exc:
            self._send_error_json(f"Edge control execution error: {exc}", 500)

    def _handle_api_edge_alerts(self) -> None:
        _GLOBAL_EDGE_MONITOR.check_deadline()
        self._send_json({
            "success": True,
            "status": _GLOBAL_EDGE_MONITOR.get_status(),
            "active_alerts": [a.to_dict() for a in _GLOBAL_EDGE_MONITOR.active_alerts.values()],
            "history": _GLOBAL_EDGE_MONITOR.get_alert_history(limit=30),
        })

    def _handle_api_edge_heartbeat(self, body: dict) -> None:
        _GLOBAL_EDGE_TELEMETRY["packets_in"] += 1
        if hasattr(self, "client_address") and self.client_address:
            _GLOBAL_EDGE_TELEMETRY["edge_ip"] = self.client_address[0]

        device_id = str(body.get("device_id", "EDGE-PI5-DESK-01")).strip()
        rtt_ms = float(body.get("rtt_ms", 0.0))
        if rtt_ms > 0:
            _GLOBAL_EDGE_TELEMETRY["rtt_history"].append(rtt_ms)
            if len(_GLOBAL_EDGE_TELEMETRY["rtt_history"]) > 30:
                _GLOBAL_EDGE_TELEMETRY["rtt_history"].pop(0)

        subsystems_ready = bool(body.get("subsystems_ready", True))
        if not _GLOBAL_EDGE_MONITOR.paired:
            _GLOBAL_EDGE_MONITOR.record_pairing(device_id, "Raspberry Pi 5 Digital Avatar")
        telemetry_payload = body.get("telemetry")
        if telemetry_payload:
            _GLOBAL_EDGE_TELEMETRY["last_telemetry"] = telemetry_payload

        status = _GLOBAL_EDGE_MONITOR.record_heartbeat(
            device_id=device_id,
            rtt_ms=rtt_ms,
            subsystems_ready=subsystems_ready,
            metadata=telemetry_payload,
        )
        _GLOBAL_EDGE_TELEMETRY["packets_out"] += 1
        cmd = _GLOBAL_EDGE_TELEMETRY["pending_commands"].pop(0) if _GLOBAL_EDGE_TELEMETRY["pending_commands"] else None
        # V41: lưu telemetry Edge Agent nếu heartbeat có kèm (5 năng lực chủ động)
        agent_payload = body.get("edge_agent")
        if isinstance(agent_payload, dict):
            _GLOBAL_EDGE_TELEMETRY["last_edge_agent"] = agent_payload
        self._send_json({
            "success": True,
            "edge_status": status,
            "target_avatar_state": _GLOBAL_EDGE_TELEMETRY.get("target_avatar_state", "IDLE"),
            "transcript": _GLOBAL_EDGE_TELEMETRY.get("transcript", ""),
            "face_only_mode": _GLOBAL_EDGE_TELEMETRY.get("face_only_mode", True),
            "remote_command": cmd,
        })

    def _handle_api_edge_events(self, body: dict) -> None:
        """V41: nhận batch events Edge Agent tự thu thập (tự phối hợp năng lực 4).

        Lưu vào edge monitor alert history (severity CRITICAL/WARNING → alert record
        ghi nhận; INFO chỉ đếm). Fail-closed: lỗi không giết server.
        """
        try:
            device_id = str(body.get("device_id", "EDGE-UNKNOWN")).strip()
            events = body.get("events", [])
            if not isinstance(events, list):
                events = []
            accepted = 0
            for ev in events[:50]:  # giới hạn batch
                if not isinstance(ev, dict):
                    continue
                accepted += 1
                etype = str(ev.get("type", "UNKNOWN"))
                severity = str(ev.get("severity", "INFO")).upper()
                details = ev.get("details", {})
                if severity in ("CRITICAL", "WARNING"):
                    _GLOBAL_EDGE_MONITOR._trigger_alert(  # noqa: SLF001 — internal API
                        code=(
                            EdgeAlertCode.ALERT_B_SUDDEN_DISCONNECT
                            if etype == "BRAIN_CONNECTION_LOST"
                            else EdgeAlertCode.ALERT_C_CHANNEL_DEGRADED
                        ),
                        title=f"Edge Agent: {etype}",
                        message=str(details.get("desc", etype)),
                        severity="CRITICAL" if severity == "CRITICAL" else "WARNING",
                        metadata={"agent_event": ev, "device_id": device_id},
                    )
            _GLOBAL_EDGE_TELEMETRY["edge_events_received"] = (
                _GLOBAL_EDGE_TELEMETRY.get("edge_events_received", 0) + accepted
            )
            self._send_json({"success": True, "accepted": accepted})
        except Exception as exc:
            self._send_json({"success": False, "error": str(exc)})

    def _handle_api_edge_mouth_sync(self, body: dict) -> None:
        action = str(body.get("action", "generate")).strip().lower()
        utterance_id = str(body.get("utterance_id", f"utt_{int(time.time()*1000)}")).strip()

        if action == "cancel":
            _GLOBAL_MOUTH_SYNC.cancel_utterance(utterance_id)
            self._send_json({"success": True, "cancelled": True, "utterance_id": utterance_id})
            return

        text = str(body.get("text", "")).strip()
        duration_ms = body.get("duration_ms")
        timeline = _GLOBAL_MOUTH_SYNC.generate_timeline(
            utterance_id=utterance_id,
            text=text,
            target_duration_ms=int(duration_ms) if duration_ms else None,
        )
        self._send_json({"success": True, "timeline": timeline.to_dict()})

    def _handle_api_edge_pair(self, body: dict) -> None:
        global _GLOBAL_EDGE_PAIRING_PIN, _GLOBAL_PAIRED_EDGE_DEVICES
        device_id = str(body.get("device_id", "EDGE-PI5-DESK-01")).strip()
        device_label = str(body.get("device_label", "Bàn Làm Việc Quanpt1")).strip()
        pairing_pin = str(body.get("pairing_pin", "")).strip()

        if pairing_pin != _GLOBAL_EDGE_PAIRING_PIN:
            _GLOBAL_EDGE_MONITOR.record_auth_failure(
                "Mã PIN ghép cặp không chính xác",
                metadata={"attempted_pin": pairing_pin, "device_id": device_id},
            )
            self._send_error_json("Mã PIN ghép cặp không chính xác. Vui lòng kiểm tra mã PIN hiển thị trên Bàn Điều Hành PC.", 403)
            return

        import secrets
        shared_secret = secrets.token_hex(32)
        now_ts = datetime.now(timezone.utc).isoformat()
        lan_ip = get_local_lan_ip()

        _GLOBAL_PAIRED_EDGE_DEVICES[device_id] = {
            "device_id": device_id,
            "device_label": device_label,
            "shared_secret": shared_secret,
            "paired_at_utc": now_ts,
            "last_seen_utc": now_ts,
            "status": "ONLINE_PAIRED",
        }

        # Update monitor
        _GLOBAL_EDGE_MONITOR.record_pairing(device_id, device_label)
        _GLOBAL_EDGE_MONITOR.record_heartbeat(device_id)

        self._send_json({
            "success": True,
            "device_id": device_id,
            "device_label": device_label,
            "shared_secret": shared_secret,
            "core_host": lan_ip,
            "core_port": 8766,
            "paired_at_utc": now_ts,
            "message": "Ghép cặp thiết bị Edge thành công! Khóa bí mật đã được lưu.",
        })

    def _handle_api_executive_emergency(self, body: dict) -> None:
        action = str(body.get("action", "")).strip().lower()
        reason = str(body.get("reason", "Action requested from Executive Cockpit"))
        if action not in ("stop", "freeze", "resume", "normal"):
            self._send_error_json("Invalid action; must be 'stop', 'freeze', or 'resume'", 400)
            return
        target_state = "normal" if action in ("resume", "normal") else action
        workspace = _find_workspace_root()
        try:
            from quan_ai_brain.governance.state_store import GovernanceStateStore
            gov_store = GovernanceStateStore(workspace / "data" / "governance.db", workspace=workspace)
            record = gov_store.set_emergency_state(
                state=target_state,
                reason=reason,
                activated_by="Quanpt1 (Executive Cockpit)",
            )
            self._send_json({
                "success": True,
                "emergency_state": record.state,
                "activated_by": record.activated_by,
                "activated_at": record.activated_at_utc,
            })
        except Exception as exc:
            self._send_error_json(f"Emergency state error: {exc}", 500)

    def _handle_api_voice_get_config(self) -> None:
        global _GLOBAL_WAKE_CONFIG
        self._send_json({
            "success": True,
            "config": _GLOBAL_WAKE_CONFIG.to_dict(),
        })

    def _handle_api_voice_set_config(self, body: dict) -> None:
        global _GLOBAL_WAKE_CONFIG
        try:
            enabled = bool(body.get("enabled", _GLOBAL_WAKE_CONFIG.enabled))
            lang = str(body.get("language_mode", _GLOBAL_WAKE_CONFIG.language_mode))
            timeout_val = body.get("silence_timeout_seconds", body.get("silence_timeout_sec", _GLOBAL_WAKE_CONFIG.silence_timeout_seconds))
            silence_timeout = float(timeout_val)
            chime_enabled = bool(body.get("chime_enabled", _GLOBAL_WAKE_CONFIG.chime_enabled))

            _GLOBAL_WAKE_CONFIG.enabled = enabled
            _GLOBAL_WAKE_CONFIG.language_mode = lang
            _GLOBAL_WAKE_CONFIG.silence_timeout_seconds = silence_timeout
            _GLOBAL_WAKE_CONFIG.chime_enabled = chime_enabled

            # Check if toggling specific keyword item
            if "keyword_id" in body and "keyword_enabled" in body:
                _GLOBAL_WAKE_CONFIG.update_item(str(body["keyword_id"]), bool(body["keyword_enabled"]))

            self._send_json({
                "success": True,
                "config": _GLOBAL_WAKE_CONFIG.to_dict(),
            })
        except Exception as exc:
            self._send_error_json(f"Failed to update wake config: {exc}", 400)

    def _handle_api_voice_get_tts_config(self) -> None:
        self._send_json({
            "success": True,
            **GLOBAL_TTS_MANAGER.get_config(),
        })

    def _handle_api_voice_get_tts_voices(self) -> None:
        active = GLOBAL_TTS_MANAGER.get_active_voice()
        self._send_json({
            "success": True,
            "voices": [v.to_dict() for v in GLOBAL_TTS_MANAGER.available_voices],
            "active_voice": active.to_dict() if active else None,
        })

    def _handle_api_voice_set_tts_config(self, body: dict) -> None:
        enabled = body.get("enabled", body.get("tts_enabled"))
        voice_id = body.get("voice_id", body.get("tts_voice_preference"))
        rate = body.get("rate")
        pitch = body.get("pitch")
        volume = body.get("volume")
        provider = body.get("provider")
        locale = body.get("locale", body.get("tts_locale"))

        ok = GLOBAL_TTS_MANAGER.update_config(
            enabled=enabled,
            voice_id=voice_id,
            rate=rate,
            pitch=pitch,
            volume=volume,
            provider=provider,
            locale=locale,
        )
        if not ok:
            self._send_error_json(GLOBAL_TTS_MANAGER.config.last_error or "Cập nhật cấu hình TTS thất bại.", 400)
            return

        self._send_json({
            "success": True,
            **GLOBAL_TTS_MANAGER.get_config(),
        })

    def _handle_api_voice_tts_synthesize(self, body: dict) -> None:
        import base64
        text = str(body.get("text", "")).strip()
        if not text:
            self._send_error_json("Văn bản tổng hợp âm thanh không được để trống.", 400)
            return

        voice_id = body.get("voice_id")
        audio_bytes, err = GLOBAL_TTS_MANAGER.synthesize_audio(text, voice_id=voice_id)
        if not audio_bytes:
            status_code = 400 if GLOBAL_TTS_MANAGER.config.status == TTSStatus.ERROR.value else 503
            self._send_json({
                "success": False,
                "status": GLOBAL_TTS_MANAGER.config.status,
                "error": err or "Không thể tạo âm thanh giọng nói.",
                "audio_base64": None,
            }, status=status_code)
            return

        # Generate mouth sync timeline
        clean_text = normalize_text_for_vietnamese_tts(text)
        timeline = _GLOBAL_MOUTH_SYNC.generate_timeline(
            utterance_id=f"utt_synth_{int(time.time()*1000)}",
            text=clean_text,
        )

        active = GLOBAL_TTS_MANAGER.get_active_voice()
        audio_b64 = base64.b64encode(audio_bytes).decode("ascii")
        self._send_json({
            "success": True,
            "status": "READY",
            "audio_base64": audio_b64,
            "format": "audio/mpeg",
            "text": clean_text,
            "voice_id": active.voice_id if active else GLOBAL_TTS_MANAGER.active_voice_id,
            "locale": active.locale if active else "vi-VN",
            "gender": active.gender if active else "female",
            "timeline": timeline.to_dict(),
        })

    def _handle_api_voice_telemetry(self, body: dict) -> None:
        state = str(body.get("state", "UNKNOWN"))
        event = str(body.get("event", ""))
        keyword = str(body.get("keyword", ""))
        sys.stdout.write(f"[VOICE-TELEMETRY] state={state} event={event} keyword={keyword}\n")
        sys.stdout.flush()
        self._send_json({"success": True})

    def _handle_api_edge_list_files(self) -> None:
        workspace = _find_workspace_root()
        local_assets_dir = workspace / "edge_client" / "assets" / "avatar"
        local_files = []
        if local_assets_dir.exists() and local_assets_dir.is_dir():
            for p in sorted(local_assets_dir.iterdir()):
                if p.is_file() and not p.name.startswith("."):
                    stat = p.stat()
                    local_files.append({
                        "name": p.name,
                        "size": stat.st_size,
                        "mtime": int(stat.st_mtime),
                        "url": f"/edge_client/assets/avatar/{p.name}",
                        "ext": p.suffix.lower(),
                    })

        # Include root edge client scripts so Pi 5 sync_assets updates root files as well
        edge_root = workspace / "edge_client"
        for rf in ["avatar_engine.js", "kiosk.html", "kiosk.js", "kiosk.css", "client_daemon.py"]:
            rf_path = edge_root / rf
            if rf_path.exists():
                local_files.append({
                    "name": f"../../{rf}",
                    "size": rf_path.stat().st_size,
                    "mtime": int(rf_path.stat().st_mtime),
                    "url": f"/edge_client/{rf}",
                    "ext": rf_path.suffix.lower(),
                })

        edge_resp = _send_edge_request("/api/kiosk/files", method="GET", timeout=3.0)
        remote_files = edge_resp.get("files", []) if isinstance(edge_resp, dict) and edge_resp.get("success") else []
        pi5_online = not edge_resp.get("offline", False) if isinstance(edge_resp, dict) else False

        self._send_json({
            "success": True,
            "pi5_online": pi5_online,
            "edge_ip": f"{_GLOBAL_EDGE_TELEMETRY.get('edge_ip', '192.168.1.21')}:{_GLOBAL_EDGE_TELEMETRY.get('edge_port', 8768)}",
            "remote_files": remote_files,
            "local_files": local_files,
            "count": len(local_files),
        })

    def _handle_api_edge_upload_file(self, body: dict) -> None:
        import base64
        filename = str(body.get("filename", "")).strip()
        content_b64 = str(body.get("content_b64", "")).strip()
        if not filename or not content_b64:
            self._send_error_json("Missing filename or content_b64", 400)
            return

        clean_name = Path(filename).name
        allowed_exts = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".json", ".wav", ".mp3", ".js", ".css"}
        if Path(clean_name).suffix.lower() not in allowed_exts:
            self._send_error_json(f"File extension not permitted: {clean_name}", 400)
            return

        # Save locally to edge_client/assets/avatar
        workspace = _find_workspace_root()
        local_dir = workspace / "edge_client" / "assets" / "avatar"
        local_dir.mkdir(parents=True, exist_ok=True)
        try:
            file_bytes = base64.b64decode(content_b64)
            with open(local_dir / clean_name, "wb") as f:
                f.write(file_bytes)
        except Exception as exc:
            self._send_error_json(f"Lỗi lưu tệp trên PC: {exc}", 500)
            return

        # Forward to Pi 5 Kiosk Daemon
        resp = _send_edge_request(
            "/api/kiosk/files/upload",
            method="POST",
            data={"filename": clean_name, "content_b64": content_b64},
            timeout=15.0,
        )
        self._send_json({
            "success": True,
            "filename": clean_name,
            "local_saved": True,
            "pi5_synced": resp.get("success", False),
            "pi5_message": resp.get("message", resp.get("error", "")),
        })

    def _handle_api_edge_sync_all_assets(self) -> None:
        import base64
        workspace = _find_workspace_root()
        local_dir = workspace / "edge_client" / "assets" / "avatar"
        if not local_dir.exists():
            self._send_error_json("Local assets directory not found", 404)
            return

        synced = []
        errors = []
        lan_ip = get_local_lan_ip()

        # 1. Queue sync_assets command for Raspberry Pi 5 to pick up in heartbeat
        _GLOBAL_EDGE_TELEMETRY["pending_commands"].append({
            "action": "sync_assets",
            "core_url": f"http://{lan_ip}:8766",
        })

        # 2. Check once if Pi 5 port 8768 is reachable for direct push
        pi_online = False
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1.0)
            pi_online = (sock.connect_ex((_GLOBAL_EDGE_TELEMETRY.get("edge_ip", "192.168.1.21"), _GLOBAL_EDGE_TELEMETRY.get("edge_port", 8768))) == 0)
            sock.close()
        except Exception:
            pi_online = False

        # 2. Push root kiosk files and avatar assets to Pi 5
        edge_root = workspace / "edge_client"
        root_files = ["kiosk.html", "kiosk.js", "kiosk.css", "avatar_engine.js", "wake_engine.js", "setup_pi5_audio.sh"]
        for fname in root_files:
            fp = edge_root / fname
            if fp.exists() and fp.is_file():
                synced.append(fname)
                if pi_online:
                    try:
                        with open(fp, "rb") as f:
                            b64 = base64.b64encode(f.read()).decode("ascii")
                        _send_edge_request(
                            "/api/kiosk/files/upload",
                            method="POST",
                            data={"filename": fname, "content_b64": b64},
                            timeout=10.0,
                        )
                    except Exception:
                        pass

        for p in sorted(local_dir.iterdir()):
            if p.is_file() and not p.name.startswith("."):
                synced.append(p.name)
                if pi_online:
                    try:
                        with open(p, "rb") as f:
                            b64 = base64.b64encode(f.read()).decode("ascii")
                        _send_edge_request(
                            "/api/kiosk/files/upload",
                            method="POST",
                            data={"filename": p.name, "content_b64": b64},
                            timeout=10.0,
                        )
                    except Exception:
                        pass

        # 3. Queue reload_ui command for Pi 5
        _GLOBAL_EDGE_TELEMETRY["pending_commands"].append({"action": "reload_ui"})


        self._send_json({
            "success": True,
            "synced_count": len(synced),
            "synced_files": synced,
            "errors": errors,
            "message": f"Đã phát lệnh đồng bộ {len(synced)} tài sản sang Pi 5 qua Wi-Fi và yêu cầu tải lại giao diện.",
        })

    def _handle_api_edge_delete_file(self, body: dict) -> None:
        filename = str(body.get("filename", "")).strip()
        clean_name = Path(filename).name
        if not clean_name:
            self._send_error_json("Filename is required", 400)
            return

        resp = _send_edge_request(
            "/api/kiosk/files/delete",
            method="POST",
            data={"filename": clean_name},
        )
        self._send_json(resp)

    def _handle_api_edge_remote_action(self, body: dict) -> None:
        self._handle_api_edge_control(body)

    # =========================================================================
    # REMOTE SENSORS, AUDIO CONTROL & CAMERA VIEW (ADDENDUM V2.1)
    # =========================================================================

    def _get_captures_dir(self) -> Path:
        workspace = _find_workspace_root()
        captures_dir = workspace / "data" / "edge_media" / "captures"
        captures_dir.mkdir(parents=True, exist_ok=True)
        return captures_dir

    def _handle_api_edge_audio_status(self) -> None:
        """Fetch remote microphone and audio status from Pi 5."""
        resp = _send_edge_request("/api/kiosk/audio/status", method="GET", timeout=3.0)
        if isinstance(resp, dict) and not resp.get("offline", False):
            self._send_json({
                "success": True,
                "pi5_online": True,
                "audio": resp,
            })
        else:
            self._send_json({
                "success": False,
                "pi5_online": False,
                "error": "Pi 5 offline hoặc chưa khởi động Kiosk Daemon",
                "audio": {
                    "mic_enabled": False,
                    "mic_muted": True,
                    "wake_word_enabled": False,
                    "listening_mode": "OFF",
                    "audio_level_db": -99.0,
                    "status": "DISCONNECTED",
                    "device_name": "Jieli Technology UACDemoV1.0 (Chưa kết nối)",
                },
            })

    def _handle_api_edge_audio_control(self, body: dict) -> None:
        """Dispatch microphone control command (mic_on, mic_off, mute, unmute, wake_word_toggle, test_mic)."""
        action = str(body.get("action", "")).strip().lower()
        resp = _send_edge_request("/api/kiosk/audio/control", method="POST", data=body, timeout=6.0)

        if isinstance(resp, dict) and resp.get("offline"):
            self._send_json({
                "success": False,
                "action": action,
                "error": "COMMAND_NOT_DELIVERED: Pi 5 offline, không thể gửi lệnh điều khiển micro.",
                "offline": True,
            }, status=503)
            return

        if isinstance(resp, dict) and not resp.get("success", False):
            if "error" in resp:
                _GLOBAL_EDGE_MONITOR.record_mic_fault(resp["error"])

        self._send_json(resp)

    def _handle_api_music_search(self, body: dict) -> None:
        query = str(body.get("query", "")).strip()
        limit = int(body.get("limit", 5))
        if not query:
            self._send_error_json("Missing search query", 400)
            return
        results = search_youtube_music(query, max_results=limit)
        self._send_json({"success": True, "query": query, "count": len(results), "results": results})

    def _handle_api_music_play(self, body: dict) -> None:
        video_id = str(body.get("video_id", "")).strip()
        title = str(body.get("title", "")).strip()
        url = str(body.get("url", "")).strip()
        edge_ip = _GLOBAL_EDGE_TELEMETRY.get("edge_ip", "192.168.1.21")
        edge_port = _GLOBAL_EDGE_TELEMETRY.get("edge_port", 8768)
        if not url and video_id:
            url = f"https://www.youtube.com/watch?v={video_id}"
        if not url and not video_id:
            query = str(body.get("query", "")).strip()
            if query:
                results = search_youtube_music(query, max_results=1)
                if results:
                    video_id = results[0]["video_id"]
                    title = results[0]["title"]
                    url = results[0]["url"]
        if not url:
            self._send_error_json("Could not find music to play", 400)
            return
        res = dispatch_play_music_to_pi5(video_id=video_id, title=title, url=url, edge_ip=edge_ip, edge_port=edge_port)
        self._send_json({"success": True, "title": title, "url": url, "video_id": video_id, "pi5_response": res})

    def _handle_api_music_stop(self) -> None:
        edge_ip = _GLOBAL_EDGE_TELEMETRY.get("edge_ip", "192.168.1.21")
        edge_port = _GLOBAL_EDGE_TELEMETRY.get("edge_port", 8768)
        res = dispatch_stop_music_to_pi5(edge_ip=edge_ip, edge_port=edge_port)
        self._send_json({"success": True, "playing": False, "pi5_response": res})

    def _handle_api_music_status(self) -> None:
        res = _send_edge_request("/api/kiosk/music/status", method="GET")
        self._send_json({"success": True, "edge_music": res.get("music"), "playing": res.get("playing", False)})

    def _handle_api_edge_camera_status(self) -> None:
        """Fetch remote camera status from Pi 5."""
        resp = _send_edge_request("/api/kiosk/camera/status", method="GET", timeout=3.0)
        if isinstance(resp, dict) and not resp.get("offline", False):
            self._send_json({
                "success": True,
                "pi5_online": True,
                "camera": resp,
            })
        else:
            self._send_json({
                "success": False,
                "pi5_online": False,
                "error": "Pi 5 offline hoặc camera chưa sẵn sàng",
                "camera": {
                    "camera_enabled": False,
                    "camera_streaming": False,
                    "status": "CAMERA_OFF",
                    "device_name": "Sirius USB2.0 Camera (Chưa kết nối)",
                },
            })

    def _handle_api_edge_camera_control(self, body: dict) -> None:
        """Dispatch camera control command (camera_on, camera_off, start_live, stop_live)."""
        action = str(body.get("action", "")).strip().lower()
        resp = _send_edge_request("/api/kiosk/camera/control", method="POST", data=body, timeout=5.0)

        if isinstance(resp, dict) and resp.get("offline"):
            self._send_json({
                "success": False,
                "action": action,
                "error": "COMMAND_NOT_DELIVERED: Pi 5 offline, không thể gửi lệnh điều khiển camera.",
                "offline": True,
            }, status=503)
            return

        self._send_json(resp)

    def _handle_api_edge_camera_snapshot(self) -> None:
        """Request Pi 5 to capture a single camera snapshot and stream it back."""
        resp = _send_edge_request("/api/kiosk/camera/capture", method="POST", data={}, timeout=10.0)
        if isinstance(resp, dict) and resp.get("offline"):
            self._send_json({
                "success": False,
                "error": "COMMAND_NOT_DELIVERED: Pi 5 offline, không thể chụp ảnh.",
                "offline": True,
            }, status=503)
            return

        if isinstance(resp, dict) and not resp.get("success", False):
            _GLOBAL_EDGE_MONITOR.record_camera_fault(resp.get("error", "Chụp ảnh camera thất bại"))

        if isinstance(resp, dict) and resp.get("success"):
            if "capture_id" in resp and "snapshot_id" not in resp:
                resp["snapshot_id"] = resp["capture_id"]
            if "image_base64" in resp and "image_b64" not in resp:
                resp["image_b64"] = resp["image_base64"]
            if "sha256" in resp and "sha256_hash" not in resp:
                resp["sha256_hash"] = resp["sha256"]
            if "captured_at_utc" in resp and "timestamp" not in resp:
                resp["timestamp"] = resp["captured_at_utc"]

        self._send_json(resp)

    def _handle_api_edge_camera_stream(self) -> None:
        """Proxy camera live frame from Raspberry Pi 5."""
        edge_ip = _GLOBAL_EDGE_TELEMETRY.get("edge_ip", "192.168.1.21")
        edge_port = _GLOBAL_EDGE_TELEMETRY.get("edge_port", 8768)
        url = f"http://{edge_ip}:{edge_port}/api/kiosk/camera/stream"
        try:
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=3.0) as resp:
                frame_data = resp.read()
                self.send_response(200)
                self.send_header("Content-Type", "image/jpeg")
                self.send_header("Content-Length", str(len(frame_data)))
                self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
                self.end_headers()
                self.wfile.write(frame_data)
        except urllib.error.HTTPError as he:
            self.send_response(he.code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps({"success": False, "error": f"Camera stream error: {he.reason}"}).encode("utf-8"))
        except Exception as exc:
            self.send_response(503)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps({"success": False, "error": f"Camera stream unavailable: {exc}"}).encode("utf-8"))

    def _handle_api_edge_camera_save(self, body: dict) -> None:
        """Validate hash integrity, enforce PathGuard and persist snapshot into Core capture library."""
        import base64
        import hashlib
        b64_data = str(body.get("image_base64") or body.get("image_b64") or "").strip()
        expected_hash = str(body.get("sha256") or body.get("content_hash") or body.get("sha256_hash") or "").strip().lower()
        capture_id = str(body.get("capture_id") or body.get("snapshot_id") or f"cap_{int(time.time()*1000)}").strip()
        captured_at = str(body.get("captured_at_utc") or body.get("captured_at") or body.get("timestamp") or datetime.now(timezone.utc).isoformat()).strip()
        device_id = str(body.get("device_id", "EDGE-PI5-DESK-01")).strip()
        purpose = str(body.get("purpose", "Chụp ảnh theo yêu cầu chủ sở hữu")).strip()

        if not b64_data:
            self._send_error_json("Dữ liệu ảnh rỗng (image_base64 is required)", 400)
            return

        try:
            image_bytes = base64.b64decode(b64_data)
        except Exception as e:
            self._send_error_json(f"Lỗi giải mã base64: {e}", 400)
            return

        # 1. Cryptographic SHA-256 Hash Verification (CAM-04 / NET-02)
        computed_hash = hashlib.sha256(image_bytes).hexdigest().lower()
        if expected_hash and computed_hash != expected_hash:
            self._send_json({
                "success": False,
                "error": f"HASH_MISMATCH: Hash tính toán ({computed_hash[:12]}...) không khớp hash khai báo ({expected_hash[:12]}...). Từ chối lưu trữ ảnh.",
                "verification_status": "FAILED",
                "computed_hash": computed_hash,
                "expected_hash": expected_hash,
            }, status=400)
            return

        # 2. PathGuard Confinement (UI-02)
        captures_dir = self._get_captures_dir().resolve()
        clean_ts = captured_at.replace(":", "-").replace(".", "_")
        filename_base = f"{clean_ts}_{capture_id}"
        img_path = (captures_dir / f"{filename_base}.jpg").resolve()
        meta_path = (captures_dir / f"{filename_base}.json").resolve()

        if not str(img_path).startswith(str(captures_dir)):
            self._send_error_json("PathGuard: Thư mục lưu trữ vượt ra ngoài phạm vi cho phép", 403)
            return

        metadata = {
            "capture_id": capture_id,
            "snapshot_id": capture_id,
            "source_device_id": device_id,
            "captured_at": captured_at,
            "timestamp": captured_at,
            "received_at": datetime.now(timezone.utc).isoformat(),
            "content_hash": computed_hash,
            "sha256": computed_hash,
            "sha256_hash": computed_hash,
            "media_type": "image/jpeg",
            "size_bytes": len(image_bytes),
            "capture_mode": "SNAPSHOT_ON_DEMAND",
            "purpose": purpose,
            "retention_policy": "OWNER_CONTROLLED_30D",
            "verification_status": "VERIFIED_PASS",
            "relative_file": f"data/edge_media/captures/{filename_base}.jpg",
            "file_path": f"data/edge_media/captures/{filename_base}.jpg",
            "filename": f"{filename_base}.jpg",
        }

        try:
            img_path.write_bytes(image_bytes)
            meta_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
            self._send_json({
                "success": True,
                "capture_id": capture_id,
                "snapshot_id": capture_id,
                "saved_path": metadata["relative_file"],
                "file_path": metadata["relative_file"],
                "filename": metadata["filename"],
                "size_bytes": len(image_bytes),
                "sha256": computed_hash,
                "sha256_hash": computed_hash,
                "verification_status": "VERIFIED_PASS",
                "message": f"Ảnh đã được xác minh toàn vẹn và lưu trữ an toàn tại {metadata['relative_file']}",
            })
        except Exception as exc:
            self._send_error_json(f"Lỗi ghi tệp lưu trữ Core: {exc}", 500)

    def _handle_api_edge_camera_library(self, query_str: str) -> None:
        """List all verified snapshots stored in Core library."""
        captures_dir = self._get_captures_dir().resolve()
        captures: list[dict[str, Any]] = []
        total_bytes = 0

        for json_file in sorted(captures_dir.glob("*.json"), reverse=True):
            try:
                meta = json.loads(json_file.read_text(encoding="utf-8"))
                img_file = captures_dir / meta.get("filename", json_file.stem + ".jpg")
                if img_file.exists():
                    total_bytes += img_file.stat().st_size
                    meta["exists"] = True
                    meta["size_bytes"] = img_file.stat().st_size
                    # Aliases for UI flexibility
                    if "snapshot_id" not in meta and "capture_id" in meta:
                        meta["snapshot_id"] = meta["capture_id"]
                    if "sha256_hash" not in meta and "sha256" in meta:
                        meta["sha256_hash"] = meta["sha256"]
                    if "timestamp" not in meta and "captured_at" in meta:
                        meta["timestamp"] = meta["captured_at"]
                    captures.append(meta)
            except Exception:
                pass

        self._send_json({
            "success": True,
            "total_count": len(captures),
            "total_size_bytes": total_bytes,
            "total_size_kb": round(total_bytes / 1024.0, 1),
            "quota_bytes": 500 * 1024 * 1024,  # 500MB quota
            "storage_path": "data/edge_media/captures/",
            "storage_dir": "data/edge_media/captures/",
            "captures": captures,
            "items": captures,
        })

    def _handle_api_edge_camera_serve_image(self, query_str: str) -> None:
        """Serve a stored capture image securely."""
        params = urllib.parse.parse_qs(query_str)
        ident = params.get("file", [""])[0] or params.get("id", [""])[0]
        clean_name = Path(ident).name
        if not clean_name:
            self.send_error(400, "Invalid file or id parameter")
            return

        captures_dir = self._get_captures_dir().resolve()

        # Find file: direct filename or match by snapshot/capture ID
        target = captures_dir / clean_name
        if not target.exists() and not clean_name.endswith((".jpg", ".jpeg", ".png")):
            # Try adding .jpg
            cand = captures_dir / f"{clean_name}.jpg"
            if cand.exists():
                target = cand
            else:
                # Search json metadata for matching capture_id
                for jf in captures_dir.glob("*.json"):
                    try:
                        m = json.loads(jf.read_text(encoding="utf-8"))
                        if m.get("capture_id") == clean_name or m.get("snapshot_id") == clean_name:
                            fn = m.get("filename", jf.stem + ".jpg")
                            if (captures_dir / fn).exists():
                                target = captures_dir / fn
                                break
                    except Exception:
                        pass

        # PathGuard bounds check
        if not str(target.resolve()).startswith(str(captures_dir)):
            self.send_error(403, "PathGuard: Access outside captures directory blocked")
            return

        if target.exists() and target.is_file():
            self._serve_file(target)
        else:
            self.send_error(404, "Image not found")

    def _handle_api_edge_camera_delete(self, body: dict) -> None:
        """Delete a capture from library with owner verification and PathGuard confinement."""
        ident = str(body.get("filename") or body.get("id") or body.get("snapshot_id") or body.get("capture_id") or "").strip()
        clean_name = Path(ident).name
        if not clean_name:
            self._send_error_json("Filename or ID is required", 400)
            return

        captures_dir = self._get_captures_dir().resolve()

        # Path traversal guard (UI-02)
        if ".." in ident or "/" in ident or "\\" in ident:
            # Check if resolved path escapes
            test_path = (captures_dir / ident).resolve()
            if not str(test_path).startswith(str(captures_dir)):
                self._send_error_json("PathGuard: Đường dẫn vượt quá giới hạn thư mục captures", 403)
                return

        img_target = captures_dir / clean_name
        meta_target = captures_dir / (Path(clean_name).stem + ".json")

        if not img_target.exists():
            # Match by capture_id / snapshot_id in json
            for jf in captures_dir.glob("*.json"):
                try:
                    m = json.loads(jf.read_text(encoding="utf-8"))
                    if m.get("capture_id") == clean_name or m.get("snapshot_id") == clean_name:
                        meta_target = jf
                        fn = m.get("filename", jf.stem + ".jpg")
                        img_target = captures_dir / fn
                        break
                except Exception:
                    pass

        deleted = False
        if img_target.exists():
            img_target.unlink(missing_ok=True)
            deleted = True
        if meta_target.exists():
            meta_target.unlink(missing_ok=True)
            deleted = True

        if deleted:
            self._send_json({
                "success": True,
                "deleted": clean_name,
                "message": f"Đã xóa ảnh {clean_name} an toàn khỏi thư viện PC Core.",
            })
        else:
            self._send_error_json(f"Không tìm thấy ảnh {clean_name}", 404)

    def _handle_api_edge_startup_sequence(self, body: dict) -> None:
        """Chu trình khởi động đồng bộ Raspberry Pi 5:
        1. Phát lời chào từ loa Pi 5: 'Chào anh ạ, rất vui được gặp anh.'
        2. Tự động kiểm tra microphone & camera phần cứng trên Pi 5.
        3. Tổng hợp báo cáo hiện trạng và phát ra loa của Pi 5.
        """
        greeting_text = str(body.get("greeting", "Chào anh ạ, rất vui được gặp anh.")).strip()

        # Check if Pi 5 is reachable
        status_check = _send_edge_request("/api/kiosk/status", method="GET", timeout=2.0)
        if isinstance(status_check, dict) and status_check.get("offline"):
            self._send_json({
                "success": False,
                "pi5_online": False,
                "message": "Raspberry Pi 5 hiện chưa kết nối mạng hoặc daemon chưa sẵn sàng.",
            })
            return

        # 1. Phát câu chào ra loa Pi 5
        greeting_bytes, _ = GLOBAL_TTS_MANAGER.synthesize_audio(greeting_text)
        greeting_b64 = base64.b64encode(greeting_bytes).decode("ascii") if greeting_bytes else None

        greet_res = _send_edge_request(
            "/api/kiosk/control",
            method="POST",
            data={
                "action": "speak",
                "text": greeting_text,
                "state": "SPEAKING",
                "audio_base64": greeting_b64,
                "force_hardware": True,
                "duration_ms": max(2200, len(greeting_text) * 120),
            },
            timeout=5.0,
        )

        # 2. Thực hiện tự kiểm tra mic và camera
        time.sleep(1.8)
        test_res = _send_edge_request(
            "/api/kiosk/control",
            method="POST",
            data={"action": "self_test"},
            timeout=6.0,
        )

        mic_ok = True
        cam_ok = True
        mic_details = {}
        cam_details = {}

        if isinstance(test_res, dict) and test_res.get("success"):
            mic_ok = bool(test_res.get("mic_ok", True))
            cam_ok = bool(test_res.get("camera_ok", True))
            mic_details = test_res.get("mic_data", {})
            cam_details = test_res.get("camera_data", {})

        # 3. Soạn văn bản báo cáo hiện trạng
        if mic_ok and cam_ok:
            report_text = "Báo cáo anh: Hệ thống Micro hoạt động tốt, Camera hoạt động tốt. Sẵn sàng phục vụ anh ạ."
        elif mic_ok and not cam_ok:
            report_text = "Báo cáo anh: Hệ thống Micro hoạt động tốt, Camera chưa nhận diện. Các dịch vụ khác sẵn sàng phục vụ anh ạ."
        elif not mic_ok and cam_ok:
            report_text = "Báo cáo anh: Micro cần kiểm tra lại, Camera hoạt động tốt. Sẵn sàng phục vụ anh ạ."
        else:
            report_text = "Báo cáo anh: Cần kiểm tra lại kết nối Micro và Camera trên Pi. Hệ thống điều hành vẫn sẵn sàng phục vụ anh ạ."

        # 4. Phát câu báo cáo ra loa Pi 5
        report_bytes, _ = GLOBAL_TTS_MANAGER.synthesize_audio(report_text)
        report_b64 = base64.b64encode(report_bytes).decode("ascii") if report_bytes else None

        rep_res = _send_edge_request(
            "/api/kiosk/control",
            method="POST",
            data={
                "action": "speak",
                "text": report_text,
                "state": "SPEAKING",
                "audio_base64": report_b64,
                "force_hardware": True,
                "duration_ms": max(3200, len(report_text) * 115),
            },
            timeout=6.0,
        )

        self._send_json({
            "success": True,
            "pi5_online": True,
            "greeting_sent": bool(isinstance(greet_res, dict) and greet_res.get("success")),
            "greeting_text": greeting_text,
            "mic_ok": mic_ok,
            "camera_ok": cam_ok,
            "report_text": report_text,
            "report_sent": bool(isinstance(rep_res, dict) and rep_res.get("success")),
            "mic_details": mic_details,
            "camera_details": cam_details,
        })

    def _handle_api_executive_roles(self) -> None:
        roles_list = []
        for role, meta in ROLE_METADATA.items():
            roles_list.append({
                "role_id": role.value,
                "title_vi": meta["title_vi"],
                "description": meta["description"],
                "icon": meta["icon"],
                "priority": meta["priority"],
                "is_active": role == _GLOBAL_ROLE_ORCHESTRATOR.current_role,
            })
        self._send_json({
            "success": True,
            "roles": roles_list,
            "current_role": _GLOBAL_ROLE_ORCHESTRATOR.current_role.value,
        })

    def _handle_api_voice_interact(self, body: dict) -> None:
        text = str(body.get("text") or body.get("query", "")).strip()
        is_push_to_talk = bool(body.get("is_push_to_talk", True))
        playback_active = bool(body.get("playback_active", False))
        res = _GLOBAL_VOICE_PIPELINE.handle_voice_input(
            text,
            is_push_to_talk=is_push_to_talk,
            current_playback_active=playback_active,
        )

        spoken = res.spoken_text or res.response_text
        audio_b64 = None
        try:
            import base64
            voice_id = str(body.get("voice_id", "vi-VN-HoaiMyNeural"))
            audio_bytes, _ = GLOBAL_TTS_MANAGER.synthesize_audio(spoken, voice_id=voice_id)
            if audio_bytes:
                audio_b64 = base64.b64encode(audio_bytes).decode("ascii")
        except Exception:
            pass

        timeline_dict = res.mouth_timeline
        if not timeline_dict:
            timeline_dict = _GLOBAL_MOUTH_SYNC.generate_timeline(
                utterance_id=f"utt_voice_{int(time.time()*1000)}",
                text=spoken,
                target_duration_ms=int(max(1000, len(spoken) * 110)),
            ).to_dict()

        # Update telemetry state and dispatch to Raspberry Pi 5 if connected
        _GLOBAL_EDGE_TELEMETRY["target_avatar_state"] = "SPEAKING"
        _GLOBAL_EDGE_TELEMETRY["transcript"] = spoken

        if audio_b64:
            cmd_data = {
                "action": "speak",
                "text": spoken,
                "state": "SPEAKING",
                "timeline": timeline_dict,
                "audio_base64": audio_b64,
            }
            threading.Thread(
                target=_send_edge_request,
                args=("/api/kiosk/control", "POST", cmd_data, 10.0),
                daemon=True,
            ).start()

        self._send_json({
            "success": True,
            "query": res.query,
            "response_text": res.response_text,
            "reply": res.response_text,
            "spoken_text": spoken,
            "audio_base64": audio_b64,
            "has_audio": bool(audio_b64),
            "active_role": res.active_role,
            "state": res.state,
            "barge_in": res.barge_in_occurred,
            "mouth_timeline": timeline_dict,
            "duration_ms": res.duration_ms,
        })


    def _handle_api_voice_barge_in(self, body: dict) -> None:
        reason = str(body.get("reason", "User interrupted")).strip()
        interrupted = _GLOBAL_VOICE_PIPELINE.process_barge_in(reason)
        self._send_json({"success": True, "interrupted": interrupted})

    def _handle_api_edge_transfer_initiate(self, body: dict) -> None:
        try:
            device_id = str(body.get("device_id", "pi5_kiosk_01"))
            direction_str = str(body.get("direction", "PC_TO_EDGE"))
            direction = TransferDirection(direction_str)
            relative_path = str(body.get("relative_path", "")).strip()
            classification_str = str(body.get("classification", "INTERNAL_OPERATIONAL"))
            classification = DataClassification(classification_str)
            content_bytes_b64 = body.get("content_base64")

            import base64
            if content_bytes_b64:
                content_bytes = base64.b64decode(content_bytes_b64)
            else:
                content_str = str(body.get("content", ""))
                content_bytes = content_str.encode("utf-8")

            manifest = _GLOBAL_TRANSFER_SERVICE.initiate_transfer(
                device_id=device_id,
                direction=direction,
                relative_path=relative_path,
                content_bytes=content_bytes,
                classification=classification,
            )
            self._send_json({
                "success": manifest.status == TransferStatus.IN_PROGRESS,
                "manifest": manifest.to_dict(),
            })
        except Exception as exc:
            self._send_error_json(str(exc), 400)

    def _handle_api_edge_transfer_chunk(self, body: dict) -> None:
        try:
            transfer_id = str(body.get("transfer_id", ""))
            chunk_index = int(body.get("chunk_index", 0))
            total_chunks = int(body.get("total_chunks", 1))
            chunk_data_b64 = str(body.get("chunk_data_base64", ""))
            chunk_hash = str(body.get("chunk_hash", ""))

            import base64
            data_bytes = base64.b64decode(chunk_data_b64)
            chunk = TransferChunk(
                transfer_id=transfer_id,
                chunk_index=chunk_index,
                total_chunks=total_chunks,
                data_bytes=data_bytes,
                chunk_hash=chunk_hash,
            )
            success, msg, manifest = _GLOBAL_TRANSFER_SERVICE.receive_chunk(chunk)
            self._send_json({
                "success": success,
                "message": msg,
                "manifest": manifest.to_dict() if manifest else None,
            })
        except Exception as exc:
            self._send_error_json(str(exc), 400)

    def _handle_api_edge_transfer_ack(self, body: dict) -> None:
        transfer_id = str(body.get("transfer_id", ""))
        receiver_hash = str(body.get("receiver_hash", ""))
        success, msg = _GLOBAL_TRANSFER_SERVICE.acknowledge_transfer(transfer_id, receiver_hash)
        self._send_json({"success": success, "message": msg})

    def _handle_api_edge_transfer_status(self, query_str: str) -> None:
        params = urllib.parse.parse_qs(query_str)
        transfer_id = params.get("transfer_id", [""])[0]
        status = _GLOBAL_TRANSFER_SERVICE.get_transfer_status(transfer_id)
        if not status:
            self._send_error_json("Transfer not found", 404)
            return
        self._send_json({"success": True, "manifest": status.to_dict()})

    def _handle_api_edge_transfer_history(self, query_str: str) -> None:
        params = urllib.parse.parse_qs(query_str)
        limit = int(params.get("limit", [20])[0])
        history = _GLOBAL_TRANSFER_SERVICE.list_transfers(limit=limit)
        self._send_json({
            "success": True,
            "transfers": [m.to_dict() for m in history],
        })

    def _handle_api_edge_release_create(self, body: dict) -> None:
        try:
            version = str(body.get("version", "1.1.0")).strip()
            notes = str(body.get("notes", "Automated release")).strip()
            manifest = _GLOBAL_RELEASE_MANAGER.create_release(version=version, release_notes=notes)
            self._send_json({"success": True, "release": manifest.to_dict()})
        except Exception as exc:
            self._send_error_json(str(exc), 400)

    def _handle_api_edge_release_stage(self, body: dict) -> None:
        try:
            release_id = str(body.get("release_id", "")).strip()
            success, msg = _GLOBAL_RELEASE_MANAGER.stage_release(release_id)
            self._send_json({"success": success, "message": msg})
        except Exception as exc:
            self._send_error_json(str(exc), 400)

    def _handle_api_edge_release_activate(self, body: dict) -> None:
        try:
            release_id = str(body.get("release_id", "")).strip()
            success, msg = _GLOBAL_RELEASE_MANAGER.activate_release(release_id)
            self._send_json({"success": success, "message": msg})
        except Exception as exc:
            self._send_error_json(str(exc), 400)

    def _handle_api_edge_release_rollback(self, body: dict) -> None:
        try:
            target_release_id = body.get("target_release_id")
            success, msg = _GLOBAL_RELEASE_MANAGER.rollback_to(target_release_id)
            self._send_json({"success": success, "message": msg})
        except Exception as exc:
            self._send_error_json(str(exc), 400)

    def _handle_api_edge_release_list(self) -> None:
        releases = _GLOBAL_RELEASE_MANAGER.list_releases()
        self._send_json({
            "success": True,
            "active_version": _GLOBAL_RELEASE_MANAGER.active_version,
            "releases": [r.to_dict() for r in releases],
        })

    def _handle_api_supervisor_state(self) -> None:
        try:
            sup = _get_global_supervisor()
            task = sup.current_task
            self._send_json({
                "success": True,
                "state": sup.state.value,
                "current_task": task.to_dict() if task else None,
                "cycle_history": sup.cycle_history[-10:],
            })
        except Exception as exc:
            self._send_error_json(f"Error fetching supervisor state: {exc}", 500)

    # ------------------------------------------------------------------
    # Sprint 8 (a)+(c): To-do + Approval Center (27/10/2026)
    # ------------------------------------------------------------------

    def _handle_api_todos_list(self) -> None:
        try:
            from quan_ai_brain.tools.todo_store import TodoStore

            store = TodoStore(_find_workspace_root() / "data" / "todos.db")
            self._send_json({"success": True, "todos": store.list_open()})
        except Exception as exc:
            self._send_error_json(f"Error listing todos: {exc}", 500)

    def _handle_api_todos_add(self, body: dict) -> None:
        try:
            from quan_ai_brain.tools.todo_store import TodoStore

            store = TodoStore(_find_workspace_root() / "data" / "todos.db")
            item = store.add(
                title=str(body.get("title", "")),
                due=str(body.get("due", "")),
                priority=str(body.get("priority", "normal")),
            )
            self._send_json({"success": True, "todo": item})
        except ValueError as exc:
            self._send_error_json(str(exc), 400)
        except Exception as exc:
            self._send_error_json(f"Error adding todo: {exc}", 500)

    def _handle_api_todos_done(self, body: dict) -> None:
        try:
            from quan_ai_brain.tools.todo_store import TodoStore

            store = TodoStore(_find_workspace_root() / "data" / "todos.db")
            ok = store.mark_done(int(body.get("id", 0)))
            self._send_json({"success": ok}, 200 if ok else 404)
        except Exception as exc:
            self._send_error_json(f"Error completing todo: {exc}", 500)

    def _handle_api_approvals_list(self) -> None:
        try:
            from quan_ai_brain.governance.approval_cards import ApprovalCardStore

            workspace = _find_workspace_root()
            store = ApprovalCardStore(
                workspace / "data" / "governance.db", workspace=str(workspace)
            )
            cards = [
                {
                    "task_code": c.task_code,
                    "title": c.title,
                    "status": c.status,
                    "version": c.version,
                    "updated_at_utc": c.updated_at_utc,
                    "card_markdown": c.card_markdown,
                }
                for c in store.list_cards()
            ]
            self._send_json({"success": True, "cards": cards})
        except Exception as exc:
            self._send_error_json(f"Error listing approval cards: {exc}", 500)

    def _handle_api_approvals_decide(self, body: dict) -> None:
        """Duyệt/từ chối card từ dashboard. An toàn:
        - Chỉ localhost (server bind 127.0.0.1 mặc định; kiểm thêm header host).
        - Require task_code + decision + note; consume-once như chuẩn.
        """
        try:
            # localhost-only guard
            client = (self.client_address[0] if self.client_address else "")
            if client not in ("127.0.0.1", "::1"):
                self._send_error_json("Approvals API chỉ chấp nhận localhost", 403)
                return

            from quan_ai_brain.governance.approval_cards import ApprovalCardStore

            workspace = _find_workspace_root()
            store = ApprovalCardStore(
                workspace / "data" / "governance.db", workspace=str(workspace)
            )
            task_code = str(body.get("task_code", "")).strip()
            decision = str(body.get("decision", "")).strip().lower()
            note = str(body.get("note", ""))[:300]

            if not task_code:
                self._send_error_json("Thiếu task_code", 400)
                return
            if decision == "approve":
                card = store.approve_card(
                    task_code, "quanpt1",
                    auth_method="dashboard_approval_center",
                    notes=note or "Approved via dashboard Approval Center",
                )
                self._send_json({
                    "success": True, "task_code": task_code,
                    "status": card.status,
                })
            elif decision == "reject":
                if not note:
                    self._send_error_json("Từ chối phải kèm lý do (note)", 400)
                    return
                card = store.reject_card(task_code, note)
                self._send_json({
                    "success": True, "task_code": task_code,
                    "status": card.status,
                })
            else:
                self._send_error_json("decision phải là 'approve' hoặc 'reject'", 400)
        except PermissionError as exc:
            self._send_error_json(str(exc), 409)
        except KeyError as exc:
            self._send_error_json(f"Card không tồn tại: {exc}", 404)
        except Exception as exc:
            self._send_error_json(f"Error deciding approval: {exc}", 500)

    # ------------------------------------------------------------------
    # Sprint 11 (b): Experience Memory — lessons API (localhost-only, fail-closed)
    # ------------------------------------------------------------------

    def _handle_api_experience_lessons_list(self, parsed_query) -> None:
        """Danh sách lessons: candidates (chờ duyệt) + confirmed (đã duyệt)."""
        client_ip = self.client_address[0] if self.client_address else ""
        if client_ip not in ("127.0.0.1", "::1", "localhost"):
            self._send_error_json("Chỉ truy cập được từ máy chủ (localhost)", 403)
            return
        workspace = _find_workspace_root()
        try:
            from quan_ai_brain.memory.experience_consolidation import list_lessons
            from quan_ai_brain.memory.sqlite_store import MemoryStore

            store = MemoryStore(workspace / "data" / "brain.db", workspace=workspace)
            data = list_lessons(store)
            self._send_json({
                "success": True,
                "candidates": data["candidates"],
                "confirmed": data["confirmed"],
                "counts": {
                    "candidates": len(data["candidates"]),
                    "confirmed": len(data["confirmed"]),
                },
            })
        except Exception as exc:
            self._send_error_json(f"Lỗi đọc lessons: {exc}", 500)

    def _handle_api_experience_consolidate(self, body: dict) -> None:
        """Sinh lesson candidate từ kết quả nhiệm vụ (COMPLETED/FAILED)."""
        client_ip = self.client_address[0] if self.client_address else ""
        if client_ip not in ("127.0.0.1", "::1", "localhost"):
            self._send_error_json("Chỉ truy cập được từ máy chủ (localhost)", 403)
            return
        task_id = str(body.get("task_id", "")).strip()
        outcome = str(body.get("outcome", "")).strip()
        if not task_id or not outcome:
            self._send_error_json("task_id và outcome là bắt buộc", 400)
            return
        workspace = _find_workspace_root()
        try:
            from quan_ai_brain.memory.experience_consolidation import extract_candidate_lesson
            from quan_ai_brain.memory.sqlite_store import MemoryStore
            from quan_ai_brain.orchestration.task_registry import DurableTaskRegistry

            registry = DurableTaskRegistry(workspace / "data" / "tasks.db", workspace=workspace)
            task = registry.get_task(task_id)
            goal = task.goal if task else str(body.get("goal", ""))
            store = MemoryStore(workspace / "data" / "brain.db", workspace=workspace)
            result = extract_candidate_lesson(
                store,
                task_id,
                goal,
                outcome,
                result_summary=str(body.get("result_summary", "")),
            )
            self._send_json({"success": True, **result.to_dict()})
        except Exception as exc:
            self._send_error_json(f"Lỗi consolidate: {exc}", 500)

    def _handle_api_experience_lessons_promote(self, body: dict) -> None:
        """Owner duyệt lesson → VERIFIED + active. Bắt buộc owner xác nhận trong body."""
        client_ip = self.client_address[0] if self.client_address else ""
        if client_ip not in ("127.0.0.1", "::1", "localhost"):
            self._send_error_json("Chỉ truy cập được từ máy chủ (localhost)", 403)
            return
        memory_id = str(body.get("memory_id", "")).strip()
        owner_confirm = str(body.get("owner_confirm", "")).strip().upper()
        if not memory_id:
            self._send_error_json("memory_id là bắt buộc", 400)
            return
        if owner_confirm != "DUYET":
            self._send_error_json(
                "Cần owner_confirm='DUYET' — lesson chỉ promoted khi chủ sở hữu xác nhận",
                403,
            )
            return
        workspace = _find_workspace_root()
        try:
            from quan_ai_brain.memory.experience_consolidation import promote_lesson
            from quan_ai_brain.memory.sqlite_store import MemoryStore

            store = MemoryStore(workspace / "data" / "brain.db", workspace=workspace)
            result = promote_lesson(
                store,
                memory_id,
                lesson_note=str(body.get("lesson_note", "")),
                approved_by="quanpt1",
                approval_verified=True,  # owner_confirm=DUYET đã kiểm ở trên
            )
            self._send_json({"success": True, **result})
        except KeyError as exc:
            self._send_error_json(str(exc), 404)
        except PermissionError as exc:
            self._send_error_json(str(exc), 403)
        except ValueError as exc:
            self._send_error_json(str(exc), 409)
        except Exception as exc:
            self._send_error_json(f"Lỗi promote: {exc}", 500)

    # ------------------------------------------------------------------
    # Sprint 12 (b): Web read-only API (localhost-only, fail-honest)
    # ------------------------------------------------------------------

    def _web_common_guard(self) -> tuple[bool, None | dict, None | int]:
        client_ip = self.client_address[0] if self.client_address else ""
        if client_ip not in ("127.0.0.1", "::1", "localhost"):
            return False, {"error": "Chỉ truy cập được từ máy chủ (localhost)"}, 403
        return True, None, None

    @staticmethod
    def _parse_web_query(parsed_query) -> dict[str, list[str]]:
        import urllib.parse as _up

        if isinstance(parsed_query, str):
            return _up.parse_qs(parsed_query)
        return parsed_query if isinstance(parsed_query, dict) else {}

    def _handle_api_web_search(self, parsed_query) -> None:
        ok, err, code = self._web_common_guard()
        if not ok:
            self._send_error_json(err["error"], code)  # type: ignore[index]
            return
        params = self._parse_web_query(parsed_query)
        q = (params.get("q", [""])[0] if "q" in params else "").strip()
        try:
            max_results = min(int(params.get("max_results", ["5"])[0]), 10)
        except ValueError:
            max_results = 5
        if not q:
            self._send_error_json("q là bắt buộc", 400)
            return
        try:
            from quan_ai_brain.integration.web_connector import BingRssSearcher

            results = BingRssSearcher().search(q, max_results=max_results)
            self._send_json({"success": True, "query": q, "results": results, "count": len(results)})
        except Exception as exc:
            self._send_json({"success": False, "query": q, "error": str(exc), "results": []})

    def _handle_api_web_page(self, parsed_query) -> None:
        ok, err, code = self._web_common_guard()
        if not ok:
            self._send_error_json(err["error"], code)  # type: ignore[index]
            return
        params = self._parse_web_query(parsed_query)
        url = (params.get("url", [""])[0] if "url" in params else "").strip()
        if not url:
            self._send_error_json("url là bắt buộc", 400)
            return
        try:
            from quan_ai_brain.integration.web_connector import HttpWebConnector

            page = HttpWebConnector().fetch_page(url)
            self._send_json({"success": True, "page": page})
        except Exception as exc:
            self._send_json({"success": False, "url": url, "error": str(exc)})

    def _handle_api_web_rss(self, parsed_query) -> None:
        ok, err, code = self._web_common_guard()
        if not ok:
            self._send_error_json(err["error"], code)  # type: ignore[index]
            return
        params = self._parse_web_query(parsed_query)
        url = (params.get("url", [""])[0] if "url" in params else "").strip()
        try:
            max_items = min(int(params.get("max_items", ["10"])[0]), 25)
        except ValueError:
            max_items = 10
        if not url:
            self._send_error_json("url là bắt buộc", 400)
            return
        try:
            from quan_ai_brain.integration.web_connector import RssConnector

            feed = RssConnector().fetch_feed(url, max_items=max_items)
            self._send_json({"success": True, "feed": feed})
        except Exception as exc:
            self._send_json({"success": False, "url": url, "error": str(exc)})

    # ------------------------------------------------------------------
    # Sprint 13 (b): Improvement report API (localhost-only, fail-honest)
    # ------------------------------------------------------------------

    def _handle_api_improvement_report(self, parsed_query) -> None:
        client_ip = self.client_address[0] if self.client_address else ""
        if client_ip not in ("127.0.0.1", "::1", "localhost"):
            self._send_error_json("Chỉ truy cập được từ máy chủ (localhost)", 403)
            return
        workspace = _find_workspace_root()
        try:
            from quan_ai_brain.cognition.improvement_report import build_improvement_report

            report = build_improvement_report(workspace)
            self._send_json({"success": True, "report": report})
        except Exception as exc:
            self._send_error_json(f"Lỗi đọc improvement report: {exc}", 500)

    def _handle_api_improvement_export(self, body: dict) -> None:
        client_ip = self.client_address[0] if self.client_address else ""
        if client_ip not in ("127.0.0.1", "::1", "localhost"):
            self._send_error_json("Chỉ truy cập được từ máy chủ (localhost)", 403)
            return
        workspace = _find_workspace_root()
        try:
            from quan_ai_brain.cognition.improvement_report import (
                build_improvement_report,
                export_report_markdown,
            )

            report = build_improvement_report(workspace)
            path = export_report_markdown(report, workspace)
            self._send_json({
                "success": True,
                "exported": True,
                "path": str(path.relative_to(workspace)),
                "matrix_count": len(report.get("matrix", [])),
            })
        except Exception as exc:
            self._send_error_json(f"Lỗi xuất báo cáo: {exc}", 500)

    # ------------------------------------------------------------------
    # Sprint 14 (c): Semantic search kinh nghiệm (GET, localhost-only, read-only)
    # ------------------------------------------------------------------
    def _handle_api_experience_search(self, parsed_query) -> None:
        """Tìm kinh nghiệm bằng BGE-M3 dense; fail-open + cờ trung thực."""
        client = self.client_address[0] if self.client_address else ""
        if client not in ("127.0.0.1", "::1"):
            self._send_error_json("Experience search API chỉ chấp nhận localhost", 403)
            return

        from quan_ai_brain.cognition.experience_semantic import (
            find_similar_experiences_semantic,
        )

        params = urllib.parse.parse_qs(parsed_query)
        q = (params.get("q", [""])[0] or "").strip()
        if not q:
            self._send_error_json("Thiếu tham số q", 400)
            return

        limit = 5
        try:
            limit = max(1, min(20, int(params.get("limit", ["5"])[0])))
        except (TypeError, ValueError):
            pass

        workspace = _find_workspace_root()
        db_path = workspace / "data" / "brain.db"
        try:
            with MemoryStore(db_path, workspace=workspace) as store:
                result = find_similar_experiences_semantic(store, q, limit=limit)
        except Exception as exc:
            # DB lỗi — fail-open trung thực, không chết luồng
            self._send_json({
                "success": True,
                "query": q,
                "semantic_available": False,
                "reason": f"brain.db không đọc được: {exc}",
                "confirmed": [],
                "candidates": [],
            })
            return

        self._send_json({"success": True, "query": q, **result})

    # ------------------------------------------------------------------
    # Sprint 15 (b): Evidence traceability — cognitive state của một task
    # ------------------------------------------------------------------
    def _handle_api_task_cognitive_state(self, parsed_query) -> None:
        """Trả cognitive state + plan warnings đã persist cho task (read-only).

        - localhost-only; 404 nếu task không tồn tại; task cũ không có state →
          has_cognitive_state=false (trung thực, không 0 giả); còn UNRESOLVED
          contradiction → needs_review=true (KHÔNG tự phân giải — §IV.C).
        """
        client = self.client_address[0] if self.client_address else ""
        if client not in ("127.0.0.1", "::1"):
            self._send_error_json("Cognitive-state API chỉ chấp nhận localhost", 403)
            return

        params = urllib.parse.parse_qs(parsed_query)
        task_id = (params.get("task_id", [""])[0] or "").strip()
        if not task_id:
            self._send_error_json("Thiếu tham số task_id", 400)
            return

        from quan_ai_brain.orchestration.task_registry import DurableTaskRegistry

        workspace = _find_workspace_root()
        try:
            registry = DurableTaskRegistry(workspace / "data" / "tasks.db", workspace=workspace)
            task = registry.get_task(task_id)
        except Exception as exc:
            self._send_error_json(f"tasks.db không đọc được: {exc}", 500)
            return
        if task is None:
            self._send_error_json(f"Task {task_id} không tồn tại", 404)
            return

        checkpoint = task.checkpoint_data or {}
        snap = checkpoint.get("sprint15_cognitive_state") if isinstance(checkpoint, dict) else None
        if not isinstance(snap, dict):
            self._send_json({
                "success": True,
                "task_id": task_id,
                "has_cognitive_state": False,
                "reason": "Task đăng ký trước Sprint 15 — không có cognitive state persist (trung thực, không suy diễn).",
                "needs_review": False,
                "warnings": [],
            })
            return

        cog = snap.get("cognitive_state") if isinstance(snap.get("cognitive_state"), dict) else None
        contradictions = (cog or {}).get("contradictions") or []
        unresolved = [
            c for c in contradictions
            if isinstance(c, dict) and str(c.get("resolution_status", "UNRESOLVED")).upper() == "UNRESOLVED"
        ]
        self._send_json({
            "success": True,
            "task_id": task_id,
            "has_cognitive_state": True,
            "plan_id": snap.get("plan_id"),
            "plan_source": snap.get("plan_source"),
            "persisted_at_utc": snap.get("persisted_at_utc"),
            "needs_review": bool(unresolved),
            "unresolved_contradiction_count": len(unresolved),
            "warnings": snap.get("plan_warnings") or [],
            "cognitive_state": cog,
        })

    def _handle_api_email_proposals_list(self, parsed_query) -> None:
        """Sprint 10 (c): danh sách đề xuất email (đọc-only). Tự generate nếu chưa có.

        Generate dùng mock intake HIỆN CÓ trong data/email_intake.db (source=mock).
        """
        client = self.client_address[0] if self.client_address else ""
        if client not in ("127.0.0.1", "::1"):
            self._send_error_json("Email proposals API chỉ chấp nhận localhost", 403)
            return
        try:
            from quan_ai_brain.integration.email_intelligence import (
                ProposalStore,
                generate_proposals_for_intake,
            )
            from quan_ai_brain.memory.sqlite_store import MemoryStore

            workspace = _find_workspace_root()
            intake_db = workspace / "data" / "email_intake.db"
            # Generate proposals cho ACTION_REQUIRED chưa có (idempotent)
            gen = generate_proposals_for_intake(intake_db, MemoryStore(workspace / "data" / "memory.db"))
            store = ProposalStore(intake_db)
            self._send_json({
                "success": True,
                "generated": gen,
                "proposals": store.list_proposals(limit=50),
                "vmail_status": "BLOCKED",
            })
        except Exception as exc:
            self._send_error_json(f"Proposals lỗi: {type(exc).__name__}: {exc}", 500)

    def _handle_api_email_task_create(self, body: dict) -> None:
        """Sprint 10 (b): tạo NHIỆM VỤ ỨNG VIÊN từ đề xuất — chỉ khi owner bấm.

        Task PENDING, LEVEL_A, idempotent theo message_id (cùng email → cùng task).
        KHÔNG có đường thực thi tự động — task nằm chờ approval gate như mọi nhiệm vụ.
        """
        client = self.client_address[0] if self.client_address else ""
        if client not in ("127.0.0.1", "::1"):
            self._send_error_json("Email task create chỉ chấp nhận localhost", 403)
            return
        try:
            from quan_ai_brain.integration.email_intelligence import ProposalStore
            from quan_ai_brain.memory.sqlite_store import MemoryStore
            from quan_ai_brain.orchestration.models import AutonomyLevel
            from quan_ai_brain.orchestration.task_registry import DurableTaskRegistry

            proposal_id = str(body.get("proposal_id", "")).strip()
            if not proposal_id:
                self._send_error_json("Thiếu proposal_id", 400)
                return
            workspace = _find_workspace_root()
            store = ProposalStore(workspace / "data" / "email_intake.db")
            record = store.get(proposal_id)
            if not record:
                self._send_error_json(f"Không tìm thấy đề xuất {proposal_id}", 404)
                return
            if record["linked_task_id"]:
                # Idempotent: email đã có task — trả lại task cũ, không tạo trùng
                self._send_json({
                    "success": True,
                    "task_id": record["linked_task_id"],
                    "created": False,
                    "note": "Email này đã có nhiệm vụ ứng viên (idempotent)",
                })
                return

            payload = record["payload"]
            reg = DurableTaskRegistry(workspace / "data" / "tasks.db", workspace=str(workspace))
            task = reg.register_task(
                goal=f"[EMAIL:{record['message_id']}] {record['goal']}",
                risk_level="R1",
                autonomy_level=AutonomyLevel.LEVEL_A,
                acceptance_criteria=payload.get("success_criteria", []),
                approved_scope=["read-only", "draft-only"],
                idempotency_key=f"email_task_{record['message_id']}",
            )
            task_id = task.task_id
            store.link_task(proposal_id, task_id)
            # Ghi back liên kết vào intake_emails (Sprint 9 schema)
            try:
                import sqlite3 as _sq

                con = _sq.connect(str(workspace / "data" / "email_intake.db"))
                with con:
                    con.execute(
                        "UPDATE intake_emails SET related_task_id = ? WHERE message_id = ?",
                        (task_id, record["message_id"]),
                    )
                con.close()
            except Exception:
                pass  # liên kết intake là nice-to-have — task đã tạo thành công
            # Cập nhật kinh nghiệm: nhớ MemoryStore liên quan (dùng chung 1 instance)
            MemoryStore(workspace / "data" / "memory.db")  # warm-up (nếu DB chưa có)
            self._send_json({
                "success": True,
                "task_id": task_id,
                "created": True,
                "status": "PENDING",
                "autonomy": "LEVEL_A",
                "note": "Nhiệm vụ ứng viên PENDING — chờ phê duyệt, không tự thực thi",
            })
        except Exception as exc:
            self._send_error_json(f"Tạo nhiệm vụ lỗi: {type(exc).__name__}: {exc}", 500)

    def _handle_api_email_intake_sync(self, body: dict) -> None:
        """Sprint 9 (C): 1 chu kỳ sync mock intake → data/email_intake.db.

        Nguồn thật (Vmail) BLOCKED — endpoint này chỉ chạy connector mock và
        GHI RÕ source="mock" trên từng email. Không giả vờ đọc hộp thư thật.
        """
        client = self.client_address[0] if self.client_address else ""
        if client not in ("127.0.0.1", "::1"):
            self._send_error_json("Email intake API chỉ chấp nhận localhost", 403)
            return
        try:
            from quan_ai_brain.integration.email_intake import (
                EmailIntakeStore,
                MockEmailConnector,
                sync_intake,
            )

            workspace = _find_workspace_root()
            store = EmailIntakeStore(workspace / "data" / "email_intake.db")
            result = sync_intake(MockEmailConnector(), store)
            self._send_json({
                "success": True,
                "result": result.to_dict(),
                "emails": store.list_emails(limit=20),
                "vmail_status": "BLOCKED",
            })
        except Exception as exc:
            self._send_error_json(f"Intake sync lỗi: {type(exc).__name__}: {exc}", 500)

    def _handle_api_email_intake_list(self, parsed_query) -> None:
        """Sprint 9 (C): danh sách email đã tiếp nhận (mock), đọc-only."""
        try:
            from quan_ai_brain.integration.email_intake import EmailIntakeStore

            workspace = _find_workspace_root()
            store = EmailIntakeStore(workspace / "data" / "email_intake.db")
            category = parsed_query.get("category", [None])[0] if "category" in parsed_query else None
            self._send_json({
                "success": True,
                "emails": store.list_emails(limit=50, category=category),
                "count": store.count(),
                "vmail_status": "BLOCKED",
            })
        except Exception as exc:
            self._send_error_json(f"Intake list lỗi: {type(exc).__name__}: {exc}", 500)

    def _handle_api_workbench_overview(self) -> None:
        """Sprint 9 (A): tổng quan workbench — số liệu THẬT từ các DB/API hiện có.

        Nguyên tắc trung thực: mỗi khối độc lập; một nguồn lỗi → trạng thái
        "CHƯA XAC MINH" cho khối đó, KHÔNG điền 0 để tạo cảm giác hệ thống tốt.
        """
        overview: dict = {"success": True, "generated_at_utc": datetime.now(timezone.utc).isoformat()}
        workspace = _find_workspace_root()

        # --- Nhiệm vụ (data/tasks.db, DurableTaskRegistry) ---
        try:
            from quan_ai_brain.orchestration.task_registry import DurableTaskRegistry

            reg = DurableTaskRegistry(workspace / "data" / "tasks.db", workspace=str(workspace))
            tasks = reg.list_tasks()
            by_status: dict[str, int] = {}
            for t in tasks:
                st = t.status.value if hasattr(t.status, "value") else str(t.status)
                by_status[st] = by_status.get(st, 0) + 1
            overview["tasks"] = {
                "status": "OK",
                "total": len(tasks),
                "by_status": by_status,
                "waiting_approval": by_status.get("WAITING_APPROVAL", 0),
                "in_progress": by_status.get("IN_PROGRESS", 0),
                "pending": by_status.get("PENDING", 0),
                "approved_not_done": by_status.get("APPROVED", 0),
                "failed": by_status.get("FAILED", 0),
                "blocked": by_status.get("BLOCKED", 0),
                "completed": by_status.get("COMPLETED", 0),
            }
        except Exception as exc:
            overview["tasks"] = {"status": "CHƯA XÁC MINH", "error": f"{type(exc).__name__}: {exc}"}

        # --- Thông tin còn thiếu (data/information_gaps.db, đếm thô sqlite) ---
        try:
            import sqlite3 as _sq

            con = _sq.connect(f"file:{workspace / 'data' / 'information_gaps.db'}?mode=ro", uri=True)
            try:
                row = con.execute("SELECT COUNT(*) FROM information_gaps").fetchone()
                open_row = con.execute(
                    "SELECT COUNT(*) FROM information_gaps WHERE status IN ('OPEN','WAITING_OWNER')"
                ).fetchone() if _table_has(con, "status") else None
            finally:
                con.close()
            gaps = {"status": "OK", "total": row[0]}
            if open_row is not None:
                gaps["open"] = open_row[0]
            overview["information_gaps"] = gaps
        except Exception as exc:
            overview["information_gaps"] = {"status": "CHƯA XÁC MINH", "error": f"{type(exc).__name__}: {exc}"}

        # --- Tham vấn + phê duyệt (governance.db) ---
        try:
            from quan_ai_brain.governance.approval_cards import ApprovalCardStore

            store = ApprovalCardStore(workspace / "data" / "governance.db", workspace=str(workspace))
            cards = store.list_cards()
            by_card_status: dict[str, int] = {}
            for c in cards:
                st = c.status.value if hasattr(c.status, "status") else str(c.status)
                by_card_status[str(c.status)] = by_card_status.get(str(c.status), 0) + 1
            overview["approvals"] = {
                "status": "OK",
                "total": len(cards),
                "pending": by_card_status.get("PENDING_APPROVAL", 0),
                "approved": by_card_status.get("APPROVED", 0),
                "rejected": by_card_status.get("REJECTED", 0),
            }
        except Exception as exc:
            overview["approvals"] = {"status": "CHƯA XÁC MINH", "error": f"{type(exc).__name__}: {exc}"}

        # --- To-do (data/todos.db) ---
        try:
            from quan_ai_brain.tools.todo_store import TodoStore

            todo = TodoStore(workspace / "data" / "todos.db")
            items = todo.list_open()
            today = datetime.now().strftime("%Y-%m-%d")
            overdue = [t for t in items if t.get("due") and t["due"] < today]
            due_today = [t for t in items if t.get("due") == today]
            overview["todos"] = {
                "status": "OK",
                "open": len(items),
                "overdue": len(overdue),
                "due_today": len(due_today),
            }
        except Exception as exc:
            overview["todos"] = {"status": "CHƯA XÁC MINH", "error": f"{type(exc).__name__}: {exc}"}

        # --- Trạng thái dịch vụ cục bộ (probe thật, không đoán) ---
        services = {}
        for name, port in (("dual_server_8765", 8765), ("dual_server_8766", 8766), ("ollama", 11434)):
            try:
                import socket as _sock

                with _sock.create_connection(("127.0.0.1", port), timeout=1.0):
                    services[name] = "CONNECTED"
            except Exception:
                services[name] = "DISCONNECTED"
        overview["services"] = services
        self._send_json(overview)

    def _handle_api_workbench_tasks(self, parsed_query) -> None:
        """Sprint 9 (B): danh sách nhiệm vụ thật từ DurableTaskRegistry, kèm filter."""
        try:
            from quan_ai_brain.orchestration.task_registry import DurableTaskRegistry, TaskStatus

            # parsed_query là chuỗi raw query ("a=b&c=d") — parse thành dict
            import urllib.parse as _up

            params = _up.parse_qs(parsed_query) if isinstance(parsed_query, str) else parsed_query
            workspace = _find_workspace_root()
            reg = DurableTaskRegistry(workspace / "data" / "tasks.db", workspace=str(workspace))
            status_filter = params.get("status", [None])[0] if "status" in params else None
            status_enum = TaskStatus(status_filter) if status_filter else None
            limit = int(params.get("limit", [50])[0]) if "limit" in params else 50
            tasks = reg.list_tasks(status=status_enum, limit=limit)
            items = []
            for t in tasks[:limit]:
                d = t.to_dict() if hasattr(t, "to_dict") else {}
                items.append({
                    "task_id": d.get("task_id"),
                    "goal": d.get("goal"),
                    "status": d.get("status"),
                    "risk_level": d.get("risk_level"),
                    "created_at_utc": d.get("created_at_utc"),
                    "updated_at_utc": d.get("updated_at_utc"),
                })
            self._send_json({"success": True, "tasks": items, "count": len(items)})
        except Exception as exc:
            self._send_error_json(f"Tasks unavailable: {type(exc).__name__}: {exc}", 503)

    def _handle_api_supervisor_tick(self, body: dict) -> None:
        try:
            sup = _get_global_supervisor()
            max_duration_sec = float(body.get("max_duration_sec", 10.0))
            max_steps = int(body.get("max_steps", 5))
            dry_run = bool(body.get("dry_run", True))
            result = sup.run_background_tick(
                max_duration_sec=max_duration_sec,
                max_steps=max_steps,
                dry_run=dry_run,
                autonomic_system=GLOBAL_AUTONOMIC_SYSTEM,
            )
            task = sup.current_task
            self._send_json({
                "success": True,
                "tick_result": result,
                "supervisor_state": sup.state.value,
                "current_task": task.to_dict() if task else None,
            })
        except Exception as exc:
            self._send_error_json(f"Error executing supervisor tick: {exc}", 500)


class ThreadedHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = True


def is_port_in_use(port: int, host: str = "127.0.0.1") -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex((host, port)) == 0


def run_web_server(port: int = 8765, open_browser: bool = True) -> None:
    host = "127.0.0.1"
    actual_port = port
    while is_port_in_use(actual_port, host):
        actual_port += 1
        if actual_port > port + 50:
            raise RuntimeError(f"Could not find an available port between {port} and {actual_port}")

    server = ThreadedHTTPServer((host, actual_port), BrainAPIHandler)
    url = f"http://{host}:{actual_port}"

    print(f"\n======================================================================")
    print(f"        QUAN AI BRAIN — LOCAL WEB UI DASHBOARD (ONLINE)")
    print(f"======================================================================")
    print(f"  URL Giao Dien:   {url}")
    print(f"  Trang thai mang: Localhost (127.0.0.1) — An toan tuyet doi")
    print(f"  Nhan Ctrl+C de dung server bat cu luc nao.")
    print(f"======================================================================\n")

    if open_browser:
        threading.Timer(1.0, lambda: webbrowser.open(url)).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[Dung Server] Dang dong QUAN AI BRAIN Web UI...")
        server.server_close()

    # ========== CLO V1: Continuous Learning API Handlers ==========

    def _handle_api_learning_status(self) -> None:
        """GET /api/learning/status — Get current CLO status."""
        try:
            from quan_ai_brain.cognition.continuous_learning_engine import ContinuousLearningEngine
            
            with MemoryStore(self.workspace / "data" / "brain.db", workspace=self.workspace) as store:
                clo_engine = ContinuousLearningEngine(store, workspace=self.workspace)
                status = clo_engine.get_learning_status()
            
            self._send_json({"success": True, "status": status})
        except Exception as e:
            self._send_json({"success": False, "error": str(e)[:200]})

    def _handle_api_learning_start(self, parsed_query) -> None:
        """POST /api/learning/start — Start continuous learning mode."""
        try:
            from quan_ai_brain.cognition.continuous_learning_engine import ContinuousLearningEngine
            
            # Parse request body
            import json
            content_length = int(self.headers.get('Content-Length', 0))
            body = json.loads(self.rfile.read(content_length).decode('utf-8')) if content_length > 0 else {}
            
            objectives = body.get("objectives", ["Learn from tasks and interactions"])
            source_manifest = body.get("source_manifest", {"sources": ["chat", "tasks", "memory"]})
            
            with MemoryStore(self.workspace / "data" / "brain.db", workspace=self.workspace) as store:
                clo_engine = ContinuousLearningEngine(store, workspace=self.workspace)
                session = clo_engine.start_continuous_learning(objectives, source_manifest)
            
            self._send_json({
                "success": True,
                "message": "Continuous learning started",
                "session": session.to_dict()
            })
        except Exception as e:
            self._send_json({"success": False, "error": str(e)[:200]})

    def _handle_api_learning_stop(self, parsed_query) -> None:
        """POST /api/learning/stop — Stop continuous learning permanently."""
        try:
            from quan_ai_brain.cognition.continuous_learning_engine import ContinuousLearningEngine
            
            import json
            content_length = int(self.headers.get('Content-Length', 0))
            body = json.loads(self.rfile.read(content_length).decode('utf-8')) if content_length > 0 else {}
            
            reason = body.get("reason", "Owner requested stop")
            
            with MemoryStore(self.workspace / "data" / "brain.db", workspace=self.workspace) as store:
                clo_engine = ContinuousLearningEngine(store, workspace=self.workspace)
                clo_engine.stop_continuous_learning(reason)
            
            self._send_json({"success": True, "message": f"Continuous learning stopped: {reason}"})
        except Exception as e:
            self._send_json({"success": False, "error": str(e)[:200]})

    def _handle_api_learning_pause(self, parsed_query) -> None:
        """POST /api/learning/pause — Pause continuous learning."""
        try:
            from quan_ai_brain.cognition.continuous_learning_engine import ContinuousLearningEngine
            
            import json
            content_length = int(self.headers.get('Content-Length', 0))
            body = json.loads(self.rfile.read(content_length).decode('utf-8')) if content_length > 0 else {}
            
            reason = body.get("reason", "Temporary pause")
            
            with MemoryStore(self.workspace / "data" / "brain.db", workspace=self.workspace) as store:
                clo_engine = ContinuousLearningEngine(store, workspace=self.workspace)
                clo_engine.pause_continuous_learning(reason)
            
            self._send_json({"success": True, "message": f"Continuous learning paused: {reason}"})
        except Exception as e:
            self._send_json({"success": False, "error": str(e)[:200]})

    def _handle_api_learning_resume(self) -> None:
        """POST /api/learning/resume — Resume from pause."""
        try:
            from quan_ai_brain.cognition.continuous_learning_engine import ContinuousLearningEngine
            
            with MemoryStore(self.workspace / "data" / "brain.db", workspace=self.workspace) as store:
                clo_engine = ContinuousLearningEngine(store, workspace=self.workspace)
                clo_engine.resume_continuous_learning()
            
            self._send_json({"success": True, "message": "Continuous learning resumed"})
        except Exception as e:
            self._send_json({"success": False, "error": str(e)[:200]})

def run_executive_server(port: int = 8766, open_browser: bool = True, host: str = "0.0.0.0") -> None:
    actual_port = port
    while is_port_in_use(actual_port, "127.0.0.1"):
        actual_port += 1
        if actual_port > port + 50:
            raise RuntimeError(f"Could not find an available port between {port} and {actual_port}")

    server = ThreadedHTTPServer((host, actual_port), BrainAPIHandler)
    lan_ip = get_local_lan_ip()
    local_url = f"http://127.0.0.1:{actual_port}/"
    lan_url = f"http://{lan_ip}:{actual_port}/"

    print(f"\n======================================================================")
    print(f"   QUAN AI BRAIN -- PHONG DIEU HANH & THAM VAN CHU NHAN (ONLINE)")
    print(f"======================================================================")
    print(f"  URL Cuc Bo (PC):       {local_url}")
    print(f"  URL Mang Wi-Fi (Pi 5): {lan_url}")
    print(f"  Ma PIN Ghep Cap Edge:  {_GLOBAL_EDGE_PAIRING_PIN}")
    print(f"  Ban sao so:            Quanpt1 Digital Replica & Executive Desk")
    print(f"  Trang thai mang:       LAN / Localhost (Bao ve boi HMAC-SHA256)")
    print(f"  Nhan Ctrl+C de dung server bat cu luc nao.")
    print(f"======================================================================\n")

    _GLOBAL_EDGE_MONITOR.start_watchdog(interval_sec=0.5)

    if open_browser:
        threading.Timer(1.0, lambda: webbrowser.open(local_url)).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[Dung Server] Dang dong Phong Dieu Hanh...")
        _GLOBAL_EDGE_MONITOR.stop_watchdog()
        server.server_close()
        print("[Hoan tat] Da tat server an toan.")


if __name__ == "__main__":
    run_web_server()
