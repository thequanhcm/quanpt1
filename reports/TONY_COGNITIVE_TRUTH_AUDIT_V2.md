# TONY_COGNITIVE_TRUTH_AUDIT_V2.md — PHASE 0 CAI V3.0 (02/11/2026 18:5x)

Phương pháp: SQL trực tiếp + import API + probe Pi5. Mỗi kết luận có bằng chứng.

## 1. Số liệu tươi (so với báo cáo cũ)

| Mục | Cũ | Tươi 02/11 | Trạng thái |
|---|---|---|---|
| episodes | 2.889 | **2.907** | OBSERVED (+18) |
| facts (semantic_memory) | 2.127 | **5.051** | OBSERVED (bảng khác — cũ đếm bảng khác) |
| knowledge_units | 150 | **150** | VERIFIED (không đổi) |
| candidate_knowledge | — | **7.950** | OBSERVED (chưa promote) |
| memories | — | **2.364** | OBSERVED |
| approval_cards | — | 0 | OBSERVED |
| approval_cards_v2 | — | 1 | OBSERVED (card UAG V1) |
| memory_review_runs | — | 1 | OBSERVED |
| feedback | — | 828 | OBSERVED |
| evidence rows | — | **0** | **FAILED** — bảng evidence chưa tồn tại trong brain.db |

## 2. Tool Registry — root cause "trống"

- `ToolRegistry()` instance mới: **0 tool** (KHÔNG tự load — phải register thủ công)
- `QPIG().registered_tools()`: **25 tool** (đã đăng ký qua QPIG.__init__)
- **Root cause:** ToolRegistry là in-memory, không có auto-discovery. QPIG có 25 tool
  nhưng chỉ tồn tại trong instance QPIG — không có instance nào được tạo trong chat
  pipeline. → Tool Registry "trống" vì **không có instance nào được wire vào /api/chat**.

## 3. QPIG chưa vào chat (§IV)

- Tìm `chat`/`conversation` files dùng QPIG: **0 file**
- Chat pipeline thật: `web/server.py::_handle_api_chat` (line 1588) — routing LLM →
  MemoryStore → CognitiveRetriever → PromptContextBuilder → LLM. **Không có bước
  Tool Selection / QPIG / Pi5** trong luồng hiện tại.

## 4. Memory daemon self-eval 35%

- File `daemon/` chỉ có `health.py` — **KHÔNG có scorecard module**
- Báo cáo cũ ghi 35% — không tìm thấy code tương ứng để xác minh lại
- Trạng thái: **UNKNOWN** (không thể verify vì module không tồn tại)

## 5. Embedding latency 6s

- Module `quan_ai_brain.knowledge.embedding` / `embeddings`: **KHÔNG TỒN TẠI**
- Class `embed_text` có ở `cognition/embedding.py:72` và `ai/neural_symbolic.py:289`
- Trạng thái: **FAILED** — module báo cáo cũ không import được; cần đo lại với module thật

## 6. Pi5 H6

- Ping 192.168.1.2: **REACHABLE** (latency ~2ms)
- 11 cổng probe: **TẤT CẢ ĐÓNG** (SSH/API chưa mở — chờ owner chạy script trên Pi)
- Trạng thái: **OBSERVED** REACHABLE nhưng **FAILED** cho mọi kênh thực thi

## 7. Evidence Store

- Bảng `evidence` trong brain.db: **không tồn tại**
- `EvidenceStore` class ở `security/containment.py` (sprint UIE-V2 đã thêm 11 trường)
  dùng **DB riêng** (`data/evidence.db`), không phải brain.db
- Trạng thái: **PARTIAL** — class có, schema 11 trường có, nhưng chưa có bằng chứng
  can thiệp thực tế trong production (chỉ có evidence từ sprint test/demo)

## 8. Kết luận PHASE 0

- **6 lỗ hổng báo cáo cũ vẫn còn** (ToolRegistry rỗng, QPIG chưa vào chat, embedding
  module lỗi, evidence production rỗng, Pi5 kênh đóng, daemon scorecard không tồn tại)
- **Số liệu episodes/facts/knowledge đã tăng** — hệ thống vẫn ghi nhận, không đứng
- **SPRINT 1 ưu tiên:** Tool Registry auto-load + QPIG wire vào /api/chat
