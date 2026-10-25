# QUAN AI BRAIN — SPRINT 1: GLM-5.3 NETMIND PROVIDER INTEGRATION

**Mã tài liệu:** `RPT-QAB-GLM53-SPRINT1-V1`
**Ngày:** 2026-10-25
**Chủ sở hữu phê duyệt:** Anh Quân — `Quanpt1` (đã duyệt D1–D7 ngày 2026-10-25)
**Workspace:** `E:\AI\QUAN AI BRAIN`
**Phạm vi được duyệt:** Sprint 0 audit + D1–D7. Không mở rộng phạm vi.

---

## 1. Baseline
- Sprint 0 audit (`reports/QUAN_AI_BRAIN_SPRINT0_ARCHITECTURE_AUDIT.md`): 484 passed / 1 skipped / 0 failed; Ollama online; GPU 4GB (partial offload 7B); NetMind catalog xác minh; GLM-5.3-Flash chat smoke 0.52s.
- Working tree đã neo tại commit `4d90465` trước khi sửa mã (D7).

## 2. Kiến trúc cũ
- `LLMRouter` (heuristic fast/reasoning) → `LLMProvider` facade → `OllamaClient` (local-only, chặn host ngoài) / `MockLLMProvider` (mock có nhãn). Không có bất kỳ đường cloud nào.

## 3. Kiến trúc mới
- Thêm `NetMindProvider` (cloud, fail-closed) gắn vào `LLMProvider` facade qua optional `netmind=`.
- Routing: model ID chính xác `zai-org/GLM-5.3-Flash` → NetMind; model khác → Ollama local như cũ. Fallback-to-mock vẫn do caller quyết định (`FallbackMode`), không bao giờ tự động.
- Qwen local giữ nguyên toàn bộ; không xóa, không đổi hành vi mặc định.

## 4. Các file đã thay đổi
**Mới:**
- `src/quan_ai_brain/llm/netmind_provider.py` — provider cloud fail-closed
- `tests/test_netmind_provider.py` — 18 test (mock HTTP, không đụng key thật)
- `tools/sprint1_reasoning_param_probe.py` — probe tham số reasoning gateway
- `tools/sprint1_benchmark_dataset.py` — bộ dữ liệu 28 prompts / 14 nhóm
- `tools/sprint1_benchmark_runner.py` — runner so sánh GLM vs Qwen
- `reports/SPRINT1_VIETNAMESE_BENCHMARK.json` — bằng chứng benchmark

**Sửa:**
- `src/quan_ai_brain/llm/models.py` — thêm `ProviderType.NETMIND`
- `src/quan_ai_brain/llm/__init__.py` — export NetMindProvider
- `src/quan_ai_brain/llm/provider.py` — routing NetMind trong generate() + health tổng hợp
- `src/quan_ai_brain/cli.py` — lệnh `netmind-health`, `netmind-ask`
- `src/quan_ai_brain/cognition/autonomous_mind.py` — keep-warm vật lý (D5)
- `tools/validate_and_report.py` — 3 trường trung thực (D4) + sửa dòng ma trận lỗi thời
- `tests/test_validate_and_report.py` — assert 3 trường mới
- `docs/PROJECT_STATUS.md` — milestone Sprint 1 (D1)
- `bao cao xay dung he thong/BAO_CAO_KIEN_TRUC_...md` — chú thích hiệu chỉnh §8.2 (D1)

## 5. Provider và model ID thực tế
- **Base URL:** `https://stream-netmind.viettel.vn/aigw/ai/v1`
- **Chat model duy nhất trong catalog:** `zai-org/GLM-5.3-Flash`
- `zai-org/GLM-5.3` (đầy đủ) và `zai-org/GLM-5.3-FlashX`: **KHÔNG có** trong catalog tài khoản → không dùng. Cả 3 tầng định tuyến đều dùng Flash theo quyết định D2 của chủ sở hữu; Qwen local giữ vai trò offline/riêng tư.

## 6. Cấu hình NetMind đã xác minh
| Biến | Ý nghĩa | Mặc định |
|---|---|---|
| `NETMIND_BASE_URL` | Gateway endpoint | URL đã xác minh |
| `NETMIND_API_KEY` (hoặc `HERMES_CUSTOM_NETMIND_API_KEY`) | Key, chỉ đọc từ env lúc gọi | Không có → `NO_API_KEY` |
| `NETMIND_EXTERNAL_DATA_ALLOWED` | Cổng dữ liệu ra ngoài — **fail-closed** | `false` → `NETMIND_DISABLED` |
| `NETMIND_TIMEOUT_SECONDS` | (qua `timeout` ctor) 1–300s | 30s |
| `NETMIND_MAX_RETRIES` | 0–3, backoff mũ có trần | 1 |
| `reasoning_effort="low"` | Tắt reasoning token (đã chứng minh 60→0) | `low` |

Key không bao giờ: hardcode, in, log, lưu file, nhận qua constructor. Test dùng fake key monkeypatch-scoped.

## 7. Kết quả benchmark trước/sau
Trước Sprint 1: chỉ có Qwen local. Sau Sprint 1 (cùng bộ 28 prompts tiếng Việt, cùng scorer — `reports/SPRINT1_VIETNAMESE_BENCHMARK.json`):

| Chỉ số | GLM-5.3-Flash (NetMind) | Qwen2.5:1.5b (local) |
|---|---|---|
| Clean pass (đúng, không vi phạm) | **28/28 (100%)** | 28/28 (100%) |
| Keyword accuracy | **88.5%** | 69.2% |
| Latency avg | **1.33s** | 1.76s |
| Latency p95 | **1.99s** | 3.48s |
| Tone tiếng Việt giữ nguyên | 100% | 100% |
| Câu rỗng / vi phạm forbidden / mock | 0 / 0 / 0 | 0 / 0 / 0 |

