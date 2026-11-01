---
name: battery-health-intelligence
description: |
  Advanced Industrial Battery Health Intelligence, Diagnostics & Prognostics.
  Use when analyzing, modeling, diagnosing, or predicting the condition of UPS and Data Center battery systems (VRLA, AGM, Gel, and LiFePO4):
    1. State of Health (SoH) and State of Charge (SoC) quantification.
    2. Internal resistance (Ri / Conductance) drift analysis and baseline comparison.
    3. Cell-to-cell voltage divergence and string imbalance detection.
    4. Thermal runaway risk early warning and temperature delta monitoring.
    5. Causal Root Cause Analysis (RCA) for failure modes: sulfation, dry-out, grid corrosion, thermal short.
    6. Remaining Useful Life (RUL) estimation and replacement scheduling.
    7. Safe battery testing procedures (strict R0-R3 telemetry, R4 discharge testing gate).
license: Apache-2.0
metadata:
  version: v2.0.0
  domain: Battery Energy Storage & Telecommunications Power
  governance: Strict Learning Bounds & R0-R5 Policy Matrix
---

# Battery Health Intelligence & Prognostics Engine

A scientific, standard-aligned operational skill for monitoring, diagnosing, and predicting industrial battery fleet health across Telecom Central Offices, Data Centers, and UPS systems.

> [!IMPORTANT]
> **Safety & Ground Truth Verification Standard**:
> 1. **Discharge Test as Ultimate Ground Truth**: Electrochemical impedance spectroscopy (EIS) and continuous float voltage are predictive indicators. Only verified discharge tests ($C_{actual}$) confer ground truth status to SoH claims.
> 2. **Thermal Disconnect Threshold**: If any individual cell temperature exceeds ambient by $> 8.0^\circ\text{C}$ during float or displays $\frac{dT}{dt} > 1.5^\circ\text{C/min}$, flag an immediate thermal runaway alert.
> 3. **R4 Authorization for Discharge Testing**: Automated discharge testing imposes operational risk and requires explicit owner-approved scheduling.

---

## 1. Electrochemical Diagnostic Metrics & Equations

### 1.1 State of Health (SoH)
SoH reflects the current usable capacity of a battery compared to its factory rated nameplate capacity:

$$\text{SoH} (\%) = \frac{C_{\text{actual}} (\text{Ah})}{C_{\text{nominal}} (\text{Ah})} \times 100\%$$

- **Good / Optimal**: $\text{SoH} \ge 80.0\%$
- **Degraded / Warning**: $70.0\% \le \text{SoH} < 80.0\%$ (Prepare replacement staging)
- **End of Life (EOL) / Critical**: $\text{SoH} < 70.0\%$ or IEEE 450/1188 threshold: $< 80\%$ for mission-critical Tier III/IV Data Centers.

### 1.2 State of Charge (SoC) via Hybrid Method
Combines Open Circuit Voltage (OCV) curve mapping at rest with Coulomb Counting during charge/discharge:

$$\text{SoC}(t) = \text{SoC}(t_0) + \frac{1}{C_{\text{nominal}}} \int_{t_0}^t \eta \cdot I(\tau) \, d\tau$$

Where $\eta$ is Coulombic efficiency ($\approx 0.95$ for VRLA, $\approx 0.99$ for LFP).

### 1.3 Internal Resistance ($R_i$) & Conductance
Internal resistance measures the ohmic and polarization resistance of the cell. Under step load changes $\Delta I$:

$$R_i = \frac{\Delta V}{\Delta I} = \frac{V_{\text{float}} - V_{\text{load}}}{I_{\text{load}}}$$

- **Healthy Baseline**: $R_i \le 1.15 \times R_{\text{baseline}}$
- **Degraded**: $1.15 \times R_{\text{baseline}} < R_i \le 1.30 \times R_{\text{baseline}}$
- **Failure Pending**: $R_i > 1.50 \times R_{\text{baseline}}$ (Internal plate degradation or dry-out)

### 1.4 Cell Voltage Divergence ($\Delta V_{\text{cell}}$)
Across a series string of $N$ cells under steady float charge ($T_{\text{ambient}} = 25^\circ\text{C}$):

$$\Delta V = \max_{k}(V_k) - \min_{k}(V_k)$$

- **Balanced**: $\Delta V < 25\text{ mV}$
- **Imbalance Warning**: $25\text{ mV} \le \Delta V < 50\text{ mV}$
- **Severe Defect / Micro-Short**: $\Delta V \ge 50\text{ mV}$ (Float) or $\Delta V \ge 200\text{ mV}$ (Discharge)

---

## 2. Causal Root Cause Analysis (RCA) Decision Tree

When battery telemetry anomalies occur, execute this deterministic diagnostic procedure:

