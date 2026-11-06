# AUDIT & ĐỒNG NHẤT HỆ THỐNG — 1 TONY DUY NHẤT
**Ngày:** 06/11/2026 13:20 · **Workspace hiện hành:** E:\BRAIN (Cognitive Core V6/V7)
**Phạm vi:** Chỉ-đọc toàn bộ. Chưa xóa/sửa/migrate gì. Mọi bước thực thi chờ anh duyệt.

---

## 1. HIỆN TRẠNG 2 TONY (bằng chứng audit 3 luồng)

| | **TONY hiện hành** (E:\BRAIN) | **TONY cũ** (BRAIN_0 = TONY-AI, máy cũ chép sang) |
|---|---|---|
| Runtime | ✅ LIVE: 8765+8766 (PID 8956), responder, watchdog | ❌ Đã tự dừng 01:17 06/11 (log cuối /api/chat 200 lúc 01:02) |
| Bot NetChat | **bot_tony** — DM "TONY" (`mwp3nk…`) | "Tony Assistant" — DM `131u5z…` (bot id edojmne9…) |
| Tests | **3.609 pass / 34 skip / 0 FAIL** (EXIT 0) | 3.509 hàm test (211 file, 30 file nm1/nm2/nm3 chỉ có ở BRAIN_0) |
| Git | thequanhcm/quanpt1, master `2bcd8d8` | thequanhcm/TONY-AI, HEAD `843e8c5` nm3.5 (06/11 01:02) |
| DB brain.db | memories 2.403 · semantic 5.051 · candidate 8.553 | memories 2.636 · semantic 6.462 · candidate 9.509 |
| Hardcode máy cũ | Không (LOCALAPPDATA discovery, _NO_WIN) | Có (`C:\Users\quocd` cứng trong responder) |

**Kết luận code:** deps/AGENTS.md/Dockerfile/docker-compose **giống hệt nhau** — khác biệt 100% nằm ở src/tools/tests + data. E:\BRAIN là bản mới hơn về hạ tầng (UDC-1, SSH pi5, guard 1-instance). BRAIN_0 giàu hơn về **tính năng học** (nm1/nm2/nm3/nm3.5 + CCLE).

---

## 2. TÀI SẢN CODE CHỈ CÓ Ở BRAIN_0 (đề xuất port theo lô)

| Ưu tiên | Lô | Nội dung | Quy mô |
|---|---|---|---|
| P1 | NM2.5/2.6+NM2 | chat_guard, evidence_gate (mọi claim phải có citation), metacognition RiskAwareRouter | ~483 dòng + tests |
| P2 | NM3.5+NM3 | chat_extractor (trích tri thức từ chat owner → pending proposals), Self-Learning V2 (ledger fail-loud, cap 20/ngày, apply chỉ owner quanpt1) | ~354 dòng + tests |
| P3 | CCLE S1–S6 | 6 module tái dựng ngữ cảnh + benchmark, 0-token chỉ-đọc | ~1.019 dòng |
| P4 | NM1 super-memory | semantic_index, hybrid_retriever, graph_service, temporal_query (parse "hôm qua"), chat_enrich, consolidation_runner, holdout, accuracy_gate, consolidation | ~1.437 dòng |
| — | KHÔNG port | netmind_bridge (kênh bot cũ), tools q4_*, migrate_new_pc | — |

**Không xung đột key API** — các module additive, web/server.py E:\BRAIN chưa có các route này.

---

## 3. DỮ LIỆU: PHÂN KỲ 2 CHIỀU (khác ID đủ, không sample)

- memories: 2.322 chung / **+314 chỉ BRAIN_0** / +81 chỉ E · episodes: 2.866 chung / **+294 chỉ BRAIN_0**
- semantic: +1.411 chỉ BRAIN_0 · knowledge_relations: **+585 chỉ BRAIN_0**
- candidate_knowledge: 4.619 chung (160 khác status!) / +4.890 BRAIN_0 / +3.934 E
- **29 memories trùng ID khác nội dung** → E làm canonical, bản BRAIN_0 dump vào `memories_b0_conflicts` chờ anh review
- **CẢNH BÁO: WAL 105,8MB > file chính 103,1MB** — copy brain.db không kèm -wal/-shm sẽ HỎNG (đã verify malformed). Phải wal_checkpoint trước khi copy.
- Encoding an toàn: 0 lỗi UTF-8, 2.634/2.636 memories tiếng Việt chuẩn.

