---
name: battery-ai-system
description: >-
  Comprehensive skill for the entire Battery AI ecosystem at e:\AI\battery-ai-\.
  Covers all 4 subsystems: BATTERY_AI_V4 (main production API server, AI engines,
  dashboard), BATTERY_AI_V3 (legacy server, data source), BOT_PDL (Netchat bot
  platform with 5 bots: bat, tb, vtdp, pauctt, td), and Ollama (e:\AI\Ollama — local
  LLM runtime with qwen2.5:1.5b, llama3.1, mistral, qwen). Use when the user asks
  to develop, modify, debug, deploy, operate, extend, or understand any component
  of the Battery AI system. Covers: server architecture, API endpoints, prediction
  engine, RCA analyzer, battery advisor (LLM), knowledge engine, ML pipeline,
  dashboard, IoT receiver, auto-importer, Netchat bots (5 bots), ticketing service,
  TTS, database schema, Ollama LLM management, deployment procedures, V3 legacy
  compatibility, and cross-system data flow.
---

# Battery AI — Full System Skill

> **Scope**: This skill covers the **entire** Battery AI ecosystem at
> `e:\AI\battery-ai-\` — including V4 (production), V3 (legacy), BOT_PDL (Netchat
> bots), Ollama LLM runtime (`e:\AI\Ollama\`), and root-level utilities.

---

## 1. System Overview

| Field | Value |
|-------|-------|
| **Name** | Battery AI — Edge AI Battery Management Platform |
| **Purpose** | Monitor, analyze, and predict UPS/DC battery lifespan at telecom stations & datacenters |
| **Author** | QUANPT1 (Phạm Thế Quân) — TTKTKV1 — Viettel Networks |
| **Scale** | 53 power sources, 96 battery strings at TTKV1 |
| **Root Path** | `e:\AI\battery-ai-\` |

### Subsystems

| Subsystem | Path | Port | Role |
|-----------|------|------|------|
| **BATTERY_AI_V4** | `BATTERY_AI_V4/` | 9090 | Main production API server, AI engines, web dashboard |
| **BATTERY_AI_V3** | `BATTERY_AI_V3/` | 8080 | Legacy server, data source for V3 logfile_bat, backward compatibility |
| **BOT_PDL** | `BOT_PDL/` | — | Netchat bot platform (5 bots: bat, tb, vtdp, pauctt, td) |
| **Ollama** | `e:\AI\Ollama\` | 11434 | Local LLM runtime — powers all AI Chat/Advisor features |
| **_ARCHIVE_LEGACY** | `_ARCHIVE_LEGACY/` | — | Archived old versions (V1, V2/BAT_Platform, NetAgent) |

### Technology Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.11, `ThreadingHTTPServer` |
| Database | SQLite (`battery_ups_v4.db`, `battery_ups_v3.db`) |
| LLM Runtime | **Ollama** at `e:\AI\Ollama\ollama.exe` — self-host, port 11434 |
| LLM Models | `qwen2.5:1.5b` (primary), `llama3.1`, `mistral`, `qwen` (installed) |
| Model Storage | `e:\AI\Ollama\models\` (`OLLAMA_MODELS` env var) |
| NLP Search | `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` (BOT_PDL) |
| Frontend | HTML/CSS/JS (vanilla, no framework) |
| Bot Protocol | Mattermost/Netchat WebSocket API |
| TTS | Viettel AI TTS API |

---

## 2. Full Directory Structure

```
e:\AI\battery-ai-\
├── start_v4_oneclick.bat          # ROOT ONE-CLICK: launches V4 + all services
├── Battery AI FULL.json           # Full system configuration export
├── patch.py / patch_location.py   # Database patching utilities
├── logo viettel.png               # Viettel brand logo
│
├── BATTERY_AI_V4/                 # ══════ MAIN PRODUCTION ══════
│   ├── .env                       # Env config (Ollama, TTS, OpenAI)
│   ├── run_v4_server.bat          # 7-step autonomous launcher
│   ├── data/
│   │   └── battery_ups_v4.db      # PRIMARY database (53 sources, 96 strings)
│   ├── scripts/
│   │   ├── server.py              # Main API server (port 9090)
│   │   ├── handlers/              # Modular API handlers
│   │   │   ├── base.py            #   Base handler, DB_PATH, logger
│   │   │   ├── core_api.py        #   Devices, readings, cells, strings, voltage-history
│   │   │   ├── analytics_api.py   #   Health-score, trend, alerts, predictions, rul, rca
│   │   │   ├── chat_api.py        #   Chat v1/v2, TTS, streaming
│   │   │   ├── reports_api.py     #   Report list/generate
│   │   │   ├── upload_api.py      #   CSV/Excel upload
│   │   │   └── auth_api.py        #   Login, register, approve
│   │   ├── prediction_engine.py   # SOH/RUL/Anomaly detection
│   │   ├── rca_analyzer.py        # Root Cause Analysis (8 categories)
│   │   ├── battery_advisor.py     # LLM advisor v1 (7-section, Ollama)
│   │   ├── battery_advisor_v2.py  # LLM advisor v2
│   │   ├── chatbot.py             # Rule-based chatbot (v1 fallback)
│   │   ├── analytics.py           # Analytics calculations
│   │   ├── report_generator.py    # PDF report generation
│   │   ├── auto_importer.py       # Watches logfile_bat every 5s
│   │   ├── iot_receiver.py        # IoT data receiver (SNMP/API)
│   │   ├── ticketing_service.py   # Ticketing integration (41KB!)
│   │   ├── tts_service.py         # Text-to-Speech (Viettel AI)
│   │   ├── csv_to_sqlite.py       # CSV/Excel → SQLite
│   │   ├── run_v3_pipeline.py     # Full sync: V3 logs → V4 DB → AI
│   │   ├── send_daily_report.py   # Scheduled daily report
│   │   ├── import_all_logfile_bat.py  # Bulk import
│   │   ├── import_1month_history.py   # History import
│   │   ├── cron_memory_agent.py   # Memory consolidation cron
│   │   ├── voice_assistant.py     # Voice assistant module
│   │   ├── ai_agent_integration.py # Agent integration layer
│   │   ├── knowledge_engine/      # Knowledge & Experience Engine
│   │   ├── ml_pipeline/           # ML modules (15 files)
│   │   │   ├── feature_engineering.py
│   │   │   ├── anomaly_detector.py
│   │   │   ├── soh_predictor.py
│   │   │   ├── rul_predictor.py
│   │   │   ├── mlops_manager.py
│   │   │   ├── pca_analyzer.py
│   │   │   ├── risk_engine.py
│   │   │   ├── data_quality_gate.py
│   │   │   ├── model_calibration.py
│   │   │   ├── vendor_knowledge.py
│   │   │   ├── physics_engine.py
│   │   │   ├── survival_engine.py
│   │   │   ├── transformer_rul.py
│   │   │   └── autoencoder_engine.py
│   │   ├── advisor/               # Advisor tool functions
│   │   └── agent/                 # Autonomous agent modules
│   ├── dashboard/                 # Web frontend (12 pages)
│   │   ├── index.html             # Homepage overview
│   │   ├── inventory.html         # Device inventory
│   │   ├── analytics.html         # Voltage trend charts
│   │   ├── predictions.html       # SOH/RUL predictions
│   │   ├── chat.html              # AI Chat interface
│   │   ├── about.html             # About / system info
│   │   ├── device.html            # Single device detail
│   │   ├── digital_twin.html      # Digital twin
│   │   ├── population.html        # PCA population analysis
│   │   ├── realtime-input.html    # Manual data input
│   │   ├── rec.html               # REC device page
│   │   ├── login.html / register.html / admin_users.html
│   │   ├── css/common.css
│   │   ├── js/auth.js
│   │   └── images/
│   ├── logs/                      # Runtime logs
│   │   └── ai-advisor/            # AI conversation logs
│   └── BATTERY AI V4 – MASTER PROMPT*.md  # Architecture docs (2 files)
│
├── BATTERY_AI_V3/                 # ══════ LEGACY SERVER ══════
│   ├── .env                       # Env config (includes OpenAI key)
│   ├── run_v3_server.bat          # V3 launcher (port 8080 + bot)
│   ├── data/
│   │   └── battery_ups_v3.db      # Legacy database
│   ├── logfile_bat/               # Raw log files from BMS (CSV/Excel)
│   ├── scripts/
│   │   ├── server.py              # Legacy API server (port 8080, 13KB)
│   │   ├── handlers/              # Handler mixins (same pattern as V4)
│   │   ├── prediction_engine.py   # Same engine (shared codebase)
│   │   ├── rca_analyzer.py        # Same RCA (shared codebase)
│   │   ├── battery_advisor.py     # Same advisor
│   │   ├── chatbot.py             # Same chatbot
│   │   ├── analytics.py           # Analytics
│   │   ├── auto_importer.py       # Auto-import for V3
│   │   ├── csv_to_sqlite.py       # CSV → SQLite
│   │   ├── run_v3_pipeline.py     # V3 pipeline
│   │   ├── ml_pipeline/           # ML modules (shared)
│   │   └── advisor/               # Advisor tools
│   ├── dashboard/                 # Legacy dashboard (no auth, 12 pages)
│   │   ├── index.html / inventory.html / analytics.html / etc.
│   │   └── css/ / js/ / images/
│   └── logs/
│
├── BOT_PDL/                       # ══════ NETCHAT BOT PLATFORM ══════
│   ├── .env                       # Bot config (Netchat tokens, channels, prefixes)
│   ├── README.md                  # User-facing bot usage guide
│   ├── bot_config.json            # Runtime config (channels, alerts, authorized users)
│   ├── bot_state.json             # Bot state persistence
│   ├── bot_registry.json          # Multi-bot registry
│   ├── bot_heartbeats.json        # Health heartbeats
│   ├── requirements.txt           # Python deps (requests, websocket-client, python-dotenv)
│   ├── Dockerfile + docker-compose.yml  # Docker deployment
│   │
│   ├── bot_battery_ai.py          # 🔋 BAT BOT (73KB!) — Battery AI Netchat bot
│   │                              #    Trigger: "bat <câu hỏi>"
│   │                              #    Connects to V4 API /api/chat/v2
│   │                              #    Direct DB query on battery_ups_v4.db
│   │                              #    Alert system: emergency, periodic 4h, daily 24h
│   ├── bot_tb.py                  # 📋 TB BOT (13KB) — Thiết bị (Device lookup)
│   │                              #    Trigger: "tb <tên thiết bị hoặc serial>"
│   │                              #    Data: data/data_tb/
│   ├── bot_td.py                  # 📋 TD BOT (13KB) — Tra dịch (Translation/lookup)
│   │                              #    Trigger: "td <query>"
│   │                              #    Data: data/data_td/
│   ├── bot_vtdp.py                # 📦 VTDP BOT (50KB) — Vật tư dự phòng (Spare parts)
│   │                              #    Trigger: "vtdp <model/part number>"
│   │                              #    OCR image search, Excel data lookup
│   │                              #    Data: data/data_vtdp/
│   ├── bot_pauctt.py              # 🆘 UCTT BOT (34KB) — Ứng cứu thông tin
│   │                              #    Triggers: "uctt/xlsc/vhkt <mã trạm> <query>"
│   │                              #    Stations: pdl, gvm, hlc1, hlc2, pvn, vsat
│   │                              #    Data: data/data_uctt/
│   ├── bot_controller_agent.py    # 🎛️ Bot Controller Agent (50KB) — master orchestrator
│   ├── run_all_bots_monolithic.py # Run all bots in one process
│   ├── run_all_bots.bat           # Launch all bots separately
│   ├── run_all_bots_hidden.vbs    # Launch silently (Windows service)
│   │
│   ├── core/                      # Shared bot infrastructure
│   │   ├── orchestrator.py        #   Multi-bot orchestrator
│   │   └── response_generator.py  #   Response formatting
│   ├── emergency_alert_service.py # Emergency alert push to channels
│   ├── report_overview.py         # Overview report generator (28KB)
│   ├── response_builder.py        # Response formatting (16KB)
│   ├── search_engine.py           # Semantic search engine (sentence-transformers)
│   ├── source_lookup.py           # Data source resolver
│   ├── excel_cache.py             # Excel caching for performance
│   ├── text_normalizer.py         # Vietnamese text normalization
│   ├── bot_status_manager.py      # Bot health/status tracking
│   ├── history_logger.py          # Chat history persistence
│   │
│   ├── data/                      # Bot data directories
│   │   ├── data_tb/               #   Device inventory Excel files
│   │   ├── data_td/               #   Translation data
│   │   ├── data_uctt/             #   Emergency procedures docs
│   │   └── data_vtdp/             #   Spare parts inventory Excel files
│   ├── downloads/                 # Downloaded files cache
│   ├── logs/                      # Bot logs
│   ├── processed_messages.db      # Message dedup database
│   └── battery_ups_v4.db          # Local DB copy for direct queries
│
└── _ARCHIVE_LEGACY/               # ══════ ARCHIVED VERSIONS ══════
    ├── BATTERY V1/                # First prototype
    ├── BAT_Platform_V2/           # V2 platform
    ├── NetAgent/                  # Network agent experiment
    └── logfile_bat demo/          # Sample data files
