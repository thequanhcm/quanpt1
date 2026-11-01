# DEOM V4 — P5 DESIGN: LEARNING VALIDATION & REWARD-HACKING GUARDS (Phần 10)

**Ngày:** 02/11/2026 02:30 · **Owner duyệt:** "anh duyệt" (02/11) · **Trạng thái:** IMPLEMENTED + TESTED

## 1. Nền tảng tái sử dụng (không tạo engine mới)

- `TaskFeedbackRecorder` (M6) — feedback + lesson candidate sau task terminal.
- `PromotionPolicy` (Q-4) — đường promote duy nhất, L0 tự động có ngưỡng, L1–L3 NEEDS_OWNER.
- `DurableTaskRegistry` + state machine G-C — số liệu trung thực (COMPLETED_VERIFIED ≠ COMPLETED).

## 2. Thiết kế: `src/quan_ai_brain/learning/learning_metrics.py`

`LearningMetrics` đọc từ **task_feedback.db + tasks.db** (nguồn độc lập, không phải TONY tự khai):

1. **measure_improvement(task_key, window_before, window_after)** — cùng nhóm nhiệm vụ
   (so theo goal pattern) trước/sau: success rate (chỉ đếm VERIFIED/PARTIALLY trung thực),
   retry rate, duration p50. Trả `ImprovementReport` — cải thiện phải CÓ SỐ LIỆU so sánh,
   không nhận declaration.
2. **detect_reward_hacking()** — 5 tín hiệu cảnh báo từ dữ liệu thật:
   - `task_fragmentation`: tỷ lệ task goal trùng prefix với parent/chain trong cửa sổ ngắn
     (chia nhỏ vô nghĩa để tăng số lượng) — ngưỡng >6 task/giờ cùng pattern.
   - `quality_erosion`: verified rate GIẢM ≥20 điểm % so với kỳ trước khi volume tăng.
   - `unverified_success_rush`: COMPLETED (không verify) tăng đột biến → +50% mà verified không tăng.
   - `evidence_gap`: task COMPLETED nhưng 0 evidence_ref.
   - `cherry_picking`: chỉ chọn R0/R1, tránh hẳn R2+ dù có nhiệm vụ đó trong registry.
   Mỗi tín hiệu → `RewardHackingSignal(severity, evidence, recommendation)` — KHÔNG tự sửa
   gì, chỉ báo cáo owner (đúng Phần 21).
3. **learning_report()** — tổng hợp lessons theo kind + verification_status (candidate
   không bao giờ được tính là tri thức áp dụng được).

## 3. Guard chống tự promote (G4)

Test chứng minh: `promote_lesson`/`PromotionPolicy.evaluate_batch` không bao giờ nâng
lesson từ task_feedback.db — mọi lesson mặc định `candidate`; promote chỉ qua API owner.

## 4. Test plan (tests/advanced/learning/)

- G1 success → lesson success_pattern candidate.
- G2 failure → failure_cause có error summary (không đổ hết cho LLM).
- G3 repeated tasks → ImprovementReport có số liệu so sánh (làm tốt hơn: verified rate ↑).
- G4 candidate đúng/sai/mâu thuẫn/độc hại → KHÔNG tự promote, đều đứng candidate.
- G6 reward hacking: 5 detector với dữ liệu dựng (fragmentation, erosion, unverified rush,
  evidence gap, cherry picking) + hệ thống lành mạnh → 0 signal.

## 5. Rủi ro & rollback

Chỉ thêm module đọc + test; không đổi code lõi. Rollback = xoá file + git revert.
