# Battery AI — API Quick Reference (V4 + V3 + Bot)

## V4 API — `http://localhost:9090`

### Core Data
```
GET /api/health           → System health + service status
GET /api/stats            → Overall statistics
GET /api/devices          → All UPS/DC devices
GET /api/readings         → Battery readings        ?device_id=&limit=100
GET /api/cells            → Cell-level data          ?device_id=&reading_id=
GET /api/strings          → Strings with voltages    ?device_id=
GET /api/voltage-history  → Voltage time series      ?device_id=&limit=200
```

### AI / Analytics
```
GET /api/health-score     → SOH score               ?device_id=
GET /api/predictions      → Failure predictions      ?device_id=
GET /api/rul              → Remaining Useful Life    ?device_id=&cell=
GET /api/rca              → Root Cause Analysis      ?device_id=&cell=
GET /api/anomalies        → Anomaly detections       ?device_id=
GET /api/trend            → Trend analysis           ?device_id=&limit=100
GET /api/alerts           → Active alerts            ?device_id=
GET /api/pca-population   → PCA population analysis
GET /api/autonomous-discharge-test → Discharge test  ?device_id=
GET /api/thermal-runaway  → Thermal check            ?device_id=
GET /api/v3/digital-twin  → Digital twin snapshots
```

### Chat / AI
```
POST /api/chat            → Chat v1 (rule-based)     {"message":"..."}
POST /api/chat/v2         → Chat v2 (LLM Advisor)    {"message":"..."}
POST /api/chat/stream     → Streaming v1              {"message":"..."}
POST /api/chat/v2/stream  → Streaming v2              {"message":"..."}
GET  /api/chat/status     → Service status
POST /api/chat/mode       → Switch mode               {"mode":"v1"/"v2"}
POST /api/chat/clear      → Clear history
POST /api/v4/ai-advisor   → BAT Workforce Advisor     {"message":"..."}
```

### Reports / Upload
```
GET  /api/reports          → List reports
GET  /api/reports/generate → Generate PDF             ?device_id=
POST /api/upload           → Upload CSV/Excel         {"data":"base64","filename":"..."}
POST /api/realtime         → Push realtime data
POST /api/realtime/snmp    → SNMP data push
POST /api/realtime/bacnet  → BACnet data push
```

### Auth
```
POST /api/auth/login       → Login                   {"username":"...","password":"..."}
POST /api/auth/register    → Register                {"username","password","role"}
POST /api/auth/approve     → Approve user
POST /api/admin/bot        → Bot admin control
```

### TTS
```
POST /api/tts              → Text-to-Speech          {"text":"..."}
POST /api/tts/stream       → Streaming TTS
POST /api/tts/clear-cache  → Clear TTS cache
```

---

## V3 API — `http://localhost:8080`

Same endpoint pattern as V4 but:
- No auth endpoints
- No `/api/v4/ai-advisor`
- No `/api/admin/bot`
- Database: `battery_ups_v3.db`

---

## Netchat Bot Triggers

| Bot | Trigger | Example |
|-----|---------|---------|
| Battery AI | `bat <query>` | `bat tình trạng nguồn UPS-01` |
| Thiết bị | `tb <name/serial>` | `tb N10_HW_OSN1800V_1` |
| Vật tư DP | `vtdp <part/model>` | `vtdp mccb 100a schneider` |
| Ứng cứu TT | `uctt <station> <situation>` | `uctt pdl mất điện trạm` |
| Xử lý sự cố | `xlsc <station> <incident>` | `xlsc gvm cảnh báo nhiệt độ cao` |
| Vận hành KT | `vhkt <station> <procedure>` | `vhkt hlc1 bảo dưỡng tủ nguồn` |

Stations: `pdl`, `gvm`, `hlc1`, `hlc2`, `pvn`, `vsat`

### Bot Admin API (via Netchat)
Authorized users (`Quanpt1`, `admin`) can control bots via direct message commands in Netchat.