```

---

## 3. Cross-System Data Flow

```
┌─────────────────────────────────────────────────────────────────┐
│  BMS / UPS / REC Devices (SNMP, CSV/Excel, IoT API)            │
└────────────────────────┬────────────────────────────────────────┘
                         │
         ┌───────────────▼───────────────┐
         │      BATTERY_AI_V3            │
         │  logfile_bat/ (raw CSV/Excel) │
         │  battery_ups_v3.db            │
         │  server.py :8080              │
         └───────────────┬───────────────┘
                         │ run_v3_pipeline.py syncs
                         │ V3 data → V4 DB
         ┌───────────────▼───────────────┐
         │      BATTERY_AI_V4            │
         │  battery_ups_v4.db (primary)  │
         │  server.py :9090              │
         │  ┌──────────────────────────┐ │
         │  │ Prediction Engine (SOH)  │ │
         │  │ RCA Analyzer             │ │
         │  │ Battery Advisor (LLM)    │ │
         │  │ Knowledge Engine         │ │
         │  │ ML Pipeline              │ │
         │  └──────────────────────────┘ │
         │  Dashboard (12 web pages)     │
         │  IoT Receiver                 │
         │  Auto-Importer                │
         │  Ticketing Service            │
         │  TTS Service                  │
         └──────┬────────────────────────┘
                │ /api/chat/v2
         ┌──────▼────────────────────────┐
         │      BOT_PDL                  │
         │  bot_battery_ai.py (bat)      │◄─── Netchat WebSocket
         │  bot_tb.py (tb)               │
         │  bot_vtdp.py (vtdp)           │
         │  bot_pauctt.py (uctt/xlsc)    │
         │  bot_td.py (td)               │
         │  emergency_alert_service.py   │──── Push alerts to channels
         └───────────────────────────────┘