```
Telemetry Anomaly Triggered
 ├── Scenario A: High Ri (> 130% baseline) + Low Float Voltage (< 2.18V/cell)
 │    └── Root Cause: Plate Sulfation (Lead Sulfate crystallization due to prolonged undercharging).
 │    └── Remedy: Controlled Equalize Charge (R3/R4) or individual block reconditioning.
 │
 ├── Scenario B: High Ri (> 150% baseline) + High Cell Temp (Delta T > 4°C) + Normal Float V
 │    └── Root Cause: Electrolyte Dry-out (Micro-venting, valve seal failure).
 │    └── Remedy: Permanent physical replacement required. Cannot be regenerated.
 │
 ├── Scenario C: Low Float Voltage (< 2.05V/cell) + High Float Current + Temp Spike
 │    └── Root Cause: Internal Short Circuit (Dendrite growth or separator breakdown).
 │    └── Remedy: IMMEDIATE BLOCK ISOLATION (Thermal hazard).
 │
 ├── Scenario D: High Overall String Voltage + Normal Temp + All Ri High
 │    └── Root Cause: Rectifier Float Voltage Drift (Overcharging setting).
 │    └── Remedy: Calibrate Rectifier voltage temperature-compensation curve (mV/°C/cell).
 │
 └── Scenario E: Capacity drop during discharge test without high Ri
      └── Root Cause: Positive Grid Corrosion / Active Material Loss (Age-related fatigue).
      └── Remedy: Scheduled string replacement based on RUL curve.
```

---

## 3. Prognostic Remaining Useful Life (RUL) Modeling

The engine models degradation rate by combining Arrhenius thermal acceleration ($k_T$) and cycle fatigue ($k_C$):

$$\text{RUL}_{\text{months}} = \frac{\text{SoH}_{\text{current}} - \text{SoH}_{\text{EOL}}}{\text{Degradation Rate}_{\text{effective}}}$$

$$\text{Degradation Rate}_{\text{effective}} = \text{Base Rate} \times 2^{\frac{T_{\text{avg}} - 25}{10}} \times \left(1 + \beta \cdot N_{\text{deep-discharges}}\right)$$

*Rule of Thumb (Arrhenius Rule)*: For every $10^\circ\text{C}$ continuous operating temperature above $25^\circ\text{C}$, VRLA battery service life is cut by **50%**.

---

## 4. Operational Telemetry Checklist (SOP-BAT-01)

### Daily Automated Scan (R0)
1. Read string total voltage, string charging/discharging current.
2. Read all individual cell voltages ($V_1 \dots V_N$).
3. Identify min, max, average, and standard deviation $\sigma_V$.
4. Check temperature probe telemetry across positive terminals and ambient sensors.
5. Compute daily cell divergence delta $\Delta V(t)$.

### Monthly Impedance / Conductance Audit (R0/R1)
1. Collect internal resistance measurements $R_{i,k}$.
2. Compare each cell against initial installation commissioning baseline ($R_{\text{baseline},k}$).
3. Sort top 3 worst-performing blocks and append to monthly maintenance report.

### Annual Controlled Capacity Discharge Test (R4 Gate)
1. **Prerequisite Check**: Confirm alternative backup path (redundant UPS or dual feed) is fully operational.
2. **Ambient Temp Verification**: Verify room temperature is between $20^\circ\text{C} - 25^\circ\text{C}$. Cancel if $> 28^\circ\text{C}$.
3. **Owner Authorization**: Discharge test requires verified owner approval signature (`OwnerSignatureVerifier`).
4. **Discharge Execution**: Log voltage curves at 100%, 80%, 50%, 20%, and final cutoff voltage (1.75V/cell for VRLA).
5. **Ground Truth Registration**: Compute actual Ah and promote SoH metrics from `PREDICTED` to `VERIFIED`.

---

## 5. Output JSON Contract

```json
{
  "system_id": "UPS-01-BATTERY-STRING-A",
  "chemistry": "VRLA-AGM",
  "cell_count": 24,
  "nominal_capacity_ah": 200.0,
  "timestamp_utc": "2026-10-27T05:35:00Z",
  "health_metrics": {
    "soh_pct": 78.4,
    "soh_confidence": 0.88,
    "soh_status": "DEGRADED",
    "soc_pct": 99.8,
    "string_voltage": 53.76,
    "string_current_amps": 0.42,
    "max_cell_voltage": 2.264,
    "min_cell_voltage": 2.198,
    "voltage_delta_mv": 66.0,
    "worst_cell_id": "CELL-14",
    "max_temperature_c": 26.2,
    "ambient_temperature_c": 22.8
  },
  "root_cause_analysis": {
    "failure_mode": "SULFATION_AND_EARLY_DRYOUT",
    "culprit_cells": ["CELL-14"],
    "evidence": "Cell 14 float voltage depressed to 2.198V with Ri increased by 38% above string baseline."
  },
  "prognosis": {
    "estimated_rul_months": 7.5,
    "recommended_action": "Stage replacement for Cell-14 block; avoid deep discharges exceeding 30 minutes."
  }
}
```
