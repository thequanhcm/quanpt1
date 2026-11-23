# -*- coding: utf-8 -*-
"""Sprint 3 MEMORY-ADAPTER — tests (card TASK-VMAIL-S3).

Mock 100% (KHÔNG đụng data thật, KHÔNG SOAP, KHÔNG db live) — kiểm tra:
- §6.1 retrieval: MemoryFacade.search được gọi đúng, sort VERIFIED trước (§6.3),
  lỗi facade → fail-honest (result.error), contradictions phát hiện.
- §6.4 candidate: chỉ lưu nội dung có giá trị dài hạn; TỪ CHỐI email thô/
  nhạy cảm/ngắn; đường candidate → facade.add(memory_type='candidate') (R4
  quarantine); KHÔNG BAO GIỜ tự promote.
- extract_candidates_from_thread: đọc ThreadAnalysis (decisions/commitments/
  changes), trích mail #id, không vượt max_items.
- record_followup_experience: ExperienceStore mock PENDING; degraded khi None.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from quan_ai_brain.office.memory_adapter import (  # noqa: E402
    CherryMemoryAdapter, CandidateResult, RetrievalHit, RetrievalResult,
)


# ---------- helpers ----------
def make_hit(content: str, verification: str = "OBSERVED", score: float = 0.5,
             layer: str = "semantic", source_ref: str = "") -> MagicMock:
    h = MagicMock()
    h.content = content
    h.fact_level = "FACT" if verification == "VERIFIED" else "OBSERVED"
    h.verification_status = verification
    h.source_layer = layer
    h.score = score
    h.created_at = "2026-11-24T00:00:00+00:00"
    h.metadata = {"source_ref": source_ref}
    return h


def make_facade(hits: list[MagicMock] | None = None, error: bool = False) -> MagicMock:
    f = MagicMock()
    if error:
        f.search.side_effect = RuntimeError("db locked")
    else:
        f.search.return_value = hits or []
    f.add.return_value = {"layer": "quarantine", "id": "q-1", "fact_level": "QUARANTINED"}
    return f


@dataclass
class FakeAnalysis:
    """ThreadAnalysis tối giản của Sprint 2."""
    key: str = "luồng-khoi"
    decisions: list[str] = field(default_factory=list)
    commitments: list[str] = field(default_factory=list)
    changes: list[str] = field(default_factory=list)


# ---------- §6.1 retrieval ----------
class TestRetrieveContext:
    def test_calls_facade_and_wraps_hits(self):
        fac = make_facade([make_hit("Chốt phương án A (mail #12)", "OBSERVED", 0.7)])
        ad = CherryMemoryAdapter(facade=fac, experience_store=MagicMock())
        res = ad.retrieve_context("phương án A")
        assert isinstance(res, RetrievalResult)
        assert res.error == ""
        assert len(res.hits) == 1
        assert res.hits[0].content == "Chốt phương án A (mail #12)"
        fac.search.assert_called_once()

    def test_verified_ranked_before_observed(self):
        """§6.3: ưu tiên nguồn xác thực."""
        fac = make_facade([
            make_hit("nhận định A", "OBSERVED", 0.9),
            make_hit("thông tin đã xác minh B", "VERIFIED", 0.4),
        ])
        ad = CherryMemoryAdapter(facade=fac, experience_store=MagicMock())
        res = ad.retrieve_context("A B")
        assert res.hits[0].verification == "VERIFIED"

    def test_fail_honest_on_facade_error(self):
        ad = CherryMemoryAdapter(facade=make_facade(error=True),
                                 experience_store=MagicMock())
        res = ad.retrieve_context("bất kỳ")
        assert res.error and "RuntimeError" in res.error
        assert res.hits == []

    def test_short_query_rejected(self):
        ad = CherryMemoryAdapter(facade=make_facade(), experience_store=MagicMock())
        res = ad.retrieve_context("a")
        assert res.error and res.hits == []
        ad.facade.search.assert_not_called()

    def test_contradiction_detected(self):
        fac = make_facade([
            make_hit("Hạn nộp báo cáo là ngày 25/11 đã chốt với phòng", "OBSERVED", 0.6),
            make_hit("Hạn nộp báo cáo được lùi sang ngày 30/11", "VERIFIED", 0.55),
        ])
        ad = CherryMemoryAdapter(facade=fac, experience_store=MagicMock())
        res = ad.retrieve_context("hạn nộp báo cáo")
        assert res.contradictions, "phải phát hiện 2 bản ghi cùng chủ đề khác nội dung"
        assert "CẢ HAI" in res.contradictions[0]

    def test_no_contradiction_for_same_content(self):
        fac = make_facade([
            make_hit("Hạn nộp báo cáo là ngày 25/11 đã chốt", "OBSERVED", 0.6),
            make_hit("Hạn nộp báo cáo là ngày 25/11 đã chốt", "VERIFIED", 0.55),
        ])
        ad = CherryMemoryAdapter(facade=fac, experience_store=MagicMock())
        res = ad.retrieve_context("hạn nộp báo cáo")
        assert res.contradictions == []

    def test_retrieve_decisions_filters(self):
        fac = make_facade([
            make_hit("Đã chốt phương án vận chuyển", "OBSERVED", 0.6),
            make_hit("Thời tiết hôm nay đẹp", "OBSERVED", 0.59),
        ])
        ad = CherryMemoryAdapter(facade=fac, experience_store=MagicMock())
        res = ad.retrieve_decisions("vận chuyển")
        assert len(res.hits) == 1 and "chốt" in res.hits[0].content.lower()

    def test_retrieve_related_tasks_filters(self):
        fac = make_facade([
            make_hit("Anh Quân được giao nhiệm vụ tổng hợp số liệu", "OBSERVED", 0.6),
            make_hit("Cà phê sáng rất ngon", "OBSERVED", 0.59),
        ])
        ad = CherryMemoryAdapter(facade=fac, experience_store=MagicMock())
        res = ad.retrieve_related_tasks("số liệu")
        assert len(res.hits) == 1 and "nhiệm vụ" in res.hits[0].content.lower()


# ---------- §6.4 candidate ----------
class TestCreateMemoryCandidate:
    def test_worthy_content_goes_to_quarantine(self):
        fac = make_facade()
        qs = MagicMock()
        qs.add_knowledge.return_value = "q-abc"
        ad = CherryMemoryAdapter(facade=fac, experience_store=MagicMock(),
                                 quarantine_store=qs)
        res = ad.create_memory_candidate(
            "Phòng AI chốt hạn nộp báo cáo tuần trước 25/11",
            source_email_id="10233", thread_key="luồng-bc")
        assert res.created is True
        assert res.layer == "quarantine"
        assert res.id == "q-abc"
        assert res.fact_level == "QUARANTINED"
        assert res.reason and "promote" in res.reason
        qs.add_knowledge.assert_called_once()
        call = qs.add_knowledge.call_args
        all_args = list(call.args) + list(call.kwargs.values())
        assert any("email:10233" in str(a) for a in all_args)  # source_ref
        assert call.kwargs["metadata"]["thread_key"] == "luồng-bc"

    def test_no_quarantine_store_fail_honest(self):
        """§6.4 bất biến: không có quarantine → TỪ CHỐI ghi (không tự xác minh)."""
        fac = make_facade()
        ad = CherryMemoryAdapter(facade=fac, experience_store=MagicMock(),
                                 quarantine_store=None, auto_create_stores=False)
        res = ad.create_memory_candidate("Chốt deadline báo cáo trước 25/11")
        assert res.created is False and "Quarantine" in res.reason
        fac.add.assert_not_called()  # tuyệt đối không fallback vào semantic

    def test_quarantine_error_fail_honest(self):
        fac = make_facade()
        qs = MagicMock()
        qs.add_knowledge.side_effect = RuntimeError("db locked")
        ad = CherryMemoryAdapter(facade=fac, experience_store=MagicMock(),
                                 quarantine_store=qs)
        res = ad.create_memory_candidate("Chốt deadline báo cáo trước 25/11")
        assert res.created is False and "RuntimeError" in res.reason
        fac.add.assert_not_called()

    def test_plain_email_text_rejected(self):
        """§6.4: KHÔNG lưu toàn bộ email — chỉ câu có giá trị dài hạn."""
        fac = make_facade()
        ad = CherryMemoryAdapter(facade=fac, experience_store=MagicMock())
        res = ad.create_memory_candidate("Chào anh, em gửi anh file báo cáo hôm nay ạ.")
        assert res.created is False
        assert "không lưu" in res.reason.lower() or "không thuộc" in res.reason.lower()
        fac.add.assert_not_called()

    def test_sensitive_content_rejected(self):
        fac = make_facade()
        ad = CherryMemoryAdapter(facade=fac, experience_store=MagicMock())
        for text in ("Mật khẩu hệ thống là abc123 xin lưu ý",
                     "Nhận khuyến mãi sốc hôm nay"):
            res = ad.create_memory_candidate(text)
            assert res.created is False and "tỪ chỐi" in res.reason.lower() or res.created is False
        fac.add.assert_not_called()

    def test_empty_and_short_rejected(self):
        fac = make_facade()
        ad = CherryMemoryAdapter(facade=fac, experience_store=MagicMock())
        assert ad.create_memory_candidate("").created is False
        assert ad.create_memory_candidate("quá ngắn").created is False
        fac.add.assert_not_called()

    def test_never_auto_promotes(self):
        """Bất biến §6.4: adapter không có đường promote tự động."""
        ad = CherryMemoryAdapter(facade=make_facade(),
                                 experience_store=MagicMock(),
                                 quarantine_store=MagicMock())
        assert not hasattr(ad, "promote") and not hasattr(ad, "auto_promote")
        assert not hasattr(ad, "approve") and not hasattr(ad, "reject")


def make_adapter(quarantine: MagicMock | None = None) -> tuple:
    """Adapter với quarantine mock (add_knowledge → id)."""
    fac = make_facade()
    qs = quarantine if quarantine is not None else MagicMock()
    if quarantine is None:
        qs.add_knowledge.return_value = "q-x"
    return CherryMemoryAdapter(facade=fac, experience_store=MagicMock(),
                               quarantine_store=qs), fac, qs


class TestExtractFromThread:
    def test_extracts_from_all_buckets_with_max(self):
        ad, fac, qs = make_adapter()
        ana = FakeAnalysis(
            decisions=["Chốt phương án A (mail #101, 20/11)"],
            commitments=["Em sẽ gửi báo cáo trước 25/11 (mail #102, 21/11)"],
            changes=["Hạn dự án lùi 1 tuần (mail #103, 22/11)"],
        )
        results = ad.extract_candidates_from_thread(ana, max_items=3)
        assert len(results) == 3
        assert all(isinstance(r, CandidateResult) for r in results)
        created = [r for r in results if r.created]
        assert created, "ít nhất câu chốt/cam kết phải đủ giá trị lưu"
        # mail #id được trích vào source_ref (args hoặc kwargs):
        refs = " ".join(str(a) for c in qs.add_knowledge.call_args_list
                        for a in list(c.args) + list(c.kwargs.values()))
        assert "email:101" in refs or "email:102" in refs

    def test_respects_max_items(self):
        ad, fac, qs = make_adapter()
        ana = FakeAnalysis(
            decisions=["Chốt A (mail #1)", "Chốt B (mail #2)", "Chốt C (mail #3)"],
            commitments=["Cam kết D (mail #4)"],
        )
        results = ad.extract_candidates_from_thread(ana, max_items=2)
        assert len(results) <= 2
        assert qs.add_knowledge.call_count <= 2

    def test_thread_without_notable_content(self):
        ad, fac, qs = make_adapter()
        results = ad.extract_candidates_from_thread(FakeAnalysis())
        assert results == []
        qs.add_knowledge.assert_not_called()


# ---------- lesson path ----------
class TestRecordFollowupExperience:
    def test_records_pending_experience(self):
        store = MagicMock()
        store.add_experience.return_value = MagicMock(id="exp-7")
        ad = CherryMemoryAdapter(facade=make_facade(), experience_store=store)
        res = ad.record_followup_experience("Gửi báo cáo tuần", "chờ kết quả",
                                            source_email_id="55")
        assert res["ok"] is True and res["id"] == "exp-7"
        kwargs = store.add_experience.call_args.kwargs
        assert "vmail" in kwargs["tags"]
        assert kwargs["outcome"].name == "UNKNOWN"  # chưa có kết quả thật — fail-honest

    def test_degraded_when_no_store(self):
        """Truyền experience_store=None tường minh + auto_create_stores=False
        → degraded path (lesson không khả dụng, retrieval vẫn chạy)."""
        ad = CherryMemoryAdapter(facade=make_facade(), experience_store=None,
                                 auto_create_stores=False)
        assert ad.experience_store is None
        res = ad.record_followup_experience("Gửi báo cáo tuần", "chờ kết quả")
        assert res["ok"] is False and "ExperienceStore" in res["reason"]

    def test_degraded_on_store_error(self):
        store = MagicMock()
        store.add_experience.side_effect = RuntimeError("db locked")
        ad = CherryMemoryAdapter(facade=make_facade(), experience_store=store)
        res = ad.record_followup_experience("Gửi báo cáo tuần", "chờ kết quả")
        assert res["ok"] is False and "RuntimeError" in res["reason"]


# ---------- singleton ----------
class TestGetAdapter:
    def test_get_adapter_returns_instance(self):
        from quan_ai_brain.office import memory_adapter as ma
        old = ma._default_adapter
        try:
            sentinel = object()
            ma._default_adapter = sentinel
            assert ma.get_adapter() is sentinel
        finally:
            ma._default_adapter = old


# ---------- hit dataclass ----------
class TestRetrievalHit:
    def test_from_unified_keeps_source(self):
        h = make_hit("nội dung", "VERIFIED", 0.8, layer="semantic", source_ref="email:5")
        hit = RetrievalHit.from_unified(h)
        assert hit.verification == "VERIFIED"
        assert hit.source_ref == "email:5"
        assert hit.tier() == 0

    def test_tier_ordering(self):
        assert RetrievalHit("a", "FACT", "VERIFIED", "semantic", 1.0).tier() == 0
        assert RetrievalHit("a", "OBSERVED", "OBSERVED", "semantic", 1.0).tier() == 1
        assert RetrievalHit("a", "INFERENCE", "INFERRED", "semantic", 1.0).tier() == 2
        assert RetrievalHit("a", "QUARANTINED", "CANDIDATE", "semantic", 1.0).tier() == 3
