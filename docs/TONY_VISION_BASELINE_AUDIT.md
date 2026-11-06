# TONY_VISION_BASELINE_AUDIT.md — Sprint 0 TVI (06/11/2026)

> MASTER PROMPT V10.0 — TONY VISION INTELLIGENCE (TVI) · Sprint 0: BASELINE AUDIT
> Phạm vi: CHỈ ĐỌC + báo cáo (đúng §XV "Không sửa code trước khi hoàn thành audit").
> Audit thật bằng công cụ trên E:\BRAIN ngày 06/11/2026 — không phỏng đoán.

## 1. Bản đồ năng lực hiện có (9 hạng mục §XV)

| # | Hạng mục | Hiện trạng | Đánh giá | Evidence |
|---|---|---|---|---|
| 1 | **Image Intake** | DM: `extract_message_files` (tools/netchat_auto_responder.py, tải file_ids→data/netchat_files, tự OCR ảnh); Pi5: `pi_media_capture` (edge_client) → `logs/pi5_media` (48 ảnh); Dashboard: 6 route `/api/executive/edge/camera/*` | **PARTIAL** — DM + Pi5 LIVE; THIẾU Image ID/metadata chuẩn, quality check, webcam/IP-cam, PDF→ảnh, intake API cho Agent khác, retention/cleanup | grep + file reads 06/11 |
| 2 | **OCR** | Tesseract 5.4.0 (eng+vie+osd) + pytesseract 0.3.13 (cài 06/11); 2 đường: `knowledge_ingestion` V41.3 (file→tri thức) + `vision/image_analyzer` (DM "phân tích ảnh", LIVE E2E ảnh 20:54) | **PARTIAL ~20%** — chỉ `image_to_string`: KHÔNG tọa độ/bbox/confidence (§3.3 bắt buộc), KHÔNG preprocessing (deskew/denoise/enhance), KHÔNG số liệu kỹ thuật/bảng/xoay 90–270, thiếu tessdata Trung/Nhật | `tesseract --list-langs`; pytest 82/82 |
| 3 | **Vision Model / Object Recognition** | KHÔNG CÓ engine nào (không YOLO/CLIP/OpenCV). Nền sẵn: numpy 2.4.6 + onnxruntime 1.31.1 + Pillow 13; GPU Quadro T1000 4GB (đang 0 MiB) | **MISSING** — nhưng nền ONNX+GPU đủ chạy model nhỏ quantized local | pip list; nvidia-smi |
| 4 | **Multimodal / VLM** | KHÔNG — LLM router text-only (NetMind Cloud GLM/Qwen text); server.py 74 ref "image" đều là camera routes, không VLM | **MISSING** | grep server.py |
| 5 | **DM Attachment Handler** | CÓ + LIVE: file_ids → tải → ảnh tự OCR + kind_note "trả lời dựa trên OCR"; local_paths vào payload cho lệnh hiển thị/phân tích | **IMPLEMENTED** (mức OCR-only) | extract_message_files 4.4KB |
| 6 | **File Storage** | `data/netchat_files` (DM) + `logs/pi5_media` (captures Pi5) + `data/edge_media/captures` (legacy) | **PARTIAL** — KHÔNG retention policy (dung lượng + privacy §XIII) | os.listdir |
| 7 | **Memory tích hợp** | Tri thức ảnh → `candidate_knowledge` status=**quarantined** (row `364566f4…` thật) — đúng pattern learning≠deployment; ChromaDB + BGE text-embedding — KHÔNG image embedding | **IMPLEMENTED (cách ly)** / image-embedding MISSING | sqlite query 06/11 |
| 8 | **MCP** | KHÔNG CÓ (khớp GAP V9.0: MCP MISSING) | **MISSING** | os.walk "mcp" rỗng |
| 9 | **Pi5 Camera Integration** | CÓ + LIVE: camera_on/off/snapshot/stream (warm-up 6–8s đã verify 06/11), photo/video/audio qua `pi_media_capture` | **IMPLEMENTED + LIVE_VERIFIED** | healthcheck FULL_HEALTHCHECK_20261106 |

**Governance/kiểm soát (§XIII):** approval_service + approval_verifier + csef_release + policy + permission_resolver + audit log CÓ ĐỦ. Không có file tên "SENTINEL" — vai trò tương đương do governance/policy + audit + estop đảm nhận (ghi chú trung thực, không giả định đổi tên).

## 2. Khoảng cách so với V10.0 (xếp theo mức độ)

