# TONY VISION Sprint 1 — OCR + Phân tích ảnh (06/11/2026)

> Lệnh owner: "em sẽ học tập tri thức để nhận diện hình ảnh. em tải về và cài đặt
> OCR, huấn luyện cho TONY biết tất cả các hình ảnh, chi tiết để TONY phân tích được"

## Đã cài đặt + triển khai (LIVE)

| Thành phần | Chi tiết | Evidence |
|---|---|---|
| **Tesseract OCR v5.4.0** | Đã có sẵn trên PC (`C:\Program Files\Tesseract-OCR`), ngôn ngữ **vie+eng+osd** | `tesseract --list-langs` |
| **pytesseract 0.3.13** | Cài mới vào venv E:\BRAIN (trước đây thiếu → OCR_SUPPORT=False âm thầm) | pip install + import OK |
| **`quan_ai_brain.vision.image_analyzer`** | Module mới: OCR vie+eng + cấu trúc đo được (kích thước, độ sáng TB, màu chủ đạo top3, vùng sáng/tối) | 7 test mới |
| **Lệnh DM "phân tích ảnh"** | Intent `tony_analyze_image` — nhận "phân tích ảnh vừa chụp", "đọc chữ trong ảnh", "ảnh này ghi gì"... | E2E thật |
| **Nguồn ảnh tự động** | 1) Đính kèm DM đang xử lý → 2) ảnh DM trong 24h (`data/netchat_files`) → 3) ảnh TONY tự chụp trong 24h (`logs/pi5_media`) | fix root cause "phân tích ảnh vừa chụp" bị trả "chưa thấy ảnh" |
| **Tri thức tự học (cách ly)** | Mỗi lần phân tích ghi 1 dòng vào `candidate_knowledge` status=**quarantined** — TONY học dần, lên `semantic_memory` chỉ khi anh duyệt | DB row `364566f4...` |

## E2E thật — đúng tấm ảnh anh hỏi lúc 20:58 (`photo_20261106_205438.jpg`)

```
👁️ Phân tích ảnh `photo_20261106_205438.jpg`:
• Kích thước: 1280×720 px (RGB), độ sáng TB 108.9/255
• Màu chủ đạo: RGB(32, 32, 32) chiếm 31% (top3)
• Vùng rất sáng: 120 điểm (nguồn sáng/tiền cảnh)
• Vùng rất tối: 201 điểm (bóng/vật tối)
• Chữ nhận diện (OCR vie+eng): không có chữ trong ảnh (đúng — cảnh bếp không text)
• 🧠 Đã lưu tri thức ảnh vào trí nhớ (0 ký tự chữ + 9 chỉ số, chờ anh duyệt)
```

## Phạm vi — TRUNG THỰC về giới hạn

- **LÀM ĐƯỢC (UNIT_TESTED + LIVE E2E)**: đọc chữ trong ảnh (tiếng Việt + Anh), kích thước/
  độ sáng/màu chủ đạo/vùng sáng-tối, auto chọn đúng ảnh DM/ảnh tự chụp, tri thức vào hàng
  đợi cách ly chờ duyệt.
- **CHƯA LÀM ĐƯỢC — KHÔNG BỊA**: nhận diện vật thể ("đây là tủ lạnh", "có 2 người") cần
  model thị giác (YOLO/CLIP) + dữ liệu huấn luyện. TONY trả lời trung thực rằng mình chỉ
  thấy cấu trúc + chữ. **Sprint 2 (chờ duyệt)**: tích hợp model nhận diện vật thể.
- "Huấn luyện biết TẤT CẢ các hình ảnh" = cần model thị giác lớn — không thể bằng OCR;
  OCR là bước nền đúng yêu cầu "tải về và cài đặt OCR".

## Kiểm chứng

- **82/82 pytest PASS** (7 test mới `test_tony_vision.py`: routing 6 câu khớp + 4 câu
  không nuốt nhầm, OCR thật ảnh tạo local, fallback nguồn ảnh, fail-honest, DB tmp).
- E2E production: intent đúng, ảnh 20:54 phân tích OK, knowledge ghi DB quarantined.
- Responder restart nạp code mới.

## Files

- MỚI: `src/quan_ai_brain/vision/__init__.py`, `src/quan_ai_brain/vision/image_analyzer.py`
- SỬA: `tools/netchat_command_center.py` (intent + handler + HANDLERS),
  `pyproject.toml` (optional-deps `vision`), `tests/test_tony_vision.py` (mới)
