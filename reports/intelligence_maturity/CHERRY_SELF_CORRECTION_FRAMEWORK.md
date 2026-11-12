# CHERRY_SELF_CORRECTION_FRAMEWORK — thiết kế Self-Correction Engine
**Trạng thái:** PROPOSED — Phase D (Sprint INT-4). Bài học seed đã có thật: La La School (perception/source error) + backup 2AM chết (execution/verification error).

## 1. Chu trình 10 bước (master prompt §VI — giữ nguyên, thêm bằng chứng cho từng bước)
1. Ghi dự đoán ban đầu (PredictionRecord, trước khi biết kết quả — chống "chữa cháy ngược")
2. Lưu bằng chứng ban đầu (evidence_refs + hash)
3. Thu kết quả thực tế (probe/API/log thật)
4. So sánh dự đoán vs kết quả → sai lệch đo được
5. Xác định sai lệch + phân loại (8 loại dưới)
6. Phân tích nguyên nhân gốc (dùng chính reasoning engine — dogfooding)
7. Đề xuất phương pháp sửa (R2 — không tự thực hiện ngoài whitelist)
8. Kiểm thử phương pháp mới (regression trên case lỗi + variants)
9. Đánh giá trên bài toán tương tự (transfer check)
10. Kiểm tra bài toán MỚI (anti-overfitting — OOD set CPSL)

## 2. Phân loại 8 sai lầm + ví dụ seed thật
| Loại | Ví dụ thật trong hệ thống |
|---|---|
| Perception Error | TV trẻ em → wake nhầm → memory nhiễm (La La School) |
| Source Error | Tin mọi âm thanh qua wake là owner (speaker assumption ngầm) |
| Memory Error | 88 nhóm semantic dup; 1.837 spam rows |
| Reasoning Error | Kết luận nhân quả thiếu cơ chế (chưa có causal guard) |
| Planning Error | Deploy lên Pi5 khi Pi5 offline (không thể xảy ra — chặn trước) |
| Execution Error | Backup 2AM result≠0 không được phát hiện 2 đêm |
| Verification Error | "0 facts nghĩa là không có gì mới" vs enum mismatch khiến ingest path chết im lặng |
| Calibration Error | Confidence khai báo cao hơn accuracy thật (đo ở Phase C) |

## 3. Error Database (append-only)
`data/cognitive/errors.db` (SQLite riêng — không đụng brain.db):
```sql
CREATE TABLE errors (
  error_id TEXT PRIMARY KEY,          -- ERR-YYYYMMDD-<seq>
  error_type TEXT CHECK(error_type IN ('PERCEPTION','SOURCE','MEMORY','REASONING','PLANNING','EXECUTION','VERIFICATION','CALIBRATION')),
  root_cause TEXT NOT NULL,
  impact TEXT NOT NULL,
  prediction_ref TEXT,                -- link PredictionRecord
  evidence_refs TEXT NOT NULL,        -- JSON list + sha256
  corrective_action TEXT,
  regression_test TEXT,               -- test file::case — phải tồn tại trước khi đóng
  verification_result TEXT,           -- kết quả chạy test thật
  status TEXT CHECK(status IN ('OPEN','CORRECTING','VERIFIED_FIXED','ACCEPTED_RISK')) DEFAULT 'OPEN',
  never_close_without_test TEXT DEFAULT '1',  -- không được đóng khi chưa có regression test xanh
  created_at_utc TEXT, updated_at_utc TEXT
);
CREATE TABLE error_history (        -- append-only, KHÔNG XÓA LỊCH SỬ
  history_id INTEGER PRIMARY KEY AUTOINCREMENT,
  error_id TEXT, field TEXT, old_value TEXT, new_value TEXT, changed_at_utc TEXT, changed_by TEXT
);
```

## 4. Quy tắc bất biến
1. Không xóa lịch sử lỗi (append-only; sửa = ghi entry mới).
2. **Thay đổi câu trả lời ≠ khắc phục lỗi** — đóng lỗi chỉ khi: regression test PASS + verification_result ghi kết quả thật + tái lập 2 lần.
3. Mỗi lỗi khi đóng phải sinh 1 regression test mới trong `tests/cognitive/regression/`.
4. Lỗi đã fix phải được re-check trên bài toán tương tự (transfer) — tái phạm cùng loại → mở lại + nâng severity.

## 5. Tích hợp
- Self-Correction đọc CPSL results + Outcome Verifier (DEOM M2) + reflection records.
- `self_correction_engine.py` = module duy nhất; KHÔNG daemon — chạy sau mỗi phiên benchmark + khi watchdog phát hiện anomaly.

## 6. Nghiệm thu Phase D
- ≥2 lỗi thật (La La School + backup 2AM) nhập đủ chu trình 10 bước; regression test cho từng lỗi PASS; tái lập 2 lần; 0 lỗi đóng khi chưa test; history append-only verify được.

## 7. Rủi ro
- Lỗi "fix" trên giấy (test mock) — chống bằng yêu cầu verification_result là output thật, CIIA đối chiếu.
- Loop tự sửa vô hạn — mỗi error_id chỉ 1 corrective action đang mở; mở mới phải ghi history.
