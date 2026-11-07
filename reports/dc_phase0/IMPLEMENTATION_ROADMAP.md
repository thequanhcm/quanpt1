# IMPLEMENTATION_ROADMAP — CHERRY DC (PHASE 0 → 7, 07/11/2026)
- **PHASE 1** (đề xuất NGAY, chỉ cần duyệt scope): ingest PDL (BMS ops, UPS VHKT, PCCC, SLD metadata) + standards library + mapping ladder L0-L4 — 0 feed ngoài, 0 đụng production.
- **PHASE 2**: alarm P1–P4 + correlation (trên monitoring nội bộ trước); BMS feed khi owner cấp endpoint + duyệt dep; báo cáo daily/weekly.
- **PHASE 3**: EOP/MOP Assistant (từ tài liệu PDL + SOP owner cung cấp), incident timeline, escalation.
- **PHASE 4**: Battery/UPS health — cần module Battery AI thật.
- **PHASE 5**: cooling/PUE — cần meter data.
- **PHASE 6**: digital twin/dependency graph.
- **PHASE 7**: audit độc lập + đề xuất mở rộng quyền (chỉ sau kiểm thử + duyệt).
Mỗi phase: card duyệt → implement → tests → full regression → báo cáo trung thực.