Kèm đo độc lập Sprint 0: 0.5B warm 0.68s (133–145 tok/s), 1.5B warm 0.68–8.8s, 7B cold 35.6s (6 tok/s), BGE-M3 warm 0.39–0.47s.

## 8. Chất lượng tiếng Việt
GLM-5.3-Flash trả lời tự nhiên, xưng hô đúng ("em"/"anh"), xử lý tốt cả câu rút gọn ("Tóm lại là sao?"), tự sửa yêu cầu ("à nhầm"), và **từ chối lịch sự** 2 yêu cầu vượt quyền (R5) theo đúng system prompt. Khác biệt chất lượng với Qwen 1.5B rõ nhất ở nhóm phân tích/nghiên cứu/lập kế hoạch.

## 9. Trí nhớ và RAG
Không thay đổi trong sprint này (giữ nguyên SessionMemoryManager, CognitiveRetriever, BGE-M3, quarantine). Ngân sách: Sprint 3.

## 10. Điều phối công việc
Không thay đổi trong sprint này. PlanOrchestrator ↔ DurableTaskRegistry đã được xác minh tích hợp sẵn từ Sprint 0 (76 tasks thật). Ngân sách: Sprint 4.

## 11. Kết quả test
- Bộ NetMind mới: **18/18 PASS** (`tests/test_netmind_provider.py` — mock HTTP, policy fail-closed, allow-list, retry, timeout, audit metadata-only, key không lưu instance)
- Full regression: **502 passed, 1 skipped, 0 failed — 72.47s**
- `git diff --check`: sạch (chỉ warning CRLF tồn tại từ trước)
- Handoff: `reports/HANDOFF_LATEST.md` sinh tự động, số liệu khớp test output

## 12. Đã xác minh trên PC
- Gateway thật: catalog + chat E2E + kiểm soát reasoning (2 probe + CLI E2E)
- Benchmark 2 model trên 28 prompts thật
- Keep-warm vật lý fast tier + BGE-M3 qua Ollama thật
- 502 test tự động xanh

## 13. Đã xác minh trên Pi
- **KHÔNG** — Pi 5 offline trong toàn bộ phiên. Test TTS hardware giữ trạng thái BLOCKED trung thực. Không có bất kỳ tuyên bố voice/edge nào được nâng cấp.

## 14. Phần mock hoặc chưa kiểm chứng
- 18 test NetMind dùng HTTP mock (đúng thiết kế — không gọi gateway thật trong unit test)
- Streaming chưa triển khai/xác minh (ngân sách Sprint 2)
- Tool/function calling chưa xác minh (Sprint 2)
- E2E voice trên phần cứng Pi 5: BLOCKED chờ thiết bị

## 15. Các lỗi còn lại
- Không có lỗi mở trong phạm vi sprint. (3 test fail trong quá trình phát triển đã được sửa gốc: thứ tự gate policy→key→model; tách TIMEOUT khỏi CONNECTION_ERROR; case model rỗng chuyển đúng tầng validate.)

## 16. Rủi ro
- **Cloud dependency:** GLM-5.3-Flash phụ thuộc gateway Viettel — đã có fail-closed + retry + structured errors; Qwen local là phương án offline.
- **Quên tắt policy:** `NETMIND_EXTERNAL_DATA_ALLOWED=true` đặt env vĩnh viễn sẽ mở đường dữ liệu ra ngoài — cần chủ sở hữu chủ động quyết định; mặc định của hệ thống vẫn là false.
- **Gateway đổi hành vi:** tham số `reasoning_effort` đã xác minh hôm nay; nếu gateway nâng cấp, probe `tools/sprint1_reasoning_param_probe.py` chạy lại được trong <1 phút.
- **VRAM 4GB:** chính sách D5 giảm rủi ro evict; 7B vẫn chậm khi cold (35.6s) — đã khuyến nghị fallback lên GLM khi cần reasoning tương tác.

## 17. Chi phí / giới hạn usage
- Gateway không trả thông tin giá/quotas trong `/models`. Benchmark dùng ~4K tokens tổng — không thấy rate-limit hay lỗi 429 trong phiên. Cần theo dõi hạn mức tài khoản ở lần dùng thực tế.

## 18. Rollback
- `git revert` commit Sprint 1 (đơn file, không migration DB). Provider chỉ hoạt động khi caller truyền `netmind=` hoặc gọi trực tiếp — không path mặc định nào bị thay đổi hành vi. Cắt env `NETMIND_EXTERNAL_DATA_ALLOWED` = tắt ngay lập tức mọi đường cloud.

## 19. Quyết định cần anh Quân phê duyệt tiếp theo
1. **Bật vĩnh viễn hay không** `NETMIND_EXTERNAL_DATA_ALLOWED=true` cho hệ thống thường trực (hiện chỉ bật theo phiên/test).
2. **Sprint 2** — Vietnamese Conversation Quality: streaming GLM → Web Chat/Cockpit/TTS, barge-in, hội thoại đa lượt, chuẩn hóa Persona theo §5.2, benchmark mở rộng có Pi khi hardware online.
3. Cấp model access cho `Qwen/Qwen3.5-122B-A10B-FP8` (đã có trong catalog) nếu muốn tier reasoning cloud mạnh hơn — cần chủ sở hữu quyết định trước khi thêm vào allow-list.

## 20. Sprint tiếp theo
**Sprint 2 — Vietnamese Conversation Quality** (theo lộ trình Master Prompt §XII), mở đầu bằng streaming endpoint và chuẩn hóa persona TONY PHAM.

---
*Agent Kiến trúc trưởng — mọi số liệu trong báo cáo này đều có bằng chứng runtime hoặc file JSON kèm theo trong `reports/`.*
