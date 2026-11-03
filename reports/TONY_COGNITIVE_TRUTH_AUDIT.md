# TONY_COGNITIVE_TRUTH_AUDIT.md

**Kiểm toán trí tuệ theo mệnh lệnh UAME v1.0 (Phần A–H) — 02/11/2026, máy QUANPT, workspace E:\BRAIN**
**Phương pháp**: toàn bộ số liệu lấy trực tiếp bằng tool (SQL, socket probe, HTTP, filesystem) trong phiên này. Không dùng báo cáo cũ làm bằng chứng mặc định. Mọi mục "chưa làm được" ghi thẳng.

---

## 1. Kiến trúc Cognitive Core hiện tại (H1 — ĐẠT)

Bộ não là **package `src/quan_ai_brain/` (37 package con)**, điểm tập trung là `src/quan_ai_brain/web/server.py` (6.019 dòng) — phục vụ chat console 8765 + core API 8766. Luồng xử lý đã xác minh bằng code + log:

```
USER INPUT (chat console 8765 / DM NetChat bot_tony)
→ detect_intent + lệnh hệ thống (tools/netchat_command_center.py: phát nguyên văn, chống GLM paraphrase)
→ /api/chat (web/server.py:1588) — LLMRouter (web/server.py:154)
→ Memory retrieval: CognitiveRetriever (cognition/retrieval.py) — keyword + BGE-M3 hybrid khi embedding online
→ Reasoning: model theo routing (xem mục 2)
→ Tool/Action: code-path trong server (kiosk probe, edge control, watchdog DM) — KHÔNG qua ToolRegistry
→ Result verification: E2E tests + regression 3.442 + watcher SEC/FED cycles
→ Response → memory consolidation: episodes + memories + candidate_knowledge pipeline
```

**Thành phần CHỈ TỒN TẠI TRÊN THIẾT KẾ (chưa đấu vào luồng chat thật)**: ToolRegistry (0 tool đăng ký — test thật `ToolRegistry().list_tools()` = []), IntegrationRegistry (0), QPIG (skeleton mới xây hôm nay, 6 tool đăng ký được vào registry nhưng chưa cắm vào server chat), QEP (chỉ có master prompt, chưa code).

## 2. Model đang sử dụng (H1 — ĐẠT, có bằng chứng metadata)

Phân tích **500 chat_turn gần nhất** trong `data/brain.db` (metadata_json.model_used):

| Model | Số lượt | Vai trò |
|---|---|---|
| **zai-org/GLM-5.3-Flash** (NetMind cloud) | 282 | Suy luận chính hiện tại |
| qwen2.5:1.5b / 0.5b / 7b (Ollama local) | 218 | Cũ hơn — Ollama giờ OFFLINE |
| (mock) | còn lại | fallback khi không có model |

- **Local hay cloud**: CẢ HAI — `LLMRouter` (llm/router.py) ưu tiên cloud GLM khi policy cho phép, fallback local, cuối cùng mock. **Ngày 02/11: Ollama đã bị gỡ** → port 11434 OFFLINE (socket probe thật) → embedding BGE-M3 fail, suy luận 100% phụ thuộc cloud GLM.
- **Model routing**: CÓ (LLMRouter + explicit model param từ responder).
- **Context management**: CÓ (bọc ngữ cảnh lượt trước, kênh voice M5 P1).
- **Quản lý trạng thái suy nghĩ / self-eval khi chat**: KHÔNG có module riêng — chỉ router chọn model + policy gate. Trung thực: đây là điểm yếu.
- **Chuyển nhiệm vụ sang agent khác**: CÓ một phần — delegate_task trong netMind runtime; trong codebase TONY chưa có orchestrator chat-level tự phân công.
- **Embedding model**: BGE-M3 qua Ollama local — **hiện KHÔNG hoạt động** (daemon offline).

## 3. Cơ chế suy luận (H4 — 29/30 bài test cơ học)

Kết quả `reports/uame_b2_reasoning_test.py` — đáp án neo trước, máy xác minh độc lập (SQL/socket/tính toán):

| Nhóm | Điểm |
|---|---|
| LOGIC | 5/5 |
| PHÂN TÍCH HỆ THỐNG | 4/5 (S4 sai: đếm nhầm số package) |
| KỸ THUẬT (tính toán) | 5/5 |
| DỮ LIỆU THIẾU | 5/5 (biết nói "thiếu gì" thay vì bịa) |
| PHÁT HIỆN THÔNG TIN SAI | 5/5 (bắt đúng 4 tuyên bố sai bằng dữ liệu thật) |
| LẬP KẾ HOẠCH | 5/5 |

