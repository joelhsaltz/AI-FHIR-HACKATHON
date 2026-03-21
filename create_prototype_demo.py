#!/usr/bin/env python3
"""
Generate the demo prototype notebook: "You Are the Agent" with FHIR grounding.

Two-activity design:
  Activity 1: Student acts as the agent (manual FHIR queries + classification)
  Activity 2: Student writes prompts for an AI agent (repeatable, scored)

All code cells use cellView: "form" metadata so students never see Python code.
FHIR queries are surfaced in output so students learn the data layer.
"""

import json
import os
import uuid


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_PATH = os.path.join(SCRIPT_DIR, "prototypes", "you_are_the_agent_demo.ipynb")


def _id():
    return uuid.uuid4().hex[:8]


def md_cell(source):
    s = source if isinstance(source, list) else [source]
    return {"cell_type": "markdown", "id": _id(), "metadata": {}, "source": s}


def form_cell(source):
    # Split into individual lines for Colab's #@param parser.
    # Colab needs separate lines in the source array to detect all form fields.
    if isinstance(source, list):
        lines = source
    else:
        lines = [line + "\n" for line in source.split("\n")]
        if lines:
            lines[-1] = lines[-1].rstrip("\n")  # no trailing newline on last line
    return {
        "cell_type": "code", "id": _id(),
        "metadata": {"cellView": "form"},
        "source": lines, "execution_count": None, "outputs": [],
    }


def build_notebook(cells):
    return {
        "nbformat": 4, "nbformat_minor": 5,
        "metadata": {
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python", "version": "3.10.0"},
            "colab": {"provenance": [], "collapsed_sections": []},
        },
        "cells": cells,
    }


# ===================================================================
# Cell code constants
# ===================================================================

SETUP = r"""
#@title Step 1: Connect to the FHIR server
import subprocess, sys
subprocess.check_call(
    [sys.executable, "-m", "pip", "install", "-q", "anthropic", "requests", "pandas"],
    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
)

import os, json
from datetime import date, datetime
import pandas as pd
import requests, urllib3
from IPython.display import Markdown, display, HTML
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ---- FHIR connection ----
FHIR_BASE = "https://lfh-fhir.eastus2.cloudapp.azure.com:9443/fhir-server/api/v4"
FHIR_SESSION = requests.Session()
FHIR_SESSION.auth = ("fhiruser", "BmI512@ccess")
FHIR_SESSION.verify = False

# ---- Anthropic client (optional) ----
try:
    from google.colab import userdata
    ANTHROPIC_API_KEY = userdata.get("ANTHROPIC_API_KEY")
except Exception:
    ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
try:
    from anthropic import Anthropic
except Exception:
    Anthropic = None
_anthropic_client = Anthropic(api_key=ANTHROPIC_API_KEY) if (Anthropic and ANTHROPIC_API_KEY) else None
MODEL = "claude-sonnet-4-20250514"

# ---- Verify ----
resp = FHIR_SESSION.get(f"{FHIR_BASE}/metadata", params={"_format": "json"}, timeout=20)
if resp.status_code != 200:
    display(Markdown("**Connection failed.** Check server URL and credentials."))
    raise RuntimeError(f"FHIR server: HTTP {resp.status_code}")
count_resp = FHIR_SESSION.get(f"{FHIR_BASE}/Patient", params={"_summary": "count", "_format": "json"}, timeout=20)
patient_count = count_resp.json().get("total", "unknown")

display(Markdown(
    "## Connection Status\n\n"
    "| Component | Status | Detail |\n"
    "|-----------|--------|--------|\n"
    f"| FHIR Server | Connected | `{FHIR_BASE.split('//')[1].split('/')[0]}` · FHIR R4 |\n"
    f"| Patient records | {patient_count} | Synthetic cohort with diabetes phenotypes |\n"
    f"| AI Agent | {'Ready' if _anthropic_client else 'Not configured'} "
    f"| {'Claude — for Activity 2' if _anthropic_client else 'Add ANTHROPIC_API_KEY in Secrets (see above)'} |\n"
))
""".strip()


