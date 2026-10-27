---
name: industrial-ocr-equipment-reader
description: |
  Industrial Computer Vision & OCR Label Reader for Telecom & Data Center Equipment.
  Use when analyzing, reading, or verifying text, barcodes, and technical specifications from photographs of physical equipment:
    1. Telecom rack IDs, device serials, shelf numbers, port/slot labels, and ODF fiber markings.
    2. Battery nameplates and manufacturer stamps (Brand, Model, Nominal Voltage V, Capacity Ah, Date Code, Batch).
    3. Power cabinets, UPS ratings, breaker tags, and warning decals.
    4. Image pre-processing (deskew, bilateral denoising, adaptive thresholding, contrast enhancement).
    5. Dual-engine OCR extraction (EasyOCR with Vietnamese/English + Tesseract fallback).
    6. Structured regex tokenization and JSON schema validation with confidence scores.
license: Apache-2.0
metadata:
  version: v2.0.0
  domain: Industrial Computer Vision & Edge Asset Verification
  governance: Read-Only R0 Analysis & Evidence Provenance
---

# Industrial OCR Equipment & Nameplate Reader

An intelligent computer vision and optical character recognition (OCR) skill tailored for automated physical asset auditing, telecom room inspections, and battery bank nameplate extraction.

> [!IMPORTANT]
> **Deterministic Read-Only Guarantee**:
> 1. This skill is strictly **R0 (Read-Only)**. It analyzes images from `data/edge_media/captures/` or operator uploads, extracts text, and generates structured observations. It never writes to production equipment.
> 2. **Confidence-Gated Acceptance**: Extracted fields with confidence $\ge 85\%$ are tagged as `OBSERVED`. Fields with confidence $< 85\%$ are marked `UNVERIFIED / NEEDS_REVIEW` to prevent dirty data ingestion.

---

## 1. Processing Pipeline Architecture

```
 Raw Input Photo (Mobile / Pi Camera / Webcam)
                      │
                      ▼
 ┌────────────────────────────────────────────────────────┐
 │             Computer Vision Pre-Processing             │
 │  • Grayscale conversion & Contrast adjustment (CLAHE)   │
 │  • Bilateral Denoising (Preserving sharp edge fonts)   │
 │  • Perspective deskew & bounding box cropping         │
 └────────────────────┬───────────────────────────────────┘
                      │
                      ▼
 ┌────────────────────────────────────────────────────────┐
 │                Dual-Engine OCR Engine                  │
 │  • Primary: EasyOCR (en, vi models with GPU/CPU)       │
 │  • Fallback: Tesseract OCR (LSTM line segmentation)    │
 └────────────────────┬───────────────────────────────────┘
                      │
                      ▼
 ┌────────────────────────────────────────────────────────┐
 │           Domain Regex & Grammar Tokenizer             │
 │  • Telecom syntax: Rack, Slot, ODF, Shelf, Device ID   │
 │  • Battery syntax: Brand, Model, V, Ah, Date, Batch    │
 └────────────────────┬───────────────────────────────────┘
                      │
                      ▼
 ┌────────────────────────────────────────────────────────┐
 │       Confidence Verification & Memory Handoff         │
 │  • Status: OBSERVED (≥85%) or UNVERIFIED (<85%)        │
 │  • Quarantine candidate output for owner confirmation │
 └────────────────────────────────────────────────────────┘
```

---

## 2. Industrial Grammar & Regex Tokenization

The tokenizer parses raw OCR strings into structured equipment identities using specialized telecom and power industry grammars:

### 2.1 Telecom Room & Data Center Syntax
| Field | Regex Pattern | Example Matches |
| :--- | :--- | :--- |
| **Rack Name** | `\b[A-Z0-9]+_R[0-9]+_G[0-9]+\b` | `PDL1_R21_G02`, `HNI2_R05_G01` |
| **Device Code** | `\bPDL[0-9A-Z]{5,15}\b` | `PDL9102DWP31`, `PDL9202MSAN01` |
| **ODF Fiber Cable** | `\bPDL[0-9]+MOF[0-9A-Z]+ODF[0-9A-Z]+(?:[/\s]*[0-9,\.]+)?\b` | `PDL9202MOF06ODF14A/ 09,10` |
| **Port / Slot** | `\b(?:SL\|Slot)\s*[0-9]+(?:/[0-9A-Za-z\.]+)?\b` | `SL1/P.IN`, `Slot 3/2`, `SL5/3` |
| **Shelf Number** | `\bShelf\s*[0-9]+\b` | `Shelf 6`, `Shelf 12` |
| **Node ID** | `\bDXC[0-9]+\b` | `DXC4`, `DXC12` |
| **Customer** | `\b(?:KH\|Khách hàng\|Cty\|Customer)\s+[A-Za-z0-9\s\.\-]+\b` | `KH Techcombank`, `Khách hàng AWS` |

