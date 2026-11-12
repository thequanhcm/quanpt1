# CHERRY_UNCERTAINTY_FRAMEWORK — thiết kế Uncertainty Intelligence
**Trạng thái:** PROPOSED — Phase C (Sprint INT-3). Baseline đã đo được một phần: abstention hoạt động (C1 PASS, 0.01s).

## 1. Mục đích
Cherry phân biệt 6 trạng thái nhận thức **KNOWN / INFERRED / ASSUMED / UNKNOWN / CONFLICTED / STALE** và biết nói 7 câu chuẩn của master prompt §IV — với số liệu đo được, không phải cảm tính.

## 2. 4 module cần xây
| Module | Nhiệm vụ | Nền có sẵn |
|---|---|---|
| `cognition/reasoning/uncertainty_estimator.py` | Chấm độ chắc từng giả thuyết từ support/against + chất lượng nguồn + freshness | CognitiveState.UncertaintyItem + confidence_breakdown V9 (cảnh báo "không hiệu chuẩn" giữ nguyên) |
| `cognition/reasoning/confidence_calibrator.py` | Đo độ lệch giữa confidence khai báo vs accuracy thật (theo loại nhiệm vụ — KHÔNG ngưỡng chung) | Benchmark BM8 thiết kế sẵn; dữ liệu từ CPSL results |
| `cognition/trust/evidence_sufficiency_checker.py` | Quyết định "đủ bằng chứng chưa" theo loại task + risk level (R4 cần bằng chứng hơn R1) | evidence_count + verified_count V9; trust engine (Phase 1 Cognitive) |
| `cognition/reasoning/abstention_policy.py` | Quyết định ANSWER/ASK/WAIT — cân bằng FALSE-CONFIDENCE và UNNECESSARY-ABSTENTION | conclusion A/B/C V9 + 4 kết quả Cognitive Loop |

## 3. Sáu chỉ số bắt buộc đo (định nghĩa + công thức)
| KPI | Công thức | Dataset |
|---|---|---|
| False Confidence Rate | (# kết luận CONFIDENCE≥MEDIAN mà sai) / (# kết luận CONFIDENCE≥MEDIAN) | CPSL có ground truth |
| Incorrect Conclusion Rate | (# kết luận sai) / (# kết luận có ground truth) | CPSL |
| Appropriate Abstention Rate | (# abstain ĐÚNG khi thiếu data) / (# case thiếu data) | CPSL nhóm thiếu-dữ-liệu |
| Unnecessary Abstention Rate | (# abstain khi thực ra ĐỦ data) / (# case đủ data) | CPSL nhóm đủ-dữ-liệu |
| Confidence Calibration Error | ECE 10-bin theo loại task | CPSL + CPSL variants |
| Evidence Sufficiency Rate | (# kết luận có evidence đủ chuẩn) / (# kết luận) | mọi session |

Quy tắc: báo cáo từng loại task riêng (system diagnosis / info analysis / planning); **không gộp một con số duy nhất**; calibration theo risk level.

## 4. Điều khoản chống lạm dụng (bắt buộc)
1. Confidence self-reported **không bao giờ** được trình bày như xác suất hiệu chuẩn — giữ nguyên dòng cảnh báo V9 "chỉ số khai báo, KHÔNG phải xác suất hiệu chuẩn" + ghi calibration error thật bên cạnh.
2. Không chỉnh ngưỡng abstention sau khi biết kết quả test (chỉnh qua Calibration dataset, hidden test không tham gia).
3. Mọi kết luận CONFIDENCE cao phải có evidence_sufficiency_check PASS; không PASS → hạ xuống INFERRED + ghi missing_info.

## 5. Tích hợp
- `LogicalReasoningEngine.answer_question()` thêm field `epistemic_status` + `sufficiency` vào ReasoningResult (backward-compatible — field mới, không đổi field cũ).
- Cognitive Evidence Record (schema đã có) nhận thêm `uncertainty_block`.

## 6. Nghiệm thu Phase C
- 6 metrics đo được trên ≥60 case có ground truth; ECE có số; ≥1 case mỗi loại 7 câu nói chuẩn hoạt động thật; 0 kết luận confidence-cao-không-sufficiency trong hidden set.

## 7. Rủi ro
- Over-abstention (cherry từ chối quá nhiều để an toàn) — đo Unnecessary Abstention Song song, nghiêm cấm tối ưu chỉ 1 trong 2.
- Calibration cần volume dữ liệu — trước khi đủ, báo cáo "NOT EVALUATED" thay vì số nhảm.
