---
name: dc-noc-operations-suite
description: |
  Comprehensive 24/7 Data Center & NOC Operations Suite.
  Use when monitoring, diagnosing, triaging, and responding to Data Center infrastructure incidents:
    1. Telecom & Data Center room situation awareness (PUE, health scores, active alarms).
    2. UPS, PDU, STS, and power distribution health analysis (phase balance, harmonics, load ratio).
    3. Cooling and environmental monitoring (CRAC/CRAH, supply/return temp, dew point, hot/cold aisle, water leak).
    4. Battery string and DC power telemetry (cell voltage divergence, string current, temperature).
    5. Incident response workflows (Triage -> Cross-domain Root Cause Analysis -> Plan -> Verify).
    6. Strict R0-R5 safety gating (R5 hard-blocked, physical switching gated under owner approval).
license: Apache-2.0
metadata:
  version: v2.0.0
  domain: Data Center Infrastructure & NOC Operations
  governance: QUAN AI BRAIN Policy Matrix R0-R5
---

# Data Center & NOC Operations Suite (DC-NOC)

A mission-critical, production-grade operational skill engineered for autonomous and human-in-the-loop (HITL) supervision of Data Center infrastructure, telecom rooms, power distribution, and climate systems.

> [!IMPORTANT]
> **Data Center Uptime & Human Safety Primacy**:
> 1. Preserving IT load continuous uptime takes precedence over secondary component preservation, except in confirmed human life risk or fire/thermal runaway emergencies.
> 2. Zero autonomous physical switching: Any command altering breaker states, transfer switches (STS), or UPS bypass modes is classified as **R4/R5** and strictly requires authenticated owner approval.

---

## 1. Domain Coverage & Architecture

```
                  ┌─────────────────────────────────────────┐
                  │      DC-NOC Situation Awareness         │
                  │   (Kernel Orchestrator & Dashboard)     │
                  └────────────────────┬────────────────────┘
                                       │
        ┌───────────────┬──────────────┼──────────────┬──────────────┐
        ▼               ▼              ▼              ▼              ▼
 ┌─────────────┐ ┌─────────────┐ ┌───────────┐ ┌─────────────┐ ┌─────────────┐
 │    Power    │ │     UPS     │ │  Cooling  │ │ Environment │ │   Battery   │
 │   & PDU     │ │  & Inverter │ │ & Airflow │ │  & Sensors  │ │  & DC Plant │
 └─────────────┘ └─────────────┘ └───────────┘ └─────────────┘ └─────────────┘
```

The suite orchestrates 5 functional domains:
- **Power Distribution (PDU / STS / Transformers)**: Phase imbalance, total load (kVA/kW), power factor ($\cos\phi$), crest factor, total harmonic distortion (THD).
- **Uninterruptible Power Supply (UPS)**: Rectifier DC bus, inverter sync, static bypass status, battery charger state.
- **Cooling & Climate (CRAC / CRAH / Chillers)**: Supply/return air temperature, delta T across racks ($\Delta T_{rack}$), chilled water flow, fan speed, CFM.
- **Environment & Containment**: Room ambient temperature gradient, relative humidity ($RH$), dew point, underfloor static pressure, water leak ropes, smoke/VESDA.
- **Battery & DC Plant**: String float voltage, individual cell balance, discharge load profile, temperature probes.

---

## 2. Telemetry Threshold Matrix

All diagnostic engines evaluate telemetry against the following standard SLA and safety limits:

| Parameter | Unit | Normal Range | Warning (Amber) | Critical (Red) | Action / Escalation |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **Server Cold Aisle Temp** | °C | 18.0 – 24.0 | 24.1 – 27.0 | > 27.0 | Ramp CRAC fan / Check chiller loop |
| **Server Hot Aisle Temp** | °C | 28.0 – 35.0 | 35.1 – 40.0 | > 42.0 | Check rack blanking panels / Air containment |
| **Relative Humidity (RH)** | % | 45.0 – 55.0 | 35 – 44 or 56 – 65 | < 30 (ESD risk) or > 70 (Condensation) | Adjust CRAC humidifier / dehumidifier |
| **UPS Load Ratio** | % | 40 – 70 | 71 – 85 | > 85 | Shed non-essential load / plan module addition |
| **PDU Phase Imbalance** | % | < 10.0 | 10.1 – 15.0 | > 15.0 | Rebalance server feed distribution |
| **Battery String Voltage** | VDC | 53.5 – 54.5 | 52.0 – 53.4 | < 48.0 (Discharging) | Verify rectifier output / utility presence |
| **Battery Cell Voltage Delta**| mV | < 20 | 21 – 50 | > 50 (Under float) | Identify failing cell / schedule impedance test |
| **Battery Temp Differential** | °C | < 3.0 | 3.1 – 5.0 | > 5.0 ($T_{cell} - T_{amb}$) | Thermal runaway risk: throttle charger current |
| **Water Leak Resistance** | k$\Omega$ | > 500 (Dry) | 50 – 500 (Damp) | < 50 (Wet) | Dispatch floor inspection immediately |

