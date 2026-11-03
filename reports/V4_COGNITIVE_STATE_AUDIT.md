# QUAN AI BRAIN — V4 COGNITIVE STATE & REASONING AUDIT REPORT

**Phiên thẩm định:** 2026-10-27T18:12:00+07:00  
**Tài liệu quy chiếu:** Master Implementation Prompt V4  
**Workspace:** `E:\AI\QUAN AI BRAIN`  
**Chủ sở hữu:** Quanpt1 — Phạm Thế Quân  
**Trạng thái kiểm thử Baseline:** **927 PASSED**, **0 FAILED**, **1 SKIPPED** (Phần cứng Pi 5 offline). Exit code: 0 (Tổng: 928 bài test across 82 test files).

---

## 1. Mục đích Audit

Kiểm tra đối chiếu toàn diện mã nguồn, mô hình trạng thái nhận thức hiện hữu, cơ chế lưu trữ bộ nhớ, luồng lập kế hoạch điều hành và rào chắn an toàn trước khi thực hiện bất kỳ thay đổi nào trong đợt nâng cấp V4.

Đảm bảo tuân thủ các nguyên tắc cốt lõi:
- *Audit first, change second.*
- *Evidence before confidence; Explicit uncertainty over fabricated certainty.*
- *Observe and learn automatically; apply consequential changes only with authorized owner approval.*
- *Reuse existing architecture; no duplicate engines.*
- *Fail closed whenever authorization, provenance, integrity or safety cannot be established.*
- *Zero production execution; R5 hard-blocked; R4 Dual-Factor gated.*

---

## 2. Kiểm tra Môi trường, Git và Trạng thái Working Tree

### 2.1. Git Metadata
- **Branch:** `master`
- **Head Commit:** `6b6df30c4848183d82bf7d09c04754853ef9ee6e`
- **Trạng thái Working Tree:**
  - Files đã sửa đổi (Modified):
    - `docs/PROJECT_STATUS.md`: Ghi nhận cột mốc V3 Epistemic Grounding & Adversarial Testing.
    - `reports/HANDOFF_LATEST.md` & `reports/TEST_RUN_LATEST.txt`: Báo cáo bàn giao phiên trước.
    - `src/quan_ai_brain/planning/coordinator.py`: Đã gắn `CognitiveState` vào quy trình lập kế hoạch `ExecutiveCoordinator.plan()`.
    - `src/quan_ai_brain/planning/models.py`: Đã bổ sung trường `cognitive_state` vào `TaskPlan`.
  - Files mới chưa theo dõi (Untracked):
    - `src/quan_ai_brain/cognition/cognitive_state.py`: Mô hình `CognitiveState`, `BeliefItem`, `ContradictionRecord`, `MetacognitiveEvaluation`.
    - `tests/test_cognitive_state.py`: 8 unit test cho mô hình nhận thức cơ sở.
    - `tests/test_adversarial_cognition.py`: 12 test đối kháng theo Mục X Master Prompt V3.
    - Các báo cáo kỹ thuật tổng thể trong thư mục `bao cao xay dung he thong/`.
  - Files bị xóa (Deleted):
    - `edge_client/assets/avatar/test_asset.json`: Tệp rác kiểm thử tạm thời đã được dọn dẹp.

### 2.2. Kết quả Chạy Kiểm thử Toàn bộ Baseline
- **Lệnh thực thi:** `.\.venv\Scripts\python.exe -m pytest -q tests`
- **Thời gian chạy:** 86.92 giây.
- **Kết quả:**
  - `927 passed, 1 skipped in 86.92s`
  - Exit code: `0`
  - Bài test bị bỏ qua: `tests/test_vietnamese_tts.py:266` (Phần cứng Raspberry Pi 5 vật lý không cắm mạng trong phiên này; PC Core đã được xác thực 100%).

---

## 3. Phân loại Hiện trạng Thành phần Kiến trúc

Theo yêu cầu của Master Prompt V4 Mục 1, bảng phân loại hiện trạng phân tách rõ 6 nhóm:

