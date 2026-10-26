# DIGITAL EMPLOYEE BRAIN — BÁO CÁO TEST (Sprint A)

**Mã tài liệu:** TEST-QAB-DEB-A-20261026
**Ngày chạy:** 2026-10-26 23:xx ICT
**Môi trường:** Windows 10, Python venv project, CPU/GPU Quadro T1000 (GPU không dùng cho test), KHÔNG có gateway thật trong test (mock hết theo ràng buộc Sprint 0).

---

## 1. Kết quả full regression

```
Lệnh: ./.venv/Scripts/python.exe -m pytest -q tests --tb=no -p no:cacheprovider
Kết quả: 1 failed, 546 passed, 2 skipped in 164.14s (0:02:44)
Collected: 549
```

Phân loại theo chuẩn Master Prompt Bước 5:

| Kết quả | Số lượng | Phân loại |
|---|---|---|
| PASS | 546 | — |
| FAIL | 1 | **FAIL do môi trường** (không phải code) |
| SKIPPED | 2 | 1 do môi trường (Ollama offline), 1 do phần cứng (Pi 5) |
| UNVERIFIED | 0 | — |

## 2. Chi tiết FAIL/SKIP — nguyên nhân gốc đã probe

| Test | Lỗi | Nguyên nhân gốc (bằng chứng độc lập) | Sprint xử lý |
|---|---|---|---|
| `tests/test_autonomous_mind.py::test_keep_warm_pulse` | `assert False is ...` | Ollama daemon OFFLINE — probe trực tiếp `http://127.0.0.1:11434/api/tags` → URLError (đo 2026-10-26 23:xx). Test này assert keep-warm pulse thành công lên daemon thật → đúng hành vi, môi trường thiếu daemon | A3 (hướng dẫn owner bật Ollama autostart) |
| `tests/test_bge_m3_embedding.py:172` | skip | Cùng nguyên nhân: Ollama offline | A3 |
| `tests/test_vietnamese_tts.py:263` | skip | Pi 5 phần cứng không trong mạng phiên test (probe :8768 → URLError) | Khi Pi 5 nối lại mạng |

**Kết luận:** 0 lỗi code mới. Không sửa test để che lỗi implementation (tuân thủ Master Prompt Phần 10 Bước 5).

## 3. So sánh baseline

| Lần | Ngày | Kết quả | Chênh lệch |
|---|---|---|---|
| Báo cáo DC | 2026-10-26 (sáng) | 546 passed, 1 failed, 2 skipped, 175.31s | — |
| Lần này | 2026-10-26 (đêm) | 546 passed, 1 failed, 2 skipped, 164.14s | **0 lệch pass/fail**; thời gian nhanh hơn ~11s (máy nhàn hơn) |

→ Không regression sau batch DC Skill/ (10/10 items đã duyệt) + cập nhật báo cáo (commit 4bdd774).

## 4. Kiểm thử an toàn (đã xác minh trong audit, chứng minh bằng code/probe)

| Kịch bản Master Prompt Phần 8 | Bằng chứng hiện có |
|---|---|
| R5 luôn bị chặn | `governance/policy.py:51-52` — hard-block, return BLOCKED, không override (đã đọc code) |
| Provider offline | `tests/test_netmind_provider.py` 18 tests — fail-closed, TIMEOUT tách riêng, không fallback âm thầm |
| Phê duyệt 1 lần / chống replay | governance.db có bảng `consumed_nonces` (schema có sẵn, test sprint 5/6) |
| Audit trail | logs/audit.jsonl 502 dòng thật, format {timestamp_utc, event_type, details} |
| Sandbox consent | audit có event `sandbox.consent_required` → `sandbox.execution_succeeded` sau duyệt |
| Prompt injection | guardrails + PathGuard chặn path escape (tests hiện hữu) |

## 5. Khoảng trống test phải bổ sung (theo Master Prompt Phần 8 — lên lịch Sprint B–F)

| # | Test bắt buộc còn thiếu | Sprint |
|---|---|---|
| 1 | Ollama offline → hệ thống suy giảm an toàn (DEGRADED, không crash) | B |
| 2 | NetChat mất kết nối → hàng đợi approval không mất, retry có giới hạn | B/F |
| 3 | Dữ liệu đầu vào sai/mâu thuẫn → kết luận gắn cờ confidence thấp | C/E |
| 4 | Prompt injection từ log/tài liệu → không thực thi chỉ thị trong nội dung | B |
| 5 | Candidate tri thức sai nhưng hợp lý → không lên semantic không duyệt | D |
| 6 | LLM đề xuất hành động trái policy → PolicyEngine chặn độc lập với model | B/F |
| 7 | Approval hết hạn / replay → bị từ chối | F |
| 8 | Grant hết hạn/thu hồi → hành động dừng ngay | G |
| 9 | Database lỗi → transaction an toàn, không hỏng ledger | B |
| 10 | Process restart giữa nhiệm vụ → khôi phục checkpoint đúng | B |
| 11 | Rollback thất bại → cảnh báo + DEGRADED, không giả vờ thành công | F |
| 12 | Tự báo HEALTHY nhưng dịch vụ thật chết → probe thật phát hiện | A/C (self-model verify) |

## 6. Kết luận

1. Suite 546 pass ổn định hai lần đo liên tiếp trong ngày — nền đủ tin để phát triển Sprint B.
2. 1 fail + 2 skip đều có nguyên nhân môi trường/phần cứng xác minh bằng probe độc lập, có chủ xử lý (Sprint A3, Pi 5 reconnect).
3. 12 kịch bản test an toàn bắt buộc chưa đủ — đã vào kế hoạch từng sprint, không bỏ sót.
4. Chưa đo benchmark hiệu chuẩn confidence — cấm dùng confidence LLM để tự thực thi cho đến khi có (Sprint E5).

**Người xác nhận:** QUAN AI BRAIN — evidence lưu tại logs/audit.jsonl, pytest output tại phiên 2026-10-26.