```

---

## 4. How to Start the System

### Full System One-Click (Production)

```bat
e:\AI\battery-ai-\start_v4_oneclick.bat
```

This calls `BATTERY_AI_V4\run_v4_server.bat` which runs 7 steps:
1. Start Ollama LLM daemon (port 11434)
2. Sync & import all data (`run_v3_pipeline.py`) — V3 logs → V4 DB → AI analysis
3. Start Auto-Importer (watches `logfile_bat/` every 5s)
4. Start IoT Receiver + Ticketing Service
5. Start Netchat Bot (`BOT_PDL/bot_battery_ai.py`)
6. Start V3 Server (port 8080)
7. Start V4 Server (port 9090)

### Start V3 Only (Legacy)

```bat
cd /d e:\AI\battery-ai-\BATTERY_AI_V3
run_v3_server.bat
```
Starts V3 server on port 8080 + auto-importer + Netchat bot.

### Start Bots Only

```bat
cd /d e:\AI\battery-ai-\BOT_PDL

REM Single bot:
run_battery_bot.bat         # bat bot only
run_tb_bot.bat              # tb bot only
run_vtdp_bot.bat            # vtdp bot only
run_uctt_bot.bat            # uctt bot only

REM All bots:
run_all_bots.bat            # Launch all separately
python run_all_bots_monolithic.py  # All in one process
```

### Access Points

| Service | URL / Trigger |
|---------|---------------|
| V4 Dashboard | `http://localhost:9090` |
| V3 Dashboard (legacy) | `http://localhost:8080` |
| V4 AI Chat | `http://localhost:9090/api/chat/v2` |
| Health Check | `http://localhost:9090/api/health` |
| Ollama LLM | `http://localhost:11434` |
| Netchat: Battery AI | `bat <câu hỏi>` |
| Netchat: Thiết bị | `tb <tên/serial>` |
| Netchat: Vật tư DP | `vtdp <model/part>` |
| Netchat: Ứng cứu TT | `uctt <mã_trạm> <tình_huống>` |
| Netchat: Xử lý sự cố | `xlsc <mã_trạm> <sự_cố>` |
| Netchat: Vận hành KT | `vhkt <mã_trạm> <quy_trình>` |

