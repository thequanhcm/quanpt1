# M1 — DATABASE HEALTH REPORT

**Người lập:** TONY · **Thời điểm đo:** 01/11/2026 ~11:00 giờ VN
**Nguồn:** `database_collector.py` — `sqlite3.connect(mode=ro)` + `PRAGMA quick_check` (đọc-only tuyệt đối, không vacuum, không ghi)

## Kết quả quick_check thật (E2E)

| Database | Kích thước | WAL | quick_check | Trạng thái |
|---|---|---|---|---|
| data/brain.db | 93.248 KB (~91MB) | nhỏ | `ok` | ✅ NORMAL |
| data/tasks.db | 11.612 KB | 0 KB | `ok` | ✅ NORMAL |
| data/health_alerts.db (M1 tạo) | 12 KB | — | schema riêng | ✅ |
| data/health_history.db (M1 tạo) | 12 KB | — | schema riêng | ✅ |
| data/governance.db | 552 KB | — | (không trong probe M1) | — |
| data/consultations.db | 20 KB | — | (không trong probe M1) | — |

## Row counts thật (brain.db)

| Bảng | Số dòng | Ghi chú |
|---|---|---|
| memories | 2.020 | tăng +16 từ M0 (2.004) — học tự nhiên |
| semantic_memory | 1.842 | không đổi (promotion bị chặn R4 — đúng chính sách) |
| episodes | 2.564 | +16 từ M0 (2.548) — ghi hoạt động mới |
| candidate_knowledge | 4.378 | +94 từ M0 (4.284) — quarantine tích lũy, chờ Q-4 |
| knowledge_units | 150 | không đổi |

## Nhận định

1. **Không phát hiện hư hỏng** — quick_check `ok` cả 2 DB chính; tasks.db WAL đã checkpoint sạch.
2. **Tăng trưởng lành mạnh**: memories +16/episodes +16 trong ~2,5 giờ hoạt động (responder + learning daemon) — không phải leak.
3. **candidate_knowledge +94/phiên** — tốc độ sinh tri thức quarantine nhanh hơn tốc độ duyệt (0 vì R4 verifier chưa cấu hình). Nếu duyệt Q-4, số 4.378+ này là kho xét duyệt; nếu không duyệt, đề xuất thêm ngưỡng cảnh báo khi vượt ~10.000 (gợi ý dọn định kỳ) — sẽ đưa vào ngưỡng M1 sau.
4. Đề xuất M2: thêm probe governance.db + consultations.db + learning_checkpoints.db vào database_collector (schema đã ổn định).
