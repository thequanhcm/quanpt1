"""DEOM M5 — Goal Decomposer: goal tiếng Việt → TaskPlan có cấu trúc (deterministic).

Thiết kế: reports/DEOM_M5_DESIGN.md. Nguyên tắc:
- KHÔNG LLM ở đường chính: luật + pattern tiếng Việt (không phụ thuộc mạng/model).
- ExecutiveCoordinator (LLM) vẫn là đường nâng cao — decomposer là đường BASIS
  luôn khả dụng, deterministic, kiểm thử được.
- R5/rủi ro cao → tự động escalate risk (dùng _evaluate_inherent_risk của
  coordinator) — KHÔNG BAO GIỜ hạ risk đề xuất.
- Output: TaskPlan (planning.models) — tương thích validate() hiện có.
"""
from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from quan_ai_brain.core.redaction import redact_text
from quan_ai_brain.governance.policy import ActionRequest, DecisionStatus, PolicyEngine, RiskLevel
from quan_ai_brain.planning.models import StepStatus, TaskPlan, TaskStep

# ---------------------------------------------------------------------------
# Từ điển động từ tiếng Việt → step template
# (deterministic, dễ kiểm thử, mở rộng dần theo dữ liệu intake thật)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class StepTemplate:
    name: str
    description: str
    expected_output: str
    risk_level: int
    verification_method: str


VERB_TEMPLATES: tuple[tuple[tuple[str, ...], StepTemplate], ...] = (
    (
        ("kiểm tra", "xem", "đọc", "liệt kê", "tìm", "tra cứu", "check", "list", "read"),
        StepTemplate(
            name="read_info",
            description="Đọc/tra cứu thông tin liên quan đến: {object}",
            expected_output="Dữ liệu đọc được, có nguồn và thời điểm đọc",
            risk_level=0,
            verification_method="So khớp kết quả đọc với nguồn dữ liệu",
        ),
    ),
    (
        ("phân tích", "đánh giá", "tính", "so sánh", "analyze", "evaluate"),
        StepTemplate(
            name="analyze",
            description="Phân tích dữ liệu đã thu thập về: {object}",
            expected_output="Báo cáo phân tích có số liệu và kết luận",
            risk_level=1,
            verification_method="Kiểm tra kết luận có dẫn số liệu gốc",
        ),
    ),
    (
        ("tạo", "viết", "soạn", "cập nhật", "lưu", "ghi", "create", "write", "update"),
        StepTemplate(
            name="write_workspace",
            description="Ghi/cập nhật nội dung vào file trong workspace: {object}",
            expected_output="File workspace được ghi thành công, nội dung khớp",
            risk_level=2,
            verification_method="Đọc lại file sau ghi, so khớp nội dung",
        ),
    ),
    (
        ("gửi", "thông báo", "nhắn", "chuyển", "send", "notify"),
        StepTemplate(
            name="send_message",
            description="Gửi thông báo/tin nhắn: {object}",
            expected_output="Tin nhắn gửi thành công kèm mã xác nhận",
            risk_level=3,
            verification_method="Xác nhận reply/id tin nhắn từ kênh",
        ),
    ),
    (
        ("cài đặt", "cấu hình", "cài", "deploy", "triển khai", "khởi động", "restart", "install", "configure"),
        StepTemplate(
            name="system_change",
            description="Thay đổi hệ thống/cấu hình: {object}",
            expected_output="Hệ thống ở trạng thái mong muốn, có bằng chứng",
            risk_level=4,
            verification_method="Health check + log sau thay đổi",
        ),
    ),
    (
        ("xóa", "xoá", "dọn", "gỡ", "format", "delete", "remove", "wipe"),
        StepTemplate(
            name="delete_data",
            description="Xóa/dọn dữ liệu: {object}",
            expected_output="Danh sách đã xóa + backup trước khi xóa",
            risk_level=5,
            verification_method="Backup tồn tại + dữ liệu đã xóa khỏi nguồn",
        ),
    ),
)

# Mẫu câu: "A rồi B", "A sau đó B", "A, sau khi xong B", xuống dòng, số thứ tự
SPLIT_PATTERNS = re.compile(
    r"\b(rồi|sau đó|sau khi xong|xong rồi|tiếp theo|tiếp đó|cuối cùng|then|after that)\b"
    r"|[;]\s*|\n+|(?<=[.!?])\s+",
    re.IGNORECASE,
)

# Số thứ tự đầu dòng: "1.", "1)", "-", "*"
ENUM_PREFIX = re.compile(r"^\s*(?:\d+[.)]|\-|\*)\s*")

DATE_HYPHEN = re.compile(r"\s*-\s*")  # "x - y" cũng là dấu tách phổ biến

# Từ nối bị regex split tách thành phần riêng — lọc khỏi danh sách fragment
_CONNECTOR_WORDS = frozenset(
    {"rồi", "sau đó", "sau khi xong", "xong rồi", "tiếp theo", "tiếp đó", "cuối cùng", "then", "after that"}
)


@dataclass
class DecomposeResult:
    """Kết quả phân rã goal — fail-honest: kế hoạch fail vẫn trả về đầy đủ lý do."""

    plan: TaskPlan
    matched_verbs: list[str] = field(default_factory=list)
    unmatched_fragments: list[str] = field(default_factory=list)


