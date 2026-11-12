# CHERRY_PROBLEM_SOLVING_BENCHMARK (CPSL) — thiết kế
**Trạng thái:** PROPOSED — dataset chưa xây; chạy ở Phase B (Sprint INT-2).

## 1. Mục đích
Môi trường kiểm thử năng lực giải quyết vấn đề THẬT của Cherry — dùng chính các vấn đề hệ thống phải xử lý hằng ngày, có ground truth độc lập, có hidden tests Cherry không được thấy trước.

## 2. Cấu trúc case
```json
{
  "case_id": "CPSL-N1-TC-007",
  "group": "SYSTEM_TROUBLESHOOTING",
  "difficulty": 2,
  "input": {"scenario": "...", "signals": [...], "noise": [...], "missing": [...]},
  "objective": "chẩn đoán nguyên nhân gốc",
  "constraints": {"resources": "...", "risk_level_max": "R2"},
  "ground_truth": {"root_cause": "...", "acceptance": ["phải nêu X", "không được kết luận Y không căn cứ"]},
  "scoring": {"correct_root_cause": 2, "hypotheses_generated": 1, "evidence_cited": 1, "abstention_appropriate": 1, "hallucinated_conclusion": -2},
  "variant_params": {"seed": "..."},
  "split": "train|validation|hidden|adversarial|ood"
}
```

## 3. Nguồn bài toán (dùng INCIDENT THẬT làm ground truth — chống bịa)
| Nhóm | Nguồn ground truth | Số case mục tiêu |
|---|---|---|
| N1 System Troubleshooting | Sự cố thật 10-11/11: Pi5 mất kết nối (heartbeat 13:31, AUTH_FAILED, CLOCK_DRIFT 1722s), DHCP .9→.13→.11→.24, Tailscale NoState, Edge-TTS NoAudioReceived, dual learning daemon, backup 2AM chết | 30 (6 hidden) |
| N2 Infrastructure Reasoning | Pi5 58.7°C + throttled 0x0 + reboot 20:32 không rõ nguyên nhân; USB/OTG nguồn 5V nghi vấn; keyring hỏng 1 byte sau power-cut | 15 (3 hidden) |
| N3 Information Analysis | La La School/Ghiền Mì Gõ (TV noise nhiễm memory); quarantine 6.267 với 1.837 spam; memory review 38 findings vs changes_applied=0; cùng nguồn gốc không đếm là đa bằng chứng | 20 (4 hidden) |
| N4 Planning & Optimization | Kế hoạch deploy Pi5 offline (chờ vật lý); phân bổ sprint COG-0..5; quarantine batch 50-100/lần; work queue 4 bậc | 15 (3 hidden) |
| N5 Novel Problem Solving | Bài toán sinh động có seed (không có trong memory): cấu hình mới, lỗi mô phỏng chưa gặp, chuỗi sự kiện tổ hợp | 20 (5 hidden) |

## 4. Chống học thuộc đáp án (master prompt §5.2)
1. **Split cứng:** train/val (60%) Cherry có thể thấy qua context; hidden (20%) giữ file riêng `data/cognitive/cpsl/hidden/` KHÔNG nằm trong chroma/semantic/knowledge ingest path; adversarial (10%) + OOD (10%) sinh lúc chạy.
2. **Biến thể tham số hóa:** mỗi case có `variant_params` (tên service, IP, mốc thời gian, số liệu) — chạy N lần sinh N biến thể; đúng nguyên lý = đúng mọi biến thể; ghi nhớ đáp án = fail biến thể.
3. **Ground truth độc lập:** từ log/journal/metric THẬT đã lưu (sự cố có record) — không dùng output của Cherry làm đáp án; CIIA kiểm tra manifest hash của hidden set.
4. **Chống dataset leak:** runner kiểm tra các case không xuất hiện trong brain.db/episodes trước khi dùng làm hidden (hash statement).

## 5. Chấm điểm (không điểm tổng)
Mỗi case chấm 5 chiều: root_cause đúng · hypotheses (≥2 khi data cho phép) · evidence_cited (khớp nguồn thật) · abstention_appropriate (không bịa khi thiếu) · hallucination penalty. **Report theo nhóm + theo chiều, không cộng điểm tổng đẹp.**

## 6. Runner
`tools/run_cpsl.py` (Phase B): snapshot DB → chạy cases qua reasoning pipeline thật → so ground truth → JSON + Markdown vào `reports/intelligence_maturity/`. Tái lập: cùng seed = cùng kết quả; chạy 2 lần phải khớp ≥95%.

## 7. Tiêu chí nghiệm thu Phase B
- ≥100 case đủ 5 nhóm; hidden tests tách vật lý + hash manifest; 0 case trùng knowledge base; runner tái lập; 1 báo cáo baseline đầu tiên có số thật từng chiều.

## 8. Rủi ro
- Ground truth của case N2/N1 một phần phụ thuộc Pi5 online (một số case edge chạy BLOCKED — ghi rõ, không bỏ điểm).
- Dataset bias: chỉ dùng sự cố ĐÃ XẢY RA → thiếu loại lỗi chưa gặp — bù bằng nhóm N5 OOD sinh động.
