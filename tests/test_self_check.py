# -*- coding: utf-8 -*-
"""Test TASK-MEMORY-TRUTH-M6 — self_check lite + memory eval harness.

Mock LLM 100% (không mạng). Fail-honest: assert hành vi fail-open.
"""
from __future__ import annotations

import csv
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from unittest.mock import patch as mock_patch

import pytest

BRAIN = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BRAIN / "src"))

from quan_ai_brain.cognition.self_check import (  # noqa: E402
    REFUSAL_TEXT,
    apply_removal_only_repair,
    parse_verdict,
    self_check_reply,
)
from quan_ai_brain.llm.models import LLMResponse  # noqa: E402


@dataclass
class MockProvider:
    """Provider giả: trả theo thứ tự hàng đợi text."""
    texts: list[str] = field(default_factory=list)
    calls: list[LLMResponse] = field(default_factory=list)
    raise_on_call: int | None = None
    n: int = 0

    def generate(self, request: Any) -> LLMResponse:
        self.n += 1
        if self.raise_on_call is not None and self.n == self.raise_on_call:
            raise TimeoutError("mock timeout")
        text = self.texts[self.n - 1] if self.n <= len(self.texts) else ""
        return LLMResponse(text=text, model="mock", provider="mock")


EVIDENCE = (
    "[TRÍ NHỚ] Anh dạy: trả lời ngắn gọn, trung thực là điều quan trọng nhất.\n"
    "[TRÍ NHỚ] Pi 5 là Raspberry Pi 5, chạy kiosk avatar trên TONY."
)


# ------------------------------------------------------------------ parse_verdict
def test_parse_verdict_valid_json():
    v = parse_verdict('{"du_can_cu": false, "y_khong_co_can_cu": ["ý bịa 1"]}')
    assert v == {"du_can_cu": False, "y_khong_co_can_cu": ["ý bịa 1"]}


def test_parse_verdict_wrapped_in_prose():
    v = parse_verdict('Kết quả: {"du_can_cu": true, "y_khong_co_can_cu": []} — xong.')
    assert v is not None and v["du_can_cu"] is True


def test_parse_verdict_garbage_returns_none():
    assert parse_verdict("tôi không hiểu") is None
    assert parse_verdict("") is None


# -------------------------------------------------- apply_removal_only_repair
def test_repair_refuses_longer_answer():
    """Revised dài hơn đáng kể → từ chối (chặn thêm ý mới)."""
    out = apply_removal_only_repair("câu ngắn", "câu ngắn" + " X" * 100)
    assert out == REFUSAL_TEXT


def test_repair_accepts_shorter_revision():
    out = apply_removal_only_repair("Ý đúng. Ý bịa lắm.", "Ý đúng.")
    assert out == "Ý đúng."


def test_repair_empty_revision_refusal():
    assert apply_removal_only_repair("gốc", "  ") == REFUSAL_TEXT


# ------------------------------------------------------------- self_check_reply
def test_ok_answer_untouched():
    """Mọi ý có căn cứ → giữ nguyên, không gọi repair."""
    p = MockProvider(texts=[json.dumps({"du_can_cu": True, "y_khong_co_can_cu": []}, ensure_ascii=False)])
    r = self_check_reply("anh dạy em điều gì quan trọng?", "Trả lời ngắn gọn, trung thực.", EVIDENCE, p, "mock")
    assert r["ran"] is True and r["revised"] is False
    assert r["revised_text"] == "Trả lời ngắn gọn, trung thực."
    assert p.n == 1  # chỉ grader, không repair


def test_ungrounded_claim_gets_removed():
    """Có ý không căn cứ → repair chỉ xóa ý đó."""
    answer = "Anh dạy em trả lời ngắn gọn. Ngoài ra Pi 5 có GPU 800 giờ."
    p = MockProvider(texts=[
        json.dumps({"du_can_cu": False, "y_khong_co_can_cu": ["Pi 5 có GPU 800 giờ"]}, ensure_ascii=False),
        "Anh dạy em trả lời ngắn gọn.",
    ])
    r = self_check_reply("anh dạy em điều gì?", answer, EVIDENCE, p, "mock")
    assert r["ran"] and r["revised"] is True
    assert "GPU 800" not in r["revised_text"]
    assert "ngắn gọn" in r["revised_text"]
    assert p.n == 2  # grader + repair


def test_grader_error_fail_open_keeps_original():
    """LLM grader nổ → fail-open giữ câu gốc, không raise."""
    p = MockProvider(raise_on_call=1)
    original = "câu trả lời gốc"
    r = self_check_reply("q?", original, EVIDENCE, p, "mock")
    assert r["ran"] is True
    assert r["error"] is not None
    assert r["revised_text"] == original


def test_grader_unparseable_fail_open():
    p = MockProvider(texts=["xin lỗi tôi không trả lời được"])
    original = "câu gốc"
    r = self_check_reply("q?", original, EVIDENCE, p, "mock")
    assert r["error"] == "grader_unparseable"
    assert r["revised_text"] == original


def test_greeting_query_bypasses():
    """Câu xã giao/điều khiển KHÔNG qua chấm (không đắt thời gian)."""
    p = MockProvider(texts=["KHÔNG ĐƯỢC GỌI"])
    r = self_check_reply("chào em", "Chào anh!", EVIDENCE, p, "mock")
    assert r["ran"] is False and r["verdict"] == "bypass"
    assert p.n == 0


def test_no_evidence_skips():
    p = MockProvider(texts=["KHÔNG ĐƯỢC GỌI"])
    r = self_check_reply("câu hỏi thường", "trả lời", "", p, "mock")
    assert r["ran"] is False and r["verdict"] == "no_evidence"
    assert p.n == 0


def test_refusal_when_repair_returns_marker():
    """Repair trả marker EM_KHONG_CO_CAN_CU → refusal trung thực."""
    p = MockProvider(texts=[
        json.dumps({"du_can_cu": False, "y_khong_co_can_cu": ["ý bịa"]}, ensure_ascii=False),
        "EM_KHONG_CO_CAN_CU",
    ])
    r = self_check_reply("q?", "câu có ý bịa", EVIDENCE, p, "mock")
    assert r["revised_text"] == REFUSAL_TEXT


# ------------------------------------------------------------- memory_eval
def test_memory_eval_with_mock_csv(tmp_path: Path) -> None:
    """Eval harness chạy với CSV giả: tính đúng recall@k."""
    # CSV eval giả — semantic search sẽ miss (không ingest gì) nhưng harness
    # phải trả số liệu đúng cấu trúc, fail-honest (0 hit = không recalled).
    csvp = tmp_path / "q.csv"
    with open(csvp, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["query", "answer_must_contain1", "answer_must_contain2"])
        w.writerow(["kiểm tra eval giả lập", "abc", "xyz"])
    from quan_ai_brain.cognition.semantic_memory import SemanticMemoryEngine  # noqa: F401
    # module nằm ở tools/ — import theo path
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "memory_eval", str(BRAIN / "tools" / "memory_eval.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    summary = mod.eval_memory(csvp)
    assert summary["n_questions"] == 1
    assert "recall_at_3" in summary and "results" in summary
    assert isinstance(summary["results"][0]["recalled"], bool)
    # Không ingest → 0 hit → recalled False (fail-honest)
    assert summary["results"][0]["recalled"] is False


def test_memory_eval_missing_csv_error():
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "memory_eval", str(BRAIN / "tools" / "memory_eval.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    summary = mod.eval_memory(BRAIN / "data" / "khong_ton_tai.csv")
    assert summary.get("error") == "no_questions"