---

## 5. API Reference (V4 — Key Endpoints)

### GET Endpoints

| Endpoint | Description | Params |
|----------|-------------|--------|
| `/api/health` | System health check | — |
| `/api/stats` | Overall statistics | — |
| `/api/devices` | List all UPS/DC devices | — |
| `/api/readings` | Battery readings | `?device_id=&limit=100` |
| `/api/cells` | Cell-level data | `?device_id=&reading_id=` |
| `/api/strings` | Strings with cell voltages | `?device_id=` |
| `/api/voltage-history` | Voltage time series | `?device_id=&limit=200` |
| `/api/anomalies` | Anomaly detections | `?device_id=` |
| `/api/health-score` | SOH health score | `?device_id=` |
| `/api/trend` | Trend analysis | `?device_id=&limit=100` |
| `/api/alerts` | Active alerts | `?device_id=` |
| `/api/predictions` | Failure predictions | `?device_id=` |
| `/api/rul` | Remaining Useful Life | `?device_id=&cell=` |
| `/api/rca` | Root Cause Analysis | `?device_id=&cell=` |
| `/api/reports` | List reports | — |
| `/api/reports/generate` | Generate PDF report | `?device_id=` |
| `/api/pca-population` | PCA population analysis | — |
| `/api/chat/status` | Chat service status | — |
| `/api/v3/digital-twin` | Digital twin snapshots | — |
| `/api/autonomous-discharge-test` | Discharge test data | `?device_id=` |
| `/api/thermal-runaway` | Thermal runaway check | `?device_id=` |

