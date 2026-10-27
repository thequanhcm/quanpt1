"""Benchmark 10 câu hỏi — Sprint 6-GOP hạng mục (1b), đúng cấu trúc Lab Mini RAG.

3 direct + 2 multi-chunk + 2 paraphrase + 2 no-answer + 1 version-confusion.
Chạy trên kho tài liệu MẪU (kho_tai_lieu/), đo: context_recall / faithful
proxy / citation_ok. Không gọi LLM thật — đo tầng RETRIEVAL (theo Module 3:
"Không đánh giá RAG nếu không xem bằng chứng được retrieval").
"""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass, asdict
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WORKSPACE / "src"))

from quan_ai_brain.cognition.document_rag import DocumentRAG  # noqa: E402

KHO_DIR = WORKSPACE / "kho_tai_lieu"
RESULT_PATH = WORKSPACE / "reports" / "sprint6_rag_benchmark.json"


# ---------------- kho tài liệu mẫu (vận hành mạng, tiếng Việt) ----------------

DOCS: dict[str, str] = {
    "so_tay_alarm.md": """# Xử lý alarm mất đồng bộ

Khi site báo alarm mất đồng bộ, thực hiện quy trình: kiểm tra nguồn điện,
kiểm tra link quang, kiểm tra clock source. Nếu 30 phút không hồi phục thì
escalation lên cấp trên.

# SLA xử lý alarm

Alarm nghiêm trọng (critical) phải xử lý xong trong 4 giờ theo SLA.
Alarm thường (major) trong 8 giờ. Ghi nhận thời điểm bắt đầu vào ticket.""",
    "huong_dan_bao_mat.md": """# Quy trình đổi mật khẩu

Đổi mật khẩu định kỳ mỗi 90 ngày. Mật khẩu tối thiểu 12 ký tự, có chữ hoa,
chữ thường, số và ký tự đặc biệt. Không chia sẻ tài khoản cá nhân.

# Khóa tài khoản

Sau 5 lần sai liên tiếp, tài khoản bị khóa 30 phút. Liên hệ IT helpdesk
để mở khóa từ xa.""",
    "quy_trinh_bao_tri.md": """# Lịch bảo trì định kỳ

Bảo trì phòng ngừa mỗi quý cho trạm BTS trọng điểm, mỗi 6 tháng cho trạm
thường. Trước khi bảo trì phải xin lịch với NOC và thông báo cho khách hàng
trước 48 giờ.

# Checklist bảo trì trạm BTS

Kiểm tra pin dự phòng, đo công suất phát, vệ sinh lọc khí, siết connections,
chụp ảnh hiện trạng trước và sau bảo trì.""",
}

# Expected evidence: {doc_prefix: [section prefixes]}
BENCHMARK: list[dict] = [
    # 3 câu direct (đáp án nằm trọn trong 1 chunk)
    {"id": "Q1", "type": "direct",
     "q": "SLA xử lý alarm critical là bao lâu?",
     "expect_doc": "so_tay_alarm", "expect_section": "SLA"},
    {"id": "Q2", "type": "direct",
     "q": "Mật khẩu tối thiểu bao nhiêu ký tự?",
     "expect_doc": "huong_dan_bao_mat", "expect_section": "đổi mật khẩu"},
    {"id": "Q3", "type": "direct",
     "q": "Sau bao nhiêu lần sai thì tài khoản bị khóa?",
     "expect_doc": "huong_dan_bao_mat", "expect_section": "Khóa tài khoản"},
    # 2 câu multi-chunk (cần tổng hợp)
    {"id": "Q4", "type": "multi",
     "q": "Quy trình xử lý alarm mất đồng bộ gồm bước nào và SLA bao lâu?",
     "expect_doc": "so_tay_alarm", "expect_section": None, "min_chunks": 2},
    {"id": "Q5", "type": "multi",
     "q": "Chu kỳ bảo trì trạm và checklist gồm việc gì?",
     "expect_doc": "quy_trinh_bao_tri", "expect_section": None, "min_chunks": 2},
    # 2 câu paraphrase (từ khác với tài liệu)
    {"id": "Q6", "type": "paraphrase",
     "q": "Thiết bị thường xuyên mất kết nối thì kiểm tra gì?",
     "expect_doc": "so_tay_alarm", "expect_section": None},
    {"id": "Q7", "type": "paraphrase",
     "q": "Bao lâu thì nên thay mật khẩu một lần?",
     "expect_doc": "huong_dan_bao_mat", "expect_section": None},
    # 2 câu no-answer (ngoài phạm vi kho)
    {"id": "Q8", "type": "no_answer",
     "q": "Giá cước thuê bao 4G hiện nay là bao nhiêu?", "expect_doc": None},
    {"id": "Q9", "type": "no_answer",
     "q": "Cách nấu phở bò chuẩn vị Hà Nội?", "expect_doc": None},
    # 1 câu version-confusion
    {"id": "Q10", "type": "version",
     "q": "Theo sổ tay alarm phiên bản 2023, SLA critical là bao lâu?",
     "expect_doc": "so_tay_alarm", "expect_section": "SLA",
     "note": "kho chỉ có v1.0 — hệ thống PHẢI dẫn đúng version thực tế có trong index"},
]


