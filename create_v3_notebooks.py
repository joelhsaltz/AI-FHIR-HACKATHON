#!/usr/bin/env python3
"""
Create v3 hackathon notebooks from scratch for the SBU FHIR server.

V3 is a substantive content rewrite targeting 1,027 phenotype-structured
synthetic patients on the SBU LinuxForHealth FHIR server. Generates 6
notebooks: student + instructor variants for Sessions 1-3.

Usage:
    python create_v3_notebooks.py
"""

import json
import uuid
import os

# ──────────────────────────────────────────────────────────────
# Paths
# ──────────────────────────────────────────────────────────────

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
STUDENT_DIR = os.path.join(SCRIPT_DIR, "student_materials", "notebooks")
INSTRUCTOR_DIR = os.path.join(SCRIPT_DIR, "instructor_materials", "notebooks")

# ──────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────

def _id():
    return uuid.uuid4().hex[:8]


def code_cell(source):
    return {
        "cell_type": "code",
        "id": _id(),
        "metadata": {},
        "source": source,
        "execution_count": None,
        "outputs": [],
    }


def md_cell(source):
    return {
        "cell_type": "markdown",
        "id": _id(),
        "metadata": {},
        "source": source,
    }


def build_notebook(cells):
    return {
        "nbformat": 4,
        "nbformat_minor": 5,
        "metadata": {
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3",
            },
            "language_info": {
                "name": "python",
                "version": "3.10.0",
            },
        },
        "cells": cells,
    }


