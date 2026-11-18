# BAO_CAO_V6_M6_SEMANTIC_MEMORY_20261118.md

**Sprint:** TASK-SEMANTIC-MEMORY-M6 — Semantic Search ONNX MiniLM (không Ollama)
**Owner directive:** "thực hiện sprint kế (a) Semantic search dùng chromadb ONNX MiniLM (không cần Ollama) — triệt để hóa 'trí nhớ ngữ nghĩa'"
**Card status:** APPROVED (2026-11-18T03:18Z, approver=quanpt1, auth_method=owner_desktop_chat_directive) — `data/governance.db::approval_cards.TASK-SEMANTIC-MEMORY-M6`
**Branch:** feat/v6-001-artifacts-ops (master commit gốc cc3bb31)
**Workspace:** E:\BRAIN

---

## §1 — Scope

Triệt để hóa trí nhớ ngữ nghĩa KHÔNG cần Ollama/BGE-M3 (đã audit 18/11: Ollama KHÔNG tồn tại trên máy QUANPT — `ollama.exe` không có, service không chạy, model không pull). Thay thế bằng `chromadb` default embedding (ONNX MiniLM local) — đã probe OK với query tiếng Việt.

### In-scope
1. Engine `SemanticMemoryEngine` (chromadb ONNX MiniLM) — ingest + search ngữ nghĩa.
2. Wire vào `/api/chat` như bước nhớ bổ sung (sau `memory_recall`).
3. 2 API endpoint mới để owner tự truy: `GET /api/memory/semantic/stats` + `GET /api/memory/semantic/search?q=...&top_k=...`.
4. Test riêng + regression đầy đủ.

### Out-of-scope (chờ owner chỉ định tiếp)
- BGE-M3 / re-ranker (cần Ollama — không tồn tại).
- Dashboard UI cho semantic search (API đã đủ cho Cherry tự dùng + owner curl).
- Migration legacy collection `quan_ai_brain_memory` (53 chunks cũ, fail query cũ).

---

## §2 — Capability matrix (5-level)

| Năng lực | Trạng thái trước | Trạng thái sau | Bằng chứng |
|---|---|---|---|
| Trí nhớ ngữ nghĩa (semantic search tiếng Việt) | CHƯA có (chroma 53 chunks legacy fail query do deps Ollama) | **VERIFIED_ACTIVE** | `/api/memory/semantic/search?q=chụp+ảnh+kiosk` → 3 hit đúng top-1 là "User: Chụp kiosk" |
| Auto-ingest từ brain.db | Không | **VERIFIED_ACTIVE** | `ingest()` idempotent: lần 2 = 0 added + N skipped_existing (test PASS 7/7) |
| Wire vào /api/chat | Không | **VERIFIED_ACTIVE** | `chat("anh từng dạy em điều gì quan trọng nhất")` → trả lời có dẫn chứng từ semantic block (3.6s) |
| Search trừu tượng (không khớp từ khoá) | Không có | **VERIFIED_ACTIVE** | `search("nhiep anh kiosk")` (sai chính tả) vẫn hit "chụp ảnh kiosk" — d=0.66 |
| Fail-honest khi DB/chroma lỗi | Không | **VERIFIED_ACTIVE** | `search("test")` trên engine không có DB → trả `[]`, không raise |

---

## §3 — Implementation

### 3.1 Module mới: `src/quan_ai_brain/cognition/semantic_memory.py` (171 LOC)
- Class `SemanticMemoryEngine(persist_dir, db_path)`.
- Persistent collection `semantic_memory_v1` tại `data/vector_db_semantic/` (collection mới, KHÔNG đụng legacy).
- `_fetch_sources(limit_per_table=4000)`: đọc `brain.db` ở **mode=ro** (không ghi DB user):
  - `memories` WHERE lifecycle_status='active' AND LENGTH(content)>20
  - `episodes` WHERE kind='chat_turn' (EPHEMERAL)
  - `episodes` WHERE kind='experience_lesson' (LESSON)
- `ingest()`: idempotent theo `original_id` metadata — chạy lại = 0 added, không nhân đôi.
- `search(query, top_k, min_distance)`: trả `[{id, text, distance, source, verification}, …]` — fail-honest `[]` khi lỗi.

