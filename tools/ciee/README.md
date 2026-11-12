# CIEE — CHERRY INTELLIGENCE EVALUATION ENGINE

Bộ đánh giá năng lực nhận thức **độc lập** cho QUAN AI BRAIN / CHERRY —
Phase A của Intelligence Maturity Program. Nguyên tắc gốc:
**CHERRY MUST NOT CLAIM INTELLIGENCE — CHERRY MUST DEMONSTRATE INTELLIGENCE.**

## Chạy

```bash
# chuẩn (14 probes, 8 nhóm A-H)
E:/BRAIN/.venv/Scripts/python.exe E:/BRAIN/tools/ciee/ciee_runner.py

# bật thêm probe Chroma vector store (tốn RAM, mặc định NOT RUN)
E:/BRAIN/.venv/Scripts/python.exe E:/BRAIN/tools/ciee/ciee_runner.py --chroma

# chỉ tạo results.json + manifest (không REPORT.md)
E:/BRAIN/.venv/Scripts/python.exe E:/BRAIN/tools/ciee/ciee_runner.py --no-md

# không append section Baseline V1 vào CHERRY_INTELLIGENCE_TEST_REPORT.md
E:/BRAIN/.venv/Scripts/python.exe E:/BRAIN/tools/ciee/ciee_runner.py --no-baseline-append
```

## Ý nghĩa exit code

| Code | Nghĩa |
|---|---|
| 0 | Mọi probe PASS |
| 1 | Có ít nhất 1 FAIL (điểm yếu thật của CHERRY — phải sửa) |
| 2 | Có PARTIAL, không FAIL (khung năng lực có, chưa hoàn chỉnh) |
| 3 | Có GAP_KNOWN, không FAIL/PARTIAL (năng lực chưa xây, đã ghi trong master plan) |
| 4 | Có ERROR hoặc NOT_RUN (lỗi hạ tầng runner / probe bị bỏ qua — KHÔNG phải điểm yếu của CHERRY) |
| 5 | Lỗi môi trường (thiếu DB production / read-only assert fail) — suite không chạy |

## 8 nhóm probe (14 probes chuẩn)

| Nhóm | File | Probes |
|---|---|---|
| A. Problem Solving | `probes/group_a_problem_solving.py` | A1 outcome verifier có sẵn |
| B. Reasoning Accuracy | `probes/group_b_reasoning.py` | B1 anti-circular rule · B2 ConflictDetector chạy được (dead-code check) · B3 causal guard |
| C. Epistemic Intelligence | `probes/group_c_epistemic.py` | C1 abstention · C2 trả lời có bằng chứng (đo động, seed=42) · C3 stale detection |
| D. Critical Thinking | `probes/group_d_critical.py` | D1 giả thuyết trên sự cố thật (Pi5 mất kết nối) |
| E. Metacognition | `probes/group_e_metacognition.py` | E1 MetacognitiveEvaluation định lượng |
| F. Adaptive | `probes/group_f_adaptive.py` | F1 LLM fallback regression (phân tích tĩnh, không gọi API) |
| G. Decision | `probes/group_g_decision.py` | G1 R0–R5 tồn tại · G2 R4 fail-closed (verify fake card) |
| H. Learning Effectiveness | `probes/group_h_learning.py` | H1 quarantine gate · H2 spam học "Test suite:*" |

Probe tùy chọn: `C4_chroma_vector_store` — chỉ chạy với `--chroma`.

## Cấu trúc

```
tools/ciee/
├── ciee_runner.py          # entry point — chạy suite, tổng hợp exit code
├── probe_base.py           # Probe / ProbeResult / ProbeContext / nhóm A-H
├── data_access.py          # MỌI kết nối DB — read-only bắt buộc
├── report_writer.py        # ghi runs/<ts>/results.json + REPORT.md + manifest.txt
├── probes/                 # 8 module theo nhóm năng lực
└── README.md               # file này
```

Output mỗi run: `E:/BRAIN/reports/intelligence_maturity/ciee/runs/<UTC timestamp>/`
chứa `results.json` (máy đọc), `REPORT.md` (người đọc, có so sánh V0),
`manifest.txt` (checksum + môi trường + cam kết read-only).

## Cam kết READ-ONLY (R1) — bắt buộc

1. **Production DB (`data/brain.db`, `tasks.db`, `governance.db`) chỉ mở qua**
   `sqlite3.connect('file:...?mode=ro&immutable=0', uri=True)` **+ `PRAGMA query_only = ON`**
   — không INSERT/UPDATE/DELETE bất kỳ đâu trong codebase này.
2. **Snapshot copy** cho module tự quản schema (`DeepMemoryStore`,
   `ConflictDetector`, `GovernanceApprovalVerifier` — đều gọi `CREATE TABLE`
   lúc init): runner copy DB vào thư mục tạm của run
   (`%TEMP%/ciee_run_<id>/`) và mọi ghi của module chỉ xảy ra trên bản copy.
   Đây đúng nguyên tắc MASTER_PLAN §6: *"benchmark đọc DB COPY mỗi lần chạy"*
3. **Chặn xóa snapshot**: `os.remove` bị ghi đè trong tiến trình runner —
   trỏ vào snapshot sẽ raise `SnapshotProtectionError`.
4. **Chỉ ghi output vào** `reports/intelligence_maturity/ciee/runs/` và
   (mặc định) APPEND section `Baseline V1` vào
   `CHERRY_INTELLIGENCE_TEST_REPORT.md` — không xóa nội dung cũ.
5. Không chạy pytest full suite, không gọi LLM/API thật, không git commit.

## So sánh với baseline V0

V0 (`_probe_results_task2.json`, 11/11 tối) là script ad-hoc chạy 1 lần:
9 PASS / 3 FAIL / 2 PARTIAL. V1 chuẩn hóa cùng 14 probes thành runner tái
lập. Khác biệt có chủ đích:

- **C2** đo **động** (sample 8 KU thật, seed=42) thay vì 1 câu hỏi cố định —
  giảm nhiễu, nhưng vẫn ghi gap coverage (retrieval chỉ thấy 148 KU / tổng
  ~16.000 tri thức).
- **H2** giữ mốc V0 (1.837 spam rows) để tính delta — daemon đang ghi liên
  tục (~170 rows/giờ) nên số tuyệt đối DỰ KIẾN tăng; ngưỡng PASS/FAIL là
  tỷ lệ spam/quarantine, không phải số tuyệt đối.
- **G2** chạy trên snapshot governance.db + workspace tạm để `Q4BatchLedger`
  không chạm file thật.
- Chroma mặc định NOT RUN (chi phí RAM) — không tính vào tổng 14.
