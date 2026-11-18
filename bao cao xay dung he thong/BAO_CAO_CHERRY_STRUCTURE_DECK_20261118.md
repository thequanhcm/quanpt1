# Báo cáo — Tạo tài liệu cấu trúc Cherry AI Digital Human

**Ngày**: 2026-11-18  
**Tác giả**: Phạm Thế Quân (quanpt1@viettel.com.vn)  
**Workspace**: E:/BRAIN  
**Skill dùng**: viettel-ppt-master (PPT Viettel-branded)

---

## Kết quả

Đã tạo **deck 14 slides** theo kết cấu PDF "Chia sẻ kinh nghiệm học lớp Kỹ sư AI VTNET qua project trợ lý ảo":

| Slide | Nội dung | Nguồn |
|-------|----------|-------|
| P01 | Bìa — Cherry AI Digital Human | cherry_live_facts.json |
| P02 | TOC — 2 phần | design_spec |
| P03 | Mở đầu 4 việc (tốc độ, giọng, motion, audit) | cherry_live_facts.json |
| P04 | Chapter 1 — Kiến trúc 5 lớp & trí nhớ sống | design_spec |
| P05 | Kiến trúc 5 lớp UI/API/App/Cognition/Infra | facts.md f_arch |
| P06 | Use case 3 (kiosk Pi5, dashboard PC, NetChat) | facts.md f_uc1-3 |
| P07 | Luồng RAG 2 pha (BM25 + ChromaDB) | facts.md f_rag1-3 |
| P08 | Quy trình 6 bước người-AI | facts.md f_s1-6 |
| P09 | KPI: 3,151 mem / 6,578 chunks / 115 tests / ~1.2s | facts.md f_kpi_* |
| P10 | Chapter 2 — Harness AGENTS.md | design_spec |
| P11 | 9 nguyên tắc + 3 rule tiêu biểu | facts.md f_hr1-3 |
| P12 | So sánh Prompt vs Skill vs Harness | facts.md f_cmp1-3 |
| P13 | Luồng duyệt PR 4 bước | facts.md f_pr1-4 |
| P14 | Đánh đổi fail-honest + 408 commits | facts.md f_e1-4 |

## Files output

- **PPTX**: `E:/BRAIN/bao cao xay dung he thong/CHERRY_STRUCTURE_DECK_20261118.pptx` (94,269 bytes, 14 slide)
- **Design spec**: `E:/BRAIN/projects/cherry_intro_ppt169_20261118/design_spec.md`
- **Content review**: `E:/BRAIN/projects/cherry_intro_ppt169_20261118/content_review.json`
- **SVG output**: `E:/BRAIN/projects/cherry_intro_ppt169_20261118/svg_output/` (14 SVG files)

## Quy trình chạy (3 stage PASS)

1. **plan**: validate 14 content-lock fences — facts có entity/unit/period/scope/status, sources trỏ về block-id thật trong `sources/cherry_facts_20261118.md`, SHA256 source_index verified
2. **svg**: render 14 SVG từ content-lock — mỗi text element có data-claims binding tới fact ID, page numbers dùng chrome exemption, 14 required content visible
3. **export**: content_review verified + svg_to_pptx convert native DrawingML → editable trong PowerPoint

## Bằng chứng số (anchored)

Mọi fact trong deck đều cite block-id trong `cherry_facts_20261118.md` (sha256: `13057958d02e8fc5e41df54c66f1a247a32277be7c73b4bc004be930a5c8e244`):

- 3,151 memories (brain.db, snapshot 18/11/2026)
- 6,578 semantic chunks (ChromaDB vector_db_semantic)
- 115 tests PASS (38 v7 + 30 expansion + 40 speech_utils + 7 endpoint)
- 408 commits
- 22 wake phrases (18 cũ + 4 vivi port)
- 11 skills (5 TESTED mới)
- 1.2s GLM-5.3-Flash latency vs 10-15s Ollama

## Đánh đổi fail-honest

- **Font**: FS Magistral thiếu trên host → SVG dùng Arial fallback (PowerPoint sẽ vẫn hiển thị đúng nhờ native DrawingML)
- **Khuôn mẫu**: dùng 5 template skill (cover, toc, chapter, content_*, ending) → không phải 14 layout custom
- **Visualization**: deck hiện dùng `template="none"` (không vẽ chart) — facts đã verified, charts để v2 sau

## Lệnh chạy lại

```bash
cd E:/BRAIN/projects/cherry_intro_ppt169_20261118
E:/BRAIN/.venv/Scripts/python.exe "C:/Users/DELL/AppData/Local/netmind_desktop/profiles/tony/skills/viettel-ppt-master/scripts/content_check.py" . --stage plan
E:/BRAIN/.venv/Scripts/python.exe "C:/Users/DELL/AppData/Local/netmind_desktop/profiles/tony/skills/viettel-ppt-master/scripts/content_check.py" . --stage svg
E:/BRAIN/.venv/Scripts/python.exe "C:/Users/DELL/AppData/Local/netmind_desktop/profiles/tony/skills/viettel-ppt-master/scripts/content_check.py" . --stage export
E:/BRAIN/.venv/Scripts/python.exe "C:/Users/DELL/AppData/Local/netmind_desktop/profiles/tony/skills/viettel-ppt-master/scripts/svg_to_pptx.py" . -o exports/Cherry_AI_Digital_Human.pptx
```

## Còn chờ

- Anh duyệt nội dung 14 slide (đọc PPTX hoặc design_spec.md)
- Nếu OK → commit design_spec vào repo (để có version control)
- Nếu cần chart đẹp → sprint sau bật visualization template (đã có sẵn 5 loại chart trong catalog)
