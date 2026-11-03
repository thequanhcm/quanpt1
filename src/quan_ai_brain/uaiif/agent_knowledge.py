"""UAIIF-S4 (GĐ1): Universal Agent Knowledge — kho hiểu biết thế giới Agent.

Master prompt UAIIF v1.0 mục III: 7 LAYER kiến thức (fundamentals → physical AI),
20 nhóm Agent (mục I). Chu trình học mục VIII:
DISCOVER → STUDY → UNDERSTAND → TEST → VERIFY → REMEMBER → APPLY → REVIEW.

NGUYÊN TẮC NHẬN THỨC LUẬN (master prompt mục VI):
- Mỗi kiến thức có trạng thái: VERIFIED (có bằng chứng/test) / OBSERVED (đã
  quan sát thật) / INFERRED (suy luận từ tài liệu) / UNKNOWN (chưa biết).
- KHÔNG đánh đồng đọc tài liệu với thành thạo (mục VIII): trạng thái VERIFIED
  PHẢI kèm evidence_ref; INFERRED không được dùng khi ra quyết định can thiệp.
- Scorecard (mục IX): điểm gắn bằng chứng — không tự cho điểm cảm tính.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

# Trạng thái nhận thức luận
VERIFIED = "VERIFIED"      # có bằng chứng kiểm thử thật
OBSERVED = "OBSERVED"      # đã quan sát trên hệ thống thật
INFERRED = "INFERRED"      # suy luận từ tài liệu — CHƯA kiểm chứng
UNKNOWN = "UNKNOWN"        # chưa biết
EPISTEMIC_STATUSES = (VERIFIED, OBSERVED, INFERRED, UNKNOWN)

# 7 LAYER kiến thức (master prompt mục III)
LAYERS = (
    "L01_FUNDAMENTALS",
    "L02_ARCHITECTURE",
    "L03_COMMUNICATION",
    "L04_MEMORY_LEARNING",
    "L05_SECURITY",
    "L06_MULTI_AGENT",
    "L07_PHYSICAL_EMBODIED",
)

# 20 nhóm Agent (master prompt mục I)
AGENT_KINDS = (
    "architectural", "multi_agent", "autonomous", "cognitive", "planning",
    "reasoning", "tool_calling", "coding", "security", "robotics",
    "physical_ai", "edge_ai", "distributed", "swarm", "orchestration",
    "a2a_communication", "memory", "identity_permission", "runtime_execution",
    "security_governance",
)

VN_TZ = timezone(timedelta(hours=7))


def _now() -> str:
    return datetime.now(VN_TZ).isoformat()


def _clamp(v: int) -> int:
    return max(0, min(100, int(v)))


class UniversalAgentKnowledge:
    """Kho kiến thức Agent — SQLite data/uaiif_knowledge.db. Fail-honest."""

    def __init__(self, db_path: str | Any) -> None:
        self.db_path = str(db_path)
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS knowledge_items (
                    item_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    topic TEXT NOT NULL,
                    layer TEXT NOT NULL,
                    agent_kind TEXT NOT NULL,
                    content TEXT NOT NULL,
                    epistemic_status TEXT NOT NULL,
                    evidence_ref TEXT NOT NULL DEFAULT '',
                    source TEXT NOT NULL DEFAULT '',
                    learned_at TEXT NOT NULL,
                    reviewed_at TEXT NOT NULL DEFAULT '',
                    cycle TEXT NOT NULL DEFAULT ''     -- DISCOVER/STUDY/...
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_knowledge_topic ON knowledge_items(topic)"
            )

    # ------------------------------------------------------------------
    def learn(self, topic: str, layer: str, agent_kind: str, content: str, *,
              status: str = INFERRED, evidence_ref: str = "",
              source: str = "", cycle: str = "STUDY") -> int:
        """Ghi kiến thức mới. VERIFIED bắt buộc có evidence_ref (mục VIII)."""
        if not topic or not content:
            raise ValueError("topic + content bắt buộc")
        if layer not in LAYERS:
            raise ValueError(f"layer phải thuộc 7 LAYER: {layer}")
        if agent_kind not in AGENT_KINDS:
            raise ValueError(f"agent_kind phải thuộc 20 nhóm: {agent_kind}")
        if status not in EPISTEMIC_STATUSES:
            raise ValueError(f"trạng thái nhận thức luận sai: {status}")
        if status == VERIFIED and not evidence_ref:
            raise ValueError(
                "VERIFIED bắt buộc evidence_ref — đọc tài liệu không phải thành thạo")
        with self._connect() as conn:
            cur = conn.execute(
                "INSERT INTO knowledge_items (topic, layer, agent_kind, content,"
                " epistemic_status, evidence_ref, source, learned_at, cycle)"
                " VALUES (?,?,?,?,?,?,?,?,?)",
                (topic, layer, agent_kind, content, status, evidence_ref,
                 source, _now(), cycle))
            return int(cur.lastrowid)

    def promote(self, item_id: int, to_status: str, *,
                evidence_ref: str = "") -> None:
        """Nâng trạng thái (sau test/thực nghiệm). VERIFIED cần evidence_ref."""
        if to_status not in EPISTEMIC_STATUSES:
            raise ValueError(f"trạng thái sai: {to_status}")
        if to_status == VERIFIED and not evidence_ref:
            raise ValueError("VERIFIED bắt buộc evidence_ref")
        with self._connect() as conn:
            conn.execute(
                "UPDATE knowledge_items SET epistemic_status=?, evidence_ref=?,"
                " reviewed_at=? WHERE item_id=?",
                (to_status, evidence_ref, _now(), item_id))

    def query(self, *, layer: str | None = None, agent_kind: str | None = None,
              status: str | None = None, min_confidence: str | None = None) -> list[dict[str, Any]]:
        """Tra kho kiến thức. min_confidence: chỉ lấy >= mức (VERIFIED cao nhất)."""
        sql = "SELECT * FROM knowledge_items WHERE 1=1"
        params: list[Any] = []
        if layer:
            sql += " AND layer=?"
            params.append(layer)
        if agent_kind:
            sql += " AND agent_kind=?"
            params.append(agent_kind)
        if status:
            sql += " AND epistemic_status=?"
            params.append(status)
        rows = [dict(r) for r in self._connect().execute(sql, params).fetchall()]
        if min_confidence:
            order = {UNKNOWN: 0, INFERRED: 1, OBSERVED: 2, VERIFIED: 3}
            floor = order.get(min_confidence, 0)
            rows = [r for r in rows if order.get(r["epistemic_status"], 0) >= floor]
        return rows

    def stats(self) -> dict[str, Any]:
        with self._connect() as conn:
            total = conn.execute("SELECT COUNT(*) c FROM knowledge_items").fetchone()["c"]
            by_status = {s: 0 for s in EPISTEMIC_STATUSES}
            for r in conn.execute(
                    "SELECT epistemic_status s, COUNT(*) c FROM knowledge_items"
                    " GROUP BY epistemic_status"):
                by_status[r["s"]] = r["c"]
            by_layer = {l: 0 for l in LAYERS}
            for r in conn.execute(
                    "SELECT layer l, COUNT(*) c FROM knowledge_items GROUP BY layer"):
                by_layer[r["l"]] = r["c"]
        return {"total": total, "by_status": by_status, "by_layer": by_layer}

    # ------------------------------------------------------------------
    # Agent Intelligence Scorecard (master prompt mục IX) — điểm GẮN BẰNG CHỨNG
    # ------------------------------------------------------------------
    SCORECARD_QUESTIONS = (
        "hiểu bao nhiêu loại Agent",
        "hiểu kiến trúc bên trong",
        "phân biệt thật/suy luận",
        "kết nối và giao tiếp với Agent",
        "xác định quyền hạn của Agent",
        "phát hiện hành vi bất thường",
        "can thiệp an toàn",
        "xác minh kết quả can thiệp",
    )
    # Trọng số: mỗi câu hỏi lấy bằng chứng từ nguồn dữ liệu khác nhau
    _SOURCES = (
        ("kinds", 20),        # số nhóm agent có kiến thức >= INFERRED
        ("layers", 20),       # số layer có kiến thức >= INFERRED
        ("epistemic", 12),    # tỷ lệ kiến thức phân biệt thật/suy luận rõ ràng
        ("federation", 12),   # khả năng kết nối: số nút đã đăng ký/probe
        ("profiles", 12),     # hồ sơ agent có permission_scope xác định
        ("sentinel", 12),     # phát hiện bất thường: test SENTINEL pass
        ("containment", 6),   # can thiệp an toàn: containment gates có test
        ("evidence", 6),      # xác minh kết quả: evidence store có bản ghi
    )

    def scorecard(self, *, sentinel_stats: dict[str, Any] | None = None,
                  federation_nodes: int = 0,
                  profiles_with_scope: int = 0,
                  containment_tests_pass: bool = False,
                  evidence_count: int = 0) -> dict[str, Any]:
        """Điểm 0-100 từ 8 câu hỏi — mỗi điểm có bằng chứng đi kèm."""
        st = self.stats()
        order = {UNKNOWN: 0, INFERRED: 1, OBSERVED: 2, VERIFIED: 3}
        kinds_ok = len({r["agent_kind"] for r in self.query()
                        if order.get(r["epistemic_status"], 0) >= 1})
        layers_ok = len({r["layer"] for r in self.query()
                         if order.get(r["epistemic_status"], 0) >= 1})
        total = st["total"] or 1
        epistemic_ratio = (st["by_status"].get(VERIFIED, 0) +
                           st["by_status"].get(OBSERVED, 0)) / total

        raw = {
            "kinds": min(1.0, kinds_ok / len(AGENT_KINDS)),
            "layers": min(1.0, layers_ok / len(LAYERS)),
            "epistemic": epistemic_ratio,
            "federation": min(1.0, federation_nodes / 3),   # chuẩn: ≥3 nút = đủ
            "profiles": min(1.0, profiles_with_scope / 3),
            "sentinel": 1.0 if (sentinel_stats or {}).get("tests_pass") else 0.0,
            "containment": 1.0 if containment_tests_pass else 0.0,
            "evidence": min(1.0, evidence_count / 10),
        }
        questions: list[dict[str, Any]] = []
        total_score = 0.0
        for (key, weight), q in zip(self._SOURCES, self.SCORECARD_QUESTIONS):
            s = round(raw.get(key, 0.0) * weight)
            total_score += s
            questions.append({
                "question": q, "score": s, "max": weight,
                "evidence": self._evidence_for(
                    key, st, kinds_ok, layers_ok, federation_nodes,
                    profiles_with_scope, sentinel_stats, containment_tests_pass,
                    evidence_count),
            })
        return {"total": round(total_score), "questions": questions}

    @staticmethod
    def _evidence_for(key: str, st: dict[str, Any], kinds_ok: int, layers_ok: int,
                      federation_nodes: int, profiles_with_scope: int,
                      sentinel_stats: dict[str, Any] | None,
                      containment_tests_pass: bool, evidence_count: int) -> str:
        if key == "kinds":
            return f"{kinds_ok}/20 nhóm agent có kiến thức >= INFERRED"
        if key == "layers":
            return f"{layers_ok}/7 layer có kiến thức >= INFERRED"
        if key == "epistemic":
            return (f"{st['by_status'].get(VERIFIED, 0)} VERIFIED + "
                    f"{st['by_status'].get(OBSERVED, 0)} OBSERVED / {st['total']} mục")
        if key == "federation":
            return f"{federation_nodes} nút liên bang đã đăng ký (SEC-S2 NodeRegistry)"
        if key == "profiles":
            return f"{profiles_with_scope} Universal Agent Profile có permission_scope"
        if key == "sentinel":
            return "bộ test SENTINEL-S3 PASS (khả năng phát hiện bất thường)"
        if key == "containment":
            return "containment governance 3 cấp có test PASS (can thiệp an toàn)"
        return f"{evidence_count} bản ghi bằng chứng trong EvidenceStore"
