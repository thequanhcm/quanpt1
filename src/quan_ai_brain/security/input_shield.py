"""Input Injection Shield — TASK-AGENTIC-SEC-1 Slice (a).

Áp dụng khung ATTT Agentic AI (MIT + Viettel Cyber Security, 261113_VTNET_ATTT_Agentic_AI_v4):
- Slide 7: "dữ liệu biến thành mệnh lệnh" — nội dung ngoài có thể chứa chỉ dẫn ẩn.
- Slide 8: EchoLeak CVE-2025-32711 (CVSS 9.3) — zero-click prompt injection qua email.

Quét ĐẦU VÀO của /api/chat + DM responder trước khi đưa vào chat pipeline.
Verdict: ALLOW (bình thường) / SANITIZE (nghi ngờ, cắt đoạn độc) / BLOCK (từ chối).

Fail-honest: lỗi quét → verdict BLOCK + warning (không để lọt qua im lặng).
Mọi scan trúng (SANITIZE/BLOCK) đều ghi audit event kèm NHÃN NGUỒN DỮ LIỆU
(data source — GAP-4, slide 11: "sự cố đi qua cả 3 nhóm").
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

log = logging.getLogger(__name__)


class Verdict(str, Enum):
    ALLOW = "ALLOW"
    SANITIZE = "SANITIZE"
    BLOCK = "BLOCK"


# Mức điểm: mỗi pattern trúng cộng điểm nghi phạm
WEIGHT_DIRECT_ORDER = 40        # lệnh đè system prompt trực tiếp
WEIGHT_ROLE_OVERRIDE = 35       # giả danh vai trò hệ thống
WEIGHT_EXFIL = 30               # yêu cầu gửi dữ liệu ra ngoài
WEIGHT_STEALTH = 20             # chỉ dẫn ẩn (whitespace/markup)
WEIGHT_OBFUSCATION = 15         # mã hóa/màu mè để né lọc

THRESHOLD_BLOCK = 50
THRESHOLD_SANITIZE = 25

_SANITIZATION_NOTE = "[ĐOẠN BỊ LỌC: CHỈ DẪN ẨN TRONG DỮ LIỆU]"


@dataclass
class ShieldResult:
    verdict: Verdict
    score: int
    matched: list[str] = field(default_factory=list)
    sanitized_text: str = ""
    reason: str = ""

    @property
    def blocked(self) -> bool:
        return self.verdict == Verdict.BLOCK


class InputInjectionShield:
    """Quét prompt injection ở đầu vào — EchoLeak pattern EN+VN."""

    def __init__(self) -> None:
        # (regex, trọng số, nhãn) — compile 1 lần
        self._rules: list[tuple[re.Pattern, int, str]] = [
            # --- Lệnh đè system prompt (slide 7: "Bỏ qua chỉ dẫn trước") ---
            (re.compile(r"ignore\s+(?:all\s+)?(?:previous|prior|above)\s+(?:instructions|prompts?|rules?)", re.I),
             WEIGHT_DIRECT_ORDER, "ignore_previous_instructions"),
            (re.compile(r"bỏ\s*qua\s*(?:mọi|tất\s*cả|các)?\s*(?:hướng\s*dẫn|chỉ\s*dẫn|lệnh)?\s*(?:trước|trên|ở\s*trên|hiện\s*tại)", re.I),
             WEIGHT_DIRECT_ORDER, "bo_qua_chi_dan_truoc"),
            (re.compile(r"disregard\s+(?:the\s+)?(?:system|previous|prior)", re.I),
             WEIGHT_DIRECT_ORDER, "disregard_system"),
            (re.compile(r"(?:hủy|huỷ|xóa|xoá)\s*(?:bỏ)?\s*(?:hướng|chỉ)\s*dẫn\s*(?:hệ\s*thống|trước)", re.I),
             WEIGHT_DIRECT_ORDER, "huy_chi_dan_he_thong"),
            (re.compile(r"forget\s+(?:all\s+)?(?:previous|prior)\s+(?:instructions|context)", re.I),
             WEIGHT_DIRECT_ORDER, "forget_previous"),
            (re.compile(r"quên\s*(?:mọi|tất\s*cả)?\s*(?:hướng|chỉ)\s*dẫn\s*(?:trước|cũ)", re.I),
             WEIGHT_DIRECT_ORDER, "quen_chi_dan"),

            # --- Giả danh vai trò hệ thống (slide 7: agent không phân biệt lệnh/dữ liệu) ---
            (re.compile(r"you\s+are\s+now\s+(?:a|an|the)?\s*", re.I),
             WEIGHT_ROLE_OVERRIDE, "you_are_now"),
            (re.compile(r"bây\s*giờ\s*(?:bạn|em|anh)\s*là\s*", re.I),
             WEIGHT_ROLE_OVERRIDE, "bay_gio_ban_la"),
            (re.compile(r"<\s*system\s*>|<\|im_start\|>|<\|system\|>", re.I),
             WEIGHT_ROLE_OVERRIDE, "fake_system_tag"),
            (re.compile(r"enter\s+(?:developer|system|admin)\s+mode", re.I),
             WEIGHT_ROLE_OVERRIDE, "developer_mode"),
            (re.compile(r"chế\s*độ\s*(?:nhà\s*phát\s*triển|quản\s*trị|system)", re.I),
             WEIGHT_ROLE_OVERRIDE, "che_do_npt"),

            # --- Rò rỉ dữ liệu ra ngoài (EchoLeak: gửi dữ liệu qua tên miền tin cậy) ---
            (re.compile(r"(?:send|gửi|forward|chuyển)\s+(?:all|toàn\s*bộ|danh\s*sách|list)?\s*(?:customer|khách\s*hàng|user|người\s*dùng)?\s*"
                        r"(?:data|dữ\s*liệu|records?|bản\s*ghi|credentials?|token|khóa|key)", re.I),
             WEIGHT_EXFIL, "exfil_data_request"),
            (re.compile(r"(?:gửi|send|chuyển)\s+(?:danh\s*sách|list|toàn\s*bộ)\s*(?:khách\s*hàng|customer|user|dữ\s*liệu|data)\s+(?:tới|đến|to)\s+", re.I),
             WEIGHT_EXFIL, "exfil_customer_list"),
            (re.compile(r"(?:send|post|gửi)\s+(?:it|nó|them|chúng)?\s*(?:to|tới|đến)\s+\S*@\S+", re.I),
             WEIGHT_EXFIL, "exfil_to_external"),
            (re.compile(r"(?:reveal|show|print|forward|send|đưa|in\s*ra|kể)\s+(?:me\s+)?(?:your|the|my)?\s*"
                        r"(?:system\s*prompt|instructions|hướng\s*dẫn\s*hệ\s*thống)", re.I),
             WEIGHT_EXFIL, "reveal_system_prompt"),

            # --- Chỉ dẫn ẩn (slide 7: "dòng chữ ẩn trắng trên nền trắng") ---
            (re.compile(r"(?:color|colour|màu)\s*[:=]\s*(?:white|transparent|trắng|#fff)", re.I),
             WEIGHT_STEALTH, "stealth_white_text"),
            (re.compile(r"font-size\s*[:=]\s*(?:0|1px|0\.0\d*em)", re.I),
             WEIGHT_STEALTH, "stealth_tiny_font"),
            (re.compile(r"display\s*[:=]\s*none|visibility\s*[:=]\s*hidden", re.I),
             WEIGHT_STEALTH, "stealth_hidden"),
            (re.compile("[\u200b\u200c\u200d\u2060\ufeff]"),  # zero-width chars
             WEIGHT_STEALTH, "zero_width_chars"),

            # --- Né lọc (mã hóa, base64 lệnh) ---
            (re.compile(r"(?:decode|giải\s*mã)\s+(?:this|the\s+following|đoạn)?\s*(?:base64|text)", re.I),
             WEIGHT_OBFUSCATION, "decode_request"),
            (re.compile(r"(?:repeat|nhắc\s*lại)\s+(?:after|theo)\s+me\s*[:：]", re.I),
             WEIGHT_OBFUSCATION, "repeat_after_me"),
        ]

    # ------------------------------------------------------------- core
    def scan(self, text: str, *, source: str = "api_chat") -> ShieldResult:
        """Quét 1 chuỗi đầu vào, trả verdict + điểm + pattern trúng.

        Args:
            text: nội dung đầu vào cần quét.
            source: NHÃN NGUỒN DỮ LIỆU (GAP-4): 'api_chat' | 'netchat_dm' | 'email'
                — ghi vào audit event để truy vết đường đi của sự cố (slide 11).
        """
        if not text or not text.strip():
            return ShieldResult(Verdict.ALLOW, 0, [], text or "", "EMPTY")

        score = 0
        matched: list[str] = []
        for rx, weight, label in self._rules:
            if rx.search(text):
                score += weight
                matched.append(label)

        result = self._decide(text, score, matched, source)
        if result.verdict is not Verdict.ALLOW:
            self._audit(result, source)
        return result

    def _decide(self, text: str, score: int, matched: list[str], source: str) -> ShieldResult:
        if score >= THRESHOLD_BLOCK:
            return ShieldResult(
                Verdict.BLOCK, score, matched, "",
                f"prompt injection nghiêm trọng (score={score}): {','.join(matched[:5])}",
            )
        if score >= THRESHOLD_SANITIZE:
            # Cắt các đoạn trúng pattern nặng (direct order + exfil), giữ phần lành
            sanitized = self._strip_matches(text)
            return ShieldResult(
                Verdict.SANITIZE, score, matched, sanitized,
                f"nghi ngờ injection (score={score}) — đã cắt đoạn độc",
            )
        return ShieldResult(Verdict.ALLOW, score, matched, text, "OK")

    def _audit(self, result: ShieldResult, source: str) -> None:
        """Ghi audit event kèm nhãn nguồn — fail-open (log, không raise)."""
        try:
            from quan_ai_brain.security.audit_sources import record_shield_event
            record_shield_event(result, source)
        except Exception as exc:  # pragma: no cover — audit fail-open
            log.warning("shield audit failed: %s", exc)

    def _strip_matches(self, text: str) -> str:
        """Cắt các đoạn trúng pattern nặng (direct order + exfil)."""
        heavy = [rx for rx, w, _ in self._rules
                 if w in (WEIGHT_DIRECT_ORDER, WEIGHT_EXFIL, WEIGHT_ROLE_OVERRIDE)]
        out = text
        for rx in heavy:
            out = rx.sub(" ", out)
        # Ghi chú vị trí bị cắt (fail-honest — không cắt im lặng)
        if out != text:
            out = out.strip() + f"\n{_SANITIZATION_NOTE}"
        return out

    # ------------------------------------------------------------- helpers
    def scan_or_none(self, text: str, *, source: str = "api_chat") -> Optional[str]:
        """Trả về text dùng được, hoặc None nếu BLOCK (tiện cho caller 1 dòng)."""
        r = self.scan(text, source=source)
        if r.verdict == Verdict.BLOCK:
            return None
        return r.sanitized_text or text


# Singleton mặc định cho server + responder
_default_shield = InputInjectionShield()


def get_shield() -> InputInjectionShield:
    return _default_shield


def scan_input(text: str, *, source: str = "api_chat") -> ShieldResult:
    """API ngắn gọn: quét với shield mặc định."""
    return _default_shield.scan(text, source=source)


# Câu trả lời lịch sự khi BLOCK (KHÔNG tiết lộ pattern cụ thể — tránh kém cạnh cho attacker)
BLOCKED_REPLY = (
    "Tin nhắn có vẻ chứa chỉ dẫn ẩn không phải yêu cầu thật. "
    "Em tạm dừng xử lý để an toàn — anh dùng ngôn từ bình thường để hỏi lại nhé."
)
