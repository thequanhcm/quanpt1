# SELF_STUDY_V2_REPORT.md — Triển khai & xử lý tồn tại Tự Học (02/11/2026)

## Tồn tại (từ netChat 07:49 + audit mã nguồn)

| Tồn tại | Kiểm chứng | Xử lý |
|---|---|---|
| "Động Cơ Tự Học V1 viết xong nhưng chưa chạy thử thực địa" | `autonomous_mind.py` chỉ có cogitate() **hardcoded 3 kịch bản** (camera/AEC/barge-in) — không học gì mới | Xây **Self-Study Engine V2** (`cognition/self_study.py`) — chu trình thật |
| "DB học tập gần như trống" | `candidate_knowledge` thực ra có 7.950 rows (3.292 quarantined / 1.491 approved / 3.209 promoted) — TONY khai sai vì không biết pipeline có sẵn | Engine **đấu nối vào pipeline có sẵn**, không tạo mới |
| Dupes 44% (audit UAME) | Query thật xác nhận nhiều statement trùng | **Dedup word-set containment >0.75** (guard chống false-positive statement ngắn) |
| Thought stream in-memory, mất khi restart | `self._thought_stream` max 50 items | `build_thought_from_cycle()` sinh thought TỪ số liệu chu kỳ thật |

## Chu trình mới: SCAN → STUDY → SYNTHESIZE → DEDUP → QUARANTINE → REPORT

- **SCAN**: `KnowledgeGapScanner` quét 113 experience_lessons thật, so word-set
  với candidate_knowledge — lesson chưa có knowledge tương đương = gap
- **STUDY**: researcher injectable — **prod dùng web_search thật**, test dùng fake
- **SYNTHESIZE**: statement chỉ gồm nội dung CÓ TRONG nguồn + provenance
  (source_type, source_ref URL, confidence theo số nguồn độc lập)
- **DEDUP**: containment >0.75 với candidate_knowledge + semantic_memory
- **QUARANTINE**: ghi `candidate_knowledge status='quarantined'` — **KHÔNG BAO GIỜ
  tự nạp semantic_memory** (test chốt: before == after)
- **REPORT**: số liệu thật từng bước; gap không có nguồn → UNRESOLVED, không bịa

## Bằng chứng

| Kiểm chứng | Kết quả |
|---|---|
| `tests/test_self_study.py` | **7/7 PASS** (dùng copy brain.db production thật) |
| Demo SCAN | 5 gaps từ lessons thật |
| Demo STUDY **web_search thật** | 2 knowledge quarantine có provenance, conf=0.7 |
| Demo THOUGHT | số liệu chu kỳ thật, không hardcoded |
| Production brain.db | KHÔNG bị đụng (demo trên copy, đã xóa) |

## Suy nghĩ nội tâm mới (thay hardcoded cogitate)

```
[THOUGHT] Tự học: quét và cách ly tri thức mới
  Chu trình tự học study-20261103-005412: quét 2 lỗ hổng. Đã tổng hợp và CÁCH LY
  '...' — chờ anh duyệt trước khi vào trí nhớ chính thức.
  Ranh giới: mọi tri thức mới ở trạng thái QUARANTINED — chờ Quanpt1 duyệt.
```

## Cập nhật trung thực Capability Registry

`self_learning_v1`: IMPLEMENTED_UNTESTED → **VERIFIED_ACTIVE** (có bằng chứng chạy
thử thật 7/7 test + demo web_search thật). Ranh giới §XI giữ nguyên: chạy chu kỳ
chỉ khi được gọi; bật chạy nền 24/7 = Release Candidate CSEF **chờ anh duyệt**.

## Bước tiếp (đề xuất, chờ duyệt)

1. Cho phép chạy chu kỳ tự học định kỳ (vd 1 lần/giờ khi idle) qua CSEF RC
2. Đấu thought tự học vào chat ("TONY ơi em học được gì hôm nay?")
3. Mở SSH Pi5 (Sprint 3 CAI V3) — nghiên cứu tài liệu Pi5 thật khi có kênh