**Ghi chú trung thực bắt buộc**: bộ verify do chính TONY viết → đây là *self-graded với mechanical checker*, KHÔNG phải kỳ thi độc lập. Quy trình ra quyết định có thể kiểm toán: dữ kiện đầu vào (SQL/probe thật) → giả thuyết → verify máy. Phân biệt BIẾT/SUY LUẬN/GIẢ ĐỊNH/CHƯA BIẾT được thể hiện ở nhóm THIẾU DỮ LIỆU 5/5.

## 4. Cơ chế Memory (H3 — ĐẠT bằng bài test thật)

Kiến trúc 3 tầng **đã xác minh bằng thực nghiệm**:

| Tầng | Thành phần | Bằng chứng phiên này |
|---|---|---|
| Short-term | Context window chat + bọc ngữ cảnh lượt trước | metadata chat có user_query/assistant_reply liền mạch |
| Long-term | `data/brain.db` — memories + episodes + semantic_memory | **Bài test marker**: ghi `UAME_AUDIT_ce1d9492` → đóng connection → connection mới → retrieve đúng marker ✓ |
| Verified | semantic_memory 5.051 rows (approved + regression=True) | Nhưng xem cảnh báo chất lượng mục 6 |

Pipeline học: candidate_knowledge (7.852: 3.209 promoted / 3.152 quarantined / 1.491 approved) → semantic_memory. Review system: memory_review_sessions + review_findings (76) + review_inferences (6) + owner_questions. **Retrieval cắm thật vào chat**: 199/200 chat gần nhất có used_memory_ids.

## 5. Kết quả kiểm toán vector/tri thức (A3)

`knowledge_units` = **150 rows** (đúng "150+ kiến thức"): 85 FACT + 60 QUESTION + 4 RULE + 1 OPINION.
- **Chất lượng nguồn: 0/150 thiếu nguồn, 0/150 thiếu bằng chứng** (source_refs + evidence_refs đầy đủ 100%).
- Trùng lặp: 20 nhóm theo 60 ký tự đầu (cần dedupe).
- Liên kết: 210 relations (173 RELATED_TO, 35 REFINES, 2 SUPERSEDES) — **93/210 (44%) is_speculative**.
- **LƯU Ý TRUNG THỰC**: đây là knowledge graph SQLite, KHÔNG phải vector embedding DB — vector thật (BGE-M3) đang offline, không còn chỗ nào lưu embedding bền vững. 5.051 semantic_memory là text đã duyệt, không phải vector.

## 6. Kết quả kiểm toán brain.db (A4)

Số liệu THẬT 02/11 (không phải 2.127 như dự kiến — DB đã tăng):

| Bảng | Rows | Vai trò |
|---|---|---|
| episodes | **2.889** | 2.775 chat_turn + 113 experience_lesson + 1 task |
| memories | 2.345 | EPISODIC 2.325 (2.142 OBSERVED + 113 UNVERIFIED + 70 VERIFIED), SEMANTIC 9, PREFERENCE 2, PROCEDURAL 2 |
| semantic_memory | 5.051 | 100% approved+regression=True |
| candidate_knowledge | 7.852 | pipeline học có quarantine |
| candidate_knowledge_archive | 110.962 | lịch sử pipeline |
| knowledge_units | 150 | knowledge graph |
| feedback | 792 | phản hồi owner |

- **Liên kết**: 2.775/2.889 episodes có session_id trong metadata + 100% có source_ref → liên kết phiên THẬT.
- **approved_by phân bổ (cảnh báo trung thực)**: Quanpt1 3.265 (64,6%), **continuous_learning_daemon 1.754 (34,7%)**, quick_learning 20, quanpt1 11, owner 1 → ~35% "đã duyệt" là daemon tự duyệt, không phải owner.
- **Truy xuất cũ**: retrieve "Pi5 mất kết nối federation" → trả đúng 3 episodes netchat/federation liên quan ✓ (bài test liên kết thật phiên này).

## 7. Những gì TONY đã học (A2 — phân loại trung thực)

| Loại | Nội dung | Bằng chứng |
|---|---|---|
| A. Nạp sẵn | Kiến thức nền GLM-5.3-Flash + system prompt + AGENTS.md + docs/ | Không phải "học" — là kiến thức nền tảng |
| B. Tra cứu | Retrieval keyword 5.051 semantic + 2.889 episodes (199/200 chat có dùng) | used_memory_ids |
| C. Tích lũy kinh nghiệm | 113 experience_lesson (lỗi taskkill → Stop-Process; lọc theo cmdline; subnet tự dò...) | episodes kind=experience_lesson |
| D. Học thêm có kiểm soát | 3.209 promoted / 3.152 quarantined qua candidate pipeline + review sessions | SQL GROUP BY status |

