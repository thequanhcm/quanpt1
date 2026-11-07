# NĂNG LỰC & CÔNG VIỆC CỦA CHERRY — DUYỆT CẬP NHẬT 07/11/2026 (00:0x–00:10)

Owner duyệt: "duyệt các năng lực và các công việc chưa hoàn thiện cho cherry"
(kèm ảnh DM 00:02 — CHERRY tự giới thiệu 7 năng lực kiểm chứng + 1 chờ duyệt).

## A. REGISTRY NĂNG LỰC — ĐỒNG BỘ THEO THỰC TRẠNG (capability_registry.py)

### Sửa 2 bản ghi LỖI THỜI (trung thực — bằng chứng sống kiểm 00:07):
1. long_term_memory: IMPLEMENTED_UNTESTED → **VERIFIED_ACTIVE**
   (episodes 2.975, semantic 5.052 đang ghi sống; hard-delete E2E POST→DELETE→404; 51/51)
2. local_llm_inference: đổi tên + mô tả "Local Ollama Engine" →
   "NetMind Cloud GLM-5.3-Flash + Ollama Local (optional)"
   (Ollama 11434 KHÔNG chạy; LLM thật là NetMind Cloud E2E 2.7s — đúng hiện trạng)

### Thêm 3 năng lực mới (06/11 đã verify):
3. edge_embodiment_pi5 — VERIFIED_ACTIVE (LAN-first RTT 28-35ms misses=0,
   kiosk avatar lip-sync, wake CHERRY ơi, camera IMX708, health panel; HDMI mirror
   ghi rõ CHƯA xong trong evidence)
4. netchat_dm_channel — VERIFIED_ACTIVE (DM 100% 4 tầng, 476 tin 0 pending)
5. speech_learning_quarantine — IMPLEMENTED_UNTESTED (516 câu quarantined,
   chưa nối prompt giọng nói)

### Kết quả đếm: 12 năng lực = 9 VERIFIED_ACTIVE + 1 INERT_STAGING
   (Job Containment chờ sign-off) + 1 IMPLEMENTED_UNTESTED (speech corpus)
   + 1 EXTERNAL_PLANNED (vệ tinh). Tests identity/self-awareness/web 30/30 PASS.

## B. CÔNG VIỆC CHƯA HOÀN THIỆN — XỬ LÝ THEO DUYỆT

### B1. ✅ TTS auto-fallback piper (22 timeout/24h — Q-3 carried)
- tts_config.py: Edge fail bền 5 lần → TỰ THỬ piper local cùng request
  (_synthesize_with_piper); fallback lỗi cũng ghi rõ (fail-honest);
  không đổi provider config toàn cục.
- E2E: Edge OK 69KB; piper provider OK 89KB; fallback unit test PASS
  (mock Edge chết → piper cứu trả audio).
- Sửa 2 test theo thiết kế mới (có comment lý do): TTS-06 (mock cả piper chết →
  TTS_UNAVAILABLE), thêm TTS-06b (fallback cứu); test wake-config 'hi tony'→
  'cherry ơi' (rename 06/11 — test này fail CẢ TRÊN HEAD CŨ, pre-existing).
- Dàn voice/tts/web: **63 passed, 1 skipped (hardware-gated), 0 failed**.

### B2. ✅ Audio "Dummy Output" — XÁC MINH KHÔNG PHẢI LỖI
- DRM HDMI-A-1/A-2 = disconnected: anh đã RÚT cáp HDMI 23:59 (tin bot xác nhận).
  PipeWire trả Dummy Output là ĐÚNG khi không có thiết bị xuất; cắm HDMI lại
  sink vc4hdmi tự quay về. Không sửa gì — tránh "sửa" điều đúng.

### B3. Responder đã restart → CHERRY giới thiệu năng lực MỚI khi hỏi lại.

## C. CÒN MỞ (không thuộc duyệt này / cần quyết riêng)
- HDMI mirror: labwc từ chối enable HDMI-A-2 (cần cmdline video= + reboot hẹn giờ
  hoặc thử trong khi anh cắm HDMI) — báo cáo HDMI_MIRROR_BUG_20261106.
- Rotate shared_secret (bước 2 mục 3) + git filter-repo (can thiệp lịch sử).
- Nối speech corpus 516 câu vào prompt giọng nói (đề xuất A — few-shot Phase F).
- 5 quyết định TVI + 3 V9.0; pair BT; Job Containment sign-off.