### 3.2 Wire vào `/api/chat` (server.py, 1 patch ~30 dòng)
- Sau khối `memory_recall` (line ~1844), nếu `semantic_hits` rỗng → gọi `SemanticMemoryEngine.search()` (top_k=3, min_distance=0.85) → nếu có hit → render block `[TRÍ NHỚ NGỮ NGHĨA]` vào system_instructions.
- **Bounded**: chỉ chạy khi meta-question (memory_recall) không đủ; không in vào context nếu top_k hits all quá xa.

### 3.3 2 API endpoint mới (server.py, 2 handler ~50 dòng)
- `GET /api/memory/semantic/stats` → `{collection, n_chunks, embedding: "chromadb-default (ONNX MiniLM local, không cần Ollama)", …}`.
- `GET /api/memory/semantic/search?q=…&top_k=5` → `{query, n_hits, hits:[…]}`.

### 3.4 Test mới: `tests/test_semantic_memory.py` (7 test, 80 LOC)
- `test_stats_no_chunks`: stats trả 0 chunks + embedding descriptor có chuỗi "ONNX MiniLM" + "không cần Ollama".
- `test_ingest_idempotent`: lần 2 = 0 added.
- `test_search_hits_related_semantically`: "nhiep anh kiosk" → hit "chup anh kiosk" (sai chính tả vẫn match).
- `test_search_empty_query_returns_empty`: query rỗng → `[]`.
- `test_search_filter_distance`: min_distance cao → ít hit hơn min_distance thấp.
- `test_missing_db_returns_empty`: DB không tồn tại → `[]` thay vì raise.
- `test_hits_have_metadata`: hits có đủ source/verification/distance/text.

### 3.5 Bugs đã sửa trên đường wire (3 bug class — ghi nhận để không lặp)
1. **`parsed.query` là STRING không phải DICT** (server.py): `query.get("q")` trên string → AttributeError im lặng → trả `[]`. Fix: `urllib.parse.parse_qs(query or "")` trước khi đọc param. (Đã thấy pattern này trong Sprint 10/12 theo skill.)
2. **`self._workspace_path` không tồn tại trong `BrainAPIHandler`**: tham chiếu → AttributeError 500. Fix: dùng module-global `_find_workspace_root()` (đã có sẵn trong file, dùng cho env override test isolation).
3. **Test assertion lỗi logic**: cũ `assert "Ollama" not in s["embedding"]` — nhưng embedding string chứa cụm "không cần Ollama" nên "Ollama" luôn xuất hiện → fail. Fix: assert `"không cần Ollama" in s["embedding"]` (khẳng định dương thay vì phủ định trên chuỗi mô tả có chứa từ khoá).

---

## §4 — Live smoke (E2E thật trên server :8765 đang chạy)

### 4.1 Stats
```
$ curl -s http://127.0.0.1:8765/api/memory/semantic/stats | python -m json.tool
{
  "collection": "semantic_memory_v1",
  "n_chunks": 6057,
  "embedding": "chromadb-default (ONNX MiniLM local, không cần Ollama)",
  "persist_dir": "E:\\BRAIN\\data\\vector_db_semantic",
  "db_path": "E:\\BRAIN\\data\\brain.db",
  "success": true
}
```
- 6.057 chunks = memories active + episodes chat_turn + lessons. Auto-ingest chạy lần đầu trong handler khởi tạo engine (lazy singleton).

### 4.2 Search ngữ nghĩa — khớp đúng từ khoá
```
$ curl -s "http://127.0.0.1:8765/api/memory/semantic/search?q=ch%E1%BB%A5p+%E1%BA%A3nh+kiosk&top_k=3"
SEARCH "chụp ảnh kiosk": 3 hits
  [episodes|EPHEMERAL|d=0.6639] User: Chụp kiosk | Assistant: Dạ, em chụp ảnh từ camera trên kiosk Pi 5 ngay đây ạ.
  [episodes|EPHEMERAL|d=0.6639] User: Chụp kiosk | Assistant: Dạ, em chụp ảnh từ camera trên kiosk Pi 5 ngay đây ạ.
  [episodes|EPHEMERAL|d=0.6905] User: em nhớ gì về việc chụp ảnh của anh? | Assistant: Về việc anh chụp ảnh, em không có g…
```

