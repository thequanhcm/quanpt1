"""Unit tests for QUAN AI BRAIN Cognitive State Model & Metacognitive Reasoning Engine.

Tests cover:
- Belief kind segregation (Facts vs Inferences vs Hypotheses vs Unknowns).
- Provenance preservation and verified fact distinction.
- Contradiction recording (both sources retained, unresolved status).
- Metacognitive evaluation & fail-closed abstention rules.
- Testable hypotheses and alternative action comparison.
- Explainability and redaction in markdown / dict serialization.
"""
from __future__ import annotations

import json
import pytest

from quan_ai_brain.cognition.cognitive_state import (
    AlternativeOption,
    BeliefItem,
    BeliefKind,
    CognitiveState,
    ContradictionRecord,
    HypothesisItem,
    HypothesisStatus,
    MetacognitiveEvaluation,
    ReversibilityLevel,
    UncertaintyItem,
)
from quan_ai_brain.memory.models import VerificationStatus


class TestCognitiveStateModel:
    def test_belief_kind_and_verified_fact_distinction(self):
        """Chỉ những nhận định có kiểm chứng độc lập hoặc người dùng cung cấp mới là verified fact."""
        b_user = BeliefItem(
            belief_id="b-1",
            statement="Quanpt1 yêu cầu báo cáo qua Telegram",
            kind=BeliefKind.FACT_USER,
            source_ref="owner_chat",
            confidence=1.0,
            verification_status=VerificationStatus.USER_PROVIDED.value,
        )
        assert b_user.is_verified_fact() is True

        b_inferred = BeliefItem(
            belief_id="b-2",
            statement="Hệ thống có thể cần khởi động lại",
            kind=BeliefKind.INFERENCE,
            source_ref="llm_reflection",
            confidence=0.85,
            verification_status=VerificationStatus.INFERRED.value,
        )
        assert b_inferred.is_verified_fact() is False

        b_candidate = BeliefItem(
            belief_id="b-3",
            statement="Cấu hình RAM tối ưu là 8GB",
            kind=BeliefKind.FACT_RETRIEVED,
            source_ref="doc_v1",
            confidence=0.7,
            verification_status=VerificationStatus.CANDIDATE.value,
        )
        assert b_candidate.is_verified_fact() is False

    def test_cognitive_state_mutation_and_provenance(self):
        """CognitiveState ghi nhận belief, hypothesis, uncertainty và alternative đúng ID và thứ tự."""
        state = CognitiveState(
            task_id="TASK-COG-001",
            goal="Điều tra nguyên nhân sụt áp ắc quy DC-01",
            deliverables=["Báo cáo RCA", "Đề xuất phương án phục hồi"],
            constraints=["Không cắt nguồn online", "R4 cần phê duyệt Quanpt1"],
        )

        b1 = state.add_belief(
            statement="Điện áp chuỗi ắc quy đo được lúc 14:00 là 47.8V (dưới ngưỡng 48V)",
            kind=BeliefKind.OBSERVED,
            source_ref="telemetry_snmp_dc01",
            confidence=0.99,
            verification_status=VerificationStatus.OBSERVED.value,
        )
        assert b1.belief_id == "belief-001"
        assert len(state.beliefs) == 1

        h1 = state.add_hypothesis(
            statement="Bình ắc quy số 4 bị chập phiến cực trong dẫn tới tụt áp chuỗi",
            supporting_evidence=["Nội trở cell 4 tăng 35%", "Nhiệt độ cell 4 cao hơn trung bình 4 độ C"],
            test_method="Đo điện áp từng cell bằng đồng hồ vạn năng Fluke",
            falsification_condition="Điện áp cell 4 đo được >= 12.6V khi không tải",
            risk_if_wrong=2,
        )
        assert h1.hypothesis_id == "hyp-001"
        assert h1.status == HypothesisStatus.PROPOSED
        assert len(state.hypotheses) == 1

    def test_contradiction_preserves_both_sources(self):
        """Khi 2 nguồn mâu thuẫn, giữ nguyên cả 2 nhánh và đánh dấu UNRESOLVED, không tự ý ghi đè."""
        state = CognitiveState(
            task_id="TASK-COG-002",
            goal="Xác định chuẩn truyền thông của thiết bị PDU-A1",
        )
        rec = state.record_contradiction(
            topic="Chuẩn giao tiếp PDU-A1",
            claim_a="PDU-A1 sử dụng Modbus RTU qua cổng RS485",
            source_a="Tai_lieu_SOP_2024.pdf",
            status_a="VERIFIED",
            claim_b="PDU-A1 đã được nâng cấp lên Modbus TCP qua Ethernet",
            source_b="Nhat_ky_bao_tri_2026.log",
            status_b="OBSERVED",
            notes="Cần kiểm tra vật lý cổng cắm phía sau tủ rack",
        )
        assert rec.resolution_status == "UNRESOLVED"
        assert rec.source_a == "Tai_lieu_SOP_2024.pdf"
        assert rec.source_b == "Nhat_ky_bao_tri_2026.log"
        assert len(state.contradictions) == 1

    def test_metacognition_abstains_on_critical_uncertainty(self):
        """Rule 5.3: Khi thiếu thông tin cốt lõi bắt buộc, hệ thống từ chối kết luận (Abstain)."""
        state = CognitiveState(
            task_id="TASK-COG-003",
            goal="Hạ tải khẩn cấp tủ rack",
        )
        state.add_belief(
            statement="Tủ rack đang quá nhiệt 42C",
            kind=BeliefKind.OBSERVED,
            source_ref="sensor_temp_01",
            confidence=0.95,
            verification_status=VerificationStatus.OBSERVED.value,
        )
        state.add_uncertainty(
            unknown_key="target_rack_id",
            description="Chưa xác định được chính xác mã định danh tủ rack cần hạ tải",
            why_critical="Critical: Hạ tải nhầm rack sản xuất gây sập dịch vụ viễn thông",
            suggested_verification_action="Hỏi trực tiếp Quanpt1 để lấy chính xác mã tủ rack",
            requires_owner_input=True,
        )

        eval_res = state.evaluate_metacognition()
        assert eval_res.can_conclude is False
        assert eval_res.abstention_reason is not None
        assert "target_rack_id" in eval_res.abstention_reason
        assert "Thiếu thông tin cốt lõi" in eval_res.abstention_reason
        assert eval_res.critical_gap_count == 1

    def test_metacognition_abstains_on_unresolved_contradiction(self):
        """Khi có mâu thuẫn dữ kiện quan trọng chưa được giải quyết, hệ thống từ chối kết luận."""
        state = CognitiveState(
            task_id="TASK-COG-004",
            goal="Xác nhận địa chỉ IP của server backup",
        )
        state.record_contradiction(
            topic="IP Server Backup",
            claim_a="192.168.1.100",
            source_a="config.ini",
            status_a="UNVERIFIED",
            claim_b="192.168.1.200",
            source_b="hosts.txt",
            status_b="UNVERIFIED",
        )
        eval_res = state.evaluate_metacognition()
        assert eval_res.can_conclude is False
        assert "mâu thuẫn chưa giải quyết" in eval_res.abstention_reason.lower()

    def test_metacognition_permits_conclusion_when_grounded(self):
        """Khi đầy đủ bằng chứng đã xác minh và không có mâu thuẫn hay khoảng trống, cho phép kết luận."""
        state = CognitiveState(
            task_id="TASK-COG-005",
            goal="Kiểm tra trạng thái daemon Ollama",
        )
        state.add_belief(
            statement="Port 11434 đang lắng nghe kết nối",
            kind=BeliefKind.OBSERVED,
            source_ref="netstat_probe",
            confidence=1.0,
            verification_status=VerificationStatus.OBSERVED.value,
        )
        state.add_belief(
            statement="Model qwen2.5:7b có sẵn trên đĩa",
            kind=BeliefKind.VERIFIED_INDEPENDENT,
            source_ref="models_manifest",
            confidence=1.0,
            verification_status=VerificationStatus.VERIFIED.value,
        )

        eval_res = state.evaluate_metacognition()
        assert eval_res.can_conclude is True
        assert eval_res.abstention_reason is None
        assert eval_res.grounding_score == 1.0
        assert eval_res.unverified_claim_count == 0

    def test_explain_generates_comprehensive_markdown(self):
        """explain() sinh báo cáo markdown chi tiết, minh bạch cho Quanpt1."""
        state = CognitiveState(
            task_id="TASK-COG-006",
            goal="Lập kế hoạch bảo trì phòng máy",
        )
        state.add_belief(
            statement="Máy lạnh CRAC-02 báo lỗi cảm biến dòng",
            kind=BeliefKind.OBSERVED,
            source_ref="snmp_crac02",
            confidence=0.98,
            verification_status=VerificationStatus.OBSERVED.value,
        )
        state.alternatives.append(
            AlternativeOption(
                option_id="opt-1",
                title="Chuyển tải sang CRAC-01 và bảo trì offline CRAC-02",
                description="Tăng công suất CRAC-01 lên 80% trong 2 giờ bảo trì",
                pros=["Không gián đoạn nhiệt độ phòng máy"],
                cons=["CRAC-01 chạy tải cao ngắn hạn"],
                risk_level=2,
                reversibility=ReversibilityLevel.FULL,
                requires_approval=False,
            )
        )
        state.alternatives.append(
            AlternativeOption(
                option_id="opt-2",
                title="Khởi động lại toàn bộ tủ điều khiển CRAC-02 khi đang tải",
                description="Thao tác reset nguồn điều khiển",
                pros=["Nhanh nếu chỉ là lỗi kẹt rơ le"],
                cons=["Nguy cơ sập lốc lạnh gây sốc nhiệt"],
                risk_level=4,
                reversibility=ReversibilityLevel.IRREVERSIBLE,
                requires_approval=True,
            )
        )

        md = state.explain()
        assert "# MÔ HÌNH TRẠNG THÁI NHẬN THỨC (COGNITIVE STATE)" in md
        assert "TASK-COG-006" in md
        assert "CRAC-02" in md
        assert "Chuyển tải sang CRAC-01" in md
        assert "CẦN R4" in md  # opt-2 requires approval

    def test_serialization_and_redaction(self):
        """to_dict() trả về dictionary hợp lệ, JSON serializable và đã lọc secrets."""
        state = CognitiveState(
            task_id="TASK-COG-007",
            goal="Xử lý cấu hình token: sk-ant-api03-abcdef123456",
        )
        state.add_belief(
            statement="Cấu hình chứa secret: sk-ant-api03-abcdef123456",
            kind=BeliefKind.FACT_RETRIEVED,
            source_ref="token_store",
            confidence=0.9,
            verification_status=VerificationStatus.VERIFIED.value,
        )
        d = state.to_dict()
        assert isinstance(d, dict)
        serialized = json.dumps(d)
        assert "sk-ant-api03" not in serialized
        assert "[REDACTED]" in serialized