TOOLS = r"""
#@title Step 2: Load clinical query tools

import random as _random

# === Coding systems ===
SNOMED = {"t1d": "46635009", "t2d": "44054006", "ckd": "709044004"}
LOINC = {
    "hba1c": "4548-4", "c_peptide": "1986-9", "bmi": "39156-5",
    "creatinine": "2160-0", "egfr": "33914-3", "uacr": "14959-1",
}
LAB_LOOKUP = {
    "HbA1c": ("4548-4", "Hemoglobin A1c — glycemic control over ~3 months"),
    "C-peptide": ("1986-9", "C-peptide — marker of endogenous insulin production"),
    "BMI": ("39156-5", "Body mass index — insulin-resistance context"),
    "Creatinine": ("2160-0", "Serum creatinine — kidney function"),
    "eGFR": ("33914-3", "Estimated GFR — kidney function"),
}

# === FHIR query functions ===
def _compute_age(birth_date):
    if not birth_date: return None
    born = datetime.strptime(birth_date, "%Y-%m-%d").date()
    today = date.today()
    return today.year - born.year - ((today.month, today.day) < (born.month, born.day))

def _normalize_patient_ref(ref):
    # Extract patient ID from various FHIR reference formats.
    if not ref:
        return None
    if ref.startswith("urn:uuid:"):
        return None  # Can't resolve URN references
    if "Patient/" in ref:
        return ref.split("Patient/")[-1]
    return ref.split("/")[-1]

def _fhir_get(path, params=None):
    # Execute a FHIR GET and return (url_display, json).
    url = f"{FHIR_BASE}/{path}"
    resp = FHIR_SESSION.get(url, params={**(params or {}), "_format": "json"}, timeout=30)
    resp.raise_for_status()
    # Build a human-readable query string
    display_params = "&".join(f"{k}={v}" for k, v in (params or {}).items() if k != "_format")
    display_url = f"GET /{path}" + (f"?{display_params}" if display_params else "")
    return display_url, resp.json()

def _get_patient(patient_id):
    fhir_url, patient = _fhir_get(f"Patient/{patient_id}")
    name = patient.get("name", [{}])[0]
    result = {
        "id": patient.get("id"),
        "name": f"{' '.join(name.get('given', []))} {name.get('family', '')}".strip(),
        "gender": patient.get("gender", ""),
        "birthDate": patient.get("birthDate", ""),
        "age": _compute_age(patient.get("birthDate", "")),
    }
    return fhir_url, result

def _search_conditions(code, max_results=50):
    fhir_url, bundle = _fhir_get("Condition", {"code": code, "_count": max_results})
    rows = []
    for entry in bundle.get("entry", []):
        r = entry["resource"]
        coding = r.get("code", {}).get("coding", [{}])[0]
        rows.append({
            "patient_reference": r.get("subject", {}).get("reference", ""),
            "code": coding.get("code", ""),
            "display": coding.get("display", ""),
        })
    return fhir_url, {"total": bundle.get("total", 0), "results": rows}

def _search_all_conditions_raw(patient_id, max_results=20):
    fhir_url, bundle = _fhir_get("Condition", {"subject": f"Patient/{patient_id}", "_count": max_results})
    rows = []
    for entry in bundle.get("entry", []):
        r = entry["resource"]
        coding = r.get("code", {}).get("coding", [{}])[0]
        rows.append({
            "condition": coding.get("display", ""),
            "code": coding.get("code", ""),
            "clinical_status": r.get("clinicalStatus", {}).get("coding", [{}])[0].get("code", ""),
        })
    return fhir_url, {"total": bundle.get("total", 0), "results": rows}

# Plausible non-diabetes conditions for scrambling the problem list
_DIABETES_CODES = {"46635009", "44054006"}  # T1D, T2D SNOMED codes
_FAKE_CONDITIONS = [
    {"condition": "Essential hypertension", "code": "59621000", "clinical_status": "active"},
    {"condition": "Hyperlipidemia", "code": "55822004", "clinical_status": "active"},
    {"condition": "Asthma", "code": "195967001", "clinical_status": "active"},
    {"condition": "Gastroesophageal reflux disease", "code": "235595009", "clinical_status": "active"},
    {"condition": "Osteoarthritis", "code": "396275006", "clinical_status": "active"},
    {"condition": "Allergic rhinitis", "code": "61582004", "clinical_status": "active"},
    {"condition": "Generalized anxiety disorder", "code": "21897009", "clinical_status": "active"},
    {"condition": "Low back pain", "code": "279039007", "clinical_status": "active"},
    {"condition": "Obstructive sleep apnea", "code": "78275009", "clinical_status": "active"},
    {"condition": "Iron deficiency anemia", "code": "87522002", "clinical_status": "active"},
]

def _search_all_conditions(patient_id, max_results=20):
    # Scrambled version: replaces diabetes diagnoses with random non-diabetes conditions
    # so the problem list doesn't give away the answer.
    import hashlib
    fhir_url, raw_result = _search_all_conditions_raw(patient_id, max_results)
    # Deterministic seed per patient so same patient always gets same fakes
    seed = int(hashlib.md5(patient_id.encode()).hexdigest()[:8], 16)
    rng = _random.Random(seed)
    available_fakes = list(_FAKE_CONDITIONS)
    rng.shuffle(available_fakes)
    fake_idx = 0
    scrambled = []
    for row in raw_result["results"]:
        if row.get("code") in _DIABETES_CODES:
            if fake_idx < len(available_fakes):
                scrambled.append(dict(available_fakes[fake_idx]))
                fake_idx += 1
            # else skip — ran out of fakes (unlikely)
        else:
            scrambled.append(row)
    return fhir_url, {"total": raw_result["total"], "results": scrambled}

def _search_observations(patient_id, loinc_code, max_results=5):
    fhir_url, bundle = _fhir_get("Observation", {
        "subject": f"Patient/{patient_id}", "code": loinc_code,
        "_count": max_results, "_sort": "-date",
    })
    rows = []
    for entry in bundle.get("entry", []):
        r = entry["resource"]
        coding = r.get("code", {}).get("coding", [{}])[0]
        vq = r.get("valueQuantity", {})
        rows.append({
            "display": coding.get("display", ""),
            "value": vq.get("value"), "unit": vq.get("unit", ""),
            "date": r.get("effectiveDateTime", ""),
        })
    return fhir_url, {"total": bundle.get("total", 0), "results": rows}

def _search_medications(patient_id, max_results=10):
    fhir_url, bundle = _fhir_get("MedicationRequest", {
        "subject": f"Patient/{patient_id}", "_count": max_results,
    })
    rows = []
    for entry in bundle.get("entry", []):
        r = entry["resource"]
        mc = r.get("medicationCodeableConcept", {})
        coding = mc.get("coding", [{}])[0] if mc.get("coding") else {}
        rows.append({
            "medication": coding.get("display") or mc.get("text", "unknown"),
            "status": r.get("status", ""),
            "authoredOn": r.get("authoredOn", ""),
        })
    return fhir_url, {"total": bundle.get("total", 0), "results": rows}

def _search_encounters(patient_id, max_results=10):
    fhir_url, bundle = _fhir_get("Encounter", {
        "subject": f"Patient/{patient_id}", "_count": max_results, "_sort": "-date",
    })
    rows = []
    for entry in bundle.get("entry", []):
        r = entry["resource"]
        etype = r.get("type", [{}])[0].get("text", "") if r.get("type") else ""
        rows.append({
            "status": r.get("status", ""),
            "class": r.get("class", {}).get("code", ""),
            "type": etype,
            "period_start": r.get("period", {}).get("start", ""),
        })
    return fhir_url, {"total": bundle.get("total", 0), "results": rows}

# === Helper: show a FHIR query banner ===
def _show_query(fhir_url, resource_type=None):
    extra = f" · **{resource_type}** resource" if resource_type else ""
    display(Markdown(f"> **FHIR Query:** `{fhir_url}`{extra}"))

# === Ground truth ===
def _get_ground_truth(patient_id):
    _, conds = _search_all_conditions_raw(patient_id)
    codes = [r.get("code", "") for r in conds.get("results", [])]
    if "46635009" in codes:
        return "Type 1"
    if "44054006" in codes:
        return "Type 2"
    return "No diabetes"

# === State ===
_state = {
    "question": "Classify this patient: Type 1 diabetes, Type 2 diabetes, or no diabetes?",
    "num_cases": 0,
    "case_patients": [],
    "current_case_idx": 0,
    "patient_id": None,
    "patient_label": None,
    "history": [],
    "evidence": {},
    "correct_answer": None,
    "human_results": [],
    "agent_runs": [],
    "agent_prompt": "",
}

def _evidence_gaps():
    ev = _state["evidence"]
    gaps = []
    if "demographics" not in ev:
        gaps.append(("Demographics — age at onset", "Patient"))
    if "conditions" not in ev:
        gaps.append(("Problem list — existing diagnoses", "Condition"))
    if "c_peptide" not in ev:
        gaps.append(("C-peptide — direct T1/T2 differentiator", "Observation"))
    if "hba1c" not in ev:
        gaps.append(("HbA1c — glycemic control", "Observation"))
    if "bmi" not in ev:
        gaps.append(("BMI — insulin resistance context", "Observation"))
    if "egfr" not in ev:
        gaps.append(("eGFR — kidney function / CKD staging", "Observation"))
    if "treatment_regimen" not in ev:
        gaps.append(("Treatment regimen — insulin-only vs oral agents", "MedicationRequest"))
    return gaps

def _render_dashboard():
    lines = ["---", "## Your Agent Dashboard", ""]
    _case_num = _state["current_case_idx"] + 1
    _total = _state["num_cases"]
    lines.append(f"**Case {_case_num} of {_total}**")
    lines.append(f"  \n**Clinical Question:** {_state['question']}")
    if _state["patient_label"]:
        lines.append(f"  \n**Patient:** {_state['patient_label']} · ID: `{_state['patient_id']}`")
    lines.append("")

    ev = _state["evidence"]
    lines.append("### Evidence Collected")
    if not ev:
        lines.append("*No evidence gathered yet. Use the menu below to start querying.*")
    else:
        lines.append("\n| Category | FHIR Resource | Finding |")
        lines.append("|----------|---------------|---------|")
        for key, value in ev.items():
            if key == "demographics":
                lines.append(f"| Demographics | `Patient` | Age {value.get('age')}, {value.get('gender')}, DOB {value.get('birthDate')} |")
            elif key == "conditions":
                names = [r["condition"] for r in value[:5]]
                lines.append(f"| Problem List | `Condition` | {', '.join(names) if names else 'None found'} |")
            elif key == "treatment_regimen":
                meds = [r["medication"] for r in value[:5]]
                lines.append(f"| Treatment Regimen | `MedicationRequest` | {', '.join(meds) if meds else 'None found'} |")
            elif key == "encounters":
                if value:
                    e = value[0]
                    lines.append(f"| Encounters | `Encounter` | Most recent: {e.get('type', 'N/A')} ({e.get('period_start', 'N/A')}) |")
                else:
                    lines.append("| Encounters | `Encounter` | None found |")
            else:
                lab_label = key.replace('_', ' ').title()
                if isinstance(value, dict) and "latest" in value:
                    latest = value["latest"]
                    if latest:
                        lines.append(f"| {lab_label} | `Observation` | {latest.get('value')} {latest.get('unit', '')} ({latest.get('date', 'N/A')}) |")
                    else:
                        lines.append(f"| {lab_label} | `Observation` | No results found |")
        lines.append("")

    gaps = _evidence_gaps()
    lines.append("### Still Needed")
    if gaps:
        for label, resource in gaps:
            lines.append(f"- {label} — *query* `{resource}`")
    else:
        lines.append("*All key evidence categories covered. You may be ready to classify.*")
    lines.append("")

    lines.append("### Query Log")
    if not _state["history"]:
        lines.append("*No queries yet.*")
    else:
        lines.append("\n| # | FHIR Query | Finding |")
        lines.append("|---|------------|---------|")
        for item in _state["history"][-8:]:
            lines.append(f"| {item['step']} | `{item['fhir_query']}` | {item['note']} |")
    lines.append("\n---")
    return "\n".join(lines)

# === Claude tool schemas (for the AI agent in Activity 2) ===
CLAUDE_TOOLS = [
    {
        "name": "get_patient",
        "description": (
            "FHIR query: GET /Patient/{id}. Returns demographics (age, gender, DOB). "
            "Age at onset is clinically relevant: younger onset leans toward Type 1."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"patient_id": {"type": "string"}},
            "required": ["patient_id"],
        },
    },
    {
        "name": "search_observations",
        "description": (
            "FHIR query: GET /Observation?subject=Patient/{id}&code={loinc}. "
            "Query ONE lab at a time to reason about each result before deciding the next query. "
            "Key LOINC codes: 1986-9 C-peptide (direct T1/T2 differentiator — low means beta-cell "
            "destruction), 4548-4 HbA1c (glycemic control, severity not type), 39156-5 BMI "
            "(insulin resistance context), 33914-3 eGFR (kidney function / CKD staging)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "patient_id": {"type": "string"},
                "loinc_code": {"type": "string"},
                "max_results": {"type": "integer", "default": 5},
            },
            "required": ["patient_id", "loinc_code"],
        },
    },
    {
        "name": "search_medications",
        "description": (
            "FHIR query: GET /MedicationRequest?subject=Patient/{id}. Returns treatment regimen. "
            "Insulin-only pattern suggests Type 1; oral agents (metformin, sulfonylureas) suggest Type 2."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "patient_id": {"type": "string"},
                "max_results": {"type": "integer", "default": 10},
            },
            "required": ["patient_id"],
        },
    },
    {
        "name": "search_all_conditions",
        "description": (
            "FHIR query: GET /Condition?subject=Patient/{id}. Returns full problem list with "
            "SNOMED codes and clinical status. Note: diabetes-specific diagnoses have been "
            "replaced to prevent answer leakage — use labs and medications for classification."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "patient_id": {"type": "string"},
                "max_results": {"type": "integer", "default": 20},
            },
            "required": ["patient_id"],
        },
    },
    {
        "name": "search_encounters",
        "description": (
            "FHIR query: GET /Encounter?subject=Patient/{id}. Returns visit history. "
            "Care pattern context — frequency and type of visits."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "patient_id": {"type": "string"},
                "max_results": {"type": "integer", "default": 10},
            },
            "required": ["patient_id"],
        },
    },
]

# Map tool names to local functions for the agent runner
def _tool_runner(fn_name, fn_args):
    dispatch = {
        "get_patient": lambda **kw: _get_patient(**kw)[1],
        "search_observations": lambda **kw: _search_observations(**kw)[1],
        "search_medications": lambda **kw: _search_medications(**kw)[1],
        "search_all_conditions": lambda **kw: _search_all_conditions(**kw)[1],
        "search_encounters": lambda **kw: _search_encounters(**kw)[1],
    }
    fn = dispatch.get(fn_name)
    if fn is None:
        return {"error": f"Unknown tool: {fn_name}"}
    return fn(**fn_args)

# Map tool names to FHIR display URLs for the agent log
def _tool_to_fhir_display(fn_name, fn_args):
    pid = fn_args.get("patient_id", "?")
    if fn_name == "get_patient":
        return f"GET /Patient/{pid}"
    if fn_name == "search_all_conditions":
        return f"GET /Condition?subject=Patient/{pid}"
    if fn_name == "search_observations":
        loinc = fn_args.get("loinc_code", "?")
        return f"GET /Observation?subject=Patient/{pid}&code={loinc}"
    if fn_name == "search_medications":
        return f"GET /MedicationRequest?subject=Patient/{pid}"
    if fn_name == "search_encounters":
        return f"GET /Encounter?subject=Patient/{pid}"
    return fn_name

# Map tool names to plain-English action descriptions
def _tool_to_human_label(fn_name, fn_args):
    labels = {
        "get_patient": "Get demographics",
        "search_all_conditions": "Get problem list",
        "search_medications": "Get treatment regimen",
        "search_encounters": "Get encounters",
    }
    if fn_name == "search_observations":
        loinc = fn_args.get("loinc_code", "")
        loinc_labels = {
            "4548-4": "Get HbA1c",
            "1986-9": "Get C-peptide",
            "39156-5": "Get BMI",
            "2160-0": "Get creatinine",
            "33914-3": "Get eGFR",
            "14959-1": "Get UACR",
        }
        return loinc_labels.get(loinc, f"Get lab ({loinc})")
    return labels.get(fn_name, fn_name)

# Create a brief human-readable summary of what came back
def _summarize_result(fn_name, fn_args, result):
    if fn_name == "get_patient":
        age = result.get("age", "?")
        gender = result.get("gender", "?")
        return f"Age {age}, {gender}"
    if fn_name == "search_all_conditions":
        items = result.get("results", [])
        if not items:
            return "No conditions found"
        names = [r.get("condition", "?") for r in items[:3]]
        suffix = f" (+{len(items)-3} more)" if len(items) > 3 else ""
        return ", ".join(names) + suffix
    if fn_name == "search_observations":
        items = result.get("results", [])
        if not items:
            return "No results found"
        latest = items[0]
        return f"{latest.get('value', '?')} {latest.get('unit', '')}"
    if fn_name == "search_medications":
        items = result.get("results", [])
        if not items:
            return "No medications found"
        names = [r.get("medication", "?") for r in items[:3]]
        suffix = f" (+{len(items)-3} more)" if len(items) > 3 else ""
        return ", ".join(names) + suffix
    if fn_name == "search_encounters":
        items = result.get("results", [])
        if not items:
            return "No encounters found"
        return f"{len(items)} encounters found"
    return ""

display(Markdown("**Clinical query tools loaded.** Proceed to the next step."))
""".strip()