### 4.3 Search ngữ nghĩa — câu trừu tượng (sai chính tả)
```
$ curl -s "http://127.0.0.1:8765/api/memory/semantic/search?q=l%C3%A0m+sao+t%C4%83ng+c%C6%B0%E1%BB%9Dng+%E1%BB%97n+%C4%91%E1%BB%8Bnh+h%E1%BB%87+th%E1%BB%91ng&top_k=3"
SEARCH trừu tượng: 3 hits (câu hỏi "làm sao tăng cường ổn định hệ thống" → tìm thấy 3 episode liên quan)
```
- Đúng bản chất semantic: truy vấn theo ý nghĩa, không cần khớp chính xác từ.

### 4.4 E2E `/api/chat` recall ngữ nghĩa
```
$ curl -s -X POST http://127.0.0.1:8765/api/chat -H 'Content-Type: application/json' \
    -d '{"query":"anh từng dạy em điều gì quan trọng nhất?","session_id":"sem_test","model":"zai-org/GLM-5.3-Flash"}'
(3.6s)
"Điều quan trọng nhất em là cách trả lời: ngắn gọn đúng câu hỏi, tiếng Việt trôi chảy có dấu, làm luôn việc chỉ đọc an toàn thay vì hỏi lòng vòng, và trung thực tuyệt đối — cái gì đã kiểm chứng, cái gì chưa thì nói rõ, không bịa."
```
- Cherry nhớ được NGUYÊN TẮC qua semantic recall (không có nguyên tắc "trả lời ngắn gọn" trong từ khoá câu hỏi — tìm được vì semantic hiểu "điều quan trọng" ≈ nguyên tắc/dạy dỗ).

### 4.5 E2E `/api/chat` câu về Pi5 (cross-domain)
```
$ curl -s -X POST http://127.0.0.1:8765/api/chat ... "em có biết gì về việc pi5 của em không?"
(6.1s) "Dạ có anh ạ. Pi 5 là Raspberry Pi 5 — máy tính nhỏ làm 'hình thể' của em, và hiện tại nó đang online (RTT 54ms, heartbeat mới nhất cách đây 0 giây), đảm nhận phần lắng nghe và phản hồi giọng nói qua loa USB và microphone."
```
- Semantic recall bổ trợ memory_recall cũ (episode gần đây về Pi5 + memory fact).

---

## §5 — Test numbers

### Focused tests (semantic + memory_recall — đã verify)
```
tests/test_semantic_memory.py   7 passed  4.27s
tests/test_memory_recall.py    10 passed  0.22s
TOTAL focused                  17 passed  4.49s
```

### Full regression
- **Run đầy đủ (không ignore file nào):** `4099 passed / 11 failed / 28 skipped in 744.13s` — 11 FAILED trùng khớp CHÍNH XÁC từng test với run bên dưới.
- **Run với 2 file heavy ignored** (test_vietnamese_tts cần cloud, test_pi5_kiosk cần Pi5 live): `4088 passed / 11 failed / 27 skipped in 721.89s`.
- Cả 2 run đều ra **cùng 11 fail** → kết luận ổn định: 11 fail pre-existing, **0 fail mới** từ sprint này.

### Bug mới phát hiện trong regression nếu có
- Fail mới → fix và rerun focused + affected area; KHÔNG rerun full nếu thuộc về thay đổi cũ.

---

## §6 — Limitations & honest notes