---

## 3. Standard Operating Procedures (SOPs)

### SOP-01: High-Temperature Alert & Cooling Triage

```
Step 1: Ingest Alarm
  ├── Extract rack location, sensor ID, and measured value
  └── Cross-reference adjacent rack temperature sensors
Step 2: Cross-Domain Correlation
  ├── Check Cooling Domain: Are CRAC units operating? Compressor alarm? Water loop flow?
  └── Check Power Domain: Is there a sudden kW surge in that row?
Step 3: Fault Isolation
  ├── If localized to 1 rack: Probable cause = Fan failure, blocked perforations, missing blanking panel.
  └── If row-wide / room-wide: Probable cause = CRAC failure, chilled water valve stuck, or containment breach.
Step 4: Containment Recommendation
  ├── Non-intrusive (R0): Increase fan speed of redundant CRAC unit N+1.
  └── Owner Consent (R4): Transfer IT workload via VM migration if thermal runaway cannot be stabilized.
```

### SOP-02: UPS Transfer to Bypass or Battery Discharge

```
Step 1: Immediate Power Path Audit
  ├── Check Utility Mains voltage (Phase A, B, C).
  ├── Verify Generator start signal and ATS status if utility failed.
Step 2: Battery Autonomy Calculation
  ├── Read current discharge current (Amperes) and battery string voltage.
  ├── Compute remaining runtime: Runtime_minutes = (Battery_Ah_effective * String_V) / (Load_kW * 1000) * 60 * 0.85.
  └── Broadcast autonomy estimate to NOC console every 60 seconds.
Step 3: Load Prioritization
  ├── If autonomy < 15 minutes and generator failed:
  │   └── Trigger Tier-2 non-critical server graceful shutdown notification.
```

### SOP-03: Battery Cell Imbalance & Thermal Hazard Prevention

```
Step 1: Cell Imbalance Detection
  ├── Condition: Max(V_cell) - Min(V_cell) > 50mV under steady float charging.
  └── Flag specific Cell ID (e.g., String 2, Cell 18).
Step 2: Thermal Delta Verification
  ├── Measure Temp(Cell_suspicious) - Temp(Ambient).
  ├── If Delta T > 5°C: High probability of internal micro-short / dry-out.
Step 3: Safe Mitigation Plan
  ├── R1 Recommendation: Lower rectifier float voltage from 2.27V/cell to 2.23V/cell temporarily.
  └── R4 Request: Request physical maintenance ticket to isolate or replace defective block.
```

---

## 4. Governance & Safety Bounds (R0–R5)

This skill operates under strict boundaries defined in `AGENTS.md` and `quan_ai_brain.governance.policy`:

| Risk Tier | Permitted Autonomous Actions | Restricted / Prohibited Actions |
| :---: | :--- | :--- |
| **R0** | Read telemetry, parse logs, query database, compute statistics, render graphs. | Modifying any system configuration. |
| **R1** | Dry-run simulations, plan creation, validating threshold compliance. | Writing to external control APIs. |
| **R2** | Creating temporary local report files in `data/` or `reports/`. | Overwriting existing production configs. |
| **R3** | Non-invasive diagnostics (ping, SNMP walk, query Modbus read registers). | Modifying Modbus holding registers (write). |
| **R4** | Staging an approved equipment failover plan (requires 2FA Owner Approval). | Executing failover without verified signature. |
| **R5** | **STRICTLY BLOCKED**: Trip circuit breaker, shut down main UPS, wipe telemetry DB. | No bypass or override secret exists. |

---

## 5. Structured Diagnostic Output Contract

When reporting incidents or audits, always output structured JSON matching this schema:

```json
{
  "incident_id": "INC-20261027-NOC01",
  "timestamp_utc": "2026-10-27T05:30:00Z",
  "domain": "COOLING",
  "severity": "WARNING",
  "location": "DATA_CENTER_ROOM_A / ROW_03",
  "telemetry": {
    "sensor_id": "TEMP-RACK-03-TOP",
    "measured_value": 26.8,
    "unit": "CELSIUS",
    "threshold": 24.0,
    "delta": 2.8
  },
  "root_cause_analysis": {
    "hypothesis": "CRAC-02 compressor stage 2 tripped; adjacent air volume insufficient.",
    "confidence_score": 0.92,
    "correlated_signals": ["CRAC-02-ALARM-COMPRESSOR", "FAN-SPEED-SATURATED"]
  },
  "recommended_plan": [
    {
      "step": 1,
      "risk_level": "R0",
      "action": "Increase CRAC-01 standby airflow setpoint to 85%",
      "requires_owner_approval": false
    },
    {
      "step": 2,
      "risk_level": "R4",
      "action": "Restart CRAC-02 controller via management bus",
      "requires_owner_approval": true
    }
  ],
  "safety_status": "NORMAL_OPERATION"
}
```
