# BÁO CÁO KỸ THUẬT — audit_va_dong_nhat_1_tony

> Sinh tự động 06/11/2026 13:04:41 (giờ VN) theo chỉ thị owner 02/11/2026:
> báo cáo chi tiết sau MỖI tác vụ — có phân tích, đánh giá, định hướng, đề xuất.

## 1. TÓM TẮT ĐIỀU HÀNH
Audit 3 luong chi-doc BRAIN_0 vs E:BRAIN (code/data/ha-tang) HOAN TAT. Don rac phase A.1: xoa 1081 __pycache__ (211.3MB), khoi_dong_ollama.log (35.5MB, Ollama da go), junk 0-byte; logs 141->105.7MB; smoke taxonomy 36/36 PASS sau don; .gitignore them BRAIN_0/ + artifact tam. Root cause 24/7: PC ngu sau 600s idle (Dell 7550 laptop, AC power) -> miss backup 2AM lan 2 (backup moi nhat 29.5h tuoi) - de xuat powercfg standby-timeout-ac 0 CHO DUYET. Data phan ky 2 chieu: B0 co +314 memories/+294 episodes/+1411 semantic/+585 relations; 29 memories trung ID khac noi dung (E canonical); WAL 105MB > main 103MB - copy thieu wal/shm se HONG. Ke hoach hop nhat 5 giai doan A-E: reports/AUDIT_MERGE_BRAIN_0_PLAN.md

## 2. PHÂN TÍCH
- 2 TONY song song: bot_tony (E:BRAIN, 3609 tests, LIVE) vs Tony Assistant (BRAIN_0/TONY-AI, 3509 ham test, da tu dung 01:17 06/11 sau khi bao dong bo cho chuyen may)
- Code: deps/AGENTS/Dockerfile GIONG HET nhau; khac biet 100% o src/tools/tests+data. BRAIN_0 giau tinh nang hoc: nm1 super-memory + nm2 evidence gate + nm3 self-learning V2 + nm3.5 chat extraction + CCLE (~3293 dong + 30 test file)
- Data: phan ky 2 chieu (chi tiet trong plan); candidate_knowledge xung dot nang nhat (3934 chi-E / 4890 chi-B0 / 160 common khac status)
- Ha tang: 3 task scheduler song deu Result=0; watchdog 5 restarts/h; CHI 1 diem nghen = PC tu ngu 600s idle

## 3. ĐÁNH GIÁ
- E:BRAIN la ban dung lau dai: ha tang moi hon (UDC-1, SSH pi5, guard 1-instance, LOCALAPPDATA discovery) va baseline 3609 tests
- BRAIN_0 khong the bo qua: chiem 300MB code gia tri hoc tu chat owner (nm3.5: trich tri thuc tu loi noi anh Quan -> pending proposals, cap 20/ngay, apply chi owner)
- Rui ro cao nhat: WAL 105MB; copy brain.db thieu -wal/-shm se malformed (da verify)

## 4. ĐỊNH HƯỚNG
- Một Core (E:BRAIN) nhiều năng lực: port code BRAIN_0 theo lô P1→P4 có test, migrate data 4 giai đoạn có quarantine, vệ sinh bot cũ sau cùng  - c- o- d- e-  - B- R- A- I- N- _- 0-  - t- h- e- o-  - l- o-  - P- 1- -- >- P- 4-  - c- o-  - t- e- s- t- ,-  - m- i- g- r- a- t- e-  - d- a- t- a-  - 4-  - g- i- a- i-  - d- o- a- n-  - c- o-  - q- u- a- r- a- n- t- i- n- e- ,-  - v- e-  - s- i- n- h-  - b- o- t-  - c- u-  - s- a- u-  - c- u- n- g
## 5. ĐỀ XUẤT
- GIAI DOAN A.2 (cho duyet): xoa 19 log cu >7 ngay (1.9MB) + 16 backup cu (1.33GB, giu 5 moi nhat)
- GIAI DOAN B (cho duyet): powercfg standby-timeout-ac 0 - sua root cause 24/7; theo doi backup 2AM dem nay
- GIAI DOAN C: migration data 4 buoc (freeze+checkpoint -> import thang INSERT OR IGNORE -> quarantine candidate -> rebuild semantic_index)
- GIAI DOAN D: port code P1 (chat_guard+evidence_gate+metacognition 483 dong) -> P2 (chat_extractor+SelfLearningV2 354) -> P3 (CCLE 1019) -> P4 (NM1 stack 1437)
- GIAI DOAN E: ve sinh bot cu - anh tu go bot Tony Assistant khoi NetChat (em khong co quyen)

## 6. BẰNG CHỨNG & MINH CHỨNG SỐ
- reports/AUDIT_MERGE_BRAIN_0_PLAN.md (plan day du 7 muc)
- Smoke test sau don rac: 36/36 PASS (.venv pytest test_memory_taxonomy)
- Event Log: ngu 01:40 dem 05/11, resume 12:43 hom nay - TONY chet 11h dem qua
- powercfg: AC sleep=600s; schtasks: backup LastRun 05/11 07:33 (catch-up), NextRun 07/11 02:00

## 7. RỦI RO & TRUNG THỰC
- PC tiep tuc ngu dem nay -> miss backup 2AM lan 3 neu chua sua powercfg
- Copy brain.db sai cach lam HONG DB production (WAL 105MB)
- Import candidate_knowledge thang se lam o DB quarantine 8553 rows hien tai

## 8. VIỆC CHỜ OWNER QUYẾT ĐỊNH
- Duyet Giai doan B: powercfg standby-timeout-ac 0 (sua root cause 24/7)?
- Duyet Giai doan A.2: xoa log cu + backup cu (1.33GB)?
- Duyet Giai doan C+D: migration data + port code theo lo (sau khi B on dinh)?
