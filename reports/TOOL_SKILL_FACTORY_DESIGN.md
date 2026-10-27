# TOOL & SKILL FACTORY — DESIGN (Master Prompt V6)

**Thời điểm:** 27/10/2026 22:45 GMT+7 · **Branch:** `feature/cognitive-state-integration`

## 1. NGUYÊN TẮC THIẾT KẾ

1. **Reuse before creating** — mở rộng module hiện có, không tạo engine trùng.
2. **Fail-honest** — thiếu bằng chứng → ghi `UNKNOWN`/`NOT VERIFIED`, không bịa số.
3. **Fail-safe** — ADVISE không được phép khi chưa VERIFY (gate an toàn).
4. **Small diff** — 1 module mới + 1 test file; không đụng session song song.

## 2. KIẾN TRÚC TÁI SỬ DỤNG

```
information_gap_analyzer.TaskSpecification   ← giữ nguyên (hiểu bài toán)
cognition/task_pipeline.py (MỚI)             ← pipeline stage-tracking bọc ngoài
continuous_learning_engine (CLO V1)          ← mỗi pipeline run = evidence cho learning session
capability_registry.CapabilityRegistry       ← nguồn DISCOVER (liệt kê năng lực sẵn có)
experience pipeline (S9)                     ← đích REUSE (candidate lesson, không tạo mới)
```

## 3. MODULE MỚI: `cognition/task_pipeline.py`

### 3.1. PipelineStage (§III — 11 stage chuẩn)

UNDERSTAND → DECOMPOSE → DISCOVER → PLAN → LEARN → BUILD → TEST → ANALYZE → VERIFY → ADVISE → REUSE

Quy tắc chuyển stage:
- Chỉ được đi **tới trước**, không quay lại (history giữ vết).
- Bỏ qua stage được phép (stage không áp dụng) nhưng **bắt buộc ghi lý do**.
- `ADVISE` chặn cứng: chỉ vào được khi `VERIFY` đã hoàn tất **hoặc** VERIFY ghi rõ `not_verified=True` với danh sách bằng chứng thiếu. Không có ngoại lệ.

### 3.2. TaskPipeline (dataclass)

| Trường | Nguồn |
|--------|-------|
| `spec: TaskSpecification` | tái sử dụng nguyên xi |
| `stage_history: list[StageRecord]` | mỗi record: stage, at, notes, evidence_refs, skipped_reason? |
| `evidence_manifest: dict` | stage → list bằng chứng (file path, task_id, URL…) |
| `validation_results: dict` | VERIFY ghi kết quả đối chiếu + độ tin cậy |
| `reusable_assets: list[str]` | REUSE ghi tên tool/skill/quy trình kiểm chứng |
| `final_recommendation: str` | chỉ ghi được khi stage == ADVISE |

### 3.3. TaskPipelineEngine (API tối thiểu)

- `create_pipeline(owner_request, task_goal, acceptance_criteria, risk_level="R1") -> TaskPipeline`
  - UNDERSTAND tự động ghi với owner_request làm bằng chứng gốc.
- `advance(pipeline, stage, notes, evidence_refs=None, skipped_reason=None) -> TaskPipeline`
  - Validate thứ tự; VERIFY yêu cầu ≥1 acceptance_criteria đã có kết luận hoặc not_verified; ADVISE chặn nếu chưa VERIFY.
- `to_dict()` — đầy đủ để persist vào `checkpoint_data_json` (tái dùng cơ chế S15, không tạo bảng mới).

### 3.4. Không làm trong increment này (tránh scope creep)

- Không tự gọi LLM để phân rã bài toán (DECOMPOSE do caller/owner cung cấp).
- Không tự tạo lesson ở REUSE — chỉ trả danh sách `reusable_assets` để caller đẩy qua pipeline S9 có approval.
- Không đụng email thật (BLOCKED) — evidence là path/task_id trong workspace.

## 4. USE CASE NGHIỆM THU (§VI — dữ liệu thật trong workspace)

Vmail BLOCKED → chạy nghiệm thu trên nguồn được phép:
1. `data/tasks.db` (durable_tasks) — trạng thái công việc thật.
2. Báo cáo `.md` trong `bao cao xay dung he thong/` — bằng chứng văn bản.
Smoke: tạo pipeline "Kiểm tra tiến độ task trong hệ thống" → DISCOVER evidence từ tasks.db → VERIFY đối chiếu số liệu → ADVISE xuất khuyến nghị; mâu thuẫn (nếu có) giữ nguyên 2 phiên bản, không tự xử.

## 5. TEST PLAN (`tests/test_v6_task_pipeline.py`)

1. Stage đi đúng thứ tự 11 bước.
2. Chuyển ngược bị từ chối.
3. Skip stage không lý do → từ chối; có lý do → OK, có vết.
4. ADVISE trước VERIFY → bị chặn (safety gate).
5. VERIFY thiếu bằng chứng → `not_verified=True` ghi trung thực; ADVISE vẫn chặn khi VERIFY chưa chạy.
6. to_dict/from_dict khôi phục nguyên trạng (persist check).
7. Reuse: `reusable_assets` ghi nhận được tool kiểm chứng.

---
*Design bởi: QUAN AI BRAIN Agent · Master Prompt V6 · 27/10/2026 22:45 GMT+7*