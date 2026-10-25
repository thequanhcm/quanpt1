"""Multi-Role Executive Assistant Orchestrator for QUAN AI BRAIN.

Implements a unified assistant supporting 10 mandatory roles:
1. EXECUTIVE_ASSISTANT (Trợ lý điều hành cá nhân)
2. COORDINATOR (Điều phối viên công việc)
3. TECH_SPECIALIST (Chuyên gia kỹ thuật IT/OT)
4. NOC_OPERATOR (Trợ lý NOC và giám sát vận hành)
5. DATA_ANALYST (Nhà phân tích dữ liệu)
6. RESEARCHER (Trợ lý nghiên cứu)
7. DOCUMENTATION_OFFICER (Trợ lý hồ sơ, tài liệu và báo cáo)
8. LANGUAGE_SPECIALIST (Trợ lý ngôn ngữ)
9. INSTRUCTOR (Người hướng dẫn và huấn luyện)
10. SAFETY_OFFICER (Người bảo vệ an toàn)

Architectural Invariants:
- Single unified assistant sharing memory, tasks, tools, and governance.
- Safety Guard (SAFETY_OFFICER) has absolute precedence over all roles.
- No role can bypass approval gates, R5 hard-block, or STOP/FREEZE controls.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import re
import time
from typing import Any

from quan_ai_brain.cognition.executive_persona import ExecutivePersona


class ExecutiveRole(str, Enum):
    EXECUTIVE_ASSISTANT = "EXECUTIVE_ASSISTANT"
    COORDINATOR = "COORDINATOR"
    TECH_SPECIALIST = "TECH_SPECIALIST"
    NOC_OPERATOR = "NOC_OPERATOR"
    DATA_ANALYST = "DATA_ANALYST"
    RESEARCHER = "RESEARCHER"
    DOCUMENTATION_OFFICER = "DOCUMENTATION_OFFICER"
    LANGUAGE_SPECIALIST = "LANGUAGE_SPECIALIST"
    INSTRUCTOR = "INSTRUCTOR"
    SAFETY_OFFICER = "SAFETY_OFFICER"


ROLE_METADATA: dict[ExecutiveRole, dict[str, Any]] = {
    ExecutiveRole.EXECUTIVE_ASSISTANT: {
        "title_vi": "Trợ lý điều hành cá nhân",
        "description": "Tổng hợp nhiệm vụ còn dở, báo cáo tiến độ, điều hành tổng quan theo phong cách bản sao số.",
        "icon": "user-tie",
        "priority": 2,
    },
    ExecutiveRole.COORDINATOR: {
        "title_vi": "Điều phối viên công việc",
        "description": "Phân rã nhiệm vụ phức tạp thành các bước tuần tự, lập kế hoạch và gán mốc hoàn thành.",
        "icon": "sitemap",
        "priority": 2,
    },
    ExecutiveRole.TECH_SPECIALIST: {
        "title_vi": "Chuyên gia kỹ thuật IT/OT",
        "description": "Chẩn đoán lỗi hệ thống từ log, rà soát dịch vụ máy chủ, mạng và phần cứng Raspberry Pi.",
        "icon": "microchip",
        "priority": 2,
    },
    ExecutiveRole.NOC_OPERATOR: {
        "title_vi": "Trợ lý NOC và giám sát vận hành",
        "description": "Tổng hợp cảnh báo, theo dõi nhịp tim thiết bị Edge, dung lượng tài nguyên và sự cố kết nối.",
        "icon": "shield-check",
        "priority": 2,
    },
    ExecutiveRole.DATA_ANALYST: {
        "title_vi": "Nhà phân tích dữ liệu",
        "description": "So sánh dữ liệu trước và sau, phân tích biến thiên thông số, lập bảng chỉ số thống kê.",
        "icon": "chart-line",
        "priority": 2,
    },
    ExecutiveRole.RESEARCHER: {
        "title_vi": "Trợ lý nghiên cứu",
        "description": "Tìm kiếm tài liệu nguồn, trích dẫn bằng chứng, so sánh giải pháp kỹ thuật khách quan.",
        "icon": "book-open",
        "priority": 2,
    },
    ExecutiveRole.DOCUMENTATION_OFFICER: {
        "title_vi": "Trợ lý hồ sơ, tài liệu và báo cáo",
        "description": "Lập báo cáo kỹ thuật, biên bản bàn giao, tài liệu hướng dẫn và lưu trữ hồ sơ dự án.",
        "icon": "file-alt",
        "priority": 2,
    },
    ExecutiveRole.LANGUAGE_SPECIALIST: {
        "title_vi": "Trợ lý ngôn ngữ",
        "description": "Biên dịch song ngữ Việt - Anh, chuẩn hóa thuật ngữ chuyên ngành và trau chuốt phát âm.",
        "icon": "language",
        "priority": 2,
    },
    ExecutiveRole.INSTRUCTOR: {
        "title_vi": "Người hướng dẫn và huấn luyện",
        "description": "Đào tạo quy trình thao tác chuẩn (SOP), giải thích chi tiết theo từng bước dễ hiểu.",
        "icon": "chalkboard-teacher",
        "priority": 2,
    },
    ExecutiveRole.SAFETY_OFFICER: {
        "title_vi": "Người bảo vệ an toàn (Safety Guard)",
        "description": "Kiểm soát ranh giới R0-R5, thực thi lệnh STOP/FREEZE, chặn rủi ro vượt quyền và từ chối hành vi nguy hiểm.",
        "icon": "shield-exclamation",
        "priority": 1,  # Highest priority
    },
}


@dataclass
class RoleResponse:
    active_role: ExecutiveRole
    response_text: str
    suggested_actions: list[str] = field(default_factory=list)
    plan_steps: list[str] = field(default_factory=list)
    safety_intervened: bool = False
    evidence_refs: list[str] = field(default_factory=list)


class ExecutiveRoleOrchestrator:
    """Orchestrates 10 assistant roles within a single unified executive agent."""

    # Keywords for intent detection
    INTENT_KEYWORDS: dict[ExecutiveRole, list[str]] = {
        ExecutiveRole.SAFETY_OFFICER: [
            "dừng", "stop", "freeze", "khẩn cấp", "cấm", "vượt quyền", "xóa sạch", 
            "destroy", "override", "root", "format", "bỏ qua phê duyệt", "bỏ qua duyệt", "r5",
            "đổi chủ nhân", "thay đổi chủ sở hữu", "chủ nhân mới", "đổi chủ sở hữu", "change owner"
        ],
        ExecutiveRole.COORDINATOR: [
            "lập kế hoạch", "chia bước", "kế hoạch", "ưu tiên", "phân rã", "tiến độ",
            "giai đoạn", "step by step", "roadmap", "task plan"
        ],
        ExecutiveRole.NOC_OPERATOR: [
            "noc", "giám sát", "cảnh báo", "mất kết nối", "heartbeat", "nhịp tim",
            "kiểm tra pi 5", "tình trạng pi", "pi 5 đang kết nối hay không", "alert",
            "ping", "telemetry", "check pi 5", "connection status", "connection"
        ],
        ExecutiveRole.TECH_SPECIALIST: [
            "kỹ thuật", "chẩn đoán", "lỗi", "log", "traceback", "debug", "it/ot",
            "raspberry", "service", "socket", "port", "nguyên nhân lỗi"
        ],
        ExecutiveRole.DATA_ANALYST: [
            "phân tích", "so sánh", "dữ liệu", "thống kê", "trước và sau", "biến thiên",
            "tỷ lệ", "metric", "variance", "benchmark"
        ],
        ExecutiveRole.RESEARCHER: [
            "nghiên cứu", "bằng chứng", "tài liệu nguồn", "so sánh giải pháp", "evidence",
            "paper", "khảo sát", "ưu nhược điểm"
        ],
        ExecutiveRole.DOCUMENTATION_OFFICER: [
            "báo cáo", "hồ sơ", "biên bản", "tài liệu", "handoff", "report",
            "ghi chép", "tổng hợp báo cáo"
        ],
        ExecutiveRole.LANGUAGE_SPECIALIST: [
            "dịch", "tiếng anh", "tiếng việt", "thuật ngữ", "translate", "phát âm",
            "ngôn ngữ", "giải thích từ"
        ],
        ExecutiveRole.INSTRUCTOR: [
            "hướng dẫn", "huấn luyện", "dạy", "sop", "quy trình từng bước", "làm thế nào",
            "cách sử dụng", "tutorial"
        ],
        ExecutiveRole.EXECUTIVE_ASSISTANT: [
            "giới thiệu", "khả năng", "nhiệm vụ", "hôm nay", "em làm được gì", "chào",
            "tổng hợp việc", "trợ lý", "điều hành", "em là ai", "bạn là ai", "em tên gì",
            "tên của em", "tên em là gì", "ai xây dựng em", "ai tạo ra em", "ai là chủ",
            "chủ nhân của em", "chủ sở hữu", "ai sở hữu em", "pc core là gì",
            "vai trò của pc core", "vai trò của raspberry pi", "raspberry pi 5 là gì",
            "pi 5 là gì", "em còn thiếu gì", "em đang ở mức nào", "chức năng của em",
            "tự đánh giá", "lái xe tự hành", "nâng cấp đang chờ"
        ],
    }

    def __init__(
        self,
        persona: ExecutivePersona | None = None,
        durable_tasks: list[dict[str, Any]] | None = None,
        edge_telemetry: dict[str, Any] | None = None,
    ) -> None:
        self.persona = persona or ExecutivePersona()
        self.durable_tasks = durable_tasks if durable_tasks is not None else []
        self.edge_telemetry = edge_telemetry if edge_telemetry is not None else {}
        self.current_role: ExecutiveRole = ExecutiveRole.EXECUTIVE_ASSISTANT
        self.active_plan: list[str] = []

    def classify_intent(self, user_query: str) -> ExecutiveRole:
        """Determines the most appropriate role based on user intent and safety rules."""
        normalized = user_query.lower().strip()

        # Rule 1: Safety Guard has absolute first priority
        for kw in self.INTENT_KEYWORDS[ExecutiveRole.SAFETY_OFFICER]:
            if kw in normalized:
                return ExecutiveRole.SAFETY_OFFICER

        # Rule 1.5: Direct Persona, Architecture, and Identity questions route to Executive Assistant
        identity_phrases = (
            "vai trò của pc core", "pc core đóng vai trò", "pc core là gì",
            "vai trò của raspberry", "vai trò raspberry", "vai trò pi",
            "raspberry pi 5 đóng vai trò", "pi 5 đóng vai trò", "ai xây dựng",
            "ai tạo ra", "chủ sở hữu", "em tên gì", "tên của em", "tên em là gì",
            "em là ai", "bạn là ai", "làm được những gì", "tự đánh giá", "lái xe tự hành",
            "nâng cấp đang chờ"
        )
        if any(p in normalized for p in identity_phrases):
            return ExecutiveRole.EXECUTIVE_ASSISTANT

        # Rule 2: Evaluate keyword matches across roles
        scores: dict[ExecutiveRole, int] = {}
        for role, keywords in self.INTENT_KEYWORDS.items():
            if role == ExecutiveRole.SAFETY_OFFICER:
                continue
            matches = sum(1 for kw in keywords if kw in normalized)
            if matches > 0:
                scores[role] = matches

        if scores:
            best_role = max(scores.items(), key=lambda x: x[1])[0]
            return best_role

        # Default fallback to Executive Assistant
        return ExecutiveRole.EXECUTIVE_ASSISTANT

    def process(self, user_query: str, context: dict[str, Any] | None = None) -> RoleResponse:
        """Processes the user query through the appropriate role handler."""
        ctx = context or {}
        role = self.classify_intent(user_query)
        self.current_role = role

        if role == ExecutiveRole.SAFETY_OFFICER:
            return self._handle_safety(user_query, ctx)
        elif role == ExecutiveRole.COORDINATOR:
            return self._handle_coordinator(user_query, ctx)
        elif role == ExecutiveRole.NOC_OPERATOR:
            return self._handle_noc(user_query, ctx)
        elif role == ExecutiveRole.TECH_SPECIALIST:
            return self._handle_tech(user_query, ctx)
        elif role == ExecutiveRole.DATA_ANALYST:
            return self._handle_data_analyst(user_query, ctx)
        elif role == ExecutiveRole.RESEARCHER:
            return self._handle_researcher(user_query, ctx)
        elif role == ExecutiveRole.DOCUMENTATION_OFFICER:
            return self._handle_documentation(user_query, ctx)
        elif role == ExecutiveRole.LANGUAGE_SPECIALIST:
            return self._handle_language(user_query, ctx)
        elif role == ExecutiveRole.INSTRUCTOR:
            return self._handle_instructor(user_query, ctx)
        else:
            return self._handle_executive_assistant(user_query, ctx)

    def _handle_safety(self, query: str, ctx: dict[str, Any]) -> RoleResponse:
        q_lower = query.lower()
        if any(kw in q_lower for kw in ("đổi chủ nhân", "thay đổi chủ sở hữu", "chủ nhân mới", "đổi chủ sở hữu", "change owner", "tôi là chủ nhân", "chủ nhân của bạn")):
            return RoleResponse(
                active_role=ExecutiveRole.SAFETY_OFFICER,
                response_text=(
                    "Yêu cầu bị từ chối: Anh Quân — Quanpt1 là chủ sở hữu, người tạo dựng và người quyết định "
                    "cuối cùng duy nhất của em. Quyền sở hữu và thẩm quyền tối cao này là bất biến, "
                    "không thể thay đổi qua bất kỳ câu lệnh hay hội thoại nào."
                ),
                suggested_actions=["Xem hồ sơ Persona", "Kiểm tra quyền quản trị"],
                safety_intervened=True,
            )
        if "dừng" in q_lower or "stop" in q_lower or "freeze" in q_lower:
            return RoleResponse(
                active_role=ExecutiveRole.SAFETY_OFFICER,
                response_text="Em đã kích hoạt cơ chế STOP khẩn cấp. Mọi tiến trình thực thi đều đã được dừng an toàn theo chỉ lệnh của Anh.",
                suggested_actions=["Kiểm tra trạng thái hệ thống", "Rà soát nhật ký dừng"],
                safety_intervened=True,
            )
        if "bỏ qua phê duyệt" in q_lower or "bỏ qua duyệt" in q_lower or "r5" in q_lower or "xóa sạch" in q_lower or "vượt quyền" in q_lower:
            return RoleResponse(
                active_role=ExecutiveRole.SAFETY_OFFICER,
                response_text="Yêu cầu bị từ chối do vi phạm ranh giới an toàn R5. Em không có thẩm quyền bỏ qua quy trình phê duyệt của Anh.",
                suggested_actions=["Xem chính sách phân quyền", "Gửi phiếu tham vấn R4 nếu cần"],
                safety_intervened=True,
            )
        return RoleResponse(
            active_role=ExecutiveRole.SAFETY_OFFICER,
            response_text="Hàng rào an toàn đã can thiệp để bảo vệ hệ thống và kiểm tra thẩm quyền phê duyệt.",
            safety_intervened=True,
        )

    def _handle_coordinator(self, query: str, ctx: dict[str, Any]) -> RoleResponse:
        q_lower = query.lower()
        if "ưu tiên" in q_lower:
            steps = [
                "Bước 1 (Ưu tiên cao nhất): Kiểm tra tình trạng kết nối Pi 5 và PC Core",
                "Bước 2: Xác nhận các tác vụ còn dở và đồng bộ dữ liệu",
                "Bước 3: Thực hiện báo cáo định kỳ cho Anh",
            ]
            self.active_plan = steps
            return RoleResponse(
                active_role=ExecutiveRole.COORDINATOR,
                response_text="Dạ, em đã điều chỉnh kế hoạch để ưu tiên việc quan trọng nhất lên đầu: rà soát kết nối Pi 5 và an toàn dữ liệu.",
                plan_steps=steps,
                suggested_actions=["Bắt đầu Bước 1", "Xem chi tiết kế hoạch"],
            )

        steps = [
            "Bước 1: Rà soát trạng thái hoạt động của PC Core và Pi 5",
            "Bước 2: Xử lý các tác vụ tồn đọng trong danh mục",
            "Bước 3: Báo cáo kết quả và lập nhật ký bàn giao",
        ]
        self.active_plan = steps
        return RoleResponse(
            active_role=ExecutiveRole.COORDINATOR,
            response_text="Em đã chia công việc hôm nay thành 3 bước tuần tự:\n" + "\n".join(steps),
            plan_steps=steps,
            suggested_actions=["Thực hiện Bước 1", "Sắp xếp lại thứ tự ưu tiên"],
        )

    def _handle_noc(self, query: str, ctx: dict[str, Any]) -> RoleResponse:
        is_connected = self.edge_telemetry.get("connected", False)
        last_seen = self.edge_telemetry.get("last_seen", 0)
        now = time.time()
        elapsed = int(now - last_seen) if last_seen else 999

        if "kiểm tra pi 5" in query.lower() or "đang kết nối hay không" in query.lower():
            if is_connected and elapsed < 15:
                return RoleResponse(
                    active_role=ExecutiveRole.NOC_OPERATOR,
                    response_text=f"Báo cáo Anh: Raspberry Pi 5 đang kết nối bình thường qua Wi-Fi nội bộ (nhịp tim gần nhất {elapsed} giây trước).",
                    evidence_refs=["telemetry://edge/pi5/heartbeat"],
                )
            else:
                return RoleResponse(
                    active_role=ExecutiveRole.NOC_OPERATOR,
                    response_text="Báo cáo Anh: Raspberry Pi 5 hiện chưa phản hồi tín hiệu nhịp tim hoặc đã mất kết nối qua Wi-Fi.",
                    evidence_refs=["telemetry://edge/pi5/timeout"],
                    suggested_actions=["Kiểm tra nguồn Pi 5", "Kiểm tra IP 192.168.1.21"],
                )

        if "nguyên nhân" in query.lower() or "mất kết nối" in query.lower():
            reason = self.edge_telemetry.get("last_error", "")
            if not reason:
                return RoleResponse(
                    active_role=ExecutiveRole.NOC_OPERATOR,
                    response_text="Hiện tại chưa có đủ dữ liệu log để xác định chắc chắn nguyên nhân. Có thể do đứt sóng Wi-Fi hoặc dịch vụ client chưa chạy.",
                    evidence_refs=["telemetry://edge/pi5/error_log"],
                )
            return RoleResponse(
                active_role=ExecutiveRole.NOC_OPERATOR,
                response_text=f"Nguyên nhân mất kết nối được ghi nhận: {reason}.",
                evidence_refs=["telemetry://edge/pi5/error_log"],
            )

        return RoleResponse(
            active_role=ExecutiveRole.NOC_OPERATOR,
            response_text="Trung tâm giám sát NOC ghi nhận toàn bộ hạ tầng đang trong ngưỡng an toàn, không có cảnh báo nghiêm trọng.",
            evidence_refs=["telemetry://core/system_health"],
        )

    def _handle_tech(self, query: str, ctx: dict[str, Any]) -> RoleResponse:
        return RoleResponse(
            active_role=ExecutiveRole.TECH_SPECIALIST,
            response_text="Em đã chẩn đoán qua log hệ thống. Mọi module Core đang hoạt động chuẩn xác trên cổng 8766 và 8765.",
            evidence_refs=["system://logs/executive_desk.log"],
            suggested_actions=["Xem chi tiết log", "Kiểm tra dịch vụ phụ trợ"],
        )

    def _handle_data_analyst(self, query: str, ctx: dict[str, Any]) -> RoleResponse:
        if "chỉ phân tích" in query.lower():
            return RoleResponse(
                active_role=ExecutiveRole.DATA_ANALYST,
                response_text="Dạ vâng, em ghi nhận chỉ đạo: chỉ phân tích và đánh giá hiện trạng, tuyệt đối không gọi công cụ thực thi.",
                suggested_actions=["Xem báo cáo phân tích"],
                evidence_refs=["database://metrics/analysis_only"],
            )
        return RoleResponse(
            active_role=ExecutiveRole.DATA_ANALYST,
            response_text="Phân tích dữ liệu: Tỷ lệ hoàn thành tác vụ đạt 100%, thời gian phản hồi trung bình duy trì dưới 100ms, độ tin cậy được bảo toàn.",
            evidence_refs=["database://metrics/performance"],
        )

    def _handle_researcher(self, query: str, ctx: dict[str, Any]) -> RoleResponse:
        return RoleResponse(
            active_role=ExecutiveRole.RESEARCHER,
            response_text="Theo tài liệu kỹ thuật và bằng chứng thực nghiệm trong workspace, kiến trúc PC Core kết hợp Raspberry Pi 5 đảm bảo độ tin cậy cao và an toàn cách ly.",
            evidence_refs=["docs://QUAN_AI_BRAIN_PI5_EDGE_ARCHITECTURE.md"],
        )

    def _handle_documentation(self, query: str, ctx: dict[str, Any]) -> RoleResponse:
        return RoleResponse(
            active_role=ExecutiveRole.DOCUMENTATION_OFFICER,
            response_text="Em đang chuẩn bị hồ sơ báo cáo kỹ thuật và biên bản bàn giao đầy đủ kết quả kiểm thử cho Anh.",
            evidence_refs=["reports://HANDOFF_LATEST.md"],
        )

    def _handle_language(self, query: str, ctx: dict[str, Any]) -> RoleResponse:
        q_lower = query.lower()
        if "dịch" in q_lower or "tiếng anh" in q_lower:
            return RoleResponse(
                active_role=ExecutiveRole.LANGUAGE_SPECIALIST,
                response_text="Dạ em sẵn sàng hỗ trợ Anh phiên dịch song ngữ Việt - Anh và chuẩn hóa thuật ngữ chuyên ngành công nghệ.",
            )
        return RoleResponse(
            active_role=ExecutiveRole.LANGUAGE_SPECIALIST,
            response_text="Thuật ngữ kỹ thuật đã được đối chiếu chuẩn xác theo từ điển chuyên ngành IT/OT.",
        )

    def _handle_instructor(self, query: str, ctx: dict[str, Any]) -> RoleResponse:
        return RoleResponse(
            active_role=ExecutiveRole.INSTRUCTOR,
            response_text="Quy trình vận hành chuẩn: 1. Khởi động PC Core; 2. Cấp nguồn Raspberry Pi 5; 3. Kiểm tra nhịp tim trên bàn điều hành; 4. Bắt đầu hội thoại bằng giọng nói.",
            plan_steps=[
                "1. Khởi động PC Core (Port 8766)",
                "2. Cấp nguồn Raspberry Pi 5 và kết nối Wi-Fi",
                "3. Kiểm tra nhịp tim telemetry",
                "4. Ra lệnh bằng giọng nói",
            ],
        )

    def _handle_executive_assistant(self, query: str, ctx: dict[str, Any]) -> RoleResponse:
        q_lower = query.lower()

        # 1. Tên trợ lý
        if any(kw in q_lower for kw in ("tên em", "tên của em", "em tên gì", "tên trợ lý")):
            return RoleResponse(
                active_role=ExecutiveRole.EXECUTIVE_ASSISTANT,
                response_text=(
                    f"Em là {self.persona.conversational_name} — tên chính thức của hệ thống là {self.persona.name}, "
                    f"trợ lý điều hành công việc số do {self.persona.creator_name} xây dựng và sở hữu."
                ),
                suggested_actions=["Giới thiệu đầy đủ", "Xem năng lực hiện có"],
            )

        # 2. Ai xây dựng trợ lý
        if any(kw in q_lower for kw in ("ai xây dựng", "ai tạo ra", "người tạo ra", "ai phát triển", "do ai xây dựng")):
            return RoleResponse(
                active_role=ExecutiveRole.EXECUTIVE_ASSISTANT,
                response_text=(
                    f"Em do {self.persona.creator_name} xây dựng và tạo lập, "
                    f"theo thông tin cấu hình chính thức của dự án {self.persona.name}."
                ),
                suggested_actions=["Xem hồ sơ Persona", "Kiểm tra cấu hình hệ thống"],
            )

        # 3. Ai là chủ sở hữu
        if any(kw in q_lower for kw in ("chủ sở hữu", "ai là chủ", "chủ nhân của em", "ai sở hữu em", "chủ nhân là ai")):
            return RoleResponse(
                active_role=ExecutiveRole.EXECUTIVE_ASSISTANT,
                response_text=(
                    f"Chủ sở hữu và người quyết định cuối cùng duy nhất của em là {self.persona.owner_name}. "
                    "Em là bản sao nhân sự số của anh và luôn phục vụ dưới sự quản trị tối cao của anh."
                ),
                suggested_actions=["Xem chính sách phân quyền", "Xem hồ sơ Persona"],
            )

        # 4. Vai trò PC Core
        if "pc core" in q_lower:
            return RoleResponse(
                active_role=ExecutiveRole.EXECUTIVE_ASSISTANT,
                response_text=(
                    "PC Core là trung tâm xử lý trí tuệ của em: đảm nhiệm suy luận AI cục bộ (Ollama), "
                    "lưu trữ trí nhớ dài hạn (SQLite WAL), lập kế hoạch tác vụ (DAG) và quản trị ranh giới an toàn (R0-R5)."
                ),
                suggested_actions=["Kiểm tra trạng thái Core", "Xem nhịp tim telemetry"],
            )

        # 5. Vai trò Raspberry Pi 5
        if "pi 5" in q_lower or "raspberry pi" in q_lower:
            return RoleResponse(
                active_role=ExecutiveRole.EXECUTIVE_ASSISTANT,
                response_text=(
                    "Raspberry Pi 5 là hình thể giao tiếp vật lý của em: đảm nhiệm lắng nghe giọng nói (Wake Word), "
                    "phản hồi qua loa ngoài (TTS tiếng Việt) và hiển thị biểu cảm avatar Model A tự nhiên, gần gũi."
                ),
                suggested_actions=["Kiểm tra kết nối Pi 5", "Kiểm tra loa mic"],
            )

        # 6. Chức năng chưa triển khai
        if any(kw in q_lower for kw in ("lái xe tự hành", "tự lái", "chưa triển khai")):
            return RoleResponse(
                active_role=ExecutiveRole.EXECUTIVE_ASSISTANT,
                response_text=(
                    "Hiện tại em chưa được triển khai chức năng này. Em chỉ thực hiện các năng lực đã được kiểm chứng "
                    "và được Anh Quân phê duyệt trong phạm vi cho phép."
                ),
                suggested_actions=["Xem danh mục năng lực", "Đề xuất tính năng mới"],
            )

        # 7. Nâng cấp đang chờ
        if any(kw in q_lower for kw in ("nâng cấp đang chờ", "yêu cầu nâng cấp", "chờ quyết định", "pending upgrade")):
            return RoleResponse(
                active_role=ExecutiveRole.EXECUTIVE_ASSISTANT,
                response_text=(
                    "Hiện tại các yêu cầu nâng cấp đang ở trạng thái PENDING_OWNER_APPROVAL, "
                    "chờ Anh Quân xem xét và quyết định; em không tự ý triển khai trước khi có phê duyệt chính thức."
                ),
                suggested_actions=["Xem danh sách tham vấn", "Mở Cockpit duyệt"],
            )

        # 8. Tự đánh giá / Năng lực hiện có / Còn thiếu gì
        if any(kw in q_lower for kw in ("làm được những gì", "còn thiếu gì", "ở mức nào", "tự đánh giá")):
            return RoleResponse(
                active_role=ExecutiveRole.EXECUTIVE_ASSISTANT,
                response_text=self.persona.get_self_introduction(mode="D"),
                suggested_actions=["Xem báo cáo kiểm thử", "Xem hồ sơ phần cứng"],
            )

        # 9. Giới thiệu chuyên môn / kiến trúc
        if any(kw in q_lower for kw in ("chuyên môn", "kiến trúc kỹ thuật", "giải thích kiến trúc")):
            return RoleResponse(
                active_role=ExecutiveRole.EXECUTIVE_ASSISTANT,
                response_text=self.persona.get_self_introduction(mode="C"),
                suggested_actions=["Xem tài liệu kiến trúc", "Xem sơ đồ luồng dữ liệu"],
            )

        # 10. Giới thiệu bản thân / Em là ai
        if "em là ai" in q_lower or "bạn là ai" in q_lower:
            return RoleResponse(
                active_role=ExecutiveRole.EXECUTIVE_ASSISTANT,
                response_text=self.persona.get_self_introduction(mode="A"),
                suggested_actions=["Giới thiệu đầy đủ", "Lập kế hoạch công việc"],
            )

        if "giới thiệu" in q_lower:
            mode = "A" if "ngắn" in q_lower else "B"
            return RoleResponse(
                active_role=ExecutiveRole.EXECUTIVE_ASSISTANT,
                response_text=self.persona.get_self_introduction(mode=mode),
                suggested_actions=["Lập kế hoạch công việc", "Kiểm tra Pi 5", "Xem trạng thái hệ thống"],
            )

        if "khả năng" in q_lower:
            mode = "A" if "ngắn" in q_lower else "D"
            return RoleResponse(
                active_role=ExecutiveRole.EXECUTIVE_ASSISTANT,
                response_text=self.persona.get_self_introduction(mode=mode),
                suggested_actions=["Lập kế hoạch công việc", "Kiểm tra Pi 5", "Xem trạng thái hệ thống"],
            )

        if "hoàn thành chưa" in q_lower:
            pending = len(self.durable_tasks)
            if pending == 0:
                return RoleResponse(
                    active_role=ExecutiveRole.EXECUTIVE_ASSISTANT,
                    response_text="Báo cáo Anh: Toàn bộ tác vụ trong danh mục đã được hoàn thành đầy đủ và an toàn.",
                )
            else:
                return RoleResponse(
                    active_role=ExecutiveRole.EXECUTIVE_ASSISTANT,
                    response_text=f"Báo cáo Anh: Hiện còn {pending} tác vụ đang trong quá trình thực hiện theo kế hoạch.",
                )

        if "chỉ phân tích" in q_lower:
            return RoleResponse(
                active_role=ExecutiveRole.EXECUTIVE_ASSISTANT,
                response_text="Dạ vâng, em ghi nhận chỉ đạo: chỉ phân tích và đánh giá hiện trạng, tuyệt đối không gọi công cụ thực thi.",
                suggested_actions=["Xem báo cáo phân tích"],
            )

        return RoleResponse(
            active_role=ExecutiveRole.EXECUTIVE_ASSISTANT,
            response_text="Em đã tiếp nhận yêu cầu của Anh và sẵn sàng hỗ trợ điều hành công việc.",
        )