BUILD_CANDIDATES = r"""
#@title Step 3: Build candidate pool from FHIR
import random as _random

_final_candidates = []

display(Markdown("*Querying FHIR server for working-age adults...*"))

_candidate_rows = []
_seen_patients = set()
_query_log = []
_diabetic_pids = set()

# --- Source 1 & 2: patients with T1D or T2D conditions ---
for _label, _code in [("t1d", SNOMED["t1d"]), ("t2d", SNOMED["t2d"])]:
    _furl, _cond_result = _search_conditions(_code, max_results=50)
    _query_log.append((_furl, "Condition"))
    for _item in _cond_result["results"]:
        _pid = _normalize_patient_ref(_item.get("patient_reference", ""))
        if not _pid or _pid in _seen_patients:
            continue
        try:
            _, _pat = _get_patient(_pid)
        except Exception:
            continue
        _age = _pat.get("age")
        if _age is None or _age > 50:
            continue
        _candidate_rows.append({
            "Name": _pat.get("name", ""),
            "Age": _age,
            "Gender": _pat.get("gender", ""),
            "_group": _label,
            "_patient_id": _pid,
        })
        _seen_patients.add(_pid)
        _diabetic_pids.add(_pid)

# --- Source 3: non-diabetic patients (metabolic syndrome phenotype) ---
_furl_pat, _pat_bundle = _fhir_get("Patient", {"_count": "50"})
_query_log.append((_furl_pat, "Patient"))
for _entry in _pat_bundle.get("entry", []):
    _pat_r = _entry.get("resource", {})
    _pid = _pat_r.get("id")
    if not _pid or _pid in _seen_patients:
        continue
    _age = _compute_age(_pat_r.get("birthDate", ""))
    if _age is None or _age > 50:
        continue
    # Check this patient has NO diabetes condition
    if _pid in _diabetic_pids:
        continue
    _name = _pat_r.get("name", [{}])[0]
    _candidate_rows.append({
        "Name": f"{' '.join(_name.get('given', []))} {_name.get('family', '')}".strip(),
        "Age": _age,
        "Gender": _pat_r.get("gender", ""),
        "_group": "no_diabetes",
        "_patient_id": _pid,
    })
    _seen_patients.add(_pid)

# Shuffle to avoid demographic clustering from sequential FHIR results
_random.shuffle(_candidate_rows)

# Select up to 10 candidates, aiming for ~3-4 from each group
_group_counts = {"t1d": 0, "t2d": 0, "no_diabetes": 0}
_group_limits = {"t1d": 4, "t2d": 4, "no_diabetes": 4}
# First pass: take up to limit from each group
for _row in _candidate_rows:
    _g = _row["_group"]
    if _group_counts[_g] >= _group_limits[_g]:
        continue
    _group_counts[_g] += 1
    _row["Case #"] = len(_final_candidates) + 1
    _final_candidates.append(_row)
    if len(_final_candidates) >= 10:
        break
# Second pass: fill remaining slots
if len(_final_candidates) < 10:
    for _row in _candidate_rows:
        if _row in _final_candidates:
            continue
        _row["Case #"] = len(_final_candidates) + 1
        _final_candidates.append(_row)
        if len(_final_candidates) >= 10:
            break

for _q, _rtype in _query_log:
    _show_query(_q, _rtype)

display(Markdown(
    "## Your Patient Candidates\n\n"
    "These working-age adults (age ≤ 50) were drawn from a cohort of 1,027 synthetic "
    "patients. The pool includes patients with diabetes *and* patients without it — "
    "not every patient with metabolic risk factors has diabetes.\n\n"
    "The game tracks both your **accuracy** (% correct) and **number of queries**. "
    "In real medicine, you'd look at everything — but in agent design, every query "
    "costs time, tokens, and money.\n\n"
    "*The cohort spans 6 canonical phenotypes along the diabetes–CKD spectrum "
    "(see the data overview above).*"
))
_cdf = pd.DataFrame(_final_candidates)[["Case #", "Name", "Age", "Gender"]]
display(HTML(_cdf.to_html(index=False)))
display(Markdown(f"**{len(_final_candidates)} candidates loaded.** Proceed to Step 4 to choose how many cases to work."))
""".strip()


