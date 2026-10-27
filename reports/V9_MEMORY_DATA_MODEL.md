# V9 — MEMORY DATA MODEL (mô hình dữ liệu đích)
**Ngày:** 28/10/2026 · Additive-only lên brain.db hiện hành (không ALTER/xoá bảng cũ)

## Bảng mới 1: `knowledge_units` (đơn vị tri thức chuẩn §IV)

```sql
CREATE TABLE IF NOT EXISTS knowledge_units (
    knowledge_id      TEXT PRIMARY KEY,          -- k_ + uuid12
    knowledge_type    TEXT NOT NULL,             -- FACT|OPINION|QUESTION|RULE|PROCESS|CONCLUSION
    subject           TEXT NOT NULL,
    predicate         TEXT NOT NULL,
    object            TEXT NOT NULL,
    statement         TEXT NOT NULL,             -- câu tự nhiên đầy đủ
    source_refs_json  TEXT NOT NULL DEFAULT '[]',   -- ["episode:<id>", "chat:<id>", "doc:<path>"]
    evidence_refs_json TEXT NOT NULL DEFAULT '[]',
    created_at_utc    TEXT NOT NULL,
    updated_at_utc    TEXT NOT NULL,
    valid_from_utc    TEXT,
    valid_until_utc   TEXT,
    scope             TEXT NOT NULL DEFAULT 'general',  -- general|project:<tên>|session:<id>...
    status            TEXT NOT NULL,             -- RAW|EXTRACTED|CANDIDATE|VERIFIED|INFERRED|CONFLICTED|NEEDS_OWNER_REVIEW|REJECTED|SUPERSEDED|ARCHIVED
    confidence        REAL NOT NULL DEFAULT 0.5, -- XEM §confidence bên dưới
    verification_method TEXT NOT NULL DEFAULT 'unverified',
    derived_from_json TEXT NOT NULL DEFAULT '[]',   -- knowledge_id suy luận từ đâu
    contradiction_refs_json TEXT NOT NULL DEFAULT '[]',
    version           INTEGER NOT NULL DEFAULT 1,
    review_status     TEXT NOT NULL DEFAULT 'PENDING',  -- PENDING|OWNER_CLARIFIED|OWNER_CONFIRMED
    extraction_meta_json TEXT NOT NULL DEFAULT '{}'     -- engine, quy tắc trích xuất, sanitizer ver
);
CREATE INDEX IF NOT EXISTS idx_ku_status ON knowledge_units(status);
CREATE INDEX IF NOT EXISTS idx_ku_subject ON knowledge_units(subject);
CREATE INDEX IF NOT EXISTS idx_ku_scope ON knowledge_units(scope);
```

## Bảng mới 2: `knowledge_relations` (lớp 4 — Relational Memory)

```sql
CREATE TABLE IF NOT EXISTS knowledge_relations (
    relation_id    TEXT PRIMARY KEY,            -- r_ + uuid12
    from_id        TEXT NOT NULL,               -- knowledge_id nguồn
    relation_type  TEXT NOT NULL,               -- SUPPORTS|CONTRADICTS|DERIVED_FROM|REFINES|SUPERSEDES|DEPENDS_ON|RELATED_TO|APPLIES_TO|VERIFIED_BY|REJECTED_BY
    to_id          TEXT NOT NULL,
    basis          TEXT NOT NULL DEFAULT '',    -- CĂN CỨ bắt buộc ghi khi tạo quan hệ
    is_speculative INTEGER NOT NULL DEFAULT 0,  -- 1 = quan hệ suy đoán chờ kiểm chứng
    created_at_utc TEXT NOT NULL,
    created_by     TEXT NOT NULL DEFAULT 'v9_extractor',
    UNIQUE(from_id, relation_type, to_id)
);
CREATE INDEX IF NOT EXISTS idx_rel_from ON knowledge_relations(from_id);
CREATE INDEX IF NOT EXISTS idx_rel_to ON knowledge_relations(to_id);
CREATE INDEX IF NOT EXISTS idx_rel_type ON knowledge_relations(relation_type);
```

## Bảng mới 3: `memory_exchange_log` (PHẦN VI — protocol + chống vòng lặp)