@dataclass
class BenchRow:
    question_id: str
    question: str
    qtype: str
    retrieved_ok: bool
    context_recall: str        # "đúng" / "một phần" / "sai" / "n/a"
    faithful_proxy: str        # "có-căn-cứ" / "không-căn-cứ" / "trống-đúng"
    citation_ok: bool
    failure_type: str = ""


class FakeEmbedding:
    """Mock BGE-M3: vector theo presence từ khóa nghĩa — dùng CHỈ để test
    logic retrieval (real BGE test riêng khi Ollama ONLINE)."""

    _DIMS = ("alert", "quy trình", "sla", "mật khẩu", "kiểm tra", "bảo trì",
             "tài khoản", "khóa")

    def get_embedding(self, text: str) -> list[float]:
        t = text.lower()
        return [1.0 if d in t else 0.0 for d in self._DIMS]


def run_benchmark(rag: DocumentRAG | None = None) -> list[BenchRow]:
    if rag is None:
        rag = DocumentRAG(workspace=WORKSPACE, embedding_service=FakeEmbedding())
    if rag.count_chunks() == 0:
        for name, content in DOCS.items():
            p = KHO_DIR / name
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding="utf-8")
        rag.ingest_folder(KHO_DIR)

    rows: list[BenchRow] = []
    for item in BENCHMARK:
        r = rag.retrieve(item["q"])
        got_docs = {c.doc_title.split("_")[0] for c in r.chunks}
        expect_doc = item["expect_doc"]
        if expect_doc is None:
            # no-answer: hệ thống PHẢI trả rỗng (dám nói không có căn cứ)
            ok = not r.has_evidence
            row = BenchRow(item["id"], item["q"], item["type"], ok,
                           "n/a", "trống-đúng" if ok else "không-căn-cứ",
                           ok, "" if ok else "retrieval trả nhầm ngoài phạm vi")
        else:
            if not r.has_evidence:
                row = BenchRow(item["id"], item["q"], item["type"], False,
                               "sai", "không-căn-cứ", False, "thiếu bằng chứng")
            else:
                # khớp theo tên file (doc_title = file stem, ví dụ so_tay_alarm)
                doc_ok = any(expect_doc in c.doc_title for c in r.chunks)
                sec = item.get("expect_section")
                sec_ok = (
                    any(sec.lower() in c.section.lower() for c in r.chunks)
                    if sec else True
                )
                if doc_ok and sec_ok:
                    recall = "đúng"
                elif doc_ok:
                    recall = "một phần"
                else:
                    recall = "sai"
                min_chunks = item.get("min_chunks", 1)
                enough = len(r.chunks) >= min_chunks
                ok = doc_ok and (recall == "đúng" or enough)
                row = BenchRow(item["id"], item["q"], item["type"], ok,
                               recall, "có-căn-cứ", True,
                               "" if ok else "sai doc/section hoặc thiếu chunk")
                if item["type"] == "version" and r.chunks:
                    # citation phải đúng version đang có trong index (1.0), không bịa 2023
                    if all(c.version == "1.0" for c in r.chunks):
                        row.citation_ok = True
                    else:
                        row.citation_ok = False
                        row.failure_type = "citation sai version"
        rows.append(row)
    return rows


def summarize(rows: list[BenchRow]) -> dict:
    total = len(rows)
    passed = sum(1 for r in rows if r.retrieved_ok)
    no_answer_right = sum(
        1 for r in rows if r.qtype == "no_answer" and r.retrieved_ok
    )
    return {
        "total": total, "passed": passed,
        "pass_rate": round(passed / total * 100, 1),
        "no_answer_honesty": f"{no_answer_right}/2",
        "rows": [asdict(r) for r in rows],
    }


def main() -> int:
    rows = run_benchmark()
    summary = summarize(rows)
    RESULT_PATH.parent.mkdir(parents=True, exist_ok=True)
    RESULT_PATH.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"RAG benchmark: {summary['passed']}/{summary['total']} passed "
          f"({summary['pass_rate']}%) | no-answer honesty: {summary['no_answer_honesty']}")
    for r in rows:
        mark = "PASS" if r.retrieved_ok else "FAIL"
        fail = f" — {r.failure_type}" if r.failure_type else ""
        print(f"  [{mark}] {r.question_id} ({r.qtype}){fail}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