| Thành phần / Năng lực | Hiện trạng mã nguồn | Phân loại trạng thái | Ghi chú và Bằng chứng thực tế |
| :--- | :--- | :--- | :--- |
| **`CognitiveState` Model** | `src/quan_ai_brain/cognition/cognitive_state.py` | **ĐÃ CÓ VÀ ĐƯỢC TEST** | 8 BeliefKind, BeliefItem, ContradictionRecord, MetacognitiveEvaluation. Đã pass 8 unit tests + 12 adversarial tests. |
| **`BeliefItem` Granular Provenance** | `src/quan_ai_brain/cognition/cognitive_state.py` | **ĐÃ CÓ NHƯNG CHƯA ĐỦ ĐẶC TẢ V4** | Hiện có `source_ref` đơn lẻ; chưa hỗ trợ `source_refs` đa nguồn, chưa có `subject`/`predicate`/`value` tường minh, chưa có `valid_until_utc` và `freshness_policy`. |
| **Freshness & Stale Detection** | `src/quan_ai_brain/planning/coordinator.py` | **ĐÃ CÓ NHƯNG CHƯA ĐỦ TEST** | Coordinator đã phân loại memory hết hạn thành `UNKNOWN`, nhưng chưa có engine tính toán độ mới (FreshnessEvaluator) tổng quát độc lập. |
| **Contradiction Preservation** | `src/quan_ai_brain/cognition/cognitive_state.py` | **ĐÃ CÓ VÀ ĐƯỢC TEST** | `record_contradiction()` lưu giữ 2 nhánh `claim_a`, `claim_b` cùng nguồn gốc, trạng thái `UNRESOLVED`. |
| **Context-Aware Disambiguation** | Chưa có | **CHƯA TRIỂN KHAI** | Chưa phân biệt giữa mâu thuẫn logic thực sự và sự khác biệt về ngữ cảnh (khác biệt thời điểm, khác biệt host PC vs Pi 5, khác biệt phạm vi). |
| **State Reconciliation & Lineage** | Chưa có | **CHƯA TRIỂN KHAI** | Chưa có hàm `reconcile_state()` để so sánh bằng chứng mới với trạng thái hiện thời, lưu vết phiên bản cũ và nguồn hỗ trợ/phản bác. |
| **Cognitive Self-Assessment** | `docs/PROJECT_STATUS.md` & `reports` | **MỚI CÓ THIẾT KẾ & BÁO CÁO TĨNH** | Đã có báo cáo tự đánh giá Markdown nhưng chưa có module code động trả lời trực tiếp trạng thái xác minh (`CODE_PRESENT`, `UNIT_TESTED`, `INTEGRATION_TESTED`, `ENVIRONMENT_VERIFIED`, `HARDWARE_VERIFIED`, `PRODUCTION_APPROVED`). |
| **Memory Engine & SQLite Store** | `src/quan_ai_brain/memory/sqlite_store.py` | **ĐÃ CÓ VÀ ĐƯỢC TEST** | Hỗ trợ 6 loại VerificationStatus, 5 loại LifecycleStatus, WAL mode, schema versioning, foreign keys, thread-safe. |
| **Cognitive Memory Retriever** | `src/quan_ai_brain/cognition/retrieval.py` | **ĐÃ CÓ VÀ ĐƯỢC TEST** | Xếp hạng xác định (deterministic scoring), hỗ trợ hybrid BGE-M3, lọc theo lifecycle status. |
| **Executive Coordinator** | `src/quan_ai_brain/planning/coordinator.py` | **ĐÃ CÓ VÀ ĐƯỢC TEST** | Lập kế hoạch phân tầng R0-R5, chặn R5, gắn CognitiveState, kích hoạt Metacognition Abstention khi thiếu thông tin. |
| **Self-Learning Engine** | `src/quan_ai_brain/learning/engine.py` | **ĐÃ CÓ VÀ ĐƯỢC TEST** | Observe -> Gap -> Research Dossier -> Quarantine -> Upgrade Proposal. Không tự apply nếu thiếu owner token. |
| **Continuous Evaluation Harness** | `src/quan_ai_brain/learning/evaluation.py` | **ĐÃ CÓ VÀ ĐƯỢC TEST** | Đo lường trước/sau đề xuất nâng cấp, benchmark 5 bài toán vận hành, phát hiện hồi quy. |
| **Process Containment Sandbox** | `src/quan_ai_brain/execution/process_containment.py` | **ĐÃ CÓ VÀ ĐƯỢC TEST** | `InertProcessBackend` ném `ProductionExecutionProhibitedError`. Ngăn chặn hoàn toàn việc tạo subprocess thật. |
| **Windows Job Object Kernel** | `docs/SPRINT6_DESIGN_SIGNOFF.md` | **MỚI CÓ THIẾT KẾ** | Ở trạng thái `PENDING_OWNER_SIGNOFF`. Nghiêm cấm kích hoạt trong sprint này. |

---

## 4. Nguy cơ Trùng lặp & Xung đột Kiến trúc Cần Tránh

1. **Không tạo `CognitiveMemoryStore` thứ hai:**
   `MemoryStore` (`src/quan_ai_brain/memory/sqlite_store.py`) đã là authoritative store cho episodic, semantic và quarantined memories. `CognitiveState` là mô hình trạng thái nhận thức phiên làm việc (in-memory / working state), có thể kết xuất thành `MemoryRecord` hoặc snapshot khi cần lưu bền vững.
2. **Không ghi đè hoặc hạ chuẩn của `PolicyEngine`:**
   Mọi suy luận của LLM hoặc đề xuất hành động từ `CognitiveState` (dù là phương án thay thế) đều phải tuân thủ phân tầng R0-R5. R5 luôn luôn bị chặn cứng (`BLOCKED`); R4 bắt buộc Dual-Factor xác thực chủ nhân.