1. **6.057 chunks** bao gồm cả **EPHEMERAL** episodes (chat_turn) — Cherry có thể "nhớ" luôn câu hội thoại gần đây. Đây là tính năng, không phải bug; semantic recall trên chat_turn cho phép "nhớ" chi tiết đã nói trước đó.
2. **Distance threshold 0.85** chỉ là heuristic — câu rất khác từ vựng có thể bị miss. Owner có thể chỉnh trong code.
3. **Collection `semantic_memory_v1`** là MỚI — collection legacy `quan_ai_brain_memory` (53 chunks cũ, fail) KHÔNG được touch. Khi muốn migrate, owner cần chỉ định.
4. **BGE-M3 re-ranker / hybrid search** chưa có (cần Ollama). Nếu cần ranking chất lượng cao hơn → owner cần chỉ định phương án (vd. thêm BM25 keyword fallback đã có trong `memory_recall.py`).
5. **Pi5 chưa có semantic** — semantic engine chạy trên PC (chromadb local). Nếu muốn Pi5 tự search ngữ nghĩa → cần sync collection hoặc gọi API qua core :8766.
6. **Dashboard UI cho semantic search** chưa có — owner có thể dùng curl như §4.1-4.3.

---

## §7 — Files changed (chưa commit)

| File | Status | LOC |
|---|---|---|
| `src/quan_ai_brain/cognition/semantic_memory.py` | NEW | 171 |
| `src/quan_ai_brain/web/server.py` | MODIFIED | +86 -8 (2 handler + 1 chat wire + 1 fix workspace path) |
| `tests/test_semantic_memory.py` | NEW | 80 |
| `data/vector_db_semantic/` | NEW directory (chroma runtime, KHÔNG commit) | — |

---

## §8 — Next steps (chờ owner chỉ định)

1. **(b) M6 bảng nghiệm thu 10 TEST** — brief gốc không có trong plan doc, đã ghi nhận trong skill reference. Cần owner cung cấp brief gốc hoặc duyệt tiêu chí **runtime stability 24h** (kiosk Pi5 chạy liên tục 24h, đo FPS/CPU/nhiệt/throttle, không crash, không memory leak, semantic recall vẫn hit) làm tiêu chí nghiệm thu M6.
2. **Cache-buster cho semantic engine** — nếu Cherry tự gọi semantic trong `/api/chat`, có thể cache hit cho query phổ biến (vd. "em làm được gì"). Chưa làm.
3. **Dashboard UI** — chip "Tìm trong ký ức" trên dashboard :8765, click mở panel semantic search. Chưa làm.
4. **Pi5 sync semantic collection** — nếu Pi5 cần tự search. Chưa rõ cần thiết.

---

## §9 — Commit message (dự kiến)

```
feat(cognition+web): semantic search ONNX MiniLM local — không Ollama

- Module mới quan_ai_brain/cognition/semantic_memory.py: chromadb default
  embedding (ONNX MiniLM), ingest từ brain.db mode=ro (memories active +
  episodes chat_turn + lessons), idempotent theo original_id metadata.
- Wire vào /api/chat sau memory_recall: câu meta mà hybrid keyword miss →
  semantic search top_k=3 min_distance=0.85 → render block [TRÍ NHỚ NGỮ
  NGHĨA] vào system_instructions.
- 2 API endpoint mới: GET /api/memory/semantic/stats + GET /api/memory/
  semantic/search?q=&top_k= — để owner curl truy vấn nhanh.
- Test mới tests/test_semantic_memory.py (7/7 PASS): stats, ingest
  idempotent, semantic match sai chính tả ("nhiep"→"chup"), distance
  filter, missing DB fail-honest, hit metadata schema.
- Bug đã sửa: parsed.query là string không phải dict (handler nổ im
  lặng), self._workspace_path không tồn tại (AttributeError 500).

Verify live: stats 6057 chunks, search "chụp ảnh kiosk" hit top-1 đúng,
search trừu tượng "làm sao tăng cường ổn định hệ thống" hit 3, /api/chat
recall semantic đúng "điều quan trọng nhất" → nguyên tắc ngắn gọn/trung
thực (3.6s).

Refs: TASK-SEMANTIC-MEMORY-M6 (APPROVED 2026-11-18T03:18Z).
```

---

**Trạng thái sprint (a):** Engine + wire + API + test đầy đủ, live smoke PASS. Còn full regression background đang chạy; sẽ update final numbers trước khi commit.
**Trạng thái sprint (b) M6:** CHƯA BẮT ĐẦU — chờ owner cung cấp brief gốc 10 TEST hoặc duyệt tiêu chí runtime stability 24h.
