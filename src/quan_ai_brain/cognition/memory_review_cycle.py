"""V9 Slice 3 — Memory Review Cycle: sàng lọc theo chu kỳ + hỏi chủ nhân (A–G).

MASTER PROMPT V9 PHẦN VII + VIII:
- 10 stage: COLLECT → NORMALIZE → CLASSIFY → LINK → COMPARE → REASON →
  VALIDATE → OWNER_REVIEW → COMMIT_OR_RETAIN → REPORT.
- Checkpoint sau mỗi stage (Test H — resume sau gián đoạn).
- Batch limit (§XII.7) — không xử lý vô hạn mỗi đợt.
- Câu hỏi A–G chỉ khi: mâu thuẫn không tự giải / RULE lặp chưa rõ chính thức /
  giả thuyết cần giả định chưa xác nhận (§VIII.1). Không hỏi lại câu OPEN.
- Không tự xoá/merge/nâng trạng thái khi chưa đủ căn cứ (PHẦN XV).
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from quan_ai_brain.cognition.logical_reasoning import LogicalReasoningEngine
from quan_ai_brain.memory.deep_memory import DeepMemoryStore, _new_id, _now

STAGES = (
    "COLLECT", "NORMALIZE", "CLASSIFY", "LINK", "COMPARE",
    "REASON", "VALIDATE", "OWNER_REVIEW", "COMMIT_OR_RETAIN", "REPORT",
)


def _now_dt() -> str:
    return datetime.now(timezone.utc).isoformat()


class MemoryReviewCycle:
    def __init__(self, store: DeepMemoryStore, batch_limit: int = 50) -> None:
        if not 1 <= int(batch_limit) <= 500:
            raise ValueError("batch_limit must be between 1 and 500")
        self._store = store
        self._engine = LogicalReasoningEngine(store)
        self._batch_limit = int(batch_limit)

    # ---------------------------------------------------------------- run

    def run(self, resume_run_id: str | None = None) -> dict[str, Any]:
        """Chạy 10 stage; mỗi stage xong đều lưu checkpoint (Test H)."""
        if resume_run_id:
            run_id = resume_run_id
            run = self._store.get_review_run(run_id)
            if run is None:
                raise ValueError(f"run not found: {run_id}")
            if run["status"] == "COMPLETED":
                return {"run_id": run_id, "already_completed": True, **run["stats"]}
            done_stages = self._stages_up_to(run["checkpoint"].get("stage", ""))
            stats = dict(run["stats"])
            stats.setdefault("stages_completed", done_stages)
        else:
            run_id = self._store.create_review_run(batch_limit=self._batch_limit)
            done_stages = []
            stats = {
                "episodes_scanned": 0, "new_units": 0, "relations_created": 0,
                "duplicates_found": 0, "contradictions": 0, "owner_questions": 0,
                "stages_completed": [],
            }

        stage_methods = {
            "COLLECT": self._stage_collect,
            "NORMALIZE": self._stage_normalize,
            "CLASSIFY": self._stage_classify,
            "LINK": self._stage_link,
            "COMPARE": self._stage_compare,
            "REASON": self._stage_reason,
            "VALIDATE": self._stage_validate,
            "OWNER_REVIEW": self._stage_owner_review,
            "COMMIT_OR_RETAIN": self._stage_commit,
            "REPORT": self._stage_report,
        }

        try:
            for stage in STAGES:
                if stage in done_stages:
                    continue
                stats.update(stage_methods[stage](stats))
                stats["stages_completed"].append(stage)
                self._store.update_run_checkpoint(
                    run_id, stage, stage, list(stats.get("processed_ids", []))
                )
            self._store.finish_review_run(run_id, "COMPLETED", stats)
        except Exception as exc:  # checkpoint giữ nguyên — resume được (Test H)
            self._store.finish_review_run(run_id, "FAILED", {**stats, "error": str(exc)})
            raise
        return {"run_id": run_id, "status": "COMPLETED", **stats}

    def _stages_up_to(self, stage: str) -> list[str]:
        if stage not in STAGES:
            return []
        return list(STAGES[: STAGES.index(stage) + 1])

    # ---------------------------------------------------------------- stages

    def _stage_collect(self, stats: dict[str, Any]) -> dict[str, Any]:
        """Bước 1: chat_turn CHƯA extract (idempotency qua exchange log)."""
        pending = 0
        for episode in self._store.iter_chat_turns(batch_size=100):
            if pending >= self._batch_limit:
                break
            correlation = f"v9s1:extract:{episode['id']}"
            if not self._store.has_exchange(correlation):
                pending += 1
        return {"collect_pending": pending}

    def _stage_normalize(self, stats: dict[str, Any]) -> dict[str, Any]:
        # Chuẩn hóa định dạng đã thực hiện trong extractor (id, ISO time);
        # stage này xác nhận + ghi nhận số units hiện có.
        return {"normalized_units": self._store.deep_stats()["knowledge_units_total"]}

    def _stage_classify(self, stats: dict[str, Any]) -> dict[str, Any]:
        # Phân loại theo trạng thái — dữ liệu cho REPORT.
        s = self._store.deep_stats()
        return {"classified": s["units_by_status"]}

    def _stage_link(self, stats: dict[str, Any]) -> dict[str, Any]:
        link = self._store.link_units(batch=self._batch_limit * 4)
        return {"relations_created": link["relations_created"],
                "by_relation_type": link["by_type"]}

    def _stage_compare(self, stats: dict[str, Any]) -> dict[str, Any]:
        cmp_stats = self._store.compare_duplicates(batch=self._batch_limit * 4)
        return {"duplicates_found": cmp_stats["duplicates_found"]}

    def _stage_reason(self, stats: dict[str, Any]) -> dict[str, Any]:
        """Bước 6: đề xuất quan hệ suy luận từ mâu thuẫn hiện có (không tự commit)."""
        s = self._store.deep_stats()
        return {"contradictions": s["relations_by_type"].get("CONTRADICTS", 0)}

    def _stage_validate(self, stats: dict[str, Any]) -> dict[str, Any]:
        """Bước 7: kiểm tra bằng chứng — đếm units thiếu evidence/source."""
        with self._store._lock:
            row = self._store._connection.execute(
                """
                SELECT COUNT(*) AS n FROM knowledge_units
                WHERE evidence_refs_json = '[]' OR source_refs_json = '[]'
                """
            ).fetchone()
        return {"units_missing_evidence": row["n"]}

    def _stage_owner_review(self, stats: dict[str, Any]) -> dict[str, Any]:
        """Bước 8: sinh câu hỏi A–G — chỉ khi có căn cứ (§VIII.1)."""
        created = self._generate_owner_questions()
        return {"owner_questions": created}

    def _stage_commit(self, stats: dict[str, Any]) -> dict[str, Any]:
        """Bước 9: KHÔNG tự nâng trạng thái (PHẦN XV) — chỉ ghi nhận quyết định giữ nguyên."""
        s = self._store.deep_stats()
        return {"retained_as_is": s["knowledge_units_total"], "auto_promoted": 0}

    def _stage_report(self, stats: dict[str, Any]) -> dict[str, Any]:
        # Bước 10: REPORT = stats_json của run (finish_review_run ghi).
        return {"report_generated_at": _now_dt()}

    # ---------------------------------------------------------------- owner questions §VIII

    def _generate_owner_questions(self) -> int:
        created = 0
        created += self._questions_from_contradictions()
        created += self._questions_from_repeated_rules()
        return created

    def _questions_from_contradictions(self) -> int:
        """Mâu thuẫn không tự giải → NEEDS_OWNER_REVIEW + câu hỏi A–G."""
        with self._store._lock:
            rows = self._store._connection.execute(
                """
                SELECT from_id, to_id, basis FROM knowledge_relations
                WHERE relation_type='CONTRADICTS'
                """
            ).fetchall()
        n = 0
        for row in rows:
            a = self._store.get_unit(row["from_id"])
            b = self._store.get_unit(row["to_id"])
            if a is None or b is None:
                continue
            if self._question_exists_for_pair(a["knowledge_id"], b["knowledge_id"]):
                continue
            analysis = self._engine.analyze_contradiction(a["knowledge_id"], b["knowledge_id"])
            same_scope = analysis.get("same_scope", True)
            if not same_scope:
                # CONTEXT_DIFFERENCE — hệ thống tự xử lý được: giữ cả hai + phạm vi
                continue
            evidence = f"{a['knowledge_id']}: \"{a['statement'][:80]}\" | " \
                       f"{b['knowledge_id']}: \"{b['statement'][:80]}\" | quan hệ: {row['basis'][:60]}"
            question = (
                f"Hai thông tin sau mâu thuẫn nhau: (1) \"{a['statement'][:90]}\" và "
                f"(2) \"{b['statement'][:90]}\". Anh xác nhận giúp em: thông tin nào đúng "
                f"trong phạm vi hiện tại, hay mỗi thông tin đúng trong một điều kiện khác nhau?"
            )
            self._store.create_owner_question(
                problem=f"Hai tri thức cùng phạm vi '{a['scope']}' khẳng định trái ngược nhau.",
                evidence=evidence,
                current_view=f"Đang giữ cả hai ở trạng thái CONFLICTED (confidence đã hạ).",
                interpretations_json=json.dumps([
                    {"option": 1, "view": a["statement"][:90], "implication": "bản ghi (2) đánh dấu REJECTED sau xác nhận"},
                    {"option": 2, "view": b["statement"][:90], "implication": "bản ghi (1) đánh dấu REJECTED sau xác nhận"},
                    {"option": 3, "view": "mỗi thông tin đúng trong một điều kiện khác nhau",
                     "implication": "giữ cả hai + ghi phạm vi áp dụng cụ thể"},
                ], ensure_ascii=False),
                question=question,
                impact="Câu trả lời quyết định tri thức nào dùng cho suy luận sau này; sai sẽ lan vào mọi kết luận dựa trên nó.",
                scope_hint=f"scope '{a['scope']}' — trả lời 'tổng quát' nếu áp dụng mọi phạm vi",
            )
            self._store.mark_units_conflicted(a["knowledge_id"], b["knowledge_id"])
            n += 1
            if n >= self._batch_limit:
                break
        return n

    def _questions_from_repeated_rules(self) -> int:
        """RULE lặp lại nhiều lần nhưng chưa rõ chính thức (§VIII.1 cuối)."""
        with self._store._lock:
            rows = self._store._connection.execute(
                """
                SELECT subject, predicate, COUNT(*) AS n, MIN(statement) AS sample,
                       GROUP_CONCAT(scope) AS scopes
                FROM knowledge_units
                WHERE knowledge_type='RULE' AND status IN ('EXTRACTED','CANDIDATE')
                GROUP BY subject, predicate HAVING n >= 3
                """
            ).fetchall()
        n = 0
        for row in rows:
            qkey = f"rule:{row['subject'][:40]}:{row['predicate']}"
            if self._question_exists_for_key(qkey):
                continue
            self._store.create_owner_question(
                problem=f"Quy tắc \"{row['sample'][:80]}\" xuất hiện {row['n']} lần nhưng chưa rõ là quy tắc chính thức hay thói quen hội thoại.",
                evidence=f"{row['n']} KU loại RULE cùng subject/predicate trong scopes: {row['scopes'][:120]}",
                current_view="Đang giữ ở trạng thái EXTRACTED — chưa dùng như quy tắc bắt buộc.",
                interpretations_json=json.dumps([
                    {"option": 1, "view": "quy tắc chính thức", "implication": "nâng thành RULE có scope tổng quát"},
                    {"option": 2, "view": "chỉ là thói quen diễn đạt", "implication": "giữ EXTRACTED, không áp như quy tắc"},
                ], ensure_ascii=False),
                question=f"Quy tắc \"{row['sample'][:90]}\" lặp lại {row['n']} lần — anh xác nhận đây là quy tắc chính thức cần tuân thủ, hay chỉ là cách nói?",
                impact="Nếu là quy tắc chính thức, hệ thống sẽ ưu tiên áp khi suy luận; nếu không, không tự động áp.",
                scope_hint="trả lời kèm phạm vi nếu chỉ áp dụng cho một dự án/hệ thống cụ thể",
                question_key=qkey,
            )
            n += 1
            if n >= self._batch_limit:
                break
        return n

    def _question_exists_for_pair(self, id_a: str, id_b: str) -> bool:
        with self._store._lock:
            row = self._store._connection.execute(
                """
                SELECT COUNT(*) FROM owner_questions
                WHERE status='OPEN' AND evidence LIKE ? AND evidence LIKE ?
                """,
                (f"%{id_a}%", f"%{id_b}%"),
            ).fetchone()
        return row[0] > 0

    def _question_exists_for_key(self, key: str) -> bool:
        with self._store._lock:
            row = self._store._connection.execute(
                "SELECT COUNT(*) FROM owner_questions WHERE status='OPEN' AND question_id=?",
                (key,),
            ).fetchone()
        return row[0] > 0