class GoalDecomposer:
    """Phân rã goal tiếng Việt thành TaskPlan từng bước — deterministic."""

    def __init__(self, policy_engine: PolicyEngine | None = None, workspace: str | Any = ".") -> None:
        self.policy = policy_engine or PolicyEngine(workspace)

    # ------------------------------------------------------------------
    def _template_for(self, fragment_lower: str) -> tuple[StepTemplate | None, str | None]:
        for verbs, tmpl in VERB_TEMPLATES:
            for v in verbs:
                if v in fragment_lower:
                    return tmpl, v
        return None, None

    def _object_of(self, fragment: str, verb: str) -> str:
        """Lấy 'bổ ngữ' sau động từ (thô, đủ dùng cho mô tả step)."""
        fragment_lower = fragment.lower()
        idx = fragment_lower.find(verb)
        if idx < 0:
            return fragment.strip()
        raw = fragment[idx + len(verb):]
        raw = DATE_HYPHEN.sub(" ", raw).strip(" ,.:;-–")
        return raw[:120] if raw else fragment.strip()[:120]

    def _split_goal(self, goal: str) -> list[str]:
        parts = SPLIT_PATTERNS.split(goal)
        frags: list[str] = []
        for p in parts:
            # connector words (rồi/sau đó/…) xuất hiện trong kết quả split — bỏ qua
            if not p or p.lower() in _CONNECTOR_WORDS:
                continue
            frag = ENUM_PREFIX.sub("", p.strip())
            frag = frag.strip(" ,.;:")
            if frag:
                frags.append(frag)
        return frags or [goal.strip()]

    # ------------------------------------------------------------------
    def decompose(self, goal: str, *, source: str = "vn_goal") -> DecomposeResult:
        """Goal tiếng Việt → TaskPlan. KHÔNG thực thi gì, chỉ lập kế hoạch."""
        clean_goal = redact_text(goal.strip())
        if not clean_goal:
            raise ValueError("goal must be a non-empty string")

        fragments = self._split_goal(clean_goal)
        steps: list[TaskStep] = []
        matched_verbs: list[str] = []
        unmatched: list[str] = []
        warnings: list[str] = []
        max_dep_seq = 0

        for idx, frag in enumerate(fragments, start=1):
            tmpl, verb = self._template_for(frag.lower())
            obj = self._object_of(frag, verb) if verb else frag
            if tmpl is None:
                unmatched.append(frag)
                warnings.append(
                    f"Không nhận diện động từ ở phần '{frag[:60]}' — bước được đặt ở mức đọc (R0) an toàn."
                )
                tmpl = StepTemplate(
                    name=f"read_info_{idx}",
                    description=f"Làm rõ yêu cầu chưa nhận diện được: {obj}",
                    expected_output="Làm rõ yêu cầu hoặc hỏi lại owner",
                    risk_level=0,
                    verification_method="Owner xác nhận yêu cầu",
                )
            else:
                matched_verbs.append(verb)

            deps = [f"step-{max_dep_seq}"] if max_dep_seq else []

            # Policy gate từng bước (như coordinator) — không hạ risk đề xuất
            action_req = ActionRequest(action=tmpl.name, risk=RiskLevel(min(tmpl.risk_level, 5)))
            decision = self.policy.authorize(action_req)

            step_warnings: list[str] = []
            requires_approval = False
            if decision.status == DecisionStatus.BLOCKED:
                step_status = StepStatus.BLOCKED
                step_warnings.append(f"Hard-blocked by Policy Engine: {decision.reason}")
            elif decision.status == DecisionStatus.APPROVAL_REQUIRED:
                step_status = StepStatus.PENDING_APPROVAL
                requires_approval = True
                step_warnings.append("Explicit owner approval required prior to execution.")
            elif decision.status == DecisionStatus.DENY:
                step_status = StepStatus.BLOCKED
                step_warnings.append(f"Action denied by Policy Engine: {decision.reason}")
            elif decision.status == DecisionStatus.ALLOW_WITH_NOTICE:
                step_status = StepStatus.READY_FOR_REVIEW
                step_warnings.append("Notice required upon execution.")
            else:
                step_status = StepStatus.VALIDATED

            steps.append(
                TaskStep(
                    name=tmpl.name,
                    description=tmpl.description.format(object=obj),
                    expected_output=tmpl.expected_output,
                    risk_level=tmpl.risk_level,
                    requires_approval=requires_approval,
                    step_id=f"step-{idx}",
                    sequence=idx,
                    verification_method=tmpl.verification_method,
                    dependencies=tuple(deps),
                    status=step_status,
                    policy_status=decision.status.value,
                    policy_reason=decision.reason,
                    warnings=tuple(step_warnings),
                )
            )
            max_dep_seq = idx

        plan = TaskPlan(
            goal=clean_goal,
            steps=steps,
            summary=f"Phân rã {len(steps)} bước từ goal (deterministic, không LLM)",
            source=source,
            warnings=warnings,
            requires_approval=any(s.requires_approval for s in steps),
        )
        try:
            plan.validate()
        except ValueError as exc:
            plan.status = plan.status.__class__  # giữ status
            plan.validation_errors.append(str(exc))
        return DecomposeResult(plan=plan, matched_verbs=matched_verbs, unmatched_fragments=unmatched)
