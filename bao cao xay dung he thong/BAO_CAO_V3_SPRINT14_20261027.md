# BÁO CÁO V3 SPRINT 14 — INFORMATION GAPS SCHEMA THẬT + SEMANTIC SEARCH KINH NGHIỆM (BGE-M3)

**Ngày:** 27/10/2026
**Card:** TASK-V3-SPRINT14 (PENDING_APPROVAL → APPROVED → consumed; duyệt bởi quanpt1 qua desktop chat "duyệt Sprint 14"; approval `ac966c29` consume-once)
**Nguồn phạm vi:** §5 BÁO_CAO_V3_SPRINT13 (đã nghiệm thu) — 2 đầu việc chủ động được. Connector M-Suite KHÔNG nằm trong sprint này (cần thiết kế riêng, chờ chủ quyền).

## 1. Phạm vi đã duyệt và thực hiện
- (a) **PATCH `cognition/improvement_report.py`**: mục information_gaps đọc ĐÚNG schema thật
  `info_gap_tasks` (waiting_state NOT IN RESOLVED/CANCELLED) + `info_gap_events` — đóng
  khoảng CHƯA XÁC MINH mà Sprint 13 đã ghi trung thực (trước đó query sai bảng
  `information_gaps` không tồn tại). DB hỏng/thiếu → vẫn CHƯA XÁC MINH (fail-honest giữ nguyên).
- (b) **FILE MỚI `cognition/experience_semantic.py`**: `find_similar_experiences_semantic()` —
  embed truy vấn + toàn bộ EPISODIC/PROCEDURAL active bằng **BGE-M3** (module có sẵn từ
  Module 3, nghiệm thu 10/10), xếp cosine similarity, ngưỡng 0.30; tách confirmed/candidates
  đúng như keyword search Sprint 9; **fail-open** khi Ollama offline/DB lỗi → rỗng +
  `semantic_available=false` (trung thực, không chết luồng). Kinh nghiệm vẫn chỉ là THAM CHIẾU (§VII.3).
- (c) **API**: GET `/api/experience/search?q=&limit=` (localhost-only, read-only, fail-open).
- (d) **UI Workbench**: ô "Tìm kinh nghiệm (semantic BGE-M3)" trong khu bài học — hiển thị
  % similarity + nguồn + trạng thái xác minh; badge trung thực khi semantic không khả dụng.

## 2. Kiểm chứng
- **Test Sprint 14: 10/10 pass** (semantic rank/candidate-tách/offline-fail-open/ngưỡng/
  cosine + gap schema thật/DB hỏng → CHƯA XÁC MINH + API 400/403/offline-flag).
- **Test Sprint 13 sửa theo schema thật: 13/13 pass** (fixture information_gaps đổi sang
  info_gap_tasks/events; assert số liệu thật).
- **Full regression: 927 passed / 0 failed / 1 skipped** (Pi5 skip cố hữu; sau khi session
  song song wiring xong cognitive_state — chạy chung working tree).
- **Sự cố xử lý trong sprint:** phát hiện **session agent song song** đang sửa cùng repo
  (context_builder/planning/cognitive_state + test adversarial WIP). Đã: stash→rút đúng
  4 file Sprint 14→drop stash→vá lại server.py trên bản mới của họ; KHÔNG đụng file của họ.
  1 test E2E chat fail tạm thời do contention Ollama giữa 2 session — chạy đơn lẻ lại PASS.
  Hiệu năng: lần đầu smoke timeout 60s (embed toàn bộ memory mỗi request, service mới mỗi
  lần) → sửa thiết kế: singleton BGEEmbeddingService (cache ấm xuyên request) + prefilter
  keyword + cap 40 ứng viên embed → smoke thật cold 0.8s / warm 0.0s.

## 3. Giới hạn trung thực
- Đang có session song song hoạt động trên cùng working tree: phần lẫn trong cùng file
  (PromptContextBuilder max_chars 4000→6000, hardening `_count_rows` dùng as_uri) do họ tạo,
  được ghi rõ trong commit message, không phải thay đổi của Sprint 14.
- Hiệu năng semantic: prefilter keyword + cap 40 ứng viên embed/lần + singleton cache ấm —
  cold 0.8s, warm ~0.0s (smoke thật). Truy vấn không khớp keyword nào → fallback embed
  40 memory gần nhất (trung thực, không rỗng oan).
- Test adversarial/cognitive_state của session song song đang WIP đỏ — không thuộc phạm vi card này.
- Smoke embedding thật phụ thuộc Ollama local (bge-m3); offline → API trả `semantic_available=false`.

## 4. Next (đề xuất, CHỜ PHÊ DUYỆT RIÊNG)
1. Connector M-Suite (Outlook/Teams read-only) — cần thiết kế riêng + card riêng.
2. Đồng bộ với session song song: cognitive_state + adversarial test đang WIP.
3. Vmail thật vẫn BLOCKED — chờ owner đổi pass SSO (không đổi từ Sprint 8).