**Phân biệt bắt buộc (mục A2)**: TONY **KHÔNG hề re-train model** — không có Level 3 (Model Learning) nào. Lưu DB = Level 1 (Knowledge Acquisition); rút lesson từ nhiệm vụ = Level 2 (Experience Learning). Loading vector/knowledge vào DB **không phải huấn luyện mô hình**.

## 8. Những gì TONY thực sự nhớ / có thể suy luận / thực thi (H2/H3/H11)

- **Nhớ thật**: bài test marker qua phiên (connection mới) ✓; truy xuất theo chủ đề ✓; lesson 113 mục truy được.
- **Suy luận**: 29/30 mechanical (mục 3).
- **Thực thi thật**: dual server 8765/8766 LIVE; watchdog SEC+FED+SENTINEL cycles; DM 2 bước; 3.442-test regression nền; discovery 7 bước + profile 24 trường (34 test); containment 3 cấp + identity A–F + L0–L4 (38 test).

## 9. Những gì TONY CHƯA làm được (trung thực)

1. **Pi5 hai chiều (H6)**: Pi5 REACHABLE nhưng **mọi cổng đóng** (SSH 22, 8000, 5000, 1883, 47430 đều đóng — probe thật) → edge status DISCONNECTED, paired=false, 1 alert active. Chưa gửi/nhận lệnh vật lý thật.
2. **Kỳ thi agent hoàn chỉnh (E1–E6)**: router 192.168.1.1 toàn 401 (đúng ranh giới xác thực — không có credential không được đụng) → chỉ demo được ranh giới an ninh, chưa demo bài thi 6 bước với agent lạ.
3. **MCP/A2A adapter thật**: chưa có.
4. **Semantic retrieval**: embedding offline → chỉ còn keyword ranking (chất lượng giảm — chưa đo định lượng).
5. **Model routing tự tối ưu**: GLM hard-priority, chưa có score-based routing.

## 10. Chức năng CHỈ TỒN TẠI TRÊN THIẾT KẾ (mục 12 yêu cầu)

| Thành phần | Trạng thái thật |
|---|---|
| ToolRegistry | **Rỗng** (0 tool) — code-path chạy ngoài registry |
| IntegrationRegistry | Rỗng (0 integration) |
| QPIG 6 tool | Skeleton hôm nay — test 34/34 nhưng chưa cắm vào server chat |
| QEP | Chỉ master prompt UAME — chưa code |
| Voice/STT/TTS | voice/ 15 module — chưa audit trong phiên này (không tuyên bố) |
| 110.962 archive rows | Chỉ là lịch sử pipeline, không phải tri thức hoạt động |

## 11. Kiểm thử Pi5 (H6) — kết quả thật

- Ping REACHABLE; MAC 34-24-3e (chưa khớp OUI Pi).
- Cổng: **tất cả đóng** → không kết nối hai chiều được.
- Core edge API: state DISCONNECTED, paired=false, active_alert 1.
- **Kết luận trung thực: H6 CHƯA ĐẠT.** Chờ 1 bước vật lý của owner (`CORE_HOST=192.168.1.9 bash tony_pi5_all_in_one.sh` trên Pi).

## 12. Kết quả kết nối Agent (H7/H9) — bài thi E

- Router 192.168.1.1 (black-box, read-only): DETECT ✓, INTERFACE (:80/:443 mở, telnet đóng) ✓, **IDENTIFY = Not_Accessible (401 mọi endpoint)** — ranh giới xác thực được TONY tôn trọng đúng chuẩn SENTINEL; khuyến nghị whitelist "chỉ báo cáo".
- Agent thân quen (edge API 8766): giao tiếp 2 chiều ✓ qua DM + API thật.
- **Bài thi 6 bước với agent hoàn toàn lạ: CHƯA THỰC HIỆN ĐƯỢC** — cần owner chọn đối tượng + cấp quyền đọc (H7 tạm PARTIAL).

## 13. Giới hạn phần cứng & giao thức

- Quadro T1000 4GB: không đủ VRAM chạy model lớn local → phụ thuộc cloud GLM.
- Ollama gỡ → mất embedding + mất local fallback (single point of failure cloud).
- Pi5: SSH đóng, không thể deploy QPIG body runtime.
- Giao thức sẵn sàng: HTTP API nội bộ, DM NetChat; thiếu MCP/A2A/MQTT/serial thực chiến.

