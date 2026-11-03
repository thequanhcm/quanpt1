# CAI_V3_SPRINT1_REPORT.md — Tool Registry + QPIG Chat Integration (02/11/2026)

## PHASE 0 Audit (dữ liệu tươi)
`reports/TONY_COGNITIVE_TRUTH_AUDIT_V2.md` — 6 lỗ hổng báo cáo cũ vẫn còn:
- ToolRegistry rỗng (root cause: không có instance nào wire vào chat)
- QPIG chưa vào chat (0 file chat dùng QPIG)
- Embedding module lỗi (knowledge.embedding không tồn tại)
- Evidence production rỗng (bảng evidence chưa có trong brain.db)
- Pi5 kênh đóng (11 cổng đều đóng)
- Daemon scorecard không tồn tại

## SPRINT 1 — đã làm

### §III: Tool Registry 10 trụ cột + 13 thuộc tính/tool
- `ToolRegistryLoader` auto-load 25 tool từ QPIG (giải quyết "Tool Registry trống")
- `ToolSelector` chọn tool theo intent (keyword + name match + risk penalty + operational bonus)
- Chống Tool Description Injection: 5 pattern (EN + VN)
- Chống Schema Injection: QPIG validate input type/required
- Mỗi tool có 13 thuộc tính §III (tool_id, description, input/output schema, protocol,
  risk_level, timeout, approval, verification, ...)

### §IV: Wire QPIG vào /api/chat
- `ChatToolBridge` chèn tool evidence block vào `system_instructions` trước LLM call
- Tool AUTO (không cần ticket) → execute + evidence
- Tool R3+ → chỉ đề xuất + yêu cầu ticket Quanpt1 (§V)
- Response JSON có field `tool_calls` (n_calls, auto_executed, require_approval, evidence_ids)
- Wire tại `web/server.py` line 1844 (sau Knowledge Base RAG, trước LLM Generation)

## Bằng chứng

| Test | Kết quả |
|---|---|
| `tests/test_cai_v3_sprint1.py` | **12/12 PASS** |
| Demo thật 4 query | 2 auto-exec (evidence #4, #5) + 1 cần ticket + 1 không match |
| Loader | 25 tool loaded, 0 rejected |

## Demo §IV (chạy thật)

```
Q: "hãy quét thiết bị trong LAN xem có gì mới"
  → DEVICE_DISCOVERY: AUTO-EXEC evidence#4 verified=True
    {total_alive: 8, subnet: 192.168.1.0/24, devices: [...]}

Q: "ping 192.168.1.2 xem latency bao nhiêu"
  → NETWORK_INSPECTION: AUTO-EXEC evidence#5 verified=True
    {target: 192.168.1.2, reachable: True, latency_ms: 3}

Q: "tạo yêu cầu cô lập agent rogue"
  → AGENT_ISOLATION_REQUEST: cần ticket Quanpt1 — không tự execute (§V)

Q: "hôm nay thời tiết thế nào"
  → (không match tool nào)
```

## Còn lại (Sprint 2-6)

- Sprint 2: Memory + Reasoning + Evidence Store (PHASE 4+5+8)
- Sprint 3: Pi5 QPIG + QEP Communication (PHASE 3) — chờ owner mở SSH
- Sprint 4: SENTINEL + Approval Enforcement (PHASE 7)
- Sprint 5: Universal Agent Understanding + Adapter (PHASE 6+8)
- Sprint 6: End-to-End Integration + Self-Evolution (PHASE 9+10)
