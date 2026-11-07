# CHERRY HỌC "NHÌN" ẢNH — MÔ TẢ BỐI CẢNH (duyệt owner 07/11)

## Yêu cầu owner
"cho cherry học cách phân tích ảnh này không phải thông tin ảnh mà là hình ảnh
đang mô tả gì: ví dụ trong ảnh đang là trong nhà, có tủ lạnh, có đèn, bể cá,
cá trong bể..." (kèm ảnh DM 07:08 — CHERRY lúc đó chỉ báo kỹ thuật: độ sáng,
RGB, OCR không chữ).

## Root cause của hành vi cũ
image_analyzer.py (Vision S1) chỉ đo ĐỘ TRUNG THỰC từ file (kích thước/độ sáng/
màu/OCR) — cố tình KHÔNG gán nhãn vật thể vì "engine phân loại chưa có; huấn
luyện model nhận diện = sprint riêng chờ duyệt" (fail-honest đúng thời điểm đó).

## Giải pháp đã làm (không cần huấn luyện — dùng GLM vision sẵn có)
Probe thật 07/11: NetMind Cloud GLM-5.3-Flash NHẬN ẢNH base64 trong content[]
(image_url) — trả mô tả bối cảnh tiếng Việt ~2-4s.
- `_scene_description(path)`: gửi ảnh (resize nếu >6MB) → prompt "chụp ở đâu,
  có vật thể/con vật/con người gì, tiếng Việt thuần, không suy diễn".
- `analyze_image`: mô tả bối cảnh đặt LÊN ĐẦU reply (ghi rõ "mô tả AI, có thể
  sai chi tiết nhỏ" — trung thực); kỹ thuật + OCR giữ sau; tri thức vẫn ghi
  quarantine (learning is not deployment).
- 2 bug tìm thấy khi E2E: (1) content=None finish=length — GLM reasoning model
  hết token trong reasoning → max_tokens 1000 + retry 2000; (2) GLM trả lẫn
  tiếng Anh → prompt ép "TIẾNG VIỆT THUẦN".

## E2E thật (ảnh photo_20261107_070813.jpg CHERRY tự chụp 07:08)
"Mô tả AI GLM: Ảnh được chụp trong nhà, tại khu bếp và phòng ăn của một căn hộ.
Có một chiếc tủ lạnh màu đen dán giấy ghi chú và hình trang trí, trên nóc để
bằng khen và khung ảnh. Trần nhà gắn nhiều đèn gầm cùng máy quay giám sát.
Phía sau là tủ bếp màu trắng, có ấm đun nước và một hồ cá thủy sinh trồng cây
xanh bên trong. Không thấy con người nào xuất hiện."
→ ĐÚNG kỳ vọng của anh: trong nhà + tủ lạnh + đèn + bể cá ✓ (4.05s tổng).

## Test
- vision + OCR + image pairing + web + voice: 44/44 PASS (đã cập nhật 1 test
  lỗi thời: "đọc giúp anh ảnh này" giờ là LỆNH hệ thống tony_analyze_image →
  chạy ngay không ghép ảnh — test cũ viết TRƯỚC khi có lệnh này, fail từ trước
  thay đổi, chứng minh bằng stash; thêm test mới test_analyze_image_command_does_not_pair).
- Servers restart — lệnh DM "Phân tích ảnh" của CHERRY dùng engine mới ngay.