3. **Không tạo confidence giả lập:**
   Nếu không có phương pháp đo lường hoặc nguồn xác minh, `confidence` phải để giá trị `None` hoặc mức mặc định có chú thích rõ `UNVERIFIED`/`INFERRED`, không gán số thập phân giả tạo (ví dụ 0.95) để tạo cảm giác chắc chắn giả tạo.

---

## 5. Lựa chọn Increment Triển khai (Chosen Increment)

Căn cứ vào kết quả audit và yêu cầu của Master Prompt V4, chúng tôi chọn **Increment nhỏ nhất có giá trị nhận thức và an toàn cao nhất**:

### Tên Increment: **Evidence-Driven Cognitive Claim, Freshness Evaluation, Context-Aware Contradiction & Self-Assessment Engine**

### Nội dung triển khai cụ thể:
1. **Nâng cấp Model trong `src/quan_ai_brain/cognition/cognitive_state.py`:**
   - Hoàn thiện `CognitiveClaim` (kế thừa và tương thích ngược với `BeliefItem`):
     - `claim_id: str`
     - `subject: str`, `predicate: str`, `value: Any` (nội dung mệnh đề có cấu trúc)
     - `statement: str` (chuỗi mô tả tự nhiên)
     - `kind: BeliefKind`
     - `source_refs: tuple[str, ...]` (hỗ trợ nhiều nguồn tham chiếu độc lập)
     - `confidence: float | None` (None nếu chưa có cơ sở kiểm chứng)
     - `verification_status: str` (USER_PROVIDED, OBSERVED, VERIFIED, INFERRED, UNVERIFIED, CANDIDATE)
     - `observed_at_utc: str`, `recorded_at_utc: str`
     - `valid_until_utc: str | None`, `freshness_policy: str` (ephemeral, session, daily, long_term, immutable)
     - `supporting_sources: tuple[str, ...]`, `opposing_sources: tuple[str, ...]`
     - `contradiction_refs: tuple[str, ...]`
     - `version: int`, `superseded_by: str | None`
     - `verification_method: str | None`
2. **Bộ đánh giá độ mới (Freshness Evaluator):**
   - Đánh giá trạng thái freshness: `FRESH`, `STALE`, `EXPIRED`, `IMMUTABLE`.
   - Phân biệt dữ liệu đã hết hạn nhưng vẫn đúng trong lịch sử với dữ liệu bị bác bỏ.
3. **Bộ phân giải mâu thuẫn nhận biết ngữ cảnh (Context-Aware Contradiction Engine):**
   - Phân biệt giữa mâu thuẫn thực sự (`DIRECT_CONTRADICTION`) và khác biệt do ngữ cảnh (`CONTEXT_DIFFERENCE` — khác biệt về mốc thời gian, khác biệt về thiết bị PC vs Pi 5, khác biệt về môi trường test vs prod).
   - Tự động gắn trạng thái `NEEDS_REVIEW` khi không đủ dữ liệu để phân giải thay vì tự ý chọn một phía.
4. **Bộ đối chiếu trạng thái (State Reconciliation):**
   - Hàm `reconcile_claim()`: tiếp nhận bằng chứng mới, cập nhật phiên bản, ghi nhận nguồn ủng hộ/phản đối, bảo toàn lịch sử và không xóa vết nguồn gốc cũ.
5. **Động cơ Tự đánh giá Năng lực Thực tế (Cognitive Self-Assessment Engine):**
   - Lớp `CognitiveSelfAssessment`:
     - Phân loại rõ ràng 6 cấp độ bằng chứng thực: `CODE_PRESENT`, `UNIT_TESTED`, `INTEGRATION_TESTED`, `ENVIRONMENT_VERIFIED`, `HARDWARE_VERIFIED`, `PRODUCTION_APPROVED`.
     - Phản ánh trung thực tình trạng module, test suite đã chạy trong phiên, và rào chắn an toàn (Inert Sandbox, R5 hard-blocked).
6. **Bộ Kiểm thử Chuyên biệt V4 (`tests/test_cognitive_state_v4.py`):**
   - 20 kịch bản kiểm thử nghiêm ngặt bao gồm đầy đủ các yêu cầu tại Mục 9 Master Prompt V4.

---

## 6. Cam kết An toàn (Security Invariants)

- R5 luôn luôn bị chặn cứng (`BLOCKED`).
- R4 yêu cầu phê duyệt tường minh Dual-Factor.
- Tuyệt đối không thay đổi `InertProcessBackend`; không tạo subprocess thật.
- Không khởi chạy background daemon 24/7.
- Không truy cập hoặc chỉnh sửa các thư mục bên ngoài workspace (`E:\AI\QUAN AI BRAIN`).
- Không xuất, in hoặc lưu trữ credentials/secrets.
- Bảo toàn toàn bộ các thay đổi chưa commit trên workspace.