## 14. Lỗ hổng kiến trúc phát hiện

1. **ToolRegistry rỗng nhưng tool chạy thật ngoài registry** → không có gate R-level thống nhất cho tool chat đang dùng. (UAME-S5 phải ép mọi tool qua registry.)
2. **~35% semantic_memory do daemon tự duyệt** → "approved" không đồng nghĩa owner-phê-duyệt; cần gắn nhãn nguồn duyệt rõ ràng.
3. **Single point of failure cloud** — Ollama gỡ, không fallback local; mất Internet = mất suy luận.
4. **Embedding timeout 6s/query** khi Ollama offline — mỗi retrieval chờ chết 3 lần TCP timeout; cần circuit breaker ngắn.
5. **20 nhóm trùng lặp knowledge_units + 44% relations speculative** — cần dedupe + review speculative.
6. **QPIG/QEP chưa đấu vào luồng chat** — kiến trúc mới đứng ngoài server 8765 thật.

## 15. Kế hoạch nâng cấp (thứ tự ưu tiên)

1. **UAME-S5 (GĐ A master prompt)**: QEP core + ép tool qua ToolRegistry + mock body — giải quyết lỗ hổng 1+6.
2. **Circuit breaker embedding** (30ms thay vì 6s) + nhãn "daemon-approved" cho semantic_memory — giải quyết 2+4.
3. **Pi5 SSH mở (owner)** → QPIG body thật (GĐ B) — H6.
4. **MCP client thật** (GĐ C) → bài thi agent lạ hoàn chỉnh (H7/H9/H10).
5. **Learning Engine tự động** (GĐ D) + 200 kịch bản.

## 16. Bộ tiêu chuẩn nghiệm thu (H1–H13)

| Tiêu chuẩn | Trạng thái | Bằng chứng |
|---|---|---|
| H1 Cognitive Core | ✅ ĐẠT | web/server.py + LLMRouter + luồng 10 bước đã map |
| H2 Real Learning | ✅ ĐẠT (Level 1+2) | pipeline candidate 3.209 promoted + 113 lessons; KHÔNG có Level 3 (trung thực) |
| H3 Real Memory | ✅ ĐẠT | marker test qua phiên ✓ + 199/200 chat dùng memory |
| H4 Reasoning | ✅ ĐẠT 29/30 | mechanical test — self-graded (ghi rõ hạn chế) |
| H5 Self-aware capability | ✅ ĐẠT | mục 9-10 liệt kê thẳng cái chưa làm được |
| H6 Pi5 Interaction | ❌ CHƯA ĐẠT | mọi cổng Pi5 đóng |
| H7 Agent Discovery | ⚠️ PARTIAL | framework 7 bước + profile ✓; agent lạ thật chưa thi |
| H8 Internal Understanding | ⚠️ PARTIAL | đọc được codebase mình (audit này là bằng chứng); agent ngoài chưa |
| H9 Universal Communication | ⚠️ PARTIAL | HTTP + DM ✓; MCP/A2A chưa |
| H10 Adaptation | ⚠️ PARTIAL | QPIG skeleton đăng ký được; adapter sandbox chưa |
| H11 Memory Reuse | ✅ ĐẠT | truy xuất lesson + episode liên quan chủ đề ✓ |
| H12 Security | ✅ ĐẠT | router 401 không đụng; SENTINEL active; R-gate nguyên vẹn |
| H13 Result Verification | ✅ ĐẠT | mọi tuyên bố trong báo cáo này gắn bằng chứng phiên |

**Tổng: 7 ĐẠT / 5 PARTIAL / 1 CHƯA ĐẠT** — điểm Agent Intelligence Scorecard cập nhật theo: 60/100 → giữ nguyên (chưa có bằng chứng mới promote).

## 17. Kết luận một câu

TONY có trí nhớ dài hạn thật, pipeline học có kiểm soát thật, suy luận 29/30, và trung thực nhận diện giới hạn — nhưng **chưa có cơ thể (Pi5 đóng cửa), chưa có tool registry thống nhất (rỗng), và chưa thi với agent lạ** — ba việc này chính là 3 sprint kế tiếp đã có sẵn kế hoạch (UAME-S5/S6/S7).

---
*Báo cáo kỹ thuật chi tiết kèm theo: `BAO_CAO_kiem_toan_tri_tue_uame_*.md` trong thư mục tiến độ. Validate nền đang chạy: `reports/UAME_VALIDATE_AUDIT.txt`.*