| Khoảng cách | §V10.0 | Mức |
|---|---|---|
| Object/Scene/VLM hoàn toàn chưa có (không nhìn được vật thể) | IV, V, VI | **LỚN NHẤT** |
| OCR thiếu tọa độ, số liệu kỹ thuật, preprocessing, bảng | III | LỚN |
| Không auto-phân tích 7 mục khi owner gửi ảnh không chữ (hiện chỉ OCR→AI trả lời tự do) | XI | LỚN |
| Multi-image / so sánh / khác biệt | VIII | CHƯA CÓ |
| Skill Library + benchmark + ground truth + học từ feedback | IX, XIV | CHƯA CÓ |
| Confidence từ engine (OCR có conf; vision facts chưa có scale chuẩn) | X | MỘT PHẦN |
| Retention/xóa dữ liệu ảnh, chống prompt-injection từ OCR (ảnh là DỮ LIỆU không phải chỉ thị) | XIII | THIẾU |

## 3. Điểm mạnh nền tảng (tận dụng, không viết lại)

1. **onnxruntime + GPU 4GB trống** → YOLO-nano/RT-DETR-nano/CLIP quantized chạy local offline khả thi (benchmark Sprint 3).
2. **candidate_knowledge quarantine + approval governance** → đúng khung PROPOSE→TEST→BENCHMARK→REVIEW→APPROVAL→DEPLOY của §IX.3.
3. **Camera Pi5 LIVE + DM pipeline** → intake nền tốt, chỉ cần bổ sung lớp metadata/validation.
4. **Vision module Sprint 1 cũ (06/11)**: OCR vie+eng + facts đo được + tri thức cách ly — sẽ nâng cấp thành Sprint 2 (không bỏ).

## 4. Engine evaluation ban đầu (§XII — lý thuyết, CHƯA benchmark)

| Nhóm | Ứng viên | Ghi chú |
|---|---|---|
| OCR | Tesseract (có) → **PaddleOCR** (vie tốt, bbox sẵn) | PaddleOCR heavy; benchmark cả 2 ở Sprint 2 |
| Object detection | **YOLOv8n/RT-DETR-nano ONNX** local GPU 4GB | cần benchmark mAP/latency thật |
| VLM | Qwen2-VL-2B quantized local (nếu RAM/GPU đủ) hoặc không dùng VLM | benchmark riêng;Cloud bị cấm theo policy trừ khi duyệt |
| Embedding ảnh | CLIP-ViT-B/32 ONNX (image retrieval) | tie vào ChromaDB |

## 5. Kế hoạch Sprint (map §XV — chờ duyệt từng sprint)

- **Sprint 1 — Universal Intake**: Image ID + metadata + validate (định dạng/kích thước/hỏng) + PDF→ảnh + retention + **auto-phân tích 7 mục §XI khi ảnh không kèm chữ** (trung thực theo engine hiện có).
- **Sprint 2 — OCR Intelligence**: `image_to_data` (bbox+conf), preprocessing (deskew/enhance/denoise/rotate), số liệu kỹ thuật + check chéo, bảng, tessdata mở rộng.
- **Sprint 3 — Object/Scene**: benchmark YOLO/RT-DETR/CLIP ONNX trên GPU thật; candidate skill sandbox.
- **Sprint 4 — Technical Vision**: tủ điện/ắc quy/UPS = object+bbox+OCR kết hợp; VLM nhỏ nếu benchmark đạt.
- **Sprint 5/6 — Multi-image + Skill Library + học từ feedback** (lưu bản sai→sửa, phân tích nguyên nhân).
- **Sprint 7 — Pi5 camera E2E vào engine mới. Sprint 8 — Independent audit + TONY_VISION_BENCHMARK_REPORT.md với Ground Truth thật.**

## 6. Rủi ro & giới hạn (trung thực)

- GPU 4GB chỉ đủ model nhỏ; VLM lớn KHÔNG chạy local được — kỳ vọng "hiểu ảnh như chuyên gia" phụ thuộc model nào được duyệt.
- Nhận dạng chủng loại/model thiết bị VN (aptomát, ắc quy local brand) cần dataset riêng — zero-shot sẽ có điểm thấp, phải báo đúng.
- OCR ảnh nghiêng/mờ/chữ nhỏ chưa có preprocessing → độ chính xác chưa đo (Sprint 2 đo).
- Prompt injection qua OCR: hiện OCR text được đưa thẳng vào prompt AI — **cần hàng rào "ảnh = dữ liệu"** ở Sprint 1 ( SENTINEL/governance review).

## 7. Cần chủ sở hữu quyết định

1. **Duyệt Sprint 1** (Intake + auto-analyze 7 mục) — làm ngay khi có lệnh.
2. **Engine OCR tiếp theo**: benchmark PaddleOCR vs Tesseract (tải ~vài trăm MB) — cho phép tải?
3. **Sprint 3 model**: cho phép tải YOLO/CLIP ONNX (~50–300MB) về chạy local?
4. **VLM**: chấp nhận chạy local nhỏ (Qwen2-VL-2B quantized, ~2GB) hay bỏ VLM khỏi phạm vi?
5. **Cloud policy**: tuyệt đối local (§XIII) hay cho phép VLM cloud khi ảnh nhạy cảm thấp?