CHOOSE_NUM_CASES = r"""
#@title Step 4: Choose how many cases to work
num_cases = 3 #@param {type:"integer"}

if "_final_candidates" not in dir() or not _final_candidates:
    display(Markdown(
        "**Run Step 3 first.** The candidate pool hasn't been built yet."
    ))
elif num_cases < 1 or num_cases > len(_final_candidates):
    display(Markdown(f"**Choose between 1 and {len(_final_candidates)} cases.**"))
else:
    _state["num_cases"] = num_cases
    _state["case_patients"] = _final_candidates[:num_cases]
    _state["current_case_idx"] = 0
    _state["human_results"] = []
    _state["agent_runs"] = []

    # Load first case
    _sel = _state["case_patients"][0]
    _state["patient_id"] = _sel["_patient_id"]
    _state["patient_label"] = f"{_sel['Name']} (Age {_sel['Age']}, {_sel['Gender']})"
    _state["history"] = []
    _state["evidence"] = {}
    _state["correct_answer"] = _get_ground_truth(_sel["_patient_id"])

    _case_rows = ""
    for i, p in enumerate(_state["case_patients"]):
        marker = "→" if i == 0 else " "
        _case_rows += f"| {marker} | {i+1} | {p['Name']} | {p['Age']} | {p['Gender']} |\n"

    display(Markdown(
        f"## Working {num_cases} Cases\n\n"
        "You'll classify these patients one at a time.\n\n"
        "| | Case | Patient | Age | Gender |\n"
        "|-|------|---------|-----|--------|\n"
        f"{_case_rows}\n"
        f"**Starting with Case 1:** {_state['patient_label']}\n\n"
        "Use **Step 5** below — query the FHIR server, then classify when ready."
    ))
""".strip()