### POST Endpoints

| Endpoint | Description | Body |
|----------|-------------|------|
| `/api/chat` | Chat v1 (rule-based) | `{"message": "..."}` |
| `/api/chat/v2` | Chat v2 (LLM Advisor) | `{"message": "..."}` |
| `/api/chat/stream` / `/api/chat/v2/stream` | Streaming | `{"message": "..."}` |
| `/api/chat/mode` | Switch AI mode | `{"mode": "v1"/"v2"}` |
| `/api/chat/clear` | Clear history | `{}` |
| `/api/tts` / `/api/tts/stream` | Text-to-Speech | `{"text": "..."}` |
| `/api/upload` | Upload CSV/Excel | `{"data": "..."}` |
| `/api/realtime` | Push realtime | `{voltage, ir, temp...}` |
| `/api/realtime/snmp` / `/api/realtime/bacnet` | Protocol push | `{...}` |
| `/api/auth/login` / `/api/auth/register` / `/api/auth/approve` | Auth | `{username, password}` |
| `/api/v4/ai-advisor` | BAT Workforce Advisor | `{"message": "..."}` |
| `/api/admin/bot` | Bot admin control | `{...}` |

---

## 6. AI Engines — Technical Detail

### 6.1 Prediction Engine (`scripts/prediction_engine.py`)

```
RiskScore = 0.5 × risk_IR + 0.2 × risk_T + 0.2 × risk_ΔV + 0.1 × risk_event
SOH = w1×S_R + w2×S_V + w3×S_T + w4×S_C + w5×S_A
```

- Risk Levels: `LOW`(<30%), `MEDIUM`(30-60%), `HIGH`(60-80%), `CRITICAL`(>80%)
- IR Thresholds: warning=1.3×, critical=1.6×, failure=2.0× initial
- Voltage Deviation: normal≤20mV, monitor≤50mV, warning≤100mV, critical≤150mV
- ML Pipeline: 15 modules (feature engineering, anomaly detection, SOH/RUL prediction, PCA, physics, survival, transformer, autoencoder)

### 6.2 RCA Analyzer (`scripts/rca_analyzer.py`)

