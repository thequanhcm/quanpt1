# INTEGRATION_GAP_REPORT — CHERRY DC PHASE 0 (07/11/2026)
Khoảng trống tích hợp so với Master Prompt DC V3.0:

1. **BMS/DCIM/SCADA**: không có client nào (pymodbus/bacpypes/paho-mqtt/SNMP) — pyproject 0 dep giao thức; qpig.py chỉ NHẮC tên giao thức trong description.
2. **UPS/Battery AI**: BATTERY_AI_V4 không tồn tại trên máy này; không có điểm nhận SOH/RUL/Risk Score.
3. **Alarm pipeline**: alert_engine 2 mức (CRITICAL/WARNING) — thiếu P1–P4, thiếu correlate, thiếu alarm topology.
4. **EOP/MOP repository**: không có repo quy trình chuẩn hoá; tài liệu vận hành BMS có trong PDL nhưng chưa cấu trúc.
5. **Governance ladder DC**: ladder hiện L0_SUPREME_HUMAN/L1_EXECUTIVE/L2_SECURITY/L3_CONTROLLED — cần mapping layer sang L0 Observe…L4 Restricted Critical (không tự diễn giải lại ma trận — V7.0 §2.3).
6. **Digital Twin**: không có dependency map hạ tầng (1 hit dependency graph thuộc task planner).
7. **Workforce/HR**: không có module lịch trực/handover/skill matrix.