INVESTIGATE = r"""
#@title Step 5: Investigate and classify (change dropdown → click Run → repeat)
action = "Get demographics" #@param ["Get demographics", "Get problem list", "Get C-peptide", "Get HbA1c", "Get BMI", "Get eGFR", "Get treatment regimen", "Get encounters", "— CLASSIFY —", "Classify: Type 1", "Classify: Type 2", "Classify: No diabetes"]

if _state["patient_id"] is None:
    display(Markdown("**Run Step 4 first.**"))
elif _state["current_case_idx"] >= _state["num_cases"]:
    display(Markdown("**All cases complete.** See your results in Step 6."))
elif action == "— CLASSIFY —":
    display(Markdown(
        "**Pick a classification** — select *Classify: Type 1*, *Classify: Type 2*, "
        "or *Classify: No diabetes* from the dropdown, then click Run."
    ))
elif action.startswith("Classify: "):
    # ---- Classification logic ----
    classification = action.replace("Classify: ", "")
    _queries_used = len([h for h in _state["history"] if h.get("fhir_query") != "—"])
    _correct_answer = _state["correct_answer"]
    _is_correct = (classification == _correct_answer)
    _case_num = _state["current_case_idx"] + 1

    _state["human_results"].append({
        "case_num": _case_num,
        "patient_id": _state["patient_id"],
        "patient_label": _state["patient_label"],
        "classification": classification,
        "correct_answer": _correct_answer,
        "correct": _is_correct,
        "queries_used": _queries_used,
    })

    # Immediate feedback
    if _is_correct:
        _feedback = f"## ✓ Correct!\n\nThe answer is **{_correct_answer}**."
    else:
        _feedback = (
            f"## ✗ Incorrect\n\n"
            f"You answered **{classification}** — the correct answer is **{_correct_answer}**."
        )

    # Progress table
    _progress_rows = ""
    for r in _state["human_results"]:
        _mark = "✓" if r["correct"] else "✗"
        _progress_rows += (
            f"| {r['case_num']} | {r['patient_label']} | "
            f"{r['classification']} | {r['correct_answer']} | {_mark} | {r['queries_used']} |\n"
        )

    # Advance to next case
    _state["current_case_idx"] += 1
    if _state["current_case_idx"] < _state["num_cases"]:
        _next = _state["case_patients"][_state["current_case_idx"]]
        _state["patient_id"] = _next["_patient_id"]
        _state["patient_label"] = f"{_next['Name']} (Age {_next['Age']}, {_next['Gender']})"
        _state["history"] = []
        _state["evidence"] = {}
        _state["correct_answer"] = _get_ground_truth(_next["_patient_id"])

        display(Markdown(
            f"{_feedback}\n\n"
            "---\n"
            "### Progress\n\n"
            "| Case | Patient | You | Correct | | Queries |\n"
            "|------|---------|-----|---------|---|--------|\n"
            f"{_progress_rows}\n"
            f"**Next — Case {_state['current_case_idx']+1}:** "
            f"{_state['patient_label']}\n\n"
            "Change the dropdown back to a query action and keep going."
        ))
    else:
        # All cases done
        _total_q = sum(r["queries_used"] for r in _state["human_results"])
        _avg_q = _total_q / len(_state["human_results"])
        _num_correct = sum(1 for r in _state["human_results"] if r["correct"])
        _pct = 100 * _num_correct / len(_state["human_results"])

        display(Markdown(
            f"{_feedback}\n\n"
            "---\n"
            "### Activity 1 Complete!\n\n"
            "| Case | Patient | You | Correct | | Queries |\n"
            "|------|---------|-----|---------|---|--------|\n"
            f"{_progress_rows}\n"
            f"**Score: {_num_correct}/{len(_state['human_results'])} correct ({_pct:.0f}%), "
            f"{_avg_q:.1f} avg queries**\n\n"
            "See full results in **Step 6**, then move to **Activity 2** (Step 7)."
        ))
else:
    # ---- Evidence gathering logic ----
    _pid = _state["patient_id"]
    _case_num = _state["current_case_idx"] + 1
    _total = _state["num_cases"]

    display(Markdown(f"**Case {_case_num} of {_total}:** {_state['patient_label']}"))

    if action == "Get demographics":
        _furl, _result = _get_patient(_pid)
        _show_query(_furl, "Patient")
        _state["evidence"]["demographics"] = _result
        _state["history"].append({"step": len(_state["history"]) + 1, "fhir_query": _furl, "note": f"Age {_result.get('age')}, {_result.get('gender')}"})
        display(Markdown(
            "### Demographics\n\n"
            "| Field | Value |\n|-------|-------|\n"
            f"| Name | {_result.get('name')} |\n"
            f"| Age | {_result.get('age')} |\n"
            f"| Gender | {_result.get('gender')} |\n"
            f"| Date of Birth | {_result.get('birthDate')} |"
        ))

    elif action == "Get problem list":
        _furl, _result = _search_all_conditions(_pid)
        _show_query(_furl, "Condition")
        _state["evidence"]["conditions"] = _result["results"]
        _state["history"].append({"step": len(_state["history"]) + 1, "fhir_query": _furl, "note": f"{len(_result['results'])} conditions found"})
        if _result["results"]:
            _rows_md = "\n".join(f"| {r['condition']} | {r['code']} | {r['clinical_status']} |" for r in _result["results"][:12])
            display(Markdown(f"### Problem List\n\n| Condition | SNOMED Code | Status |\n|-----------|-------------|--------|\n{_rows_md}"))
        else:
            display(Markdown("### Problem List\n\n*No conditions found for this patient.*"))

    elif action == "Get C-peptide":
        _furl, _result = _search_observations(_pid, "1986-9")
        _show_query(_furl, "Observation")
        _latest = _result["results"][0] if _result["results"] else None
        _state["evidence"]["c_peptide"] = {"bundle": _result, "latest": _latest}
        if _latest:
            _note = f"{_latest.get('value', 'N/A')} {_latest.get('unit', '')}"
            _state["history"].append({"step": len(_state["history"]) + 1, "fhir_query": _furl, "note": f"C-peptide: {_note}"})
            display(Markdown(f"### C-peptide\n\nDirect T1/T2 differentiator — low values indicate beta-cell destruction (Type 1).\n\n| Value | Unit | Date |\n|-------|------|------|\n| {_latest.get('value', 'N/A')} | {_latest.get('unit', '')} | {_latest.get('date', 'N/A')} |\n\n*Normal range: 1.1–4.4 ng/mL*"))
        else:
            _state["history"].append({"step": len(_state["history"]) + 1, "fhir_query": _furl, "note": "C-peptide: no results"})
            display(Markdown("### C-peptide\n\n*No C-peptide results found for this patient.*"))

    elif action == "Get HbA1c":
        _furl, _result = _search_observations(_pid, "4548-4")
        _show_query(_furl, "Observation")
        _latest = _result["results"][0] if _result["results"] else None
        _state["evidence"]["hba1c"] = {"bundle": _result, "latest": _latest}
        if _latest:
            _note = f"{_latest.get('value', 'N/A')} {_latest.get('unit', '')}"
            _state["history"].append({"step": len(_state["history"]) + 1, "fhir_query": _furl, "note": f"HbA1c: {_note}"})
            display(Markdown(f"### HbA1c\n\nGlycemic control over ~3 months — indicates severity, not type.\n\n| Value | Unit | Date |\n|-------|------|------|\n| {_latest.get('value', 'N/A')} | {_latest.get('unit', '')} | {_latest.get('date', 'N/A')} |\n\n*Target: < 7.0% · Poor control: > 7.5%*"))
        else:
            _state["history"].append({"step": len(_state["history"]) + 1, "fhir_query": _furl, "note": "HbA1c: no results"})
            display(Markdown("### HbA1c\n\n*No HbA1c results found for this patient.*"))

    elif action == "Get BMI":
        _furl, _result = _search_observations(_pid, "39156-5")
        _show_query(_furl, "Observation")
        _latest = _result["results"][0] if _result["results"] else None
        _state["evidence"]["bmi"] = {"bundle": _result, "latest": _latest}
        if _latest:
            _note = f"{_latest.get('value', 'N/A')} {_latest.get('unit', '')}"
            _state["history"].append({"step": len(_state["history"]) + 1, "fhir_query": _furl, "note": f"BMI: {_note}"})
            display(Markdown(f"### BMI\n\nInsulin resistance context — higher BMI leans toward T2, but not definitive.\n\n| Value | Unit | Date |\n|-------|------|------|\n| {_latest.get('value', 'N/A')} | {_latest.get('unit', '')} | {_latest.get('date', 'N/A')} |\n\n*Overweight: 25–30 · Obese: > 30*"))
        else:
            _state["history"].append({"step": len(_state["history"]) + 1, "fhir_query": _furl, "note": "BMI: no results"})
            display(Markdown("### BMI\n\n*No BMI results found for this patient.*"))

    elif action == "Get eGFR":
        _furl, _result = _search_observations(_pid, "33914-3")
        _show_query(_furl, "Observation")
        _latest = _result["results"][0] if _result["results"] else None
        _state["evidence"]["egfr"] = {"bundle": _result, "latest": _latest}
        if _latest:
            _note = f"{_latest.get('value', 'N/A')} {_latest.get('unit', '')}"
            _state["history"].append({"step": len(_state["history"]) + 1, "fhir_query": _furl, "note": f"eGFR: {_note}"})
            display(Markdown(f"### eGFR\n\nKidney function / CKD staging — complications context.\n\n| Value | Unit | Date |\n|-------|------|------|\n| {_latest.get('value', 'N/A')} | {_latest.get('unit', '')} | {_latest.get('date', 'N/A')} |\n\n*Normal: > 90 · CKD Stage 3: 30–59 · CKD Stage 4: 15–29*"))
        else:
            _state["history"].append({"step": len(_state["history"]) + 1, "fhir_query": _furl, "note": "eGFR: no results"})
            display(Markdown("### eGFR\n\n*No eGFR results found for this patient.*"))

    elif action == "Get treatment regimen":
        _furl, _result = _search_medications(_pid)
        _show_query(_furl, "MedicationRequest")
        _state["evidence"]["treatment_regimen"] = _result["results"]
        _state["history"].append({"step": len(_state["history"]) + 1, "fhir_query": _furl, "note": f"{len(_result['results'])} medications"})
        if _result["results"]:
            _rows_md = "\n".join(f"| {r['medication']} | {r['status']} | {r.get('authoredOn', 'N/A')} |" for r in _result["results"][:10])
            display(Markdown(f"### Treatment Regimen\n\nInsulin-only suggests T1; oral agents (metformin, sulfonylureas) suggest T2.\n\n| Medication | Status | Date |\n|------------|--------|------|\n{_rows_md}"))
        else:
            display(Markdown("### Treatment Regimen\n\n*No medications found.*"))

    elif action == "Get encounters":
        _furl, _result = _search_encounters(_pid)
        _show_query(_furl, "Encounter")
        _state["evidence"]["encounters"] = _result["results"]
        _state["history"].append({"step": len(_state["history"]) + 1, "fhir_query": _furl, "note": f"{len(_result['results'])} encounters"})
        if _result["results"]:
            _rows_md = "\n".join(f"| {r.get('type', 'N/A')} | {r.get('class', '')} | {r.get('status', '')} | {r.get('period_start', 'N/A')} |" for r in _result["results"][:8])
            display(Markdown(f"### Encounters\n\n| Type | Class | Status | Date |\n|------|-------|--------|------|\n{_rows_md}"))
        else:
            display(Markdown("### Encounters\n\n*No encounters found.*"))

    display(Markdown(_render_dashboard()))
""".strip()


