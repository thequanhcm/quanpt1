# M1 — PC HEALTH REPORT (DESKTOP-SNMI929)

**Người lập:** TONY · **Thời điểm đo:** 01/11/2026 09:35–11:05 giờ VN
**Nguồn:** `pc_collector.py` (psutil 7.2.2) — đọc-only, đo thật qua `/api/health/machine`

## Snapshot đặc trưng (đo thật)

| Chỉ số | Giá trị | Ngưỡng WARN/CRIT | Trạng thái |
|---|---|---|---|
| CPU % | 7,0 | 85 / 97 | ✅ NORMAL |
| RAM % | 59,1 (6.571MB free / 16GB) | 85 / 95 | ✅ NORMAL |
| Dĩa D: dùng % | 33,7 (155,5GB free / 234,4GB) | 85 / 95 | ✅ NORMAL |
| Server RSS | 32–350MB (pythonw dual servers) | 1200 / 2000 MB | ✅ NORMAL |
| Process Python | 14–16 (server + responder + learning + watchdog + hermes) | quan sát | ✅ |
| Uptime PC | 31,9 giờ | — | ✅ |

## Services PC (service_collector)

| Service | Kiểm tra | Kết quả |
|---|---|---|
| Executive Server 8766 | HTTP GET /api/health | ✅ up (HEALTHY) |
| Dashboard 8765 | HTTP GET /api/health | ✅ up (HEALTHY) |
| NetChat responder | heartbeat log mtime | ✅ 8,4s tuổi (stale nếu >150s) |
| Learning daemon | learning_daemon.py.log mtime | ⚠️ thỉnh thoảng 150–230s (cycle ingest dài) — chưa phải treo |

## Voice PC (voice_collector)

| Thành phần | Kết quả |
|---|---|
| STT faster-whisper | ✅ import ok (v1.2.1) |
| LLM NetMind (GLM-5.3-Flash) | ✅ READY (server thật có key trong env; môi trường không key → DISABLED_BY_POLICY = đúng policy, không phải lỗi) |
| Ollama 11434 | ✅ online (8 models) |
| TTS Edge-TTS | ✅ import ok + TTS manager cấu hình |

## Nhận định

1. PC bộ não đang khỏe: không nghẽn CPU/RAM/disk; server RAM thấp.
2. 16 python process là bình thường (4 service TONY + kernel tool + editor...).
3. Điểm cần theo dõi duy nhất: learning daemon log-age — đề xuất xem log nếu vượt 600s (đã đặt ngưỡng CRITICAL tại đó).