8 categories: `THERMAL`, `OVERCHARGE`, `UNDERCHARGE`, `AGING`, `MANUFACTURING`, `ENVIRONMENTAL`, `IMBALANCE`, `UNKNOWN`

Action Priority: `IMMEDIATE` / `SCHEDULED` / `MONITOR`

### 6.3 Battery Advisor (`scripts/battery_advisor.py`)

- LLM: Ollama `qwen2.5:1.5b` (self-host)
- 7-section assessment + tool functions for direct DB query
- Cost tracking per conversation

### 6.4 Knowledge Engine (`scripts/knowledge_engine/`)

4 memory types: Raw Data → Event → Experience → Model

---

## 7. BOT_PDL — Netchat Bot Platform

### 5 Bots

| Bot | File | Trigger | Size | Purpose |
|-----|------|---------|------|---------|
| **Battery AI** | `bot_battery_ai.py` | `bat <query>` | 73KB | Battery analysis, AI copilot, alerts |
| **Thiết bị** | `bot_tb.py` | `tb <device>` | 13KB | Device lookup (rack, U position, model) |
| **Vật tư DP** | `bot_vtdp.py` | `vtdp <part>` | 50KB | Spare parts inventory, OCR image search |
| **Ứng cứu TT** | `bot_pauctt.py` | `uctt/xlsc/vhkt` | 34KB | Emergency procedures, incident handling |
| **Tra dịch** | `bot_td.py` | `td <query>` | 13KB | Translation/lookup |

### Bot Architecture

- **Protocol**: Mattermost WebSocket API → `netchat.viettel.vn:443`
- **Auth**: Bot token per bot account (`BOT_TOKEN_BATTERY`, etc.)
- **Reconnect**: Auto-reconnect with configurable delay (default 5s)
- **Alert System** (bat bot):
  - Emergency alerts: pushed immediately
  - Periodic alerts: every 4 hours
  - Daily reports: at 08:00
  - Channels: PDL_Cảnh báo_VDCIM, AI Battery tại TTKV, DC-COMMAND AIDCO
- **Data Sources**:
  - bat: V4 API (`/api/chat/v2`) + direct SQLite query
  - tb: Excel files in `data/data_tb/`
  - vtdp: Excel files in `data/data_vtdp/` + OCR
  - uctt: Documents in `data/data_uctt/`
- **NLP**: `sentence-transformers` for semantic search in bot_vtdp, bot_pauctt
- **Controller**: `bot_controller_agent.py` (50KB) — orchestrates all bots, health monitoring
- **Docker**: Dockerfile + docker-compose.yml available

### Bot Environment (`.env`)

```env
# Netchat connection
MM_URL=netchat.viettel.vn
MM_SCHEME=https
MM_PORT=443
BOT_TOKEN=<token>

# Battery AI bot
BOT_PREFIX_BATTERY=bat
API_V4_URL=http://localhost:9090/api/chat/v2

# VTDP bot
BOT_PREFIX_VTDP=vtdp
DATA_DIR_VTDP=data\data_vtdp

# Alert channels
ALERT_CHANNEL_IDS=r4dhe4tfn7yctm9esyei5rqfja,cjyr13htojfwbyypxhsra6fiph,...
```

---

## 8. V3 ↔ V4 Relationship

| Aspect | V3 | V4 |
|--------|----|----|
| Port | 8080 | 9090 |
| Database | `battery_ups_v3.db` | `battery_ups_v4.db` |
| Auth | None | Token-based, role-based |
| Dashboard | 12 pages, no auth | 12+ pages, auth + admin |
| AI modules | Same codebase (shared) | Same + Knowledge Engine, agent modules |
| Data source | `logfile_bat/` raw files | Syncs from V3 via `run_v3_pipeline.py` |
| Server size | 13KB (simpler) | 35KB (modular handlers) |

**Data sync flow**: `BATTERY_AI_V3/logfile_bat/` → `run_v3_pipeline.py` → `BATTERY_AI_V4/data/battery_ups_v4.db`

V3 is kept running for backward compatibility and as the raw data ingestion point.

---

## 9. Development Guidelines

### Adding a V4 API Endpoint

1. Choose handler mixin in `BATTERY_AI_V4/scripts/handlers/`
2. Add method to the mixin class
3. Add route in `server.py` `do_GET()` or `do_POST()`
4. Add dashboard UI in `dashboard/` if needed

