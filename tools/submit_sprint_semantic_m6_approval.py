"""Submit approval card — SPRINT SEMANTIC MEMORY (18/11/2026).

Owner directive (desktop chat 18/11): "thực hiện: sprint kế (anh chọn)
(a) Semantic search dùng chromadb ONNX MiniLM (không cần Ollama) — triệt để
hóa 'trí nhớ ngữ nghĩa' (b) M6 bảng nghiệm thu 10 TEST — cần anh cung cấp
brief gốc hoặc duyệt tiêu chí runtime stability 24h".
"""
from __future__ import annotations

import sys
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WORKSPACE / "src"))

from quan_ai_brain.governance.approval_cards import ApprovalCardStore

TASK_CODE = "TASK-SEMANTIC-MEMORY-M6"
TITLE = "Semantic Search ONNX MiniLM (không Ollama) + M6 runtime stability"

CARD_MARKDOWN = """[XIN PHÊ DUYỆT] — Mã nhiệm vụ: TASK-SEMANTIC-MEMORY-M6

## 1. Mục tiêu
(a) Triệt để hóa trí nhớ ngữ nghĩa: bật semantic search qua ChromaDB default
embedding (ONNX MiniLM chạy local, KHÔNG cần Ollama — đã probe OK 18/11).
Wire vào /api/chat retrieval như một lớp BỔ SUNG (hybrid: token LIKE + semantic),
không thay thế lớp nào. Ingest 3 nguồn hiện có vào collection mới (đọc-only từ
brain.db): memories active, episodes chat_turn, experience_lesson.
(b) M6: chủ chưa có brief gốc 10 TEST → theo phương án (b) chủ chọn trước đó:
chạy runtime stability và trình bảng nghiệm thu theo tiêu chí 24h đo được.

## 2. Phạm vi
- (a1) cognition/semantic_memory.py (MỚI): SemanticMemoryEngine — ingest
  batch (đọc brain.db mode=ro, viết ChromaDB), search top_k, stats; dùng
  chromadb PersistentClient tại data/vector_db_semantic (collection MỚI,
  không đụng collection 'quan_ai_brain_memory' cũ 53 chunks).
- (a2) server.py: +2 API localhost-only: /api/memory/semantic/search (GET),
  /api/memory/semantic/stats (GET); wire lớp semantic vào /api/chat sau
  memory_recall (bổ sung evidence block, cap 1200 chars).
- (a3) tools/semantic_ingest.py (MỚI): CLI chạy 1 lần + idempotent (skip
  chunk đã ingest theo original_id).
- (b) tools/m6_stability_probe.py (MỚI): probe 24h tự động mỗi 15 phút
  (health 8765/8766, Pi5 heartbeat, responder heartbeat, brain.db mtime,
  latency /api/chat) → reports/m6_stability_24h.json + bảng nghiệm thu.
- tests/test_semantic_memory.py (MỚI): ingest idempotent, search hit,
  server routes, fail-honest khi collection rỗng.
- KHÔNG: đụng collection cũ, cài dependency mới, đổi kiến trúc retrieval
  hiện có, tự promote tri thức quarantine, restart Pi5.

## 3. Tác động & rủi ro
- File mới ×4 + PATCH server.py (+2 route + 1 evidence block).
- ChromaDB ONNX MiniLM: download model lần đầu (~80MB, cache local) — chạy
  offline sau khi cache. Rủi ro lock: 1 writer, mở/đóng mỗi batch.
- Toàn bộ đọc brain.db mode=ro (không ghi DB người dùng).
- M6 probe chỉ ĐỌC health endpoints, không điều khiển gì.
- Rủi ro: R2 (ghi collection mới + file report). KHÔNG R3+.

## 4. Tiêu chí nghiệm thu
1. Ingest idempotent (chạy 2 lần → 0 duplicate) · 2. search trả chunk đúng
ngữ nghĩa (không cần từ khóa chính xác) · 3. /api/chat câu trừu tượng nhận
thêm evidence semantic · 4. 2 API mới 200 localhost · 5. test pass ≥12 ·
6. full regression không suy giảm · 7. probe 24h chạy, JSON đầy đủ · 8.
bảng nghiệm thu M6 trung thực (số đo thật).
"""

def main() -> int:
    store = ApprovalCardStore(WORKSPACE / "data" / "governance.db", workspace=str(WORKSPACE))
    card = store.create_card(
        task_code=TASK_CODE,
        title=TITLE,
        card_markdown=CARD_MARKDOWN,
        risk_level=2,
        goal="Semantic memory ONNX + M6 runtime stability 24h (owner chat directive 18/11)",
    )
    print(f"Card created: {card.request_id} | {card.task_code} | {card.status}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