def write_notebook(nb, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(nb, f, indent=1, ensure_ascii=False)
        f.write("\n")
    print(f"  {os.path.basename(path)}: {len(nb['cells'])} cells")


# ──────────────────────────────────────────────────────────────
# Shared markdown content
# ──────────────────────────────────────────────────────────────

FHIR_BASE = "https://lfh-fhir.eastus2.cloudapp.azure.com:9443/fhir-server/api/v4"

PHENOTYPE_DESCRIPTION = """\
## About the Patient Population

This FHIR server contains **1,027 synthetic patients** generated with \
clinically coupled phenotypes. The patients are distributed across **6 \
clinical groups**:

| # | Phenotype | Description |
|---|-----------|-------------|
| 1 | **Metabolic syndrome** | Elevated BMI, blood pressure, triglycerides, \
and fasting glucose — but no diabetes diagnosis yet. |
| 2 | **Early Type 2 diabetes** | Recently diagnosed Type 2 diabetes with \
mildly elevated HbA1c. Kidney function is normal. |
| 3 | **Type 2 diabetes with chronic kidney disease stage G2** | Established \
Type 2 diabetes with mildly reduced kidney function (eGFR 60–89). |
| 4 | **Advanced Type 2 diabetes with chronic kidney disease stage G3b** | \
Long-standing Type 2 diabetes with moderately-to-severely reduced kidney \
function (eGFR 30–44). Often on insulin and multiple medications. |
| 5 | **Type 1 diabetes with early nephropathy** | Type 1 diabetes (the \
body's immune system destroys insulin-producing cells) with early signs of \
kidney damage. Very low C-peptide. |
| 6 | **Type 1 diabetes with poor control and chronic kidney disease stage \
G3a** | Type 1 diabetes with poor glycemic control (high HbA1c) and \
moderately reduced kidney function (eGFR 45–59). |

These phenotypes are **clinically coupled** — patients with worse diabetes \
control tend to have worse kidney function, mirroring real-world patterns."""

CLINICAL_CODE_REFERENCE = """\
## Clinical Code Reference

### Diagnosis Codes (SNOMED CT)

| Code | Condition | Notes |
|------|-----------|-------|
| 44054006 | Type 2 diabetes mellitus | The body becomes resistant to insulin |
| 46635009 | Type 1 diabetes mellitus | The immune system destroys insulin-producing cells |
| 709044004 | Chronic kidney disease | Gradual loss of kidney function over time |

### Observation Codes (LOINC)

| Code | Test | What It Measures |
|------|------|-----------------|
| 4548-4 | Hemoglobin A1c (HbA1c) | Average blood sugar over 2–3 months |
| 2160-0 | Creatinine | Waste product filtered by kidneys |
| 33914-3 | Estimated glomerular filtration rate (eGFR) | How well kidneys filter blood |
| 14959-1 | Urine albumin/creatinine ratio (UACR) | Protein leakage indicating kidney damage |
| 1986-9 | C-peptide | Marker of insulin production by the pancreas |
| 85354-9 | Blood pressure panel | Systolic and diastolic blood pressure |
| 39156-5 | Body mass index (BMI) | Weight relative to height |
| 1558-6 | Fasting glucose | Blood sugar after overnight fasting |
| 2339-0 | Blood glucose | Random blood sugar measurement |
| 3094-0 | Blood urea nitrogen (BUN) | Another kidney function marker |
| 13457-7 | LDL cholesterol | "Bad" cholesterol |
| 2085-9 | HDL cholesterol | "Good" cholesterol |
| 2571-8 | Triglycerides | Blood fat linked to heart disease risk |

### Interpretation Thresholds

| Measure | Range | Interpretation |
|---------|-------|----------------|
| HbA1c | < 5.7% | Normal |
| | 5.7% – 6.4% | Prediabetes |
| | ≥ 6.5% | Diabetes |
| | **> 7.5%** | **Poor glycemic control** |
| eGFR | > 90 | Normal kidney function |
| | 60–89 | Mildly decreased |
| | 45–59 | Moderately decreased |
| | 30–44 | Moderately-to-severely decreased |
| | < 30 | Severely decreased |
| UACR | < 30 mg/g | Normal |
| | 30–300 mg/g | Moderately increased albuminuria |
| | > 300 mg/g | Severely increased albuminuria |"""

FHIR_RESOURCE_DIAGRAM = """\
## How FHIR Resources Link Together

```
                    ┌─────────────┐
                    │   Patient   │
                    │  (who)      │
                    └──────┬──────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
       ┌──────▼──────┐ ┌──▼──────────┐ ┌▼────────────────┐
       │  Condition   │ │ Observation │ │MedicationRequest│
       │  (diagnosis) │ │ (lab/vital) │ │ (prescription)  │
       └─────────────┘ └─────────────┘ └─────────────────┘

Each resource has a "subject" reference pointing back to the Patient.
To answer clinical questions, you follow these references to connect
diagnoses → patients → lab results → medications.
```"""

T1_VS_T2_COMPARISON = """\
## Type 1 vs Type 2 Diabetes — A Quick Guide

Understanding the difference between Type 1 and Type 2 diabetes is essential \
for interpreting this patient population.

**Type 1 diabetes** — the body's immune system destroys the insulin-producing \
beta cells in the pancreas. Patients:
- Have **very low C-peptide** (a marker of insulin production)
- Are **insulin-dependent** from diagnosis
- Tend to be diagnosed younger
- Are often leaner (lower BMI)

**Type 2 diabetes** — the body becomes resistant to insulin. Patients:
- Have **preserved or elevated C-peptide** (the pancreas still produces insulin)
- Often start with oral medications (metformin, SGLT2 inhibitors, GLP-1 \
receptor agonists) before needing insulin
- Are often overweight (higher BMI)
- Tend to be diagnosed later in life

**Both types** can develop chronic kidney disease, but through somewhat \
different pathways and timelines.

**Key differentiating lab:** C-peptide (LOINC 1986-9) is the clearest \
discriminator between the two types. Low C-peptide suggests Type 1; \
preserved or high C-peptide suggests Type 2."""


# ──────────────────────────────────────────────────────────────
# Shared code strings
# ──────────────────────────────────────────────────────────────

SETUP_S1 = f"""\
!pip install requests pandas matplotlib

import requests
import urllib3
import json
import pandas as pd
import matplotlib.pyplot as plt
from IPython.display import display, HTML

# Suppress SSL warnings (self-signed cert on teaching server)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ---- FHIR Server Configuration ----
FHIR_BASE = "{FHIR_BASE}"

# Credentials (hardcoded — this is synthetic teaching data only)
FHIR_SESSION = requests.Session()
FHIR_SESSION.auth = ("fhiruser", "BmI512@ccess")
FHIR_SESSION.verify = False

# Helper for exploring JSON responses
def show_json(data, max_lines=30):
    \"\"\"Pretty-print JSON with optional truncation.\"\"\"
    text = json.dumps(data, indent=2)
    lines = text.split("\\n")
    if len(lines) > max_lines:
        print("\\n".join(lines[:max_lines]))
        print(f"\\n... ({{len(lines) - max_lines}} more lines)")
    else:
        print(text)

# Verify connection
resp = FHIR_SESSION.get(f"{{FHIR_BASE}}/metadata", params={{"_format": "json"}}, timeout=10)
if resp.status_code == 200:
    fhir_version = resp.json().get("fhirVersion", "unknown")
    print(f"\\u2705 Connected to FHIR server (version {{fhir_version}})")
    count_resp = FHIR_SESSION.get(
        f"{{FHIR_BASE}}/Patient",
        params={{"_summary": "count", "_format": "json"}},
        timeout=10
    )
    if count_resp.status_code == 200:
        total = count_resp.json().get("total", "unknown")
        print(f"   {{total}} patients available")
    print(f"   Authenticated as: fhiruser")
else:
    print(f"\\u274c Could not connect: HTTP {{resp.status_code}}")"""

SETUP_S23_PIP = """\
!pip install anthropic requests pandas matplotlib"""

SETUP_S23 = f"""\
!pip install -q anthropic requests pandas matplotlib

import os, json, requests, urllib3
import pandas as pd
import matplotlib.pyplot as plt
from anthropic import Anthropic

# Suppress SSL warnings (self-signed cert on teaching server)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ---- Anthropic Client ----
try:
    from google.colab import userdata
    api_key = userdata.get("ANTHROPIC_API_KEY")
except (ImportError, Exception):
    api_key = None

api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
if not api_key:
    raise ValueError(
        "Set ANTHROPIC_API_KEY in Colab Secrets (key icon in left sidebar) "
        "or as an environment variable."
    )

client = Anthropic(api_key=api_key)
MODEL = "claude-sonnet-4-20250514"

# ---- FHIR Server ----
FHIR_BASE = "{FHIR_BASE}"
FHIR_SESSION = requests.Session()
FHIR_SESSION.auth = ("fhiruser", "BmI512@ccess")
FHIR_SESSION.verify = False

# Verify connections
resp = FHIR_SESSION.get(f"{{FHIR_BASE}}/metadata", params={{"_format": "json"}}, timeout=10)
if resp.status_code == 200:
    fhir_version = resp.json().get("fhirVersion", "unknown")
    print(f"\\u2705 FHIR server connected (version {{fhir_version}})")
    count_resp = FHIR_SESSION.get(
        f"{{FHIR_BASE}}/Patient",
        params={{"_summary": "count", "_format": "json"}},
        timeout=10
    )
    if count_resp.status_code == 200:
        total = count_resp.json().get("total", "unknown")
        print(f"   {{total}} patients available")
else:
    print(f"\\u274c FHIR server error: HTTP {{resp.status_code}}")

print(f"\\u2705 Anthropic client ready (model: {{MODEL}})")"""

# ── Tool functions (5 base tools for S2/S3) ─────────────────

TOOL_FUNCTIONS_5 = """\
# ══════════════════════════════════════════════════════════════
# FHIR Tool Functions
# ══════════════════════════════════════════════════════════════

def search_conditions(code: str, max_results: int = 50) -> dict:
    \"\"\"Search for conditions by SNOMED CT code.\"\"\"
    resp = FHIR_SESSION.get(
        f"{FHIR_BASE}/Condition",
        params={"code": code, "_count": max_results, "_format": "json"},
        timeout=30,
    )
    bundle = resp.json()
    results = []
    for entry in bundle.get("entry", []):
        r = entry["resource"]
        coding = r.get("code", {}).get("coding", [{}])[0]
        results.append({
            "condition_id": r.get("id"),
            "code": coding.get("code", ""),
            "display": coding.get("display", ""),
            "patient_reference": r.get("subject", {}).get("reference", ""),
            "clinical_status": r.get("clinicalStatus", {}).get("coding", [{}])[0].get("code", ""),
        })
    return {"total": bundle.get("total"), "results": results}


def get_patient(patient_id: str) -> dict:
    \"\"\"Get a single patient's demographics.\"\"\"
    resp = FHIR_SESSION.get(
        f"{FHIR_BASE}/Patient/{patient_id}",
        params={"_format": "json"},
        timeout=30,
    )
    p = resp.json()
    name = p.get("name", [{}])[0]
    return {
        "id": p.get("id"),
        "name": f"{' '.join(name.get('given', []))} {name.get('family', '')}".strip(),
        "gender": p.get("gender", ""),
        "birthDate": p.get("birthDate", ""),
    }


def search_observations(patient_id: str, loinc_code: str, max_results: int = 5) -> dict:
    \"\"\"Search for observations by patient and LOINC code.\"\"\"
    resp = FHIR_SESSION.get(
        f"{FHIR_BASE}/Observation",
        params={
            "subject": f"Patient/{patient_id}",
            "code": loinc_code,
            "_count": max_results,
            "_sort": "-date",
            "_format": "json",
        },
        timeout=30,
    )
    bundle = resp.json()
    results = []
    for entry in bundle.get("entry", []):
        r = entry["resource"]
        value_qty = r.get("valueQuantity", {})
        result_entry = {
            "observation_id": r.get("id"),
            "code": r.get("code", {}).get("coding", [{}])[0].get("code", ""),
            "display": r.get("code", {}).get("coding", [{}])[0].get("display", ""),
            "value": value_qty.get("value"),
            "unit": value_qty.get("unit", ""),
            "date": r.get("effectiveDateTime", ""),
        }
        # Handle component-based observations (e.g., blood pressure)
        if not value_qty.get("value") and r.get("component"):
            components = []
            for comp in r["component"]:
                comp_code = comp.get("code", {}).get("coding", [{}])[0]
                comp_val = comp.get("valueQuantity", {})
                components.append({
                    "component": comp_code.get("display", ""),
                    "value": comp_val.get("value"),
                    "unit": comp_val.get("unit", ""),
                })
            result_entry["components"] = components
        results.append(result_entry)
    return {"total": bundle.get("total"), "results": results}


def search_medications(patient_id: str, max_results: int = 10) -> dict:
    \"\"\"Search for medication requests for a patient.\"\"\"
    resp = FHIR_SESSION.get(
        f"{FHIR_BASE}/MedicationRequest",
        params={
            "subject": f"Patient/{patient_id}",
            "_count": max_results,
            "_format": "json",
        },
        timeout=30,
    )
    bundle = resp.json()
    results = []
    for entry in bundle.get("entry", []):
        r = entry["resource"]
        med_concept = r.get("medicationCodeableConcept", {})
        coding = med_concept.get("coding", [{}])[0] if med_concept.get("coding") else {}
        med_name = coding.get("display") or med_concept.get("text", "unknown")
        results.append({
            "medication": med_name,
            "code": coding.get("code", ""),
            "status": r.get("status", ""),
            "date": r.get("authoredOn", ""),
        })
    return {"total": bundle.get("total"), "results": results}


def search_all_conditions(patient_id: str, max_results: int = 20) -> dict:
    \"\"\"Get all conditions (full problem list) for a specific patient.\"\"\"
    resp = FHIR_SESSION.get(
        f"{FHIR_BASE}/Condition",
        params={
            "subject": f"Patient/{patient_id}",
            "_count": max_results,
            "_format": "json",
        },
        timeout=30,
    )
    bundle = resp.json()
    results = []
    for entry in bundle.get("entry", []):
        r = entry["resource"]
        coding = r.get("code", {}).get("coding", [{}])[0]
        results.append({
            "condition_id": r.get("id"),
            "code": coding.get("code", ""),
            "display": coding.get("display", ""),
            "clinical_status": r.get("clinicalStatus", {}).get("coding", [{}])[0].get("code", ""),
        })
    return {"total": bundle.get("total"), "results": results}


# ---- Smoke tests ----
print("Testing tool functions...")
_test = search_conditions("44054006", max_results=3)
print(f"  search_conditions('44054006'): {_test['total']} conditions found")
if _test["results"]:
    _pid = _test["results"][0]["patient_reference"].split("/")[-1]
    _p = get_patient(_pid)
    print(f"  get_patient('{_pid}'): {_p['name']}")
    _obs = search_observations(_pid, "4548-4", max_results=1)
    print(f"  search_observations(HbA1c): {_obs['total']} observations")
    _meds = search_medications(_pid)
    print(f"  search_medications: {_meds['total']} medications")
    _conds = search_all_conditions(_pid)
    print(f"  search_all_conditions: {_conds['total']} conditions")
print("\\u2705 All tools working")"""

# ── Extra tool functions for S3 ──────────────────────────────

TOOL_FUNCTIONS_2_EXTRA = """\
# ══════════════════════════════════════════════════════════════
# Additional Session 3 Tool Functions
# ══════════════════════════════════════════════════════════════

def search_encounters(patient_id: str, max_results: int = 10) -> dict:
    \"\"\"Search for clinical encounters (visits) for a patient.\"\"\"
    resp = FHIR_SESSION.get(
        f"{FHIR_BASE}/Encounter",
        params={
            "subject": f"Patient/{patient_id}",
            "_count": max_results,
            "_sort": "-date",
            "_format": "json",
        },
        timeout=30,
    )
    bundle = resp.json()
    results = []
    for entry in bundle.get("entry", []):
        r = entry["resource"]
        enc_type = r.get("type", [{}])[0].get("text", "") if r.get("type") else ""
        results.append({
            "encounter_id": r.get("id"),
            "status": r.get("status", ""),
            "class": r.get("class", {}).get("code", ""),
            "type": enc_type,
            "period_start": r.get("period", {}).get("start", ""),
            "period_end": r.get("period", {}).get("end", ""),
        })
    return {"total": bundle.get("total"), "results": results}


def search_patients(max_results: int = 50) -> dict:
    \"\"\"Search for patients — batch demographics retrieval.\"\"\"
    resp = FHIR_SESSION.get(
        f"{FHIR_BASE}/Patient",
        params={"_count": max_results, "_format": "json"},
        timeout=30,
    )
    bundle = resp.json()
    results = []
    for entry in bundle.get("entry", []):
        p = entry["resource"]
        name = p.get("name", [{}])[0]
        results.append({
            "id": p.get("id"),
            "name": f"{' '.join(name.get('given', []))} {name.get('family', '')}".strip(),
            "gender": p.get("gender", ""),
            "birthDate": p.get("birthDate", ""),
        })
    return {"total": bundle.get("total"), "results": results}"""

S3_SMOKE_TESTS = """\
# ---- Test Session 3 tools ----
print("Testing additional tools...")
if _test["results"]:
    _enc = search_encounters(_pid)
    print(f"  search_encounters: {_enc['total']} encounters")
_pts = search_patients(max_results=5)
print(f"  search_patients: {_pts['total']} total patients")
print("\\u2705 All 7 tools working")"""

# ── Tool schemas ─────────────────────────────────────────────

TOOL_SCHEMAS_5 = """\
# ══════════════════════════════════════════════════════════════
# Tool Schemas — what the LLM sees
# ══════════════════════════════════════════════════════════════

tools = [
    {
        "name": "search_conditions",
        "description": (
            "Search for patient conditions by SNOMED CT diagnosis code. "
            "Returns matching conditions with patient references. "
            "Common codes: 44054006 (Type 2 diabetes mellitus), "
            "46635009 (Type 1 diabetes mellitus), "
            "709044004 (chronic kidney disease)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "SNOMED CT code (e.g., '44054006' for Type 2 diabetes)",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum results to return (default: 50)",
                },
            },
            "required": ["code"],
        },
    },
    {
        "name": "get_patient",
        "description": (
            "Retrieve demographics for a single patient by ID. "
            "Returns name, gender, and birth date."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "patient_id": {
                    "type": "string",
                    "description": "The patient ID (from a condition's patient_reference, e.g., 'abc123')",
                },
            },
            "required": ["patient_id"],
        },
    },
    {
        "name": "search_observations",
        "description": (
            "Search for clinical observations (lab results, vitals) for a patient "
            "by LOINC code. Returns values sorted by date (most recent first). "
            "Common codes: 4548-4 (HbA1c), 2160-0 (creatinine), 33914-3 (eGFR), "
            "1986-9 (C-peptide), 14959-1 (urine albumin/creatinine ratio), "
            "85354-9 (blood pressure), 39156-5 (BMI), 1558-6 (fasting glucose), "
            "2339-0 (blood glucose), 3094-0 (BUN), 13457-7 (LDL cholesterol), "
            "2085-9 (HDL cholesterol), 2571-8 (triglycerides)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "patient_id": {
                    "type": "string",
                    "description": "The patient ID",
                },
                "loinc_code": {
                    "type": "string",
                    "description": "LOINC code for the observation (e.g., '4548-4' for HbA1c)",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum results to return (default: 5)",
                },
            },
            "required": ["patient_id", "loinc_code"],
        },
    },
    {
        "name": "search_medications",
        "description": (
            "Search for medication prescriptions (MedicationRequest resources) "
            "for a patient. Returns medication name, status, and date."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "patient_id": {
                    "type": "string",
                    "description": "The patient ID",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum results to return (default: 10)",
                },
            },
            "required": ["patient_id"],
        },
    },
    {
        "name": "search_all_conditions",
        "description": (
            "Retrieve the complete problem list (all diagnoses) for a specific "
            "patient. Unlike search_conditions which finds patients by one "
            "diagnosis code, this returns ALL conditions for one patient."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "patient_id": {
                    "type": "string",
                    "description": "The patient ID",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum results to return (default: 20)",
                },
            },
            "required": ["patient_id"],
        },
    },
]

available_functions = {
    "search_conditions": search_conditions,
    "get_patient": get_patient,
    "search_observations": search_observations,
    "search_medications": search_medications,
    "search_all_conditions": search_all_conditions,
}"""

TOOL_SCHEMAS_2_EXTRA = """\
# ── Add Session 3 tools ──────────────────────────────────────

tools.extend([
    {
        "name": "search_encounters",
        "description": (
            "Search for clinical encounters (visits) for a patient. "
            "Returns encounter type, status, class (ambulatory, emergency, "
            "inpatient), and dates."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "patient_id": {
                    "type": "string",
                    "description": "The patient ID",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum results to return (default: 10)",
                },
            },
            "required": ["patient_id"],
        },
    },
    {
        "name": "search_patients",
        "description": (
            "Search for patients on the server. Returns demographics (name, "
            "gender, birth date) for multiple patients at once. Useful for "
            "getting an overview of the patient population."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "max_results": {
                    "type": "integer",
                    "description": "Maximum results to return (default: 50)",
                },
            },
            "required": [],
        },
    },
])

available_functions["search_encounters"] = search_encounters
available_functions["search_patients"] = search_patients

print(f"\\u2705 {len(tools)} tools registered: {[t['name'] for t in tools]}")"""

# ── System prompts ───────────────────────────────────────────

SYSTEM_PROMPT_S2 = r'''
SYSTEM_PROMPT = """You are a clinical data assistant with access to a FHIR \
server containing synthetic patient records.

PATIENT POPULATION: The server has approximately 1,027 patients across 6 \
clinical phenotypes:
1. Metabolic syndrome
2. Early Type 2 diabetes
3. Type 2 diabetes with chronic kidney disease stage G2
4. Advanced Type 2 diabetes with chronic kidney disease stage G3b
5. Type 1 diabetes with early nephropathy
6. Type 1 diabetes with poor control and chronic kidney disease stage G3a

DIAGNOSIS CODES (SNOMED CT):
- 44054006: Type 2 diabetes mellitus
- 46635009: Type 1 diabetes mellitus
- 709044004: Chronic kidney disease

OBSERVATION CODES (LOINC):
- 4548-4: Hemoglobin A1c (HbA1c) — glycemic control marker
- 2160-0: Creatinine — kidney function marker
- 33914-3: Estimated glomerular filtration rate (eGFR) — kidney function
- 14959-1: Urine albumin/creatinine ratio (UACR) — kidney damage marker
- 1986-9: C-peptide — insulin production marker (low in Type 1, normal/high in Type 2)
- 85354-9: Blood pressure panel
- 39156-5: Body mass index (BMI)
- 1558-6: Fasting glucose
- 2339-0: Blood glucose
- 3094-0: Blood urea nitrogen (BUN)
- 13457-7: LDL cholesterol
- 2085-9: HDL cholesterol
- 2571-8: Triglycerides

INTERPRETATION THRESHOLDS:
- HbA1c > 7.5%: poor glycemic control
- eGFR < 60 mL/min/1.73m²: impaired kidney function
- eGFR < 30: severely impaired kidney function
- UACR > 30 mg/g: moderately increased albuminuria
- UACR > 300 mg/g: severely increased albuminuria

STRATEGY — think step by step:
1. Identify the condition(s) relevant to the question using search_conditions
2. Extract patient references from the condition results
3. Get patient demographics with get_patient
4. Look up relevant observations using the appropriate LOINC codes
5. Check medications if relevant to the question
6. Synthesize findings into a clear clinical summary

RULES:
- NEVER invent or hallucinate data. Only report values actually returned by tools.
- If a tool returns no results for a patient, state that explicitly.
- Always identify patients by name when available.
- Show actual lab values, not just categories.
- When comparing groups, provide counts and specific values.
- Be thorough: check all relevant patients, not just the first few.
"""
'''

SYSTEM_PROMPT_S3 = r'''
SYSTEM_PROMPT = """You are a clinical data assistant with access to a FHIR \
server containing synthetic patient records.

PATIENT POPULATION: The server has approximately 1,027 patients across 6 \
clinical phenotypes:
1. Metabolic syndrome
2. Early Type 2 diabetes
3. Type 2 diabetes with chronic kidney disease stage G2
4. Advanced Type 2 diabetes with chronic kidney disease stage G3b
5. Type 1 diabetes with early nephropathy
6. Type 1 diabetes with poor control and chronic kidney disease stage G3a

DIAGNOSIS CODES (SNOMED CT):
- 44054006: Type 2 diabetes mellitus
- 46635009: Type 1 diabetes mellitus
- 709044004: Chronic kidney disease

OBSERVATION CODES (LOINC):
- 4548-4: Hemoglobin A1c (HbA1c) — glycemic control marker
- 2160-0: Creatinine — kidney function marker
- 33914-3: Estimated glomerular filtration rate (eGFR) — kidney function
- 14959-1: Urine albumin/creatinine ratio (UACR) — kidney damage marker
- 1986-9: C-peptide — insulin production marker (low in Type 1, normal/high in Type 2)
- 85354-9: Blood pressure panel
- 39156-5: Body mass index (BMI)
- 1558-6: Fasting glucose
- 2339-0: Blood glucose
- 3094-0: Blood urea nitrogen (BUN)
- 13457-7: LDL cholesterol
- 2085-9: HDL cholesterol
- 2571-8: Triglycerides

INTERPRETATION THRESHOLDS:
- HbA1c > 7.5%: poor glycemic control
- eGFR < 60 mL/min/1.73m²: impaired kidney function
- eGFR < 30: severely impaired kidney function
- UACR > 30 mg/g: moderately increased albuminuria
- UACR > 300 mg/g: severely increased albuminuria

AVAILABLE TOOLS (7):
You have tools to search conditions by diagnosis code, get individual patient \
demographics, search observations by LOINC code, search medications, get a \
patient's full problem list, search encounters (visits), and batch-search \
patients. Use the right tool for the right task.

STRATEGY — think step by step:
1. Identify the condition(s) relevant to the question using search_conditions
2. Extract patient references from the condition results
3. Get patient demographics with get_patient (or search_patients for batch)
4. Look up relevant observations using the appropriate LOINC codes
5. Check medications and/or encounters if relevant
6. Review the full problem list (search_all_conditions) if comorbidities matter
7. Synthesize findings into a clear clinical summary

RULES:
- NEVER invent or hallucinate data. Only report values actually returned by tools.
- If a tool returns no results for a patient, state that explicitly.
- Always identify patients by name when available.
- Show actual lab values, not just categories.
- When comparing groups, provide counts and specific values.
- Be thorough: check all relevant patients, not just the first few.
"""
'''

# ── Agent loop ───────────────────────────────────────────────

AGENT_LOOP = r'''
def run_agent(question, system_prompt=SYSTEM_PROMPT, tools=tools,
              available_functions=available_functions, max_steps=25):
    """Run the tool-use agent loop."""
    print(f"\U0001f916 AGENT QUESTION: {question}\n")
    print("=" * 70)

    messages = [{"role": "user", "content": question}]
    tool_calls_log = []
    step = 0

    while step < max_steps:
        step += 1
        response = client.messages.create(
            model=MODEL,
            max_tokens=4096,
            system=system_prompt,
            tools=tools,
            messages=messages,
        )

        # Check for tool use
        tool_use_blocks = [b for b in response.content if b.type == "tool_use"]

        if not tool_use_blocks:
            # Final text response
            final_text = ""
            for block in response.content:
                if hasattr(block, "text"):
                    final_text += block.text
            print(f"\n{'=' * 70}")
            print(f"\u2705 FINAL ANSWER (after {step} steps):\n")
            print(final_text)
            return final_text, tool_calls_log, messages

        # Serialize assistant content for message history
        assistant_content = []
        for block in response.content:
            if block.type == "text":
                assistant_content.append({"type": "text", "text": block.text})
            elif block.type == "tool_use":
                assistant_content.append({
                    "type": "tool_use",
                    "id": block.id,
                    "name": block.name,
                    "input": block.input,
                })
        messages.append({"role": "assistant", "content": assistant_content})

        # Execute each tool call
        tool_results = []
        for block in tool_use_blocks:
            fn_name = block.name
            fn_args = block.input

            args_str = ", ".join(f"{k}={v!r}" for k, v in fn_args.items())
            print(f"\U0001f527 Step {step}: {fn_name}({args_str})")

            tool_calls_log.append({
                "step": step,
                "function": fn_name,
                "arguments": fn_args,
            })

            try:
                result = available_functions[fn_name](**fn_args)
            except Exception as e:
                result = {"error": str(e)}

            tool_results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": json.dumps(result, default=str),
            })

        messages.append({"role": "user", "content": tool_results})

    print(f"\n\u26a0\ufe0f Reached max steps ({max_steps})")
    return "Agent reached step limit.", tool_calls_log, messages
'''

# ── Trace display code ───────────────────────────────────────

TRACE_DISPLAY = r"""
# ── Tool Call Trace ──────────────────────────────────────────
print("\U0001f4cb TOOL CALL SEQUENCE\n")
print(f"{'Step':<6} {'Function':<25} {'Key Arguments'}")
print("-" * 70)
for tc in tool_calls_log:
    args_summary = ", ".join(f"{k}={v}" for k, v in tc["arguments"].items())
    print(f"{tc['step']:<6} {tc['function']:<25} {args_summary}")

print(f"\nTotal tool calls: {len(tool_calls_log)}")
tools_used = set(tc["function"] for tc in tool_calls_log)
print(f"Unique tools used: {sorted(tools_used)}")
"""

CONVERSATION_DISPLAY = r"""
# ── Full Conversation Anatomy ────────────────────────────────
print("FULL CONVERSATION STRUCTURE\n")
for i, msg in enumerate(messages):
    role = msg["role"]
    content = msg["content"]

    if isinstance(content, str):
        print(f"[{i}] {role}: {content[:120]}...")
    elif isinstance(content, list):
        for block in content:
            if isinstance(block, dict):
                btype = block.get("type", "?")
                if btype == "text":
                    print(f"[{i}] {role}/text: {block['text'][:120]}...")
                elif btype == "tool_use":
                    print(f"[{i}] {role}/tool_use: {block['name']}({block['input']})")
                elif btype == "tool_result":
                    preview = block["content"][:80] if isinstance(block["content"], str) else str(block["content"])[:80]
                    print(f"[{i}] {role}/tool_result: {preview}...")
            else:
                print(f"[{i}] {role}: {str(block)[:120]}...")
    print()
"""

# ── Session 1 visualization ──────────────────────────────────

S1_VISUALIZATION = r"""
# ══════════════════════════════════════════════════════════════
# VISUALIZATION: HbA1c vs eGFR
# ══════════════════════════════════════════════════════════════

# Pivot observations to get one row per patient with columns for each test
df_pivot = df_obs.pivot(index="patient_id", columns="test", values="value").reset_index()
df_plot = df_patients.merge(df_pivot, left_on="id", right_on="patient_id", how="left")

# Convert to numeric
for col in ["HbA1c", "Creatinine", "eGFR"]:
    if col in df_plot.columns:
        df_plot[col] = pd.to_numeric(df_plot[col], errors="coerce")

# Filter to patients with both values
plot_data = df_plot.dropna(subset=["HbA1c", "eGFR"])

if len(plot_data) > 0:
    fig, ax = plt.subplots(figsize=(10, 6))
    colors = ["tab:red" if h > 7.5 else "tab:green" for h in plot_data["HbA1c"]]
    ax.scatter(plot_data["HbA1c"], plot_data["eGFR"], c=colors, alpha=0.7,
               edgecolors="black", linewidth=0.5, s=80)
    ax.axhline(y=60, color="gray", linestyle="--", alpha=0.7, label="eGFR = 60 (impaired)")
    ax.axvline(x=7.5, color="gray", linestyle=":", alpha=0.7, label="HbA1c = 7.5% (poor control)")
    ax.set_xlabel("HbA1c (%)", fontsize=12)
    ax.set_ylabel("eGFR (mL/min/1.73m\u00b2)", fontsize=12)
    ax.set_title("Glycemic Control vs Kidney Function in Type 2 Diabetes Patients", fontsize=13)
    ax.legend(fontsize=10)

    # Label quadrants
    xlim = ax.get_xlim()
    ylim = ax.get_ylim()
    mid_x = 7.5
    ax.text(xlim[0] + 0.3, ylim[1] - 5, "Good control,\nhealthy kidneys",
            fontsize=9, color="green", alpha=0.8, va="top")
    ax.text(xlim[1] - 0.3, ylim[1] - 5, "Poor control,\nhealthy kidneys",
            fontsize=9, color="orange", alpha=0.8, va="top", ha="right")
    ax.text(xlim[0] + 0.3, max(ylim[0] + 2, 10), "Good control,\nimpaired kidneys",
            fontsize=9, color="orange", alpha=0.8)
    ax.text(xlim[1] - 0.3, max(ylim[0] + 2, 10), "Poor control,\nimpaired kidneys",
            fontsize=9, color="red", alpha=0.8, ha="right")

    plt.tight_layout()
    plt.show()

    print(f"\nPatients plotted: {len(plot_data)}")
    print(f"Poor control (HbA1c >7.5%): {sum(plot_data['HbA1c'] > 7.5)}")
    print(f"Impaired kidneys (eGFR <60): {sum(plot_data['eGFR'] < 60)}")
    both = sum((plot_data['HbA1c'] > 7.5) & (plot_data['eGFR'] < 60))
    print(f"Both poor control AND impaired kidneys: {both}")
else:
    print("Not enough data to plot. Check that observations were retrieved successfully.")
"""

# ── Session 2 visualization ──────────────────────────────────

S2_VISUALIZATION = r"""
# ══════════════════════════════════════════════════════════════
# VISUALIZATION: Re-query and Plot
# ══════════════════════════════════════════════════════════════
# We call the same tool functions the agent used, but collect the results
# into DataFrames for plotting.
import time

# Step 1: Get Type 2 diabetes patients
t2d_conditions = search_conditions("44054006", max_results=50)
t2d_patient_ids = list(set(
    r["patient_reference"].split("/")[-1]
    for r in t2d_conditions["results"]
))
print(f"Type 2 diabetes patients found: {len(t2d_patient_ids)}")

# Step 2: Collect HbA1c, eGFR, and medications
rows = []
all_meds = []
for pid in t2d_patient_ids:
    try:
        patient = get_patient(pid)
        hba1c = search_observations(pid, "4548-4", max_results=1)
        egfr = search_observations(pid, "33914-3", max_results=1)
        meds = search_medications(pid, max_results=10)
    except Exception:
        time.sleep(3)
        patient = get_patient(pid)
        hba1c = search_observations(pid, "4548-4", max_results=1)
        egfr = search_observations(pid, "33914-3", max_results=1)
        meds = search_medications(pid, max_results=10)

    hba1c_val = hba1c["results"][0]["value"] if hba1c["results"] else None
    egfr_val = egfr["results"][0]["value"] if egfr["results"] else None

    rows.append({
        "patient_id": pid,
        "name": patient["name"],
        "hba1c": hba1c_val,
        "egfr": egfr_val,
    })

    for m in meds.get("results", []):
        all_meds.append({"patient_id": pid, "medication": m["medication"]})
    time.sleep(0.3)  # Brief pause between patients to avoid server overload

df = pd.DataFrame(rows)
df["hba1c"] = pd.to_numeric(df["hba1c"], errors="coerce")
df["egfr"] = pd.to_numeric(df["egfr"], errors="coerce")

# ---- Plot ----
fig, axes = plt.subplots(1, 2, figsize=(14, 5))

# Left: HbA1c vs eGFR scatter
plot_df = df.dropna(subset=["hba1c", "egfr"])
if len(plot_df) > 0:
    colors = ["tab:red" if h > 7.5 else "tab:green" for h in plot_df["hba1c"]]
    axes[0].scatter(plot_df["hba1c"], plot_df["egfr"], c=colors, alpha=0.7,
                    edgecolors="black", linewidth=0.5, s=80)
    axes[0].axhline(y=60, color="gray", linestyle="--", alpha=0.7)
    axes[0].axvline(x=7.5, color="gray", linestyle=":", alpha=0.7)
    axes[0].set_xlabel("HbA1c (%)")
    axes[0].set_ylabel("eGFR (mL/min/1.73m\u00b2)")
    axes[0].set_title("HbA1c vs eGFR \u2014 Type 2 Diabetes")
else:
    axes[0].text(0.5, 0.5, "No data", ha="center", va="center")

# Right: Medication frequency bar chart
df_meds = pd.DataFrame(all_meds)
if len(df_meds) > 0:
    med_counts = df_meds["medication"].value_counts()
    med_counts.plot(kind="barh", ax=axes[1], color="steelblue")
    axes[1].set_xlabel("Number of Patients")
    axes[1].set_title("Medication Frequency \u2014 Type 2 Diabetes")
    axes[1].invert_yaxis()
else:
    axes[1].text(0.5, 0.5, "No medication data", ha="center", va="center")

plt.tight_layout()
plt.show()

print(f"\nPatients with both HbA1c and eGFR data: {len(plot_df)}")
if len(plot_df) > 0:
    both = sum((plot_df["hba1c"] > 7.5) & (plot_df["egfr"] < 60))
    print(f"Poor control + impaired kidneys: {both}")
if len(df_meds) > 0:
    print(f"Unique medications: {df_meds['medication'].nunique()}")
"""

# ── Session 3 comparison plot ────────────────────────────────

S3_COMPARISON_PLOT = r"""
# ══════════════════════════════════════════════════════════════
# COMPARISON PLOT: Type 1 vs Type 2 Diabetes
# ══════════════════════════════════════════════════════════════
# This cell queries both diabetes groups and plots C-peptide vs HbA1c
# to visualize the key biochemical difference between them.
import time

# Fetch both groups (limit to 10 per group for speed — enough to see the pattern)
t2d = search_conditions("44054006", max_results=10)
t2d_ids = list(set(r["patient_reference"].split("/")[-1] for r in t2d["results"]))

t1d = search_conditions("46635009", max_results=10)
t1d_ids = list(set(r["patient_reference"].split("/")[-1] for r in t1d["results"]))

print(f"Type 2 diabetes patients: {len(t2d_ids)}")
print(f"Type 1 diabetes patients: {len(t1d_ids)}")

# Collect C-peptide and HbA1c for both groups
rows = []
for diabetes_type, patient_ids in [("Type 2", t2d_ids), ("Type 1", t1d_ids)]:
    for pid in patient_ids:
        try:
            hba1c = search_observations(pid, "4548-4", max_results=1)
        except Exception:
            time.sleep(2)
            hba1c = search_observations(pid, "4548-4", max_results=1)
        try:
            cpeptide = search_observations(pid, "1986-9", max_results=1)
        except Exception:
            time.sleep(2)
            cpeptide = search_observations(pid, "1986-9", max_results=1)
        rows.append({
            "patient_id": pid,
            "diabetes_type": diabetes_type,
            "hba1c": hba1c["results"][0]["value"] if hba1c["results"] else None,
            "c_peptide": cpeptide["results"][0]["value"] if cpeptide["results"] else None,
        })

df_compare = pd.DataFrame(rows)
df_compare["hba1c"] = pd.to_numeric(df_compare["hba1c"], errors="coerce")
df_compare["c_peptide"] = pd.to_numeric(df_compare["c_peptide"], errors="coerce")

plot_df = df_compare.dropna(subset=["hba1c", "c_peptide"])
if len(plot_df) > 0:
    fig, ax = plt.subplots(figsize=(10, 6))

    for dtype, color, marker in [("Type 1", "tab:blue", "s"), ("Type 2", "tab:orange", "o")]:
        subset = plot_df[plot_df["diabetes_type"] == dtype]
        ax.scatter(subset["c_peptide"], subset["hba1c"], c=color, marker=marker,
                   label=f"{dtype} diabetes", alpha=0.7, edgecolors="black",
                   linewidth=0.5, s=80)

    ax.axhline(y=7.5, color="gray", linestyle=":", alpha=0.7, label="HbA1c = 7.5%")
    ax.set_xlabel("C-Peptide (ng/mL)", fontsize=12)
    ax.set_ylabel("HbA1c (%)", fontsize=12)
    ax.set_title("C-Peptide vs HbA1c: Type 1 vs Type 2 Diabetes", fontsize=13)
    ax.legend(fontsize=10)
    plt.tight_layout()
    plt.show()

    for dtype in ["Type 1", "Type 2"]:
        sub = plot_df[plot_df["diabetes_type"] == dtype]
        print(f"\n{dtype} diabetes ({len(sub)} patients):")
        print(f"  C-peptide: mean={sub['c_peptide'].mean():.2f}, range={sub['c_peptide'].min():.2f}-{sub['c_peptide'].max():.2f}")
        print(f"  HbA1c: mean={sub['hba1c'].mean():.1f}%, range={sub['hba1c'].min():.1f}-{sub['hba1c'].max():.1f}%")
else:
    print("Not enough data for comparison plot. Check that both patient groups have C-peptide and HbA1c data.")
"""

# ── Session 3 deliverable ────────────────────────────────────

S3_DELIVERABLE = r"""
# ══════════════════════════════════════════════════════════════
# DELIVERABLE — Session 3 Report
# ══════════════════════════════════════════════════════════════
from datetime import datetime

report = {
    "student_id": input("Enter your student ID: "),
    "timestamp": datetime.now().isoformat(),
    "session": 3,
    "runs": [],
}

# Add Question 1 if available
try:
    report["runs"].append({
        "question": user_question_1,
        "tool_calls": tool_calls_1,
        "num_tool_calls": len(tool_calls_1),
        "tools_used": list(set(tc["function"] for tc in tool_calls_1)),
        "final_answer": answer_1[:500] if isinstance(answer_1, str) else "",
    })
except NameError:
    print("\u26a0\ufe0f Question 1 not found \u2014 did you run it?")

# Add Question 2 if available
try:
    report["runs"].append({
        "question": user_question_2,
        "tool_calls": tool_calls_2,
        "num_tool_calls": len(tool_calls_2),
        "tools_used": list(set(tc["function"] for tc in tool_calls_2)),
        "final_answer": answer_2[:500] if isinstance(answer_2, str) else "",
    })
except NameError:
    print("\u26a0\ufe0f Question 2 not found \u2014 did you run it?")

# Save
filename = f"session3_report_{report['student_id']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
with open(filename, "w") as f:
    json.dump(report, f, indent=2, default=str)

print(f"\n\u2705 Report saved: {filename}")
print(f"   Questions answered: {len(report['runs'])}")
print(f"   Total tool calls: {sum(r['num_tool_calls'] for r in report['runs'])}")
print(f"\nDownload this file and submit it.")
"""


# ══════════════════════════════════════════════════════════════
# SESSION 1 CELLS
# ══════════════════════════════════════════════════════════════

def session1_cells(instructor=False):
    cells = []
    tag = " — INSTRUCTOR VERSION" if instructor else ""

    # 1: Title
    cells.append(md_cell(
        f"# Session 1: FHIR Fundamentals{tag}\n\n"
        "## How This Notebook Works\n\n"
        "In this session you will **query a real FHIR server** containing "
        "synthetic (fake but clinically realistic) patient data. You will:\n\n"
        "1. Explore the FHIR API structure (Bundles, Resources, References)\n"
        "2. Use the **Claude web UI** (claude.ai) to help you write Python "
        "code for FHIR queries\n"
        "3. Find patients with Type 2 diabetes\n"
        "4. Retrieve their HbA1c, creatinine, and eGFR lab values\n"
        "5. Identify patients with both **poor glycemic control** and "
        "**impaired kidney function**\n"
        "6. Visualize the relationship between diabetes control and kidney "
        "function\n\n"
        "**You write the code** (with Claude's help), paste it into the "
        "empty cells, and run it. Each step builds on the previous one."
    ))

    # 2: Phenotype description
    cells.append(md_cell(PHENOTYPE_DESCRIPTION))

    # 3: Clinical code reference
    cells.append(md_cell(CLINICAL_CODE_REFERENCE))

    # 4: FHIR resource diagram
    cells.append(md_cell(FHIR_RESOURCE_DIAGRAM))

    # 5: SETUP
    cells.append(code_cell(SETUP_S1))

    # 6: Step 0 intro
    cells.append(md_cell(
        "## Step 0: Your First FHIR Query\n\n"
        "Let's start by fetching a few patients to see what FHIR data looks "
        "like. The cell below queries `/Patient?_count=5` — asking the server "
        "for 5 patient records.\n\n"
        "Look at the response structure: it's a **Bundle** containing "
        "**entry** items, each wrapping a **Patient** resource."
    ))

    # 7: First query
    cells.append(code_cell(
        '# Your first FHIR query: fetch 5 patients\n'
        'resp = FHIR_SESSION.get(\n'
        '    f"{FHIR_BASE}/Patient",\n'
        '    params={"_count": 5, "_format": "json"},\n'
        '    timeout=30,\n'
        ')\n'
        'bundle = resp.json()\n\n'
        'print(f"Response type: {bundle[\'resourceType\']}")\n'
        'print(f"Total patients on server: {bundle.get(\'total\', \'?\')}")\n'
        'print(f"Entries returned: {len(bundle.get(\'entry\', []))}")\n'
        'print()\n\n'
        '# Show first patient\n'
        'if bundle.get("entry"):\n'
        '    first = bundle["entry"][0]["resource"]\n'
        '    show_json(first)'
    ))

    # 8: Explain what we saw
    cells.append(md_cell(
        "## What Did We Just See?\n\n"
        "The FHIR server returned a **Bundle** — a container wrapping "
        "multiple results. Key fields:\n\n"
        "- `resourceType`: always `\"Bundle\"` for search results\n"
        "- `total`: how many resources matched on the entire server\n"
        "- `entry`: an array of results, each containing one `resource`\n\n"
        "Each Patient resource has structured fields: `name`, `gender`, "
        "`birthDate`, and an `id` used to reference this patient from "
        "other resources.\n\n"
        "Now let's use this structure to answer a clinical question."
    ))

    # 9: Step 1 prompt
    cells.append(md_cell(
        "## Step 1: Find Patients with Type 2 Diabetes\n\n"
        "Go to **claude.ai** and ask Claude to write code for you. Use a "
        "prompt like:\n\n"
        "> Write Python code using `FHIR_SESSION.get()` (a pre-configured "
        "requests Session with auth) to search for Condition resources with "
        "SNOMED CT code `44054006` (Type 2 diabetes mellitus) on the FHIR "
        "server. The base URL is stored in `FHIR_BASE`. Use `_count=50` and "
        "`_format=json`. Extract the unique patient references into a set "
        "called `patient_refs`.\n\n"
        "Paste Claude's code into the cell below and run it."
    ))

    # 10: Step 1 code (empty for student, reference for instructor)
    if instructor:
        cells.append(code_cell(
            '# REFERENCE IMPLEMENTATION — Step 1\n'
            'resp = FHIR_SESSION.get(\n'
            '    f"{FHIR_BASE}/Condition",\n'
            '    params={"code": "44054006", "_count": 50, "_format": "json"},\n'
            '    timeout=30,\n'
            ')\n'
            'bundle = resp.json()\n'
            'print(f"Total Type 2 diabetes conditions: {bundle.get(\'total\', 0)}")\n\n'
            'patient_refs = set()\n'
            'for entry in bundle.get("entry", []):\n'
            '    ref = entry["resource"]["subject"]["reference"]\n'
            '    patient_refs.add(ref)\n\n'
            'print(f"Unique patients: {len(patient_refs)}")\n'
            'for ref in sorted(patient_refs):\n'
            '    print(f"  {ref}")'
        ))
    else:
        cells.append(code_cell("# Paste Claude's code here and run it\n"))

    # 11: Verification + fallback
    cells.append(code_cell(
        '# ---- Verification ----\n'
        'try:\n'
        '    assert len(patient_refs) > 0, "No patient references found"\n'
        '    print(f"\\u2705 Found {len(patient_refs)} patient references")\n'
        '    for ref in sorted(patient_refs)[:5]:\n'
        '        print(f"   {ref}")\n'
        '    if len(patient_refs) > 5:\n'
        '        print(f"   ... and {len(patient_refs) - 5} more")\n'
        'except (NameError, AssertionError) as e:\n'
        '    print(f"\\u26a0\\ufe0f Issue: {e}")\n'
        '    print("Running fallback query...")\n'
        '    resp = FHIR_SESSION.get(\n'
        '        f"{FHIR_BASE}/Condition",\n'
        '        params={"code": "44054006", "_count": 50, "_format": "json"},\n'
        '        timeout=30,\n'
        '    )\n'
        '    bundle = resp.json()\n'
        '    patient_refs = set()\n'
        '    for entry in bundle.get("entry", []):\n'
        '        ref = entry["resource"]["subject"]["reference"]\n'
        '        patient_refs.add(ref)\n'
        '    print(f"\\u2705 Fallback found {len(patient_refs)} patient references")'
    ))

    # 12: Step 2 prompt
    cells.append(md_cell(
        "## Step 2: Get Patient Demographics\n\n"
        "Now ask Claude to write code that:\n\n"
        "> For each patient reference in `patient_refs`, fetch the Patient "
        "resource from `f\"{FHIR_BASE}/Patient/{patient_id}\"` using "
        "`FHIR_SESSION.get()`. Extract the patient's name, gender, and birth "
        "date into a list of dictionaries called `patients`. Display the "
        "results as a pandas DataFrame."
    ))

    # 13: Step 2 code
    if instructor:
        _s2_ref = (
            "# REFERENCE IMPLEMENTATION \u2014 Step 2\n"
            "patients = []\n"
            "for ref in sorted(patient_refs):\n"
            "    patient_id = ref.split('/')[-1]\n"
            "    resp = FHIR_SESSION.get(\n"
            '        f"{FHIR_BASE}/Patient/{patient_id}",\n'
            '        params={"_format": "json"},\n'
            "        timeout=30,\n"
            "    )\n"
            "    p = resp.json()\n"
            "    name = p.get('name', [{}])[0]\n"
            "    given = ' '.join(name.get('given', []))\n"
            "    family = name.get('family', '')\n"
            "    patients.append({\n"
            '        "id": p["id"],\n'
            '        "name": f"{given} {family}".strip(),\n'
            '        "gender": p.get("gender", ""),\n'
            '        "birthDate": p.get("birthDate", ""),\n'
            "    })\n"
            "\n"
            "df_patients = pd.DataFrame(patients)\n"
            'print(f"Retrieved {len(patients)} patients:")\n'
            "display(df_patients)"
        )
        cells.append(code_cell(_s2_ref))
    else:
        cells.append(code_cell("# Paste Claude's code here and run it\n"))

    # 14: Demographics verification
    cells.append(code_cell(
        '# ---- Verification: Patient demographics ----\n'
        'try:\n'
        '    df_patients = pd.DataFrame(patients)\n'
        '    print(f"\\u2705 {len(patients)} patients loaded")\n'
        '    display(df_patients)\n'
        'except NameError:\n'
        '    print("\\u26a0\\ufe0f `patients` not defined. Run Step 2 first.")'
    ))

    # 15: Step 3 prompt
    cells.append(md_cell(
        "## Step 3: Retrieve Lab Values (HbA1c, Creatinine, eGFR)\n\n"
        "This is the most complex step. Ask Claude:\n\n"
        "> For each patient in `patient_refs`, search for Observation resources "
        "using `FHIR_SESSION.get()` at `f\"{FHIR_BASE}/Observation\"`. "
        "Retrieve three lab types:\n"
        "> - HbA1c (LOINC code `4548-4`)\n"
        "> - Creatinine (LOINC code `2160-0`)\n"
        "> - eGFR (LOINC code `33914-3`)\n"
        ">\n"
        "> Use parameters: `subject=Patient/{id}`, `code={loinc}`, "
        "`_count=1`, `_sort=-date`, `_format=json`. Extract the most recent "
        "value for each test into a list of dictionaries called `observations` "
        "with keys: patient_id, test, loinc_code, value, unit, date."
    ))

    # 16: Step 3 code
    if instructor:
        cells.append(code_cell(
            '# REFERENCE IMPLEMENTATION — Step 3\n'
            'observations = []\n'
            'loinc_codes = {"4548-4": "HbA1c", "2160-0": "Creatinine", "33914-3": "eGFR"}\n\n'
            'for ref in sorted(patient_refs):\n'
            '    patient_id = ref.split("/")[-1]\n'
            '    for code, name in loinc_codes.items():\n'
            '        resp = FHIR_SESSION.get(\n'
            '            f"{FHIR_BASE}/Observation",\n'
            '            params={\n'
            '                "subject": f"Patient/{patient_id}",\n'
            '                "code": code,\n'
            '                "_count": 1,\n'
            '                "_sort": "-date",\n'
            '                "_format": "json",\n'
            '            },\n'
            '            timeout=30,\n'
            '        )\n'
            '        bundle = resp.json()\n'
            '        entries = bundle.get("entry", [])\n'
            '        if entries:\n'
            '            obs = entries[0]["resource"]\n'
            '            value_qty = obs.get("valueQuantity", {})\n'
            '            observations.append({\n'
            '                "patient_id": patient_id,\n'
            '                "test": name,\n'
            '                "loinc_code": code,\n'
            '                "value": value_qty.get("value"),\n'
            '                "unit": value_qty.get("unit", ""),\n'
            '                "date": obs.get("effectiveDateTime", ""),\n'
            '            })\n'
            '        else:\n'
            '            observations.append({\n'
            '                "patient_id": patient_id,\n'
            '                "test": name,\n'
            '                "loinc_code": code,\n'
            '                "value": None,\n'
            '                "unit": "",\n'
            '                "date": "",\n'
            '            })\n\n'
            'df_obs = pd.DataFrame(observations)\n'
            'print(f"Retrieved {len(observations)} observation records")\n'
            'display(df_obs.head(15))'
        ))
    else:
        cells.append(code_cell("# Paste Claude's code here and run it\n"))

    # 17: Observations verification
    cells.append(code_cell(
        '# ---- Verification: Lab observations ----\n'
        'try:\n'
        '    assert len(observations) > 0, "observations list is empty"\n'
        '    print(f"\\u2705 {len(observations)} observation records loaded")\n'
        '    df_obs_check = pd.DataFrame(observations)\n'
        '    print(f"   Tests found: {df_obs_check[\'test\'].unique().tolist()}")\n'
        'except (NameError, AssertionError) as e:\n'
        '    print(f"\\u26a0\\ufe0f Issue: {e}")\n'
        '    print("Running fallback observation queries...")\n'
        '    observations = []\n'
        '    loinc_codes = {"4548-4": "HbA1c", "2160-0": "Creatinine", "33914-3": "eGFR"}\n'
        '    for ref in sorted(patient_refs):\n'
        '        patient_id = ref.split("/")[-1]\n'
        '        for code, name in loinc_codes.items():\n'
        '            resp = FHIR_SESSION.get(\n'
        '                f"{FHIR_BASE}/Observation",\n'
        '                params={\n'
        '                    "subject": f"Patient/{patient_id}",\n'
        '                    "code": code,\n'
        '                    "_count": 1,\n'
        '                    "_sort": "-date",\n'
        '                    "_format": "json",\n'
        '                },\n'
        '                timeout=30,\n'
        '            )\n'
        '            bundle = resp.json()\n'
        '            entries = bundle.get("entry", [])\n'
        '            if entries:\n'
        '                obs = entries[0]["resource"]\n'
        '                value_qty = obs.get("valueQuantity", {})\n'
        '                observations.append({\n'
        '                    "patient_id": patient_id,\n'
        '                    "test": name,\n'
        '                    "loinc_code": code,\n'
        '                    "value": value_qty.get("value"),\n'
        '                    "unit": value_qty.get("unit", ""),\n'
        '                    "date": obs.get("effectiveDateTime", ""),\n'
        '                })\n'
        '            else:\n'
        '                observations.append({\n'
        '                    "patient_id": patient_id,\n'
        '                    "test": name,\n'
        '                    "loinc_code": code,\n'
        '                    "value": None,\n'
        '                    "unit": "",\n'
        '                    "date": "",\n'
        '                })\n'
        '    print(f"\\u2705 Fallback retrieved {len(observations)} observation records")'
    ))

    # 18: Analysis
    cells.append(code_cell(
        '# ══════════════════════════════════════════════════════════════\n'
        '# COMBINED ANALYSIS\n'
        '# ══════════════════════════════════════════════════════════════\n\n'
        'df_patients = pd.DataFrame(patients)\n'
        'df_obs = pd.DataFrame(observations)\n\n'
        '# Pivot: one row per patient, columns for each test\n'
        'df_pivot = df_obs.pivot(index="patient_id", columns="test", values="value").reset_index()\n'
        'df_combined = df_patients.merge(df_pivot, left_on="id", right_on="patient_id", how="left")\n\n'
        '# Convert to numeric\n'
        'for col in ["HbA1c", "Creatinine", "eGFR"]:\n'
        '    if col in df_combined.columns:\n'
        '        df_combined[col] = pd.to_numeric(df_combined[col], errors="coerce")\n\n'
        '# Flag poor control and impaired kidney function\n'
        'df_combined["poor_control"] = df_combined["HbA1c"] > 7.5\n'
        'df_combined["impaired_kidneys"] = (\n'
        '    (df_combined["eGFR"] < 60) | (df_combined["Creatinine"] > 1.5)\n'
        ')\n'
        'df_combined["both_flags"] = df_combined["poor_control"] & df_combined["impaired_kidneys"]\n\n'
        'print("=" * 70)\n'
        'print("COMBINED ANALYSIS: Type 2 Diabetes Patients")\n'
        'print("=" * 70)\n'
        'display(df_combined[["name", "gender", "birthDate", "HbA1c", "Creatinine", "eGFR",\n'
        '                     "poor_control", "impaired_kidneys"]])\n\n'
        'print(f"\\n--- Summary ---")\n'
        'print(f"Total patients analyzed: {len(df_combined)}")\n'
        'n_hba1c = df_combined["HbA1c"].notna().sum()\n'
        'print(f"Patients with HbA1c data: {n_hba1c}")\n'
        'if n_hba1c > 0:\n'
        '    print(f"  Poor glycemic control (HbA1c >7.5%): {df_combined[\'poor_control\'].sum()}")\n'
        '    print(f"  Mean HbA1c: {df_combined[\'HbA1c\'].mean():.1f}%")\n'
        'n_egfr = df_combined["eGFR"].notna().sum()\n'
        'print(f"Patients with eGFR data: {n_egfr}")\n'
        'if n_egfr > 0:\n'
        '    print(f"  Impaired kidneys (eGFR <60 or Cr >1.5): {df_combined[\'impaired_kidneys\'].sum()}")\n'
        '    print(f"  Mean eGFR: {df_combined[\'eGFR\'].mean():.1f} mL/min/1.73m\\u00b2")\n'
        'print(f"\\nPatients with BOTH poor control AND impaired kidneys: {df_combined[\'both_flags\'].sum()}")'
    ))

    # 19: Visualization
    cells.append(code_cell(S1_VISUALIZATION))

    # 20: Step 4 prompt
    cells.append(md_cell(
        "## Step 4: Generate a Clinical Summary\n\n"
        "Go back to **claude.ai** and ask Claude to write a clinical "
        "narrative based on the data table above. Suggested prompt:\n\n"
        "> Based on the following patient data, write a brief clinical "
        "summary describing the relationship between glycemic control "
        "(HbA1c) and kidney function (eGFR, creatinine) in these Type 2 "
        "diabetes patients. Use ONLY the data provided. Identify which "
        "patients have both poor glycemic control and impaired kidney "
        "function.\n\n"
        "Paste the summary below."
    ))

    # 21: Clinical summary paste area
    if instructor:
        cells.append(md_cell(
            "### Sample Clinical Summary (Instructor Reference)\n\n"
            "Among the Type 2 diabetes patients examined, there is a visible "
            "correlation between glycemic control and kidney function. Patients "
            "with HbA1c values above 7.5% — indicating poor glycemic control — "
            "tend to have lower eGFR values, suggesting impaired kidney "
            "function.\n\n"
            "Several patients show both poor glycemic control (HbA1c >7.5%) "
            "and impaired kidney function (eGFR <60 mL/min/1.73m² or "
            "creatinine >1.5 mg/dL). This pattern is consistent with "
            "diabetic nephropathy, a well-known complication of poorly "
            "controlled diabetes.\n\n"
            "The scatter plot confirms this visually: patients in the "
            "upper-left quadrant (good control, healthy kidneys) contrast "
            "sharply with those in the lower-right (poor control, impaired "
            "kidneys). The synthetic data was designed with phenotype coupling "
            "to reflect this real-world clinical relationship."
        ))
    else:
        cells.append(md_cell(
            "### Your Clinical Summary\n\n"
            "*Paste Claude's clinical summary here.*\n"
        ))

    # 22: Reflection
    cells.append(md_cell(
        "## Session 1 Reflection\n\n"
        "You just built a complete clinical data pipeline:\n\n"
        "1. **Searched** for a diagnosis (Condition) by SNOMED code\n"
        "2. **Followed references** to get Patient demographics\n"
        "3. **Retrieved** lab values (Observations) by LOINC codes\n"
        "4. **Analyzed** the combined data to flag at-risk patients\n"
        "5. **Visualized** the relationship between glycemic control and "
        "kidney function\n\n"
        "**Key insight:** No single FHIR query answered our clinical "
        "question. We had to chain multiple queries together by following "
        "references. In Session 2, you'll see how an AI agent can decide "
        "this sequence automatically."
    ))

    return cells


# ══════════════════════════════════════════════════════════════
# SESSION 2 CELLS
# ══════════════════════════════════════════════════════════════

S2_QUESTION = (
    "Find patients with Type 2 diabetes (SNOMED code 44054006). "
    "For each patient, retrieve their most recent HbA1c, eGFR, and "
    "creatinine values, and list their current medications. "
    "Which patients have both poor glycemic control (HbA1c > 7.5%) "
    "and impaired kidney function (eGFR < 60)? "
    "What medications are they taking?"
)


def session2_cells(instructor=False):
    cells = []
    tag = " — INSTRUCTOR VERSION" if instructor else ""

    # 1: Title + recap
    cells.append(md_cell(
        f"# Session 2: Tool Use — AI Agents for Clinical Data{tag}\n\n"
        "## Recap from Session 1\n\n"
        "In Session 1, **you** decided the query sequence: find conditions, "
        "get patients, retrieve labs. **You** wrote each query (with Claude's "
        "help generating code) and chained results together.\n\n"
        "Now the question: what if the LLM could decide the sequence itself? "
        "Instead of you telling it \"first search conditions, then get "
        "patients,\" you just ask the clinical question and let the LLM "
        "figure out the steps.\n\n"
        "That shift — from the LLM as a **code-writing assistant** to the "
        "LLM as a **decision-making agent** — is the core idea of this "
        "session."
    ))

    # 2: Phenotype description
    cells.append(md_cell(PHENOTYPE_DESCRIPTION))

    # 3: Clinical code reference
    cells.append(md_cell(CLINICAL_CODE_REFERENCE))

    # 4: Setup (includes pip install)
    cells.append(code_cell(SETUP_S23))

    # 6: Tool functions + smoke tests
    cells.append(code_cell(TOOL_FUNCTIONS_5))

    # 7: Tool schemas
    cells.append(code_cell(TOOL_SCHEMAS_5))

    # 8: Tool schemas explanation
    cells.append(md_cell(
        "## Understanding Tool Schemas\n\n"
        "The LLM never sees your Python source code. It reads **JSON "
        "schemas** describing each tool: name, description, and parameters.\n\n"
        "The quality of these descriptions directly affects agent performance. "
        "Notice the embedded LOINC and SNOMED codes in the descriptions — "
        "the LLM uses these to choose the right arguments.\n\n"
        "There are **5 tools** available:\n\n"
        "| Tool | Purpose |\n"
        "|------|---------|\n"
        "| `search_conditions` | Find patients by diagnosis code |\n"
        "| `get_patient` | Get one patient's demographics |\n"
        "| `search_observations` | Get lab results by LOINC code |\n"
        "| `search_medications` | Get medication list |\n"
        "| `search_all_conditions` | Get full problem list for one patient |"
    ))

    # 9: Prediction worksheet
    if instructor:
        cells.append(md_cell(
            "## Predict the Agent's Behavior\n\n"
            f"The agent will be asked:\n\n> \"{S2_QUESTION}\"\n\n"
            "**What tools will it use first?**\n\n"
            "`search_conditions(\"44054006\")` to find Type 2 diabetes patients, "
            "then `get_patient()` for demographics, then "
            "`search_observations()` for HbA1c (4548-4), eGFR (33914-3), "
            "creatinine (2160-0), then `search_medications()` for each "
            "patient.\n\n"
            "**How many tool calls do you expect?**\n\n"
            "~20-25 calls: 1 condition search + N×get_patient + N×3 "
            "observation searches + N×medication searches. May approach "
            "max_steps=25.\n\n"
            "**What LOINC/SNOMED codes should it use?**\n\n"
            "44054006 (Type 2 diabetes), 4548-4 (HbA1c), 33914-3 (eGFR), "
            "2160-0 (creatinine)\n\n"
            "**What could go wrong?**\n\n"
            "Agent might not check all 3 lab types for every patient. Could "
            "run out of steps. Might not combine the data correctly in its "
            "summary."
        ))
    else:
        cells.append(md_cell(
            "## Predict the Agent's Behavior\n\n"
            f"The agent will be asked:\n\n> \"{S2_QUESTION}\"\n\n"
            "Before running it, write your predictions:\n\n"
            "**What tools will it use first?**\n\n"
            "*YOUR ANSWER:*\n\n"
            "**How many tool calls do you expect?**\n\n"
            "*YOUR ANSWER:*\n\n"
            "**What LOINC/SNOMED codes should it use?**\n\n"
            "*YOUR ANSWER:*\n\n"
            "**What could go wrong?**\n\n"
            "*YOUR ANSWER:*"
        ))

    # 10: System prompt
    cells.append(code_cell(SYSTEM_PROMPT_S2))

    # 11: Agent loop
    cells.append(code_cell(AGENT_LOOP))

    # 12: Run the agent intro
    cells.append(md_cell(
        "## Run the Agent\n\n"
        "The cell below sends the clinical question to the agent. Watch "
        "the tool call trace as it runs — each line shows a function call "
        "the LLM decided to make."
    ))

    # 13: Run agent
    cells.append(code_cell(
        f'user_question = """{S2_QUESTION}"""\n\n'
        'answer, tool_calls_log, messages = run_agent(user_question)'
    ))

    # 14: Trace
    cells.append(code_cell(TRACE_DISPLAY))

    # 15: Compare to predictions
    if instructor:
        cells.append(md_cell(
            "## Compare to Your Predictions\n\n"
            "**Did the agent use the tools you expected?**\n\n"
            "Typically yes — the agent follows a logical workflow: "
            "conditions → patients → observations → medications. It usually "
            "starts with `search_conditions` and systematically works "
            "through each patient.\n\n"
            "**Were there any surprises?**\n\n"
            "The agent may not check all 3 lab types for every patient if "
            "it starts running low on steps. It might prioritize HbA1c "
            "over creatinine/eGFR. Some runs will check medications last "
            "or skip them for some patients.\n\n"
            "**Did the agent correctly identify patients with both flags?**\n\n"
            "Usually yes, but verify against the visualization below. The "
            "agent's textual summary should match the scatter plot's red "
            "dots below the eGFR=60 line."
        ))
    else:
        cells.append(md_cell(
            "## Compare to Your Predictions\n\n"
            "**Did the agent use the tools you expected? In the order "
            "you expected?**\n\n"
            "*YOUR ANSWER:*\n\n"
            "**Were there any surprises in the agent's approach?**\n\n"
            "*YOUR ANSWER:*\n\n"
            "**Did the agent correctly identify patients with both poor "
            "control and impaired kidneys?**\n\n"
            "*YOUR ANSWER:*"
        ))

    # 16: Full conversation
    cells.append(code_cell(CONVERSATION_DISPLAY))

    # 17: Visualization intro
    cells.append(md_cell(
        "## Visualize the Data\n\n"
        "Let's visualize the data the agent retrieved. We'll call the "
        "same tool functions the agent used, but collect the results into "
        "a DataFrame for plotting.\n\n"
        "This is cleaner than trying to parse the agent's text output — "
        "and it demonstrates how tool functions can be used both by "
        "agents and by traditional code."
    ))

    # 18: Visualization
    cells.append(code_cell(S2_VISUALIZATION))

    # 19: Takeaways
    cells.append(md_cell(
        "## Session 2 Takeaways\n\n"
        "1. **Tool-use agents** let the LLM decide which functions to "
        "call and in what order, based on the question.\n"
        "2. **The same clinical workflow** you built manually in Session 1 "
        "can be automated — but the agent's approach may differ from yours.\n"
        "3. **Visualization** makes relationships tangible: the scatter "
        "plot reveals whether the agent's data supports the expected "
        "correlation between diabetes control and kidney function.\n"
        "4. **Medications** add clinical context: patients with both poor "
        "control and impaired kidneys may be on more aggressive regimens.\n\n"
        "In **Session 3**, you'll ask your own questions, add more tools, "
        "and actively look for where the agent breaks."
    ))

    return cells


# ══════════════════════════════════════════════════════════════
# SESSION 3 CELLS
# ══════════════════════════════════════════════════════════════

def session3_cells(instructor=False):
    cells = []
    tag = " — INSTRUCTOR VERSION" if instructor else ""

    # 1: Title + goals
    cells.append(md_cell(
        f"# Session 3: Open-Ended Exploration — Type 1 vs Type 2 Diabetes{tag}\n\n"
        "## Goals\n\n"
        "- Ask **at least 2 clinical questions** of your own\n"
        "- **At least 1** must compare Type 1 and Type 2 diabetes\n"
        "- Find **at least 1 surprise or failure** in the agent's behavior\n"
        "- Visualize your findings\n"
        "- Submit a structured report"
    ))

    # 2: Phenotype description
    cells.append(md_cell(PHENOTYPE_DESCRIPTION))

    # 3: Clinical code reference
    cells.append(md_cell(CLINICAL_CODE_REFERENCE))

    # 4: T1 vs T2 comparison guide
    cells.append(md_cell(T1_VS_T2_COMPARISON))

    # 5: Setup (includes pip install)
    cells.append(code_cell(SETUP_S23))

    # 6: 5 base tool functions
    cells.append(code_cell(TOOL_FUNCTIONS_5))

    # 8: 2 additional tools
    cells.append(code_cell(TOOL_FUNCTIONS_2_EXTRA))

    # 9: Smoke tests
    cells.append(code_cell(S3_SMOKE_TESTS))

    # 10: All 7 tool schemas
    cells.append(code_cell(TOOL_SCHEMAS_5 + "\n\n" + TOOL_SCHEMAS_2_EXTRA))

    # 11: System prompt
    cells.append(code_cell(SYSTEM_PROMPT_S3))

    # 12: Agent loop
    cells.append(code_cell(AGENT_LOOP))

    # 13: Question ideas
    cells.append(md_cell(
        "## Question Ideas\n\n"
        "Choose from these or create your own. You need **at least 2**, "
        "with **at least 1 comparing Type 1 and Type 2 diabetes**.\n\n"
        "### Straightforward\n"
        "- \"Find patients with Type 1 diabetes (SNOMED 46635009) and "
        "retrieve their HbA1c and C-peptide values\"\n"
        "- \"Find patients with chronic kidney disease (SNOMED 709044004) "
        "and check their eGFR and creatinine\"\n\n"
        "### Type 1 vs Type 2 Comparisons (pick at least one)\n"
        "- \"Compare HbA1c levels between Type 1 and Type 2 diabetes "
        "patients. Which group has worse glycemic control?\"\n"
        "- \"Compare C-peptide levels between Type 1 and Type 2 diabetes "
        "patients. How do they differ and why?\"\n"
        "- \"Compare medication patterns between Type 1 and Type 2 "
        "diabetes patients\"\n\n"
        "### Complex / Multi-Step\n"
        "- \"Find patients with both diabetes and chronic kidney disease. "
        "Is there a relationship between their HbA1c and eGFR?\"\n"
        "- \"Which patients have the worst kidney function? What are their "
        "other diagnoses and medications?\"\n\n"
        "### Edge Cases (likely to produce agent failures)\n"
        "- \"Are there patients who might be misclassified — diagnosed with "
        "Type 2 diabetes but with C-peptide levels more consistent with "
        "Type 1?\"\n"
        "- \"Find the healthiest patients on this server\" (vague — "
        "interesting failure mode)\n\n"
        "After running your agent questions, you can visualize the data:\n"
        "```python\n"
        "# 1. Collect data using the tool functions directly\n"
        "# 2. Build a pandas DataFrame\n"
        "# 3. Plot with matplotlib\n"
        "# Example: plt.scatter(df['c_peptide'], df['hba1c'])\n"
        "```"
    ))

    # 14: Question 1 header
    cells.append(md_cell(
        "## Question 1\n\n"
        "Enter your first question in the cell below. Describe what you "
        "expect the agent to do before running it."
    ))

    # 15: Question 1 run
    if instructor:
        cells.append(code_cell(
            'user_question_1 = "Compare HbA1c levels between Type 1 and Type 2 diabetes '\
            'patients. Which group has worse glycemic control?"\n\n'
            'answer_1, tool_calls_1, messages_1 = run_agent(user_question_1)'
        ))
    else:
        cells.append(code_cell(
            'user_question_1 = ""\n'
            '# ^^^ Fill in your question above ^^^\n\n'
            'answer_1, tool_calls_1, messages_1 = run_agent(user_question_1)'
        ))

    # 16: Question 1 trace
    cells.append(code_cell(
        '# Question 1 trace\n'
        'tool_calls_log = tool_calls_1  # for the trace display\n'
        + TRACE_DISPLAY
    ))

    # 17: Question 2 header
    cells.append(md_cell(
        "## Question 2 — Type 1 vs Type 2 Comparison\n\n"
        "If you haven't already, make this one a **comparison between "
        "Type 1 and Type 2 diabetes**. The agent has access to SNOMED "
        "codes for both (44054006 for Type 2, 46635009 for Type 1) and "
        "C-peptide (LOINC 1986-9) is the key differentiating lab."
    ))

    # 18: Question 2 run
    if instructor:
        cells.append(code_cell(
            'user_question_2 = "Compare C-peptide levels between Type 1 and Type 2 diabetes '\
            'patients. How do they differ and why?"\n\n'
            'answer_2, tool_calls_2, messages_2 = run_agent(user_question_2)'
        ))
    else:
        cells.append(code_cell(
            'user_question_2 = ""\n'
            '# ^^^ Fill in your question above ^^^\n\n'
            'answer_2, tool_calls_2, messages_2 = run_agent(user_question_2)'
        ))

    # 19: Question 2 trace
    cells.append(code_cell(
        '# Question 2 trace\n'
        'tool_calls_log = tool_calls_2  # for the trace display\n'
        + TRACE_DISPLAY
    ))

    # 20: Visualize your findings
    cells.append(md_cell(
        "## Visualize Your Findings\n\n"
        "The cell below creates a pre-built comparison plot of Type 1 vs "
        "Type 2 diabetes patients using C-peptide and HbA1c values. Run "
        "it to see the biochemical difference between the two types.\n\n"
        "You can also create your own plots using the tool functions "
        "directly — for example:\n\n"
        "```python\n"
        "# Get data for your specific question\n"
        "results = search_observations(patient_id, \"4548-4\")\n"
        "# Build a DataFrame and plot\n"
        "df = pd.DataFrame(rows)\n"
        "plt.scatter(df['x_column'], df['y_column'])\n"
        "plt.show()\n"
        "```"
    ))

    # 21: Comparison plot
    cells.append(code_cell(S3_COMPARISON_PLOT))

    # 22: Failure/surprise analysis
    if instructor:
        cells.append(md_cell(
            "## Failure and Surprise Analysis\n\n"
            "**What surprised you about the agent's behavior?**\n\n"
            "Common surprises: the agent may not search for both diabetes "
            "types in a comparison question (only doing one, then "
            "answering). It may hallucinate a LOINC code for a lab it "
            "doesn't have. With 7 tools, it has more choices and may pick "
            "suboptimal ones.\n\n"
            "**Did the agent make any errors?**\n\n"
            "Watch for: inventing data not returned by tools, incomplete "
            "searches (checking only a few patients), wrong SNOMED codes, "
            "premature stopping before checking all patients.\n\n"
            "**How would you improve the agent?**\n\n"
            "Options: refine the system prompt to be more explicit about "
            "comparison strategies, add tool descriptions that clarify "
            "when to use `search_all_conditions` vs `search_conditions`, "
            "increase `max_steps` for complex questions."
        ))
    else:
        cells.append(md_cell(
            "## Failure and Surprise Analysis\n\n"
            "**What surprised you about the agent's behavior?**\n\n"
            "*YOUR ANSWER:*\n\n"
            "**Did the agent make any errors? (wrong data, missing "
            "patients, hallucinated values, etc.)**\n\n"
            "*YOUR ANSWER:*\n\n"
            "**How would you improve the agent to handle your questions "
            "better?**\n\n"
            "*YOUR ANSWER:*"
        ))

    # 23: Deliverable
    cells.append(code_cell(S3_DELIVERABLE))

    # 24: Final reflection
    cells.append(md_cell(
        "## Final Reflection\n\n"
        "Across all three sessions, you have:\n\n"
        "1. **Queried FHIR data manually** — understanding the API, "
        "references, and clinical codes\n"
        "2. **Watched an AI agent** perform the same workflow "
        "autonomously using tool schemas\n"
        "3. **Tested the agent** with your own questions and found its "
        "limitations\n\n"
        "The tools and patterns from these sessions — FHIR REST APIs, "
        "structured clinical terminologies (SNOMED, LOINC), LLM tool use, "
        "and agent evaluation — are the building blocks of modern clinical "
        "AI systems.\n\n"
        "**Key takeaway:** AI agents are powerful but not infallible. "
        "Domain expertise (understanding the clinical question, the data, "
        "and the expected answer) is what makes evaluation possible. "
        "The agent does the data fetching; the human ensures the answer "
        "makes clinical sense."
    ))

    return cells


# ══════════════════════════════════════════════════════════════
# Main
# ══════════════════════════════════════════════════════════════

def main():
    print("Creating v3 notebooks...\n")

    configs = [
        ("Session 1 Student", session1_cells(instructor=False),
         os.path.join(STUDENT_DIR, "session1_student_v3.ipynb")),
        ("Session 1 Instructor", session1_cells(instructor=True),
         os.path.join(INSTRUCTOR_DIR, "session1_instructor_v3.ipynb")),
        ("Session 2 Student", session2_cells(instructor=False),
         os.path.join(STUDENT_DIR, "session2_student_v3.ipynb")),
        ("Session 2 Instructor", session2_cells(instructor=True),
         os.path.join(INSTRUCTOR_DIR, "session2_instructor_v3.ipynb")),
        ("Session 3 Student", session3_cells(instructor=False),
         os.path.join(STUDENT_DIR, "session3_student_v3.ipynb")),
        ("Session 3 Instructor", session3_cells(instructor=True),
         os.path.join(INSTRUCTOR_DIR, "session3_instructor_v3.ipynb")),
    ]

    for label, cells, path in configs:
        nb = build_notebook(cells)
        write_notebook(nb, path)

    print("\nAll v3 notebooks created successfully.")


if __name__ == "__main__":
    main()