ACTIVITY1_RESULTS = r"""
#@title Step 6: Your results

if not _state.get("human_results"):
    display(Markdown("**Complete Activity 1 first** (Step 5)."))
else:
    _h = _state["human_results"]
    _rows = ""
    for r in _h:
        _mark = "✓" if r["correct"] else "✗"
        _rows += (
            f"| {r['case_num']} | {r['patient_label']} | "
            f"{r['classification']} | {r['correct_answer']} | {_mark} | {r['queries_used']} |\n"
        )

    _num_correct = sum(1 for r in _h if r["correct"])
    _pct = 100 * _num_correct / len(_h)
    _total_q = sum(r["queries_used"] for r in _h)
    _avg_q = _total_q / len(_h)

    display(Markdown(
        "## Activity 1: Your Results\n\n"
        "| Case | Patient | Your Answer | Correct Answer | | Queries |\n"
        "|------|---------|-------------|----------------|---|--------|\n"
        f"{_rows}\n"
        f"### Grade: {_num_correct}/{len(_h)} correct ({_pct:.0f}%) · {_avg_q:.1f} avg queries\n\n"
        "---\n\n"
        "Now move to **Activity 2** (Step 7) — write a prompt and see if the AI agent "
        "can do better (or worse)."
    ))
""".strip()


PROMPT_EDITOR = r"""
#@title Step 7: Write your AI prompt
agent_prompt = "You are a clinical data assistant classifying diabetes patients using FHIR queries. Classify each patient as Type 1 diabetes, Type 2 diabetes, or No diabetes. Use the minimum queries needed to reach confidence. Prefer direct evidence (C-peptide, medications) over indirect (BMI)." #@param {type:"string"}

_state["agent_prompt"] = agent_prompt

display(Markdown(
    "## Activity 2: Write Your AI Prompt\n\n"
    "This prompt tells the AI agent how to approach the classification task. "
    f"It will use this prompt for all {_state.get('num_cases', '?')} cases.\n\n"
    f"**Your prompt:**\n\n> {agent_prompt[:400]}{'...' if len(agent_prompt) > 400 else ''}\n\n"
    "**Ideas to try:**\n"
    "- Emphasize efficiency: *\"never query more than 3 tools\"*\n"
    "- Change priorities: *\"always start with C-peptide\"*\n"
    "- Add constraints: *\"ignore BMI — it's not diagnostic\"*\n"
    "- Change persona: *\"you are an endocrinologist\"*\n\n"
    "Run **Step 8** to let the agent work. You can come back here, "
    "edit the prompt, and re-run Step 8 to compare different prompts."
))
""".strip()


RUN_AI_AGENT = r"""
#@title Step 8: Run the AI agent on all cases

if not _state.get("case_patients"):
    display(Markdown("**Run Steps 3-4 first.**"))
elif _anthropic_client is None:
    display(Markdown("**AI Agent requires an API key.** See the setup section above."))
elif len(_state.get("human_results", [])) < _state.get("num_cases", 0):
    display(Markdown(
        f"**Finish Activity 1 first** (Step 5). You've classified "
        f"{len(_state.get('human_results', []))} of {_state['num_cases']} cases."
    ))
else:
    _prompt = _state.get("agent_prompt", "Classify this patient.")
    _run_num = len(_state.get("agent_runs", [])) + 1
    _run_results = []

    display(Markdown(
        f"## Agent Run #{_run_num}\n\n"
        f"Running the AI agent on all {_state['num_cases']} cases...\n"
    ))

    for _case_idx, _case_patient in enumerate(_state["case_patients"]):
        _agent_pid = _case_patient["_patient_id"]
        _agent_label = f"{_case_patient['Name']} (Age {_case_patient['Age']}, {_case_patient['Gender']})"

        display(Markdown(f"---\n### Case {_case_idx+1}: {_agent_label}"))

        _agent_question = (
            f"Review patient {_agent_pid} ({_agent_label}). "
            "Classify as Type 1 diabetes, Type 2 diabetes, or no diabetes. "
            "Use the FHIR query tools. Cite specific findings."
        )
        _agent_system = (
            "You are a clinical data assistant querying a FHIR server with synthetic "
            "patient data. You work as an agent: query one tool at a time, reason about "
            "the result, then decide your next step.\n\n"
            "CLASSIFICATION: Type 1 diabetes / Type 2 diabetes / No diabetes\n\n"
            "The patient pool includes metabolic syndrome patients who do NOT have "
            "diabetes. Key signals: normal C-peptide (1.1–4.4 ng/mL), no diabetes "
            "medications, normal HbA1c (< 6.5%) = No diabetes.\n\n"
            "After EACH tool result, state your current assessment and next step.\n"
            "STOP when confident. Be concise.\n\n"
            "STUDENT PROMPT (follow this guidance):\n" + _prompt
        )

        _agent_messages = [{"role": "user", "content": _agent_question}]
        _agent_tool_log = []
        _final_text = "(max steps reached)"

        for _step in range(1, 9):
            _resp = _anthropic_client.messages.create(
                model=MODEL, max_tokens=4096, system=_agent_system,
                messages=_agent_messages, tools=CLAUDE_TOOLS,
            )
            _tblocks = [b for b in _resp.content if b.type == "tool_use"]
            _text_blocks = [b.text for b in _resp.content if b.type == "text" and b.text.strip()]

            if not _tblocks:
                _final_text = "".join(b.text for b in _resp.content if hasattr(b, "text"))
                break

            for _reasoning in _text_blocks:
                display(Markdown(f"> {_reasoning.replace(chr(10), chr(10) + '> ')}"))

            _acontent = []
            for _b in _resp.content:
                if _b.type == "text":
                    _acontent.append({"type": "text", "text": _b.text})
                elif _b.type == "tool_use":
                    _acontent.append({"type": "tool_use", "id": _b.id, "name": _b.name, "input": _b.input})
            _agent_messages.append({"role": "assistant", "content": _acontent})

            _tool_results = []
            for _tb in _tblocks:
                _fhir_display = _tool_to_fhir_display(_tb.name, _tb.input)
                _tr = _tool_runner(_tb.name, _tb.input)
                _result_summary = _summarize_result(_tb.name, _tb.input, _tr)
                _human_label = _tool_to_human_label(_tb.name, _tb.input)
                _agent_tool_log.append({"step": _step, "action": _human_label, "fhir": _fhir_display, "result": _result_summary})
                display(Markdown(f"**Step {_step}: {_human_label}** → {_result_summary}"))
                _tool_results.append({
                    "type": "tool_result", "tool_use_id": _tb.id,
                    "content": json.dumps(_tr, default=str),
                })
            _agent_messages.append({"role": "user", "content": _tool_results})

        # Extract classification
        _agent_classification = "Unclear"
        _fl = _final_text.lower()
        if "no diabetes" in _fl:
            _agent_classification = "No diabetes"
        elif "type 1" in _fl:
            _agent_classification = "Type 1"
        elif "type 2" in _fl:
            _agent_classification = "Type 2"

        _correct_answer = _get_ground_truth(_agent_pid)
        _is_correct = (_agent_classification == _correct_answer)

        _run_results.append({
            "case_num": _case_idx + 1,
            "patient_id": _agent_pid,
            "patient_label": _agent_label,
            "classification": _agent_classification,
            "correct_answer": _correct_answer,
            "correct": _is_correct,
            "queries_used": len(_agent_tool_log),
        })

        _mark = "✓" if _is_correct else "✗"
        display(Markdown(
            f"**Agent's answer:** {_agent_classification} {_mark} "
            f"(correct: {_correct_answer}) — {len(_agent_tool_log)} queries"
        ))

        # Reset tool log for next case
        _agent_tool_log = []

    # Record this run
    _num_correct = sum(1 for r in _run_results if r["correct"])
    _pct = 100 * _num_correct / len(_run_results)
    _total_q = sum(r["queries_used"] for r in _run_results)
    _avg_q = _total_q / len(_run_results)

    _state["agent_runs"].append({
        "run_num": _run_num,
        "prompt_excerpt": _prompt[:80] + ("..." if len(_prompt) > 80 else ""),
        "results": _run_results,
        "num_correct": _num_correct,
        "pct_correct": _pct,
        "total_queries": _total_q,
        "avg_queries": _avg_q,
    })

    # Show all runs
    display(Markdown("---\n## Agent Run History\n"))
    _run_rows = ""
    for _run in _state["agent_runs"]:
        _run_rows += (
            f"| {_run['run_num']} | {_run['prompt_excerpt']} | "
            f"{_run['num_correct']}/{len(_run['results'])} ({_run['pct_correct']:.0f}%) | "
            f"{_run['avg_queries']:.1f} |\n"
        )
    display(Markdown(
        "| Run | Prompt | Accuracy | Avg Queries |\n"
        "|-----|--------|----------|-------------|\n"
        f"{_run_rows}\n"
        "To try a different prompt, go back to **Step 7**, edit it, and re-run this cell."
    ))
""".strip()