```sql
CREATE TABLE IF NOT EXISTS memory_exchange_log (
    message_id      TEXT PRIMARY KEY,          -- m_ + uuid12
    source_module   TEXT NOT NULL,
    target_module   TEXT NOT NULL,
    payload_type    TEXT NOT NULL,             -- knowledge_extracted|contradiction_found|hypothesis|process_tested|owner_question|candidate_recheck|...
    payload_ref     TEXT NOT NULL,             -- knowledge_id / relation_id / batch_id
    created_at_utc  TEXT NOT NULL,
    correlation_id  TEXT NOT NULL,
    provenance_refs_json TEXT NOT NULL DEFAULT '[]',
    status          TEXT NOT NULL DEFAULT 'DELIVERED',  -- DELIVERED|CONSUMED|REJECTED_LOOP|FAILED
    UNIQUE(correlation_id, source_module, target_module, payload_type, payload_ref)  -- idempotency
);
```

## Bảng mới 4: `memory_review_runs` (PHẦN VII — checkpoint chu kỳ)

```sql
CREATE TABLE IF NOT EXISTS memory_review_runs (
    run_id          TEXT PRIMARY KEY,          -- run_ + uuid12
    started_at_utc  TEXT NOT NULL,
    finished_at_utc TEXT,
    status          TEXT NOT NULL DEFAULT 'RUNNING',  -- RUNNING|COMPLETED|FAILED|INTERRUPTED
    checkpoint_json TEXT NOT NULL DEFAULT '{}',  -- {stage, cursor, processed_ids}
    stats_json      TEXT NOT NULL DEFAULT '{}',  -- newly_extracted, linked, duplicates, contradictions, owner_questions...
    batch_limit     INTEGER NOT NULL DEFAULT 50
);
```

## Bảng mới 5: `owner_questions` (PHẦN VIII — cấu trúc A–G)

```sql
CREATE TABLE IF NOT EXISTS owner_questions (
    question_id    TEXT PRIMARY KEY,            -- q_ + uuid12
    run_id         TEXT,
    problem        TEXT NOT NULL,               -- A. Vấn đề
    evidence       TEXT NOT NULL,               -- B. Bằng chứng (refs)
    current_view   TEXT NOT NULL,               -- C. Cách hiểu hiện tại
    interpretations_json TEXT NOT NULL,         -- D. Các cách giải thích khả dĩ
    question       TEXT NOT NULL,               -- E. Câu hỏi cho chủ
    impact         TEXT NOT NULL,               -- F. Tác động
    scope_hint     TEXT NOT NULL,               -- G. Phạm vi áp dụng
    status         TEXT NOT NULL DEFAULT 'OPEN',   -- OPEN|ANSWERED|SUPERSEDED|EXPIRED
    answer_text    TEXT,
    answered_at_utc TEXT,
    created_at_utc TEXT NOT NULL
);
```

## Quan hệ với bảng cũ (không đụng structure)
- `source_refs_json` trỏ vào `episodes.id` / đường dẫn tài liệu / NetChat post_id.
- `memories` tiếp tục là kho vận hành hiện hành; `knowledge_units` là lớp cấu trúc suy luận — trích xuất TỪ memories/episodes, không nhân bản vô tội vạ (mỗi KU giữ source_ref về memories/episodes gốc).
- `semantic_memory` / `candidate_knowledge`: giữ nguyên, chỉ đọc + dọn rác bằng trạng thái ARCHIVED trong knowledge_units (bảng cũ không sửa).

## Confidence (§IV.2 — trung thực)
`confidence` = chỉ số **tổng hợp 4 thành phần khai báo** (không phải xác suất hiệu chuẩn):
- `src` (0–0.4): độ tin cậy nguồn — owner chat 0.4, verified doc 0.35, episode 0.25, external 0.15.
- `evd` (0–0.3): độ trực tiếp bằng chứng — trực tiếp 0.3, gián tiếp 0.15, suy đoán 0.05.
- `cons` (0–0.2): nhất quán — không mâu thuẫn 0.2, đa nguồn cùng hướng 0.15, có mâu thuẫn 0.
- `ver` (0–0.1): xác minh thật (test/probe) 0.1, chưa 0.
Tổng cộng tối đa 1.0. LUÔN hiển thị kèm `verification_method` + `status` — INFERRED không bao giờ hiển thị như VERIFIED.

## Migration & rollback
- Chỉ `CREATE TABLE IF NOT EXISTS` — không ALTER bảng cũ, không xóa dữ liệu (Test I so sánh count/trước-sau).
- Rollback = DROP 5 bảng mới (không ảnh hưởng dữ liệu cũ) + code kill-switch env `QUAN_AI_BRAIN_V9_OFF=1`.
- Backup pre-migration: copy brain.db vào backups/ trước lần chạy đầu.