### Adding a New Netchat Bot

1. Create `BOT_PDL/bot_<name>.py` following pattern of `bot_tb.py`
2. Add trigger prefix to `.env` (`BOT_PREFIX_<NAME>=<prefix>`)
3. Add data directory `BOT_PDL/data/data_<name>/`
4. Register in `bot_registry.json`
5. Add to `run_all_bots.bat` and `run_all_bots_monolithic.py`

### Modifying Bot Alert Channels

Edit `BOT_PDL/bot_config.json`:
```json
{
  "channels": [
    {"id": "<channel_id>", "name": "...", "enabled": true,
     "alert_types": ["emergency", "periodic_4h", "daily_24h"]}
  ]
}
```

### Testing

```bash
# V4 tests
cd /d e:\AI\battery-ai-\BATTERY_AI_V4
py -3.11 test_full_system.py
py -3.11 test_admin_controls.py
py -3.11 test_concurrency.py
py -3.11 test_format_alerts.py
py -3.11 test_llama3_diagnosis.py

# Bot tests
cd /d e:\AI\battery-ai-\BOT_PDL
python test_netchat_conn.py
python test_help_routing.py
python test_report_generator.py
```

---

## 10. Safety & Design Principles

> **CRITICAL**: Non-negotiable when modifying ANY part of Battery AI.

1. **Human-in-the-loop**: AI NEVER auto-executes battery replacement
2. **Self-host only**: No battery data leaves internal network. LLM local via Ollama
3. **Honest uncertainty**: If data insufficient, say "không đủ dữ liệu"
4. **No auto-training**: ML models don't retrain without validation
5. **Graceful degradation**: Ollama down → fallback to rule-based chatbot v1
6. **Audit trail**: Every AI recommendation, KTV confirmation, alert is logged
7. **Kill switch**: AI advisor can be disabled without affecting data collection
8. **Bot isolation**: Each Netchat bot is independent, one crash doesn't affect others

---

## 11. Environment Variables Summary

### V4 (`.env`)
```env
USE_OLLAMA=true
OLLAMA_BASE_URL=http://localhost:11434/v1
OLLAMA_MODEL=qwen2.5:1.5b
TTS_MODE=viettel
VIETTEL_AI_TOKEN=<token>
```

### V3 (`.env`)
```env
USE_OLLAMA=true
OLLAMA_BASE_URL=http://localhost:11434/v1
OLLAMA_MODEL=qwen2.5:1.5b
OPENAI_API_KEY=<key>   # fallback
TTS_MODE=viettel
VIETTEL_AI_TOKEN=<token>
```

### BOT_PDL (`.env`)
```env
MM_URL=netchat.viettel.vn
BOT_TOKEN=<netchat_token>
BOT_PREFIX_BATTERY=bat
API_V4_URL=http://localhost:9090/api/chat/v2
ALERT_CHANNEL_IDS=<comma_separated>
```

---

## 12. Troubleshooting

| Symptom | Subsystem | Fix |
|---------|-----------|-----|
| Port 9090 in use | V4 | `netstat -ano \| findstr 9090` → kill PID |
| Port 8080 in use | V3 | `netstat -ano \| findstr 8080` → kill PID |
| Ollama not responding | V4/V3 | `e:\AI\Ollama\ollama.exe serve` |
| Bot disconnects | BOT_PDL | Check Netchat token, SSL, auto-reconnect logs |
| Bot not responding to trigger | BOT_PDL | Verify prefix in `.env`, check `ALLOW_ALL_CHANNELS` |
| Alert not sent | BOT_PDL | Check `bot_config.json` channel `enabled: true` |
| "ML Pipeline not available" | V4 | `pip install numpy scipy` |
| Chat returns empty | V4 | `ollama pull qwen2.5:1.5b` |
| Database locked | V4/V3 | Restart server (SQLite limitation) |
| V3 data not syncing to V4 | V4 | Run `py -3.11 scripts/run_v3_pipeline.py` manually |
| OCR not working (vtdp bot) | BOT_PDL | Check `sentence-transformers` installed |
| TTS fails | V4 | Update `VIETTEL_AI_TOKEN` in `.env` |
| Dashboard 404 | V4/V3 | Must `cd /d BATTERY_AI_V4` before server |