SUMMARY = r"""
#@title Step 9: Summary

if not _state.get("human_results"):
    display(Markdown("**Complete Activity 1 first.**"))
elif not _state.get("agent_runs"):
    display(Markdown("**Complete Activity 2 first** (at least one agent run)."))
else:
    _h = _state["human_results"]
    _h_correct = sum(1 for r in _h if r["correct"])
    _h_pct = 100 * _h_correct / len(_h)
    _h_avg = sum(r["queries_used"] for r in _h) / len(_h)

    # Summary table: student + all agent runs
    _summary_rows = (
        f"| You (Activity 1) | — | "
        f"{_h_correct}/{len(_h)} ({_h_pct:.0f}%) | {_h_avg:.1f} |\n"
    )
    for _run in _state["agent_runs"]:
        _summary_rows += (
            f"| Agent Run {_run['run_num']} | {_run['prompt_excerpt']} | "
            f"{_run['num_correct']}/{len(_run['results'])} ({_run['pct_correct']:.0f}%) | "
            f"{_run['avg_queries']:.1f} |\n"
        )

    display(Markdown(
        "## Final Summary\n\n"
        "| Who | Prompt | Accuracy | Avg Queries |\n"
        "|-----|--------|----------|-------------|\n"
        f"{_summary_rows}\n"
    ))

    # Per-case detail table
    _detail_rows = ""
    for i, _hr in enumerate(_h):
        _you_mark = "✓" if _hr["correct"] else "✗"
        _row = (
            f"| {_hr['case_num']} | {_hr['patient_label']} | {_hr['correct_answer']} | "
            f"{_hr['classification']} {_you_mark} | {_hr['queries_used']} |"
        )
        for _run in _state["agent_runs"]:
            if i < len(_run["results"]):
                _ar = _run["results"][i]
                _ai_mark = "✓" if _ar["correct"] else "✗"
                _row += f" {_ar['classification']} {_ai_mark} | {_ar['queries_used']} |"
            else:
                _row += " — | — |"
        _detail_rows += _row + "\n"

    # Build header
    _header = "| Case | Patient | Correct | You | Queries |"
    _separator = "|------|---------|---------|-----|---------|"
    for _run in _state["agent_runs"]:
        _header += f" Run {_run['run_num']} | Queries |"
        _separator += "------|---------|"

    display(Markdown(
        "### Per-Case Detail\n\n"
        f"{_header}\n{_separator}\n{_detail_rows}"
    ))

    display(Markdown(
        "### Discussion Questions\n\n"
        "1. **Accuracy vs efficiency:** Who was more accurate? Who used fewer queries?\n"
        "2. **Prompt impact:** How did changing your prompt affect the AI's accuracy "
        "and query count? Which prompt worked best?\n"
        "3. **Strategy differences:** Did you and the AI query the same resources? "
        "In what order?\n"
        "4. **The 'no diabetes' trap:** Which patients were hardest? What evidence "
        "distinguishes metabolic syndrome from actual diabetes?\n"
        "5. **FHIR resource value:** Which resource type mattered most?\n"
        "6. **The agent loop:** *observe → decide → act → update → repeat.* "
        "What makes the 'when to stop' decision hard?\n"
    ))
""".strip()


# ===================================================================
# Markdown cell constants
# ===================================================================

INTRO = [
    "# You Are the Agent: A Clinical Classification Game\n",
    "\n",
    "This is a game designed to teach you two things: **how AI agents work** and "
    "**how FHIR queries access clinical data**.\n",
    "\n",
    "You'll classify synthetic patients as Type 1 diabetes, Type 2 diabetes, or "
    "no diabetes. Your tools are **FHIR queries** — structured requests to an "
    "electronic health record server.\n",
    "\n",
    "**The game has two activities:**\n",
    "\n",
    "**Activity 1 — You are the agent.** You manually choose which FHIR queries to "
    "run and classify each patient yourself. It's a quiz: you get immediate feedback "
    "after each classification.\n",
    "\n",
    "**Activity 2 — You are the prompt engineer.** You write a prompt that tells an "
    "AI agent how to approach the same cases. The AI runs autonomously using your "
    "instructions. You can iterate on your prompt and compare results.\n",
    "\n",
    "Both activities track your **accuracy** (% correct) and **number of queries "
    "used**. In real medicine, there's no reason to limit evidence — you'd look at "
    "everything. But in agent design, every query costs time, tokens, and money. "
    "Tracking query count teaches you to think about the tradeoffs that matter when "
    "building real AI agents.\n",
    "\n",
    "An AI agent works in a loop:\n",
    "\n",
    "1. **Observe** — what evidence do I have so far?\n",
    "2. **Decide** — what FHIR query would be most informative next?\n",
    "3. **Act** — execute the query\n",
    "4. **Update** — add the new evidence to my assessment\n",
    "5. **Repeat** or **answer** when confident\n",
    "\n",
    "> **No coding required.** Every step uses dropdown menus and Run buttons.\n",
]

WHAT_YOULL_PRACTICE = [
    "## What You'll Learn\n",
    "\n",
    "- How the **agent loop** works: observe → decide → act → update → repeat\n",
    "- How clinical questions map to **FHIR queries** against structured data\n",
    "- Which **FHIR resources** (Patient, Condition, Observation, MedicationRequest) "
    "carry the most signal for a given question\n",
    "- How **prompt engineering** shapes an AI agent's query strategy\n",
    "- The tradeoffs in agent design: accuracy vs. cost (query count)\n",
]

CLINICAL_SCENARIO = [
    "## The Clinical Scenario\n",
    "\n",
    "**Setting:** You are an informatics fellow reviewing a cohort of working-age adults "
    "(age ≤ 50) with a diabetes diagnosis in a synthetic FHIR server.\n",
    "\n",
    "**Problem:** Not every patient with metabolic risk factors has diabetes. The pool "
    "includes patients with diabetes (Type 1 and Type 2) *and* patients with metabolic "
    "syndrome who do not have diabetes. Accurate classification matters for management.\n",
    "\n",
    "**Your task:** Query the FHIR server and decide:\n",
    "- **Type 1 diabetes** — evidence supports autoimmune diabetes\n",
    "- **Type 2 diabetes** — evidence supports insulin resistance pattern\n",
    "- **No diabetes** — metabolic risk factors but no actual diabetes\n",
    "\n",
    "The game tracks both **accuracy** and **query count**.\n",
    "\n",
    "**Key evidence to look for:**\n",
    "- **C-peptide** (low → T1, normal/high → T2) — the most direct differentiator (`Observation` LOINC `1986-9`)\n",
    "- **Treatment regimen** (insulin-only vs. oral agents) — strong T1/T2 signal (`MedicationRequest`)\n",
    "- **BMI** (lower → T1, higher → T2, not definitive) — context, not proof (`Observation` LOINC `39156-5`)\n",
    "- **HbA1c** (glycemic control) — tells you severity, not type (`Observation` LOINC `4548-4`)\n",
    "- **eGFR** (kidney function) — complications and CKD staging (`Observation` LOINC `33914-3`)\n",
    "- **Diagnosis context** — existing conditions and comorbidities (`Condition`)\n",
]