### Kế hoạch migrate 4 giai đoạn (khi anh duyệt)
1. **Freeze + checkpoint**: dừng ghi BRAIN_0 (đã dừng tự nhiên 01:17), `PRAGMA wal_checkpoint(TRUNCATE)`, backup E:\BRAIN brain.db.
2. **Import thẳng** (superset, INSERT OR IGNORE): semantic +1.411, memories +314, episodes +294, relations +585, append-only audit/health/tasks (+1.276 rows).
3. **Quarantine** (cấm import thẳng): candidate_knowledge +4.890 vào bảng staging + conflict_log; archive dedup +3.117.
4. **Hậu merge**: ALTER TABLE memories ADD 3 cột temporal; rebuild semantic_index (bản cũ chỉ phủ 730/2636); đối soát memories 2.403+314=2.717, episodes 2.940+294=3.234.

---

## 4. FILE RÁC / LỖI (kết quả quét 06/11 13:15)

### E:\BRAIN (workspace hiện hành)
| Nhóm | Kích thước | Mức an toàn |
|---|---|---|
| `__pycache__` ×1.081 thư mục | 211,3 MB | An toàn xóa |
| `logs/khoi_dong_ollama.log` (Ollama ĐÃ GỠ — log mồ côi, ghi đến 01:17 06/11) | 35,5 MB | An toàn xóa |
| `NUL` + `src/data/edge_devices.db` (0 byte, junk tái sinh) | 0 B | An toàn xóa |
| backups cũ (giữ 5 bản mới nhất) | ~1,4 GB | Cần duyệt (dữ liệu) |
| logs cũ (giữ 7 ngày; giữ watchdog/responder) | ~70 MB | Cần duyệt |
| chroma runtime 2 file (~55 MB) | — | KHÔNG đụng (runtime) |

### BRAIN_0 (7,90 GB tổng)
| Nhóm | Kích thước | Ghi chú |
|---|---|---|
| backups/ | 3,38 GB | Backups của máy cũ — archive, không cần trên máy này |
| .venv | 0,70 GB | Venv máy cũ (C:\Users\quocd hardcode) — dùng được nhưng dư |
| .git | 0,34 GB | Repo riêng TONY-AI — GIỮ (history nm3.5) |
| logs/ | 158,7 MB | Đã dừng 01:17 |
| reports + bao_cao | 373 MB | Báo cáo cũ |

---

## 5. HẠ TẦNG 24/7 — ĐIỂM NGHẼN ĐÃ XÁC MINH

### 🔴 Nghiêm trọng: PC tự ngủ sau 10 phút idle (AC power)
- Bằng chứng: `powercfg` AC=0x258 (600s) · Event Log: ngủ 01:40 đêm 05/11 (sau 2AM) → **backup 2AM hôm nay MISS lần 2** (backup mới nhất 29,5h tuổi; task Last Run 05/11 07:33 = catch-up lần trước).
- Resume gần nhất 12:43 hôm nay = lúc anh mở máy. Tức là **đêm qua TONY "chết" từ 01:40 → 12:43** — không responder, không health, không backup.
- Đây là **root cause của mọi miss 2AM** (không phải bug task). Dell Precision 7550 (laptop, PCSystemType=2) — ngủ cả khi cắm điện.
- **Sửa đề xuất (chọn 1):**
  - (a) `powercfg /change standby-timeout-ac 0` — không ngủ khi cắm điện (khuyến nghị cho 24/7; DC pin giữ nguyên 240s);
  - (b) Wake timer cho task backup + StartWhenAvailable (đã có) — nhưng phụ thuộc BIOS/UEFI support.
- **Điểm sáng:** uptime 3,05 ngày; 3 task scheduler sống đều Result=0, NextRun đúng; watchdog 5 restarts/h sẵn sàng; stack E:\BRAIN tự hồi phục sau kill.

### 🟡 learning_daemon: 2 instance giành lock brain.db (log BRAIN_0 01:15)
- BRAIN_0 bị 2 instance learning giành port 8771 + lock DB. Trên E:\BRAIN cần verify đảm bảo 1 instance (check guard).