### 2.2 Battery Nameplate & Power Equipment Syntax
| Field | Regex Pattern | Example Matches |
| :--- | :--- | :--- |
| **Brand** | `\b(VISION\|CSB\|NARADA\|LEOCH\|YUASA\|BB\|ENERSYS\|FIAMM\|ROCKET)\b` | `VISION`, `CSB`, `NARADA` |
| **Model** | `\b([A-Z]{1,4}[0-9]{1,4}[A-Z]{0,3}(?:-[0-9A-Z]+)?)\b` | `6FM100-X`, `GPL121000`, `NP100-12` |
| **Nominal Voltage**| `\b([0-9]{1,2})\s*(?:V\|Volt\|VDC)\b` | `12V`, `2V`, `48 V` |
| **Rated Capacity** | `\b([0-9]{2,4}(?:\.[0-9]+)?)\s*(?:Ah\|AH\|Ampere-hour)\b` | `100Ah`, `150 Ah`, `200Ah` |
| **Discharge Rate** | `\b(?:10\|20\|5)\s*(?:HR\|hr\|Hour\|h)\b` | `10HR`, `20HR` |
| **Date Code** | `\b(20[1-3][0-9][\-\/.](?:0[1-9]\|1[0-2])[\-\/.](?:0[1-9]\|[12][0-9]\|3[01]))\b` | `2024-08-15`, `2023/11/02` |

---

## 3. Operational Procedure (SOP-OCR-01)

### Step 1: Pre-flight Image Check
- Verify image resolution is at least $800 \times 600$ pixels.
- Check blurriness metric using the Laplacian variance method: $\text{Var}(\nabla^2 I) \ge 100$. If $< 100$, request a clearer photo.

### Step 2: Denoising & Enhancement
- Apply OpenCV `fastNlMeansDenoising` or Bilateral Filter to remove digital grain while maintaining sharp edge letterforms.
- Apply Contrast Limited Adaptive Histogram Equalization (CLAHE) with `clipLimit=2.0`, `tileGridSize=(8,8)` to resolve glare or shadow gradients.

### Step 3: Dual-Engine Character Extraction
- Invoke EasyOCR with language tuple `['en', 'vi']`.
- Calculate token-level and line-level confidence scores:
  $$\text{Confidence}_{\text{overall}} = \frac{1}{M} \sum_{i=1}^M \text{conf}_i$$

### Step 4: Tokenization & Structured Validation
- Pass raw normalized text through `LabelParser`.
- Match against both Telecom patterns and Battery patterns.
- Cross-validate extracted capacity and voltage against known catalog bounds (e.g., standard VRLA: 2V or 12V; typical capacities: 26Ah, 50Ah, 100Ah, 150Ah, 200Ah).

### Step 5: Verification & Memory Ingestion
- Tag successful fields as `VerificationStatus.OBSERVED`.
- Write structured JSON to `data/edge_media/captures/<timestamp>_metadata.json`.
- Store provenance link pointing to raw image SHA-256 hash.

---

## 4. Structured Output Contract

```json
{
  "image_source": "data/edge_media/captures/20261027_054012_battery_cell12.jpg",
  "image_sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
  "timestamp_utc": "2026-10-27T05:40:12Z",
  "overall_confidence": 0.94,
  "equipment_type": "INDUSTRIAL_BATTERY",
  "parsed_data": {
    "brand": "VISION",
    "model": "6FM100-X",
    "nominal_voltage_v": 12.0,
    "rated_capacity_ah": 100.0,
    "discharge_rating": "10HR",
    "manufacturing_date": "2024-03-18",
    "batch_code": "V240318-09B"
  },
  "telecom_context": {
    "rack_location": "PDL1_R04_G01",
    "associated_ups": "UPS-02"
  },
  "verification_status": "OBSERVED",
  "audit_trail": "OCR verified with EasyOCR (en, vi); high confidence match across 6 fields."
}
```