ABOUT_THE_DATA = [
    "## About the Data: A Purpose-Built Synthetic Cohort\n",
    "\n",
    "The patient data in this exercise was created by **Joel Saltz** specifically for this "
    "course. It is a cohort of **1,027 synthetic patients** spanning six canonical phenotypes "
    "along the diabetes–CKD spectrum:\n",
    "\n",
    "| # | Phenotype | Key Features |\n",
    "|---|-----------|-------------|\n",
    "| 1 | **Metabolic syndrome** | **No diabetes**, no CKD — high BMI, borderline HbA1c, normal C-peptide, no diabetes meds |\n",
    "| 2 | Early Type 2 diabetes | No CKD |\n",
    "| 3 | Type 2 diabetes with obesity | Early CKD |\n",
    "| 4 | Advanced Type 2 diabetes | Moderate CKD |\n",
    "| 5 | Type 1 diabetes | Early nephropathy |\n",
    "| 6 | Type 1 diabetes, poor control | With CKD |\n",
    "\n",
    "Variables are **clinically coupled** — for example, C-peptide tracks diabetes type and "
    "duration, HbA1c correlates with glucose via the ADAG equation, and renal chemistry is "
    "internally consistent. Each phenotype has an age anchor and demographic variability, so "
    "patients within a phenotype are similar but not identical.\n",
    "\n",
    "The data is loaded into a **FHIR R4 server**, so you query it the same way you would "
    "query real clinical data. Synthetic data generation is a topic you may explore in a "
    "future session.\n",
]

TOOLKIT = [
    "## Your Toolkit: FHIR Queries as Agent Tools\n",
    "\n",
    "Each tool is a **FHIR query** — a structured request to a specific resource endpoint. "
    "Choosing WHICH tool to use next is a clinical reasoning decision.\n",
    "\n",
    "| Tool | FHIR Query | Clinical Reasoning |\n",
    "|------|------------|--------------------|\n",
    "| Get demographics | `GET /Patient/{id}` | Age at onset — younger leans toward T1 |\n",
    "| Get problem list | `GET /Condition?subject=...` | Existing diagnoses, comorbidities |\n",
    "| Get C-peptide | `GET /Observation?code=1986-9` | **Direct T1/T2 differentiator** — low = beta-cell destruction |\n",
    "| Get HbA1c | `GET /Observation?code=4548-4` | Glycemic control (severity, not type) |\n",
    "| Get BMI | `GET /Observation?code=39156-5` | Insulin resistance context |\n",
    "| Get eGFR | `GET /Observation?code=33914-3` | Kidney function / CKD staging |\n",
    "| Get treatment regimen | `GET /MedicationRequest?subject=...` | Insulin-only vs oral agents |\n",
    "| Get encounters | `GET /Encounter?subject=...` | Care pattern context |\n",
    "\n",
    "**Coding systems:** SNOMED CT for diagnoses (46635009 = T1DM, 44054006 = T2DM) · "
    "LOINC for labs (4548-4 = HbA1c, 1986-9 = C-peptide, 39156-5 = BMI, 33914-3 = eGFR)\n",
    "\n",
    "> In Activity 2, the AI agent has **exactly these same tools**. The difference is "
    "the prompt you give it.\n",
]

API_KEY_SETUP = [
    "## Before You Start: Set Up Your API Key\n",
    "\n",
    "Activity 2 (Steps 7-8) uses **Claude**, an AI model, which "
    "requires an API key. Activity 1 (where *you* are the agent) works without one, but "
    "you'll need the key to see the AI in action.\n",
    "\n",
    "**How to add your API key in Colab:**\n",
    "\n",
    "1. Look at the **left sidebar** — below the file browser and variable icons, you'll "
    "see a **key icon** (🔑). Click it to open the **Secrets** panel.\n",
    "2. Click **\"Add a secret\"**\n",
    "3. Set the name to exactly: `ANTHROPIC_API_KEY`\n",
    "4. Paste your API key as the value\n",
    "5. Toggle **\"Notebook access\"** to **ON**\n",
    "\n",
    "> **Gotcha:** You cannot edit a secret after saving it. If you need to change the key, "
    "**delete** the secret and create a new one with the same name.\n",
    "\n",
    "If you don't have an API key, you can still complete Activity 1 as the human agent. "
    "Ask your instructor if you need a key.\n",
]

ACTIVITY1_INTRO = [
    "## Activity 1: You Are the Agent\n",
    "\n",
    "**Everything happens in Step 5 below.** The dropdown has two sections:\n",
    "\n",
    "1. **Query actions** (top) — run FHIR queries to gather evidence\n",
    "2. **Classify actions** (bottom) — submit your answer when ready\n",
    "\n",
    "For each case: pick queries, run as many as you want, then select a "
    "*Classify* option to submit your answer. You get immediate feedback — "
    "right or wrong, no take-backs. The next case loads automatically. "
    "Keep running the same cell for all your cases.\n",
]

INVESTIGATE_INTRO = [
    "## Investigate and Classify\n",
    "\n",
    "Each time you run the cell below, you execute **one action** — either a FHIR "
    "query or a classification. Change the **action dropdown** and click Run.\n",
    "\n",
    "**Query actions** show:\n",
    "- The **FHIR request** that was made\n",
    "- The **results** with clinical context\n",
    "- Your **Agent Dashboard** showing collected evidence, gaps, and query log\n",
    "\n",
    "**Classify actions** record your answer, give immediate feedback, and load "
    "the next case.\n",
    "\n",
    "> **Run this cell as many times as you want.** Each run is one turn.\n",
    "\n",
    "> **Note:** The problem list has been modified so that diabetes-specific diagnoses "
    "don't give away the answer. Use labs and medications to build your case.\n",
]

ACTIVITY2_INTRO = [
    "## Activity 2: Prompt the AI Agent\n",
    "\n",
    "Now write a prompt that tells an AI agent how to classify the same patients. "
    "The agent has the same FHIR tools you used. You can run it, edit your "
    "prompt, and run again to see how different instructions change accuracy "
    "and query count.\n",
]

WRAPUP = [
    "## Wrap-Up\n",
    "\n",
    "You've experienced the core **agent loop** from two perspectives:\n",
    "\n",
    "**Activity 1** — you *were* the agent, choosing queries, weighing evidence, and "
    "deciding when you had enough to classify.\n",
    "\n",
    "**Activity 2** — you were the *prompt engineer*, writing instructions that shaped "
    "how an AI agent approached the same task.\n",
    "\n",
    "```\n",
    "while not confident_enough:\n",
    "    observe current evidence\n",
    "    choose next FHIR query (GET /Resource?parameters...)\n",
    "    execute the query\n",
    "    update assessment\n",
    "```\n",
    "\n",
    "The game tracked accuracy and query count — not because limiting queries is "
    "good medicine, but because it teaches you to think about the tradeoffs that "
    "matter in real agent design: cost, latency, and token usage.\n",
    "\n",
    "**Key takeaways:**\n",
    "- The agent loop is the same whether a human or AI is running it\n",
    "- FHIR resource choice matters — some queries are more informative than others\n",
    "- Prompt engineering directly affects agent behavior and performance\n",
    "- 'When to stop' is the hardest design decision in any agent\n",
]


# ===================================================================
# Assemble notebook
# ===================================================================

cells = [
    md_cell(INTRO),
    md_cell(WHAT_YOULL_PRACTICE),
    md_cell(CLINICAL_SCENARIO),
    md_cell(ABOUT_THE_DATA),
    md_cell(TOOLKIT),
    md_cell(API_KEY_SETUP),

    form_cell(SETUP),              # Step 1
    form_cell(TOOLS),              # Step 2
    form_cell(BUILD_CANDIDATES),   # Step 3

    md_cell(ACTIVITY1_INTRO),
    form_cell(CHOOSE_NUM_CASES),   # Step 4
    md_cell(INVESTIGATE_INTRO),
    form_cell(INVESTIGATE),        # Step 5
    form_cell(ACTIVITY1_RESULTS),  # Step 6

    md_cell(ACTIVITY2_INTRO),
    form_cell(PROMPT_EDITOR),      # Step 7
    form_cell(RUN_AI_AGENT),       # Step 8

    form_cell(SUMMARY),            # Step 9

    md_cell(WRAPUP),
]

notebook = build_notebook(cells)
os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
    json.dump(notebook, f, indent=1)
    f.write("\n")

print(f"Wrote {OUTPUT_PATH}")