### 🟡 Alert "embedding OFFLINE ~6s" còn bắn (health_alerts)
- Ollama đã gỡ → embedding bị tắt → hệ thống còn fail-open, bắn alert lặp. Sau khi ổn định: xem xét v embedding sang BGE-M3 (đã có ở BRAIN_0 nm1.1a) hoặc chấp nhận offline.

---

## 6. KẾ HOẠCH ĐỒNG NHẤT (đề xuất — chờ anh duyệt từng bước)

### GIAI ĐOẠN A — Dọn rác an toàn (không đụng dữ liệu) — **A.1 ĐÃ LÀM 06/11 13:30**
> **Đã thực thi + verify:** xóa 1.081 thư mục `__pycache__` (211,3 MB), `.pytest_cache`, `logs/khoi_dong_ollama.log` (35,5 MB), `src/data/edge_devices.db` (0 B). `NUL` xác minh KHÔNG tồn tại thật (magic-name false positive của `cmd if exist`; listdir + .NET đều 0 file). Logs/ 141,2→105,7 MB. Smoke test taxonomy **36/36 PASS** sau dọn. `.gitignore` +`BRAIN_0/`, artifact tạm. Git status sạch (chỉ chroma runtime + plan file mới).
> **Chờ duyệt tiếp:** 19 log cũ >7 ngày (1,9 MB) · 16 backup cũ (1,33 GB — giữ 5 mới nhất).
1. Xóa `__pycache__` (211MB), `.pytest_cache`, NUL, edge_devices.db junk, khoi_dong_ollama.log (35MB).
2. Bổ sung `.gitignore`: `BRAIN_0/`, `__pycache__/`, `logs/*.log`, chroma runtime.
3. Xóa ollama references trong KHOI_DONG_24_7.bat (Ollama đã gỡ — script mồ côi).

### GIAI ĐOẠN B — Sửa nền tảng 24/7 (laptop không ngủ khi cắm điện)
- Chạy `powercfg /change standby-timeout-ac 0` (sau khi anh OK).
- Re-run backup task → xác minh catch-up; theo dõi 2AM đêm nay.

### GIAI ĐOẠN C — Migration dữ liệu (4 giai đoạn §3) — điểm chờ duyệt riêng
- Sau khi Phase B ổn: freeze → checkpoint → import thẳng → quarantine → rebuild → đối soát số học.

### GIAI ĐOẠN D — Port code theo lô P1→P4 (mỗi lô = sprint có test, quarantine trước khi apply)
- P1 chat_guard+evidence_gate → P2 chat_extractor+Self-Learning V2 → P3 CCLE → P4 NM1 stack.
- Mỗi lô: copy file → chạy test BRAIN_0 tương ứng (30 file nm/CCLE tests) → full regression ≥3.609 → PR riêng.

### GIAI ĐOẠN E — Vệ sinh bot cũ (sau khi C+D ổn)
1. Kill orphan learning_daemon BRAIN_0 (nếu còn); verify 1 responder duy nhất.
2. Archive TONY_START/STOP.bat + trợ lý số → 1 thư mục `BRAIN_0_archive/` (hoặc để nguyên BRAIN_0 không đụng, chỉ thêm .gitignore).
3. Anh gỡ bot "Tony Assistant" khỏi NetChat (tài khoản NetChat owner mới gỡ được bot — em không có quyền).
4. Xác minh cuối: netstat 8765/8766 1 PID duy nhất · DM "trạng thái" vào bot_tony OK · 3 task Result=0 · logs ghi liên tục qua đêm.

---

## 7. KHÔNG LÀM (bất biến)
- KHÔNG xóa/sửa BRAIN_0 trong sprint này (chỉ .gitignore khi anh duyệt).
- KHÔNG đụng chroma runtime, `.env`, SSH keys, secrets.
- KHÔNG bật production executor/daemon mới; KHÔNG tự commit/push khi chưa ra lệnh.
- KHÔNG import candidate_knowledge thẳng (chỉ staging + conflict_log).
- KHÔNG coi test PASS = hệ thống LIVE — mọi tuyên bố LIVE phải có bằng chứng runtime.
