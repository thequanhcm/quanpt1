# -*- coding: utf-8 -*-
"""Test CPSL Phase B dataset — 70 public + 30 hidden tách vật lý."""
import json, os
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parent.parent
PUBLIC = ROOT / "data" / "cognitive" / "cpsl" / "cpsl_phase_b_70.json"
HIDDEN = ROOT / "data" / "cognitive" / "cpsl" / "hidden" / "cpsl_hidden_30.json"


def test_public_dataset_exists():
    assert PUBLIC.exists(), f"Missing {PUBLIC}"


def test_public_has_70_cases():
    ds = json.loads(PUBLIC.read_text(encoding="utf-8"))
    assert len(ds["cases"]) == 70, f"Expected 70, got {len(ds['cases'])}"


def test_public_case_ids_unique():
    ds = json.loads(PUBLIC.read_text(encoding="utf-8"))
    ids = [c["case_id"] for c in ds["cases"]]
    assert len(ids) == len(set(ids)), "Duplicate case_id in public"


def test_public_all_have_ground_truth():
    ds = json.loads(PUBLIC.read_text(encoding="utf-8"))
    for c in ds["cases"]:
        assert "ground_truth" in c, f"{c['case_id']} missing ground_truth"
        assert "root_cause" in c["ground_truth"], f"{c['case_id']} missing root_cause"
        assert len(c["ground_truth"]["root_cause"]) > 10, f"{c['case_id']} root_cause too short"


def test_hidden_dataset_exists():
    assert HIDDEN.exists(), f"Missing {HIDDEN}"


def test_hidden_has_30_cases():
    ds = json.loads(HIDDEN.read_text(encoding="utf-8"))
    assert len(ds["cases"]) == 30, f"Expected 30, got {len(ds['cases'])}"


def test_hidden_ids_dont_overlap_public():
    pub = json.loads(PUBLIC.read_text(encoding="utf-8"))
    hid = json.loads(HIDDEN.read_text(encoding="utf-8"))
    pub_ids = {c["case_id"] for c in pub["cases"]}
    hid_ids = {c["case_id"] for c in hid["cases"]}
    overlap = pub_ids & hid_ids
    assert not overlap, f"Overlap: {overlap}"


def test_hidden_not_in_gitignore_violation():
    """Hidden dir phải có trong .gitignore."""
    gi = (ROOT / ".gitignore").read_text(encoding="utf-8")
    assert "cpsl/hidden/" in gi, "Hidden dir not in .gitignore — sẽ bị commit!"


def test_hidden_not_referenced_in_code():
    """Hidden KHÔNG được reference trong src/ hoặc tools/."""
    import subprocess
    for subdir in ["src", "tools"]:
        r = subprocess.run(
            ["python", "-c", f"""
import os
refs = []
for root, dirs, files in os.walk(r'{ROOT / subdir}'):
    for f in files:
        if f.endswith('.py'):
            txt = open(os.path.join(root, f), encoding='utf-8', errors='ignore').read()
            if 'cpsl_hidden' in txt or 'cpsl/hidden' in txt:
                refs.append(os.path.join(root, f))
print('\n'.join(refs) if refs else 'OK')
"""],
            capture_output=True, text=True, timeout=30
        )
        assert "OK" in r.stdout or r.stdout.strip() == "", f"Hidden referenced in {subdir}: {r.stdout}"


def test_hidden_variants_have_different_scenario():
    """Hidden case phải có scenario khác public (biến thể)."""
    pub = json.loads(PUBLIC.read_text(encoding="utf-8"))
    hid = json.loads(HIDDEN.read_text(encoding="utf-8"))
    # Lấy 5 hidden đầu, so sánh với public tương ứng
    for h in hid["cases"][:5]:
        orig_id = h["case_id"].replace("CPSL-HID-", "CPSL-MIN-")
        orig = next((c for c in pub["cases"] if c["case_id"] == orig_id), None)
        assert orig is not None, f"No public match for {h['case_id']}"
        assert h["input"]["scenario"] != orig["input"]["scenario"], f"{h['case_id']} not variant"
