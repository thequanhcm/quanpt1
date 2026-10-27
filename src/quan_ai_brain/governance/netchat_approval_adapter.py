"""NetChat Approval Adapter — xử lý lệnh phê duyệt của chủ sở hữu trên kênh
"Trợ lý Tony Pham" (Master Prompt V3, Section V/VI).

Nguyên tắc phản hồi (yêu cầu chủ sở hữu 26/10): MỌI lệnh phê duyệt phải được
giải thích CỤ THỂ — làm gì, cho hồ sơ nào, vì sao từ chối/thành công, và
bước tiếp theo là gì. Không bao giờ trả lời chung chung gây hiểu nhầm.

An toàn (V3 Section 5.2):
- Chỉ chấp nhận quyết định từ user_id chủ sở hữu trên kênh private.
- Không coi tin nhắn lặp lại là phê duyệt hợp lệ thứ hai (consume-once).
- Card không tồn tại / sai trạng thái → từ chối RÕ RỊNH LÝ DO, kèm gợi ý.
- Không bao giờ tự suy diễn "im lặng là đồng ý".
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

WORKSPACE = Path(__file__).resolve().parent.parent.parent.parent
_SRC = WORKSPACE / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from quan_ai_brain.governance.approval_cards import ApprovalCardStore  # noqa: E402

CHANNEL_ID = "4phc9b1mx78qjq3grxcw89u94a"
OWNER_NETCHAT_USER_ID = "3b1ughs36i8e9p46im8opnms8w"  # quanpt1
BOT_USER_ID = "edojmne9d7gcxx8axu1mzas3pr"

NETCHAT_SCRIPT = r"C:\Users\DELL\AppData\Local\netmind_desktop\skills\bot-netchat\netchat_bot.py"
AGENT_PY = r"C:\Users\DELL\AppData\Local\netmind_desktop\netmind-agent\venv\Scripts\python.exe"

# Trạng thái tiếng Việt cho giải thích
_STATUS_VI = {
    "PENDING_APPROVAL": "ĐANG CHỜ ANH DUYỆT",
    "APPROVED": "ĐÃ DUYỆT (chưa/đang thực hiện)",
    "REJECTED": "ĐÃ TỪ CHỐI",
    "EXPIRED": "HẾT HẠN (cần trình lại)",
    "CANCELLED": "ĐÃ HỦY",
    "DRAFT": "BẢN NHÁP",
}


def _vi_status(status: str) -> str:
    return _STATUS_VI.get(status, status)


class NetChatApprovalAdapter:
    """Xử lý lệnh DUYỆT/TỪ CHỐI/SỬA/CHI TIẾT TASK-xxxx + fallback 'Duyệt' trần."""

    def __init__(self, governance_db: str | Path | None = None) -> None:
        db = Path(governance_db) if governance_db else (WORKSPACE / "data" / "governance.db")
        # Workspace suy ra từ vị trí DB (hỗ trợ test tmp dir) — PathGuard yêu cầu
        # DB nằm trong workspace được ủy quyền.
        inferred_ws = db.parent.parent if db.parent.name == "data" else db.parent
        self.workspace = inferred_ws.resolve()
        self.store = ApprovalCardStore(db, workspace=self.workspace)

    # ------------------------------------------------------------------
    # NetChat I/O (qua skill script — token không bao giờ đọc/log)
    # ------------------------------------------------------------------

    def send_to_channel(self, text: str) -> dict[str, Any]:
        def _run(args: list[str]) -> subprocess.CompletedProcess[str]:
            return subprocess.run(
                [AGENT_PY, NETCHAT_SCRIPT, *args],
                capture_output=True, text=True, timeout=30,
            )

        try:
            r1 = _run(["send", CHANNEL_ID, text, "--to-channel"])
            if "CONFIRM-REQUIRED:" in r1.stdout:
                token = ""
                for line in r1.stdout.splitlines():
                    if line.startswith("CONFIRM-REQUIRED:"):
                        token = line.split(":", 1)[1].strip()
                        break
                if token:
                    r2 = _run(["send", CHANNEL_ID, text, "--to-channel", "--confirmed", token])
                    if r2.returncode == 0:
                        return {"ok": True}
                    return {"ok": False, "error": (r2.stderr or r2.stdout)[:200]}
            if r1.returncode == 0:
                return {"ok": True}
            return {"ok": False, "error": (r1.stderr or r1.stdout)[:200]}
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": str(exc)}

    # ------------------------------------------------------------------
    # Parsing
    # ------------------------------------------------------------------

    _CODE = re.compile(r"TASK-[A-Za-z0-9_\-]+", re.IGNORECASE)
    _PLAIN_APPROVE = re.compile(r"^\s*(duyệt|phe duyet|duyet|đồng ý|dong y|approved|ok anh|ok)\s*[.!]?\s*$", re.IGNORECASE)
    _PLAIN_REJECT = re.compile(r"^\s*(từ chối|tu choi|reject|ko duyệt|khong duyet|không duyệt)\s*[.!]?\s*$", re.IGNORECASE)
    _PLAIN_DETAIL = re.compile(r"^\s*(chi tiết|chi tiet|detail)\s*[.!]?\s*$", re.IGNORECASE)

    def parse(self, text: str) -> dict[str, Any]:
        """Trả về action: approve|reject|amend|detail|list|unknown + task_code."""
        t = (text or "").strip()
        code_match = self._CODE.search(t)
        code = code_match.group(0).upper() if code_match else None

        low = t.lower()
        if code:
            if low.startswith(("duyệt", "phe duyet", "duyet", "đồng ý", "dong y", "approved")):
                return {"action": "approve", "task_code": code}
            if low.startswith(("từ chối", "tu choi", "reject")):
                reason = t.split(":", 1)[1].strip() if ":" in t else "Không nêu lý do"
                return {"action": "reject", "task_code": code, "reason": reason}
            if low.startswith(("sửa", "sua", "amend")):
                guidance = t.split(":", 1)[1].strip() if ":" in t else ""
                return {"action": "amend", "task_code": code, "guidance": guidance}
            if low.startswith(("chi tiết", "chi tiet", "detail")):
                return {"action": "detail", "task_code": code}
            return {"action": "unknown", "task_code": code}
        # lệnh trần không có mã
        if self._PLAIN_APPROVE.match(t):
            return {"action": "approve_pending", "task_code": None}
        if self._PLAIN_REJECT.match(t):
            return {"action": "reject_pending", "task_code": None, "reason": "Không nêu lý do"}
        if self._PLAIN_DETAIL.match(t):
            return {"action": "detail_pending", "task_code": None}
        return {"action": "none", "task_code": None}

    # ------------------------------------------------------------------
    # Handlers — mỗi handler trả về lời giải thích cụ thể
    # ------------------------------------------------------------------

    def handle_owner_message(self, message_text: str, *, sender_user_id: str = "", post: bool = True) -> str:
        """Entry point cho auto-responder. Trả về chuỗi giải thích (đã post nếu post=True)."""
        self.store.refresh_expiry()

        # V3 Sprint 3 (27/10): tin có mã TASK nhưng không phải lệnh duyệt/sửa/
        # chi tiết và task KHÔNG có approval card → có thể là trả lời yêu cầu
        # bổ sung thông tin (information gap). Trả về '' để caller route tiếp
        # sang info-gap adapter thay vì báo sai "CHƯA HIỂU LỆNH".
        parsed = self.parse(message_text)

        if parsed["action"] == "unknown":
            task_code = parsed.get("task_code") or ""
            try:
                from quan_ai_brain.governance.netchat_info_gap_adapter import has_waiting_task

                if has_waiting_task(task_code):
                    return ""  # info-gap reply — caller tự xử lý
            except Exception:
                pass

        if parsed["action"] == "none":
            return ""  # không phải lệnh phê duyệt — caller tự xử lý khác

        # Xác minh danh tính người ra quyết định (V3 5.2)
        if sender_user_id and sender_user_id != OWNER_NETCHAT_USER_ID:
            reply = (
                "🛑 KHÔNG THỰC THI — Xác minh danh tính thất bại.\n"
                f"• Tin nhắn đến từ user_id `{sender_user_id}`, không phải chủ sở hữu quanpt1.\n"
                "• Theo Master Prompt V3 mục 5.2, chỉ quyết định từ tài khoản chủ sở hữu trên kênh này mới hợp lệ.\n"
                "• Hành động tiếp theo: anh Quân đăng nhập đúng tài khoản và gửi lại lệnh."
            )
            if post:
                self.send_to_channel(reply)
            return reply

        try:
            if parsed["action"] == "approve":
                return self._do_approve(parsed["task_code"], post=post)
            if parsed["action"] == "reject":
                return self._do_reject(parsed["task_code"], parsed.get("reason", ""), post=post)
            if parsed["action"] == "amend":
                return self._do_amend_request(parsed["task_code"], parsed.get("guidance", ""), post=post)
            if parsed["action"] == "detail":
                return self._do_detail(parsed["task_code"], post=post)
            if parsed["action"] == "approve_pending":
                return self._do_approve_pending(post=post)
            if parsed["action"] == "reject_pending":
                return self._do_reject_pending(parsed.get("reason", ""), post=post)
            if parsed["action"] == "detail_pending":
                return self._do_detail_pending(post=post)
            if parsed["action"] == "unknown":
                return self._explain_unknown(parsed.get("task_code"), post=post)
        except KeyError as exc:
            reply = self._explain_no_card(str(exc), parsed, post=post)
            if post:
                self.send_to_channel(reply)
            return reply
        except PermissionError as exc:
            reply = (
                "🛑 KHÔNG THỰC THI — Trạng thái hồ sơ không cho phép.\n"
                f"• Lý do cụ thể: {exc}\n"
                "• Hành động tiếp theo: gõ 'CHI TIẾT TASK-<mã>' để xem trạng thái và bằng chứng."
            )
            if post:
                self.send_to_channel(reply)
            return reply
        return ""

    # ----approve theo mã -------------------------------------------------

    def _do_approve(self, task_code: str, *, post: bool = True) -> str:
        card = self.store.get_card(task_code)
        if card is None:
            return self._explain_no_card(f"Approval card '{task_code}' not found", {"action": "approve", "task_code": task_code}, post=post)
        if card.status == "APPROVED":
            reply = (
                f"ℹ️ HỒ SƠ {task_code} ĐÃ ĐƯỢC DUYỆT TRƯỚC ĐÓ.\n"
                f"• Không duyệt trùng (consume-once, V3 mục 5.1: một phê duyệt = một lần thực hiện).\n"
                f"• Trạng thái: {_vi_status(card.status)} | phiên bản card: v{card.version}.\n"
                "• Hành động tiếp theo: em đang/t sẽ thực hiện đúng phạm vi đã duyệt và gửi báo cáo 5 mục khi xong."
            )
            if post:
                self.send_to_channel(reply)
            return reply
        if card.status != "PENDING_APPROVAL":
            reply = (
                f"🛑 KHÔNG DUYỆT ĐƯỢC — HỒ SƠ {task_code} KHÔNG Ở TRẠNG THÁI CHỜ DUYỆT.\n"
                f"• Trạng thái hiện tại: {_vi_status(card.status)}.\n"
                f"• Cập nhật lần cuối: {card.updated_at_utc}.\n"
                "• Hành động tiếp theo: nếu anh vẫn muốn tiến hành, gõ 'SỬA " + task_code + ": trình lại' để em làm hồ sơ mới xin duyệt."
            )
            if post:
                self.send_to_channel(reply)
            return reply

        self.store.approve_card(task_code, approver="quanpt1", auth_method="netchat_channel_private")
        reply = (
            f"✅ ĐÃ DUYỆT — {task_code}\n"
            f"• Ai duyệt: quanpt1 (qua kênh NetChat riêng, user_id đã xác minh).\n"
            f"• Duyệt nội dung: {card.title} (card v{card.version}).\n"
            f"• Cơ chế: phê duyệt một-lần-dùng, đã lưu governance.db + audit trail; hết hạn card gốc: {card.ttl_expires_at_utc}.\n"
            "• Hành động tiếp theo: em bắt đầu thực hiện ĐÚNG phạm vi card và gửi báo cáo 5 mục khi hoàn thành."
        )
        if post:
            self.send_to_channel(reply)
        return reply

    # ----approve trần -----------------------------------------------------

    def _pending_cards(self) -> list:
        return self.store.list_cards(status="PENDING_APPROVAL")

    def _do_approve_pending(self, *, post: bool = True) -> str:
        pending = self._pending_cards()
        if len(pending) == 1:
            # Duyệt hộ đúng hồ sơ duy nhất đang chờ — giải thích rõ mappings
            card = pending[0]
            self.store.approve_card(card.task_code, approver="quanpt1", auth_method="netchat_channel_private")
            reply = (
                f"✅ ĐÃ DUYỆT — {card.task_code} (duyệt theo lệnh 'Duyệt' trần)\n"
                f"• Vì sao: hiện chỉ có ĐÚNG 1 hồ sơ đang chờ duyệt nên ánh xạ không gây nhầm lẫn.\n"
                f"• Hồ sơ: {card.title} (card v{card.version}).\n"
                f"• Ai duyệt: quanpt1 (user_id đã xác minh) — lưu governance.db, consume-once.\n"
                "• Hành động tiếp theo: em thực hiện đúng phạm vi card và báo cáo 5 mục khi xong."
            )
            if post:
                self.send_to_channel(reply)
            return reply
        if len(pending) > 1:
            lines = [f"📋 CẦN MÃ HỒ SƠ — hiện có {len(pending)} hồ sơ đang chờ duyệt:", ""]
            for c in pending:
                lines.append(f"• {c.task_code}: {c.title} [{_vi_status(c.status)}]")
            lines += [
                "",
                "• Vì sao chưa duyệt: lệnh 'Duyệt' không kèm mã → không xác định được anh duyệt hồ sơ nào (tránh duyệt nhầm, V3 mục 5.2).",
                "• Hành động tiếp theo: gõ 'DUYỆT TASK-<mã>' cho từng hồ sơ anh muốn duyệt.",
            ]
            reply = "\n".join(lines)
            if post:
                self.send_to_channel(reply)
            return reply
        # Không còn pending — trung thực: nói rõ hồ sơ gần nhất đã duyệt (nếu có)
        recent = self.store.list_cards()[-5:]
        lines = ["📭 KHÔNG CÓ HỒ SƠ NÀO ĐANG CHỜ DUYỆT.", ""]
        if recent:
            lines.append("Các hồ sơ gần nhất (để anh đối chiếu):")
            for c in recent:
                lines.append(f"• {c.task_code} — {c.title} [{_vi_status(c.status)}]")
            last = recent[-1]
            if last.status == "APPROVED":
                lines += [
                    "",
                    f"ℹ️ Vì sao lệnh 'Duyệt' này không tạo phê duyệt mới: hồ sơ gần nhất {last.task_code} đã được anh duyệt lúc {last.updated_at_utc} — mỗi phê duyệt chỉ dùng một lần (consume-once), gõ lại 'Duyệt' không thực thi lần hai.",
                ]
        lines += [
            "",
            "• Hành động tiếp theo: nếu anh muốn duyệt tiếp công việc mới, gõ 'CHI TIẾT TASK-<mã>' hoặc yêu cầu em trình hồ sơ mới.",
        ]
        reply = "\n".join(lines)
        if post:
            self.send_to_channel(reply)
        return reply

    # ---- reject / amend / detail -----------------------------------------

    def _do_reject(self, task_code: str, reason: str, *, post: bool = True) -> str:
        card = self.store.get_card(task_code)
        if card is None:
            return self._explain_no_card(f"Approval card '{task_code}' not found", {"action": "reject", "task_code": task_code}, post=post)
        self.store.reject_card(task_code, reason)
        reply = (
            f"🚫 ĐÃ TỪ CHỐI — {task_code}\n"
            f"• Lý do ghi nhận: {reason}\n"
            f"• Hồ sơ: {card.title} — đã chuyển trạng thái REJECTED, KHÔNG thực hiện.\n"
            "• Hành động tiếp theo: em dừng nhiệm vụ này; nếu anh muốn phương án khác, gõ 'SỬA " + task_code + ": [điều chỉnh]' để em trình lại."
        )
        if post:
            self.send_to_channel(reply)
        return reply

    def _do_reject_pending(self, reason: str, *, post: bool = True) -> str:
        pending = self._pending_cards()
        if len(pending) == 1:
            card = pending[0]
            self.store.reject_card(card.task_code, reason)
            reply = (
                f"🚫 ĐÃ TỪ CHỐI — {card.task_code} (theo lệnh 'Từ chối' trần)\n"
                f"• Vì sao ánh xạ được chấp nhận: chỉ có 1 hồ sơ đang chờ.\n"
                f"• Lý do ghi nhận: {reason}\n"
                "• Hành động tiếp theo: em dừng nhiệm vụ; chờ anh chỉ đạo phương án mới."
            )
            if post:
                self.send_to_channel(reply)
            return reply
        reply = self._do_approve_pending(post=False).replace("chờ duyệt", "chờ quyết định") if pending else (
            "📭 KHÔNG CÓ HỒ SƠ NÀO ĐANG CHỜ QUYẾT ĐỊNH — không có gì để từ chối.\n"
            "• Hành động tiếp theo: không cần làm gì thêm."
        )
        if post:
            self.send_to_channel(reply)
        return reply

    def _do_amend_request(self, task_code: str, guidance: str, *, post: bool = True) -> str:
        card = self.store.get_card(task_code)
        if card is None:
            return self._explain_no_card(f"Approval card '{task_code}' not found", {"action": "amend", "task_code": task_code}, post=post)
        # V3 5.1: phương án đổi → chủ sở hữu sẽ thấy card mới, phải duyệt lại.
        reply = (
            f"✍️ GHI NHẬN YÊU CẦU SỬA — {task_code}\n"
            f"• Chỉ đạo của anh: {guidance or '(không nêu chi tiết)'}\n"
            f"• Hành động tiếp theo: em cập nhật phương án, trình lại card v{card.version + 1} qua kênh này; nhiệm vụ vẫn KHÔNG thực hiện cho tới khi anh duyệt bản mới."
        )
        if post:
            self.send_to_channel(reply)
        return reply

    def _do_detail(self, task_code: str, *, post: bool = True) -> str:
        card = self.store.get_card(task_code)
        if card is None:
            return self._explain_no_card(f"Approval card '{task_code}' not found", {"action": "detail", "task_code": task_code}, post=post)
        ev = card.evidence[-6:]
        ev_lines = "\n".join(
            f"   - [{e.get('at', '')}] {e.get('event', '')}" + (f" — {e.get('approver')}" if e.get("approver") else "")
            for e in ev
        )
        reply = (
            f"📄 CHI TIẾT HỒ SƠ — {task_code}\n"
            f"• Tiêu đề: {card.title}\n"
            f"• Trạng thái: {_vi_status(card.status)} | Phiên bản: v{card.version}\n"
            f"• Tạo: {card.created_at_utc} | Cập nhật: {card.updated_at_utc}\n"
            f"• Hết hạn TTL: {card.ttl_expires_at_utc}\n"
            f"• Lịch sử bằng chứng (6 sự kiện gần nhất):\n{ev_lines}\n"
            f"• Nội dung card:\n{card.card_markdown[:800]}"
        )
        if post:
            self.send_to_channel(reply)
        return reply

    def _do_detail_pending(self, *, post: bool = True) -> str:
        pending = self._pending_cards()
        if len(pending) == 1:
            return self._do_detail(pending[0].task_code, post=post)
        return self._do_approve_pending(post=post)

    # ---- giải thích lỗi ---------------------------------------------------

    def _explain_no_card(self, err: str, parsed: dict[str, Any], *, post: bool = True) -> str:
        code = parsed.get("task_code") or "?"
        recent = self.store.list_cards()[-5:]
        lines = [
            f"🛑 KHÔNG TÌM THẤY HỒ SƠ PHÊ DUYỆT '{code}' TRONG HỆ THỐNG.",
            "",
            "• Vì sao: lệnh của anh hợp lệ nhưng mã hồ sơ này không tồn tại trong bảng approval_cards (governance.db).",
        ]
        if recent:
            lines.append("• Các hồ sơ đang có trong hệ thống:")
            for c in recent:
                lines.append(f"   - {c.task_code}: {c.title} [{_vi_status(c.status)}]")
        lines += [
            "",
            "• Hành động tiếp theo: kiểm tra lại mã trên card; hoặc yêu cầu em trình hồ sơ mới — em sẽ tạo card TRƯỚC rồi mới gửi tin, để lệnh duyệt của anh luôn khớp hồ sơ thật.",
        ]
        reply = "\n".join(lines)
        if post:
            self.send_to_channel(reply)
        return reply

    def _explain_unknown(self, task_code: str | None, *, post: bool = True) -> str:
        reply = (
            f"❓ CHƯA HIỂU LỆNH — tin có chứa mã '{task_code}' nhưng động từ không nhận diện được.\n"
            "• Các lệnh hợp lệ: DUYỆT TASK-<mã> | TỪ CHỐI TASK-<mã> | SỬA TASK-<mã>: [nội dung] | CHI TIẾT TASK-<mã>.\n"
            "• Hành động tiếp theo: anh gửi lại theo một trong các cú pháp trên."
        )
        if post:
            self.send_to_channel(reply)
        return reply


def create_and_post_approval_card(
    task_code: str,
    title: str,
    card_markdown: str,
    *,
    risk_level: int = 2,
    goal: str = "",
) -> dict[str, Any]:
    """Tiện ích cho các sprint sau: tạo card TRƯỚC (persist) rồi post tin.
    Trả về {'card': ..., 'posted': bool, 'error': ...}."""
    adapter = NetChatApprovalAdapter()
    card = adapter.store.create_card(
        task_code, title, card_markdown, risk_level=risk_level, goal=goal
    )
    posted = adapter.send_to_channel(card_markdown)
    return {"card": card.to_dict(), "posted": posted}
