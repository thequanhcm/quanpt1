# SPRINT: PI5 NGHE GIỌNG THẬT & HỌC LỜI NÓI TỰ NHIÊN (06/11/2026)

## 1. Yêu cầu owner
"em cho Pi5 nghe giọng nói thực tế và học tập các lời nói thông thường của con người tự nhiên"

## 2. Audit trước (không code vội)
- Mic Pi5: Jieli UACDemoV1.0 qua PipeWire (đã verify 06/11 phiên trước: peak −41 dBFS)
- Wake service: Vosk vn-0.3 chạy 24/7, mọi âm thanh → partial text `[WAKE-DBG] Vosk: '...'`
  trong journal quan_ai_wake (bằng chứng 1236 dòng/24h)
- PC: 27 WAV converse lưu data/edge_media/voice (KHÔNG đụng — riêng tư)
- DB: candidate_knowledge schema thật (id, created_at_utc, statement, source_ref, rationale, status)
  + tool promote q4_batch_promote.py có sẵn

## 3. Thiết kế đã hiện thực (smallest safe change)
tools/speech_corpus.py — collector chuẩn hóa + ingest quarantined-only:
- Nguồn: journal Vosk Pi5 (scp + sed 24h) → text thô
- Lọc 5 lớp: 3–40 từ, 8–240 ký tự, regex quảng cáo/TV (NOISE_PATTERNS đo được từ
  1236 dòng thật), chuẩn hóa punctuation, Lev ≤2 chống trùng gần đúng, LIKE-head chống trùng DB
- Ghi: candidate_knowledge status='quarantined' — KHÔNG TỰ PROMOTE (V7.0 §2.2)
- WAV/audio KHÔNG lưu — chỉ text STT (riêng tư)
- KHÔNG daemon nền, KHÔNG sửa wake service, KHÔNG cloud

## 4. Kết quả chạy thật (LIVE_VERIFIED — bằng chứng terminal)
- Pull 24h journal: 1.242 dòng thô → lọc còn 674 câu đạt chuẩn
- Ingest: 516 câu MỚI (bỏ 158 trùng) — 100% quarantined
- Verify: stats() → 516 câu, status {quarantined: 516}
- conversation_state.voice có dấu hiệu converse thật (last_user_text tối nay 14:49 UTC)

## 5. Giới hạn trung thực (fail-honest)
- Phần lớn câu Vosk hiện là TIẾNG TV NỀN (phần mềm Vosk vn-0.3 nhạy ambient) —
  bộ lọc lọc được phần lớn; chất lượng câu "lời người nói trực tiếp" phụ thuộc
  mic gần miệng hơn
- CHƯA dùng được kho câu vào GLM persona (chờ owner duyệt promote → sau đó nối
  vào system_prompt như few-shot style examples)
- WAV chưa được dùng cho learning (đúng biên riêng tư; nếu owner muốn học âm
  thanh → cần thiết kế riêng + duyệt)

## 6. Đề xuất chờ owner duyệt (KHÔNG tự làm)
A. **Lịch pull tự động** (Task Scheduler 30 phút/1h): kho câu liên tục tăng
B. **Promote kho câu → văn phong TONY**: sau khi anh duyệt subset (~50-100 câu
   sạch nhất), nối vào system_instructions như few-shot examples tự nhiên
C. **Lọc nâng cao bằng GLM** (1 lần): đưa 674 câu qua GLM chấm "người nói trực
   tiếp vs TV nền" → chất lượng cao hơn nhiều
