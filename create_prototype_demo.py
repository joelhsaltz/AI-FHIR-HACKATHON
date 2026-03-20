#!/usr/bin/env python3
"""
Generate the demo prototype notebook: "You Are the Agent" with FHIR grounding.

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
    lines = source if isinstance(source, list) else [source]
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
    f"| AI Coach | {'Ready' if _anthropic_client else 'Not configured'} "
    f"| {'Claude — for coaching suggestions' if _anthropic_client else 'Add ANTHROPIC_API_KEY in Secrets (see above)'} |\n"
))
""".strip()


TOOLS = r"""
#@title Step 2: Load clinical query tools

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

def _search_all_conditions(patient_id, max_results=20):
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

# === State ===
_state = {
    "question": "Is this patient more consistent with Type 1 diabetes, Type 2 diabetes, or still unclear?",
    "patient_id": None, "patient_label": None,
    "history": [], "evidence": {}, "final_answer": None,
}

def _evidence_gaps():
    ev = _state["evidence"]
    gaps = []
    if "demographics" not in ev:
        gaps.append(("Basic demographics", "Patient"))
    if "conditions" not in ev:
        gaps.append(("Problem list / diagnosis context", "Condition"))
    if "c_peptide" not in ev:
        gaps.append(("C-peptide level (LOINC 1986-9)", "Observation"))
    if "medications" not in ev:
        gaps.append(("Medication pattern", "MedicationRequest"))
    if "bmi" not in ev:
        gaps.append(("BMI / insulin-resistance (LOINC 39156-5)", "Observation"))
    return gaps

def _render_dashboard():
    lines = ["---", "## Your Agent Dashboard", ""]
    lines.append(f"**Clinical Question:** {_state['question']}")
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
            elif key == "medications":
                meds = [r["medication"] for r in value[:5]]
                lines.append(f"| Medications | `MedicationRequest` | {', '.join(meds) if meds else 'None found'} |")
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
        lines.append("*All key evidence categories covered. You may be ready to answer.*")
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

# === Claude tool schemas (for the AI agent comparison) ===
CLAUDE_TOOLS = [
    {
        "name": "get_patient",
        "description": "FHIR query: GET /Patient/{id}. Returns demographics for one patient.",
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
            "Useful LOINC codes: 4548-4 HbA1c, 1986-9 C-peptide, 39156-5 BMI, "
            "2160-0 creatinine, 33914-3 eGFR."
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
        "description": "FHIR query: GET /MedicationRequest?subject=Patient/{id}.",
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
        "description": "FHIR query: GET /Condition?subject=Patient/{id}. Returns full problem list.",
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
        "description": "FHIR query: GET /Encounter?subject=Patient/{id}.",
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

display(Markdown("**Clinical query tools loaded.** Proceed to the next step."))
""".strip()


BUILD_CANDIDATES = r"""
#@title Step 3: Build candidate pool from FHIR
import random as _random

_final_candidates = []

display(Markdown("*Querying FHIR server for working-age adults with diabetes...*"))

_candidate_rows = []
_seen_patients = set()
_query_log = []
_TARGET = 20
for _label, _code in [("Likely T1D cohort", SNOMED["t1d"]), ("Likely T2D cohort", SNOMED["t2d"])]:
    _furl, _cond_result = _search_conditions(_code, max_results=50)
    _query_log.append(_furl)
    for _item in _cond_result["results"]:
        if len(_candidate_rows) >= _TARGET:
            break
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
            "Seed Group": _label,
            "_patient_id": _pid,
        })
        _seen_patients.add(_pid)

# Shuffle to avoid demographic clustering from sequential FHIR results
_random.shuffle(_candidate_rows)

# Select up to 10 candidates, aiming for a mix of T1D and T2D
_group_counts = {"Likely T1D cohort": 0, "Likely T2D cohort": 0}
# First pass: take up to 5 from each group
for _row in _candidate_rows:
    _g = _row["Seed Group"]
    if _group_counts[_g] >= 5:
        continue
    _group_counts[_g] += 1
    _row["Case #"] = len(_final_candidates) + 1
    _final_candidates.append(_row)
    if len(_final_candidates) >= 10:
        break
# Second pass: fill remaining slots from whichever group has more
if len(_final_candidates) < 10:
    for _row in _candidate_rows:
        if _row in _final_candidates:
            continue
        _row["Case #"] = len(_final_candidates) + 1
        _final_candidates.append(_row)
        if len(_final_candidates) >= 10:
            break

for _q in _query_log:
    _show_query(_q, "Condition")

display(Markdown(
    "## Your Patient Candidates\n\n"
    "These working-age adults were found by querying `Condition` resources for diabetes "
    "SNOMED codes (**46635009** = Type 1, **44054006** = Type 2), then retrieving "
    "`Patient` demographics and filtering to age ≤ 50.\n\n"
    "The **Seed Group** shows which diagnosis code matched — but that label might "
    "not be the whole story. Your job is to gather evidence and decide for yourself.\n\n"
    "*The cohort of 1,027 synthetic patients was purpose-built with 6 canonical "
    "phenotypes spanning the diabetes–CKD spectrum (see the data overview above).*"
))
_cdf = pd.DataFrame(_final_candidates)[["Case #", "Name", "Age", "Gender", "Seed Group"]]
display(HTML(_cdf.to_html(index=False)))
display(Markdown(f"**{len(_final_candidates)} candidates loaded.** Proceed to Step 4 to select a case."))
""".strip()


SELECT_CASE = r"""
#@title Step 4: Select a case to investigate
case_number = 1 #@param {type:"integer"}

if "_final_candidates" not in dir() or not _final_candidates:
    display(Markdown(
        "**Run Step 3 first.** The candidate pool hasn't been built yet.\n\n"
        "Click the **Run** button (▶) on **Step 3** above and wait for it to finish — "
        "you'll see a table of patients and a message saying candidates are loaded."
    ))
elif case_number < 1 or case_number > len(_final_candidates):
    display(Markdown(f"**Invalid case number.** Choose between 1 and {len(_final_candidates)}."))
else:
    _sel = _final_candidates[case_number - 1]
    _state["patient_id"] = _sel["_patient_id"]
    _state["patient_label"] = f"{_sel['Name']} (Age {_sel['Age']}, {_sel['Gender']})"
    _state["history"] = []
    _state["evidence"] = {}
    _state["final_answer"] = None

    display(Markdown(
        f"## Case {case_number} Selected\n\n"
        f"**Patient:** {_state['patient_label']} · ID: `{_state['patient_id']}`\n\n"
        f"**Clinical question:** {_state['question']}\n\n"
        "Use **Step 5** below to start querying the FHIR server. "
        "Change the dropdown, click Run, and review what comes back."
    ))
""".strip()


GATHER_EVIDENCE = r"""
#@title Step 5: Gather evidence (change dropdown → click Run → repeat)
action = "Get demographics" #@param ["Get demographics", "Get full problem list", "Get labs", "Get medications", "Get encounters"]

if _state["patient_id"] is None:
    display(Markdown("**Select a case first** (Step 4 above)."))
else:
    _pid = _state["patient_id"]

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

    elif action == "Get full problem list":
        _furl, _result = _search_all_conditions(_pid)
        _show_query(_furl, "Condition")
        _state["evidence"]["conditions"] = _result["results"]
        _state["history"].append({"step": len(_state["history"]) + 1, "fhir_query": _furl, "note": f"{len(_result['results'])} conditions found"})
        if _result["results"]:
            _rows_md = "\n".join(f"| {r['condition']} | {r['code']} | {r['clinical_status']} |" for r in _result["results"][:12])
            display(Markdown(f"### Problem List\n\n| Condition | SNOMED Code | Status |\n|-----------|-------------|--------|\n{_rows_md}"))
        else:
            display(Markdown("### Problem List\n\n*No conditions found for this patient.*"))

    elif action == "Get labs":
        _lab_rows = []
        _lab_queries = []
        for _lab_name, (_loinc_code, _lab_desc) in LAB_LOOKUP.items():
            _furl, _result = _search_observations(_pid, _loinc_code)
            _lab_queries.append(_furl)
            _ev_key = _lab_name.lower().replace("-", "_").replace(" ", "_")
            _latest = _result["results"][0] if _result["results"] else None
            _state["evidence"][_ev_key] = {"bundle": _result, "latest": _latest}
            if _latest:
                _lab_rows.append({
                    "Lab": _lab_name,
                    "LOINC": _loinc_code,
                    "Value": _latest.get("value", "N/A"),
                    "Unit": _latest.get("unit", ""),
                    "Date": _latest.get("date", "N/A"),
                    "Description": _lab_desc.split(" — ")[1] if " — " in _lab_desc else _lab_desc,
                })
            else:
                _lab_rows.append({
                    "Lab": _lab_name,
                    "LOINC": _loinc_code,
                    "Value": "—",
                    "Unit": "",
                    "Date": "—",
                    "Description": "No results found",
                })
        for _furl in _lab_queries:
            _show_query(_furl, "Observation")
        _found = [r for r in _lab_rows if r["Value"] != "—"]
        _note = ", ".join(f"{r['Lab']}: {r['Value']} {r['Unit']}" for r in _found[:3])
        if len(_found) > 3:
            _note += f" (+{len(_found)-3} more)"
        _state["history"].append({"step": len(_state["history"]) + 1, "fhir_query": f"{len(_lab_queries)} Observation queries", "note": _note or "No lab results"})
        _rows_md = "\n".join(f"| {r['Lab']} | {r['LOINC']} | {r['Value']} | {r['Unit']} | {r['Date']} | {r['Description']} |" for r in _lab_rows)
        display(Markdown(f"### Lab Results (All Available)\n\n| Lab | LOINC | Value | Unit | Date | Description |\n|-----|-------|-------|------|------|-------------|\n{_rows_md}"))

    elif action == "Get medications":
        _furl, _result = _search_medications(_pid)
        _show_query(_furl, "MedicationRequest")
        _state["evidence"]["medications"] = _result["results"]
        _state["history"].append({"step": len(_state["history"]) + 1, "fhir_query": _furl, "note": f"{len(_result['results'])} medications"})
        if _result["results"]:
            _rows_md = "\n".join(f"| {r['medication']} | {r['status']} | {r.get('authoredOn', 'N/A')} |" for r in _result["results"][:10])
            display(Markdown(f"### Medications\n\n| Medication | Status | Date |\n|------------|--------|------|\n{_rows_md}"))
        else:
            display(Markdown("### Medications\n\n*No medications found.*"))

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


LLM_COACH = r"""
#@title Step 6: Ask the AI Coach for a suggestion

if _state["patient_id"] is None:
    display(Markdown("**Select a case first** (Step 4 above)."))
elif _anthropic_client is None:
    display(Markdown(
        "**AI Coach requires an API key.** If you haven't set one up yet, see the "
        "\"Set Up Your API Key\" section above. You can continue to the next step "
        "and come back to this one after configuring your key."
    ))
else:
    display(Markdown("*Asking the AI coach...*"))
    _coach_state = {
        "question": _state["question"],
        "patient_id": _state["patient_id"],
        "evidence_collected": list(_state["evidence"].keys()),
        "missing_evidence": [g[0] for g in _evidence_gaps()],
        "steps_taken": len(_state["history"]),
    }
    _coach_resp = _anthropic_client.messages.create(
        model=MODEL, max_tokens=300,
        messages=[{
            "role": "user",
            "content": (
                "You are coaching a clinical informatics student who is acting as "
                "an agent reviewing a diabetes case using FHIR queries. "
                "Given the current state, recommend exactly one next FHIR query "
                "from: Get demographics (Patient), Get full problem list (Condition), "
                "Get labs [specify which] (Observation), Get medications (MedicationRequest), "
                "Get encounters (Encounter), or Finish and answer. "
                "Name the FHIR resource and explain why in 2-3 sentences.\n\n"
                + json.dumps(_coach_state, indent=2)
            ),
        }],
    )
    _suggestion = "".join(b.text for b in _coach_resp.content if hasattr(b, "text"))
    display(Markdown(f"## AI Coach Suggestion\n\n{_suggestion}"))
""".strip()


RECORD_ANSWER = r"""
#@title Step 7: Record your answer
classification = "Likely Type 1" #@param ["Likely Type 1", "Likely Type 2", "Unclear / needs more review"]
rationale = "" #@param {type:"string"}

if _state["patient_id"] is None:
    display(Markdown("**Select a case first** (Step 4)."))
elif not rationale.strip():
    display(Markdown(
        "**Please enter a rationale** in the text field above. "
        "Cite specific FHIR findings (e.g., 'C-peptide was 0.3 ng/mL from Observation')."
    ))
else:
    _state["final_answer"] = {"classification": classification, "rationale": rationale.strip()}
    _state["history"].append({
        "step": len(_state["history"]) + 1,
        "fhir_query": "—",
        "note": f"Final answer: {classification}",
    })
    display(Markdown(
        f"## Your Answer Recorded\n\n"
        f"**Patient:** {_state['patient_label']}\n\n"
        f"**Classification:** {classification}\n\n"
        f"**Rationale:** {rationale}\n\n"
        f"**FHIR queries used:** {len(_state['history']) - 1}\n\n"
        "---\n\n"
        "*Scroll down to watch the AI agent work the same case.*"
    ))
""".strip()


LLM_AGENT = r"""
#@title Step 8: Watch the AI agent work the same case

def _tool_to_human_label(fn_name, fn_args):
    # Map tool names to plain-English action descriptions.
    labels = {
        "get_patient": "Get demographics",
        "search_all_conditions": "Get problem list",
        "search_medications": "Get medications",
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

def _summarize_result(fn_name, fn_args, result):
    # Create a brief human-readable summary of what came back.
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

if _state["patient_id"] is None:
    display(Markdown("**Select a case first** (Step 4)."))
elif _anthropic_client is None:
    display(Markdown(
        "**AI Agent requires an API key.** If you haven't set one up yet, see the "
        "\"Set Up Your API Key\" section above."
    ))
else:
    _agent_pid = _state["patient_id"]
    _agent_question = (
        f"Review patient {_agent_pid} ({_state['patient_label']}). "
        "Decide whether the case is more consistent with Type 1 diabetes, "
        "Type 2 diabetes, or still unclear. Use the available FHIR query tools "
        "to gather evidence. Cite specific findings in your final answer."
    )
    _agent_system = (
        "You are a clinical data assistant querying a FHIR server with synthetic "
        "patient data. Prefer direct evidence over heuristics. Use C-peptide when "
        "available. If evidence is conflicting, say unclear. Be concise."
    )

    display(Markdown("## AI Agent Run\n\n*The AI agent is querying the same patient using the same FHIR tools...*\n"))

    _agent_messages = [{"role": "user", "content": _agent_question}]
    _agent_tool_log = []
    _final_text = "(Agent reached maximum steps)"

    for _step in range(1, 9):
        _resp = _anthropic_client.messages.create(
            model=MODEL, max_tokens=4096, system=_agent_system,
            messages=_agent_messages, tools=CLAUDE_TOOLS,
        )
        _tblocks = [b for b in _resp.content if b.type == "tool_use"]

        if not _tblocks:
            _final_text = "".join(b.text for b in _resp.content if hasattr(b, "text"))
            break

        _acontent = []
        for _b in _resp.content:
            if _b.type == "text":
                _acontent.append({"type": "text", "text": _b.text})
            elif _b.type == "tool_use":
                _acontent.append({"type": "tool_use", "id": _b.id, "name": _b.name, "input": _b.input})
        _agent_messages.append({"role": "assistant", "content": _acontent})

        _tool_results = []
        for _tb in _tblocks:
            _human_label = _tool_to_human_label(_tb.name, _tb.input)
            _fhir_display = _tool_to_fhir_display(_tb.name, _tb.input)
            _tr = _tool_runner(_tb.name, _tb.input)
            _result_summary = _summarize_result(_tb.name, _tb.input, _tr)
            _agent_tool_log.append({
                "Step": _step,
                "Action": _human_label,
                "FHIR Query": _fhir_display,
                "Result": _result_summary,
            })
            display(Markdown(
                f"**Step {_step}: {_human_label}** — "
                f"retrieving {_human_label.lower().replace('get ', '')}\n"
                f"  \nFHIR: `{_fhir_display}` → {_result_summary}"
            ))
            _tool_results.append({
                "type": "tool_result", "tool_use_id": _tb.id,
                "content": json.dumps(_tr, default=str),
            })
        _agent_messages.append({"role": "user", "content": _tool_results})

    display(Markdown("---"))
    display(Markdown(f"### AI Agent's Answer\n\n{_final_text}"))
    if _agent_tool_log:
        display(Markdown("### AI Agent's FHIR Query Log"))
        display(HTML(pd.DataFrame(_agent_tool_log).to_html(index=False)))
""".strip()


DEBRIEF = r"""
#@title Step 9: Compare and reflect

display(Markdown("## Comparison & Reflection"))

if _state["final_answer"]:
    display(Markdown(
        f"### Your Answer\n\n"
        f"**Classification:** {_state['final_answer']['classification']}\n\n"
        f"**Rationale:** {_state['final_answer']['rationale']}\n\n"
        f"**FHIR queries used:** {len(_state['history']) - 1}"
    ))

display(Markdown(
    "### Discussion Questions\n\n"
    "1. **Query strategy:** Did you and the AI query the same FHIR resources? "
    "In what order? Which query was most informative?\n"
    "2. **Stopping point:** Did you query more or fewer resources? "
    "Could either of you have stopped earlier?\n"
    "3. **FHIR resource value:** Which resource type (`Patient`, `Condition`, "
    "`Observation`, `MedicationRequest`, `Encounter`) mattered most for this "
    "question? Would that change for a different clinical question?\n"
    "4. **Uncertainty:** Did either you or the AI express appropriate uncertainty? "
    "What FHIR data (if it existed) would resolve the ambiguity?\n"
    "5. **The agent loop:** Describe it: *observe evidence → choose FHIR query → "
    "execute → update assessment → repeat or answer.* What makes this hard?"
))

if _state["history"]:
    display(Markdown("### Your Query Log"))
    display(HTML(pd.DataFrame(_state["history"]).to_html(index=False)))
""".strip()


# ===================================================================
# Assemble notebook
# ===================================================================

cells = [
    md_cell([
        "# You Are the Agent\n",
        "\n",
        "## A Clinical Decision-Making Exercise Using FHIR\n",
        "\n",
        "In this exercise, **you play the role of a clinical AI agent.** You have a clinical ",
        "question to answer about a patient. Your tools are **FHIR queries** — structured ",
        "requests to an electronic health record server.\n",
        "\n",
        "An AI agent works in a loop:\n",
        "\n",
        "1. **Observe** — what evidence do I have so far?\n",
        "2. **Decide** — what FHIR query would be most informative next?\n",
        "3. **Act** — execute the query\n",
        "4. **Update** — add the new evidence to my assessment\n",
        "5. **Repeat** or **answer** when confident\n",
        "\n",
        "This is exactly how real LLM-based agents work in production — from clinical decision ",
        "support to automated chart review. By doing it manually first, you develop intuition ",
        "for what makes an agent good or bad at clinical reasoning: which queries matter, when ",
        "to stop, and how to weigh conflicting evidence. After your manual run, you'll watch an ",
        "AI agent tackle the same case and compare strategies.\n",
        "\n",
        "> **No coding required.** Every step uses dropdown menus and Run buttons. ",
        "After each query, you'll see the FHIR request that was made and the results.\n",
    ]),

    md_cell([
        "## What You'll Practice\n",
        "\n",
        "- Describe the **agent loop** (observe → decide → act → update → repeat)\n",
        "- Choose which **FHIR resource** to query based on missing evidence\n",
        "- Understand how clinical questions map to **structured FHIR queries**\n",
        "- Decide when evidence is **sufficient** to answer\n",
        "- Compare your query strategy with an AI agent's approach\n",
    ]),

    md_cell([
        "## The Clinical Scenario\n",
        "\n",
        "**Setting:** You are an informatics fellow reviewing a cohort of working-age adults ",
        "(age ≤ 50) with a diabetes diagnosis in a synthetic FHIR server.\n",
        "\n",
        "**Problem:** Some patients may have been labeled with the wrong diabetes type. ",
        "Type 1 and Type 2 diabetes require different management, so accurate classification matters.\n",
        "\n",
        "**Your task:** Query the FHIR server and decide:\n",
        "- **Likely Type 1** — evidence supports autoimmune diabetes\n",
        "- **Likely Type 2** — evidence supports insulin resistance pattern\n",
        "- **Unclear** — evidence is insufficient or conflicting\n",
        "\n",
        "**Key evidence to look for:**\n",
        "- C-peptide level (low → T1, normal/high → T2) — `Observation` with LOINC `1986-9`\n",
        "- Medication pattern (insulin-only vs. oral agents) — `MedicationRequest`\n",
        "- BMI (lower → T1, higher → T2, not definitive) — `Observation` with LOINC `39156-5`\n",
        "- Diagnosis context — `Condition` resource\n",
    ]),

    md_cell([
        "## About the Data: A Purpose-Built Synthetic Cohort\n",
        "\n",
        "The patient data in this exercise was created by **Joel Saltz** specifically for this ",
        "course. It is a cohort of **1,027 synthetic patients** spanning six canonical phenotypes ",
        "along the diabetes–CKD spectrum:\n",
        "\n",
        "| # | Phenotype | Key Features |\n",
        "|---|-----------|-------------|\n",
        "| 1 | Metabolic syndrome | No diabetes, no CKD |\n",
        "| 2 | Early Type 2 diabetes | No CKD |\n",
        "| 3 | Type 2 diabetes with obesity | Early CKD |\n",
        "| 4 | Advanced Type 2 diabetes | Moderate CKD |\n",
        "| 5 | Type 1 diabetes | Early nephropathy |\n",
        "| 6 | Type 1 diabetes, poor control | With CKD |\n",
        "\n",
        "Variables are **clinically coupled** — for example, C-peptide tracks diabetes type and ",
        "duration, HbA1c correlates with glucose via the ADAG equation, and renal chemistry is ",
        "internally consistent. Each phenotype has an age anchor and demographic variability, so ",
        "patients within a phenotype are similar but not identical.\n",
        "\n",
        "The data is loaded into a **FHIR R4 server**, so you query it the same way you would ",
        "query real clinical data. Synthetic data generation is a topic you may explore in a ",
        "future session.\n",
    ]),

    md_cell([
        "## Your Toolkit: FHIR Queries as Agent Tools\n",
        "\n",
        "Each tool is a **FHIR query** — a structured request to a specific resource endpoint.\n",
        "\n",
        "| Tool | FHIR Query | Returns | When to Use |\n",
        "|------|------------|---------|-------------|\n",
        "| Get demographics | `GET /Patient/{id}` | Name, age, gender, DOB | Basic patient context |\n",
        "| Get problem list | `GET /Condition?subject=Patient/{id}` | Diagnoses + clinical status | Full diagnostic picture |\n",
        "| Get labs | `GET /Observation?subject=Patient/{id}&code={LOINC}` | Lab values sorted by date | C-peptide, HbA1c, BMI |\n",
        "| Get medications | `GET /MedicationRequest?subject=Patient/{id}` | Med names, status, dates | Insulin-only vs oral agents |\n",
        "| Get encounters | `GET /Encounter?subject=Patient/{id}` | Visit type, class, dates | Care context |\n",
        "\n",
        "**Coding systems:** SNOMED CT for diagnoses (46635009 = T1DM, 44054006 = T2DM) · ",
        "LOINC for labs (4548-4 = HbA1c, 1986-9 = C-peptide, 39156-5 = BMI)\n",
        "\n",
        "> The AI agent has **exactly these same tools**. The difference isn't the tools — ",
        "it's the *strategy* for choosing which to use and when to stop.\n",
    ]),

    md_cell([
        "## Before You Start: Set Up Your API Key\n",
        "\n",
        "Steps 6 (AI Coach) and 8 (AI Agent comparison) use **Claude**, an AI model, which ",
        "requires an API key. Steps 1–7 (where *you* are the agent) work without one, but ",
        "you'll need the key to see the AI in action.\n",
        "\n",
        "**How to add your API key in Colab:**\n",
        "\n",
        "1. Look at the **left sidebar** — below the file browser and variable icons, you'll ",
        "see a **key icon** (🔑). Click it to open the **Secrets** panel.\n",
        "2. Click **\"Add a secret\"**\n",
        "3. Set the name to exactly: `ANTHROPIC_API_KEY`\n",
        "4. Paste your API key as the value\n",
        "5. Toggle **\"Notebook access\"** to **ON**\n",
        "\n",
        "> **Gotcha:** You cannot edit a secret after saving it. If you need to change the key, ",
        "**delete** the secret and create a new one with the same name.\n",
        "\n",
        "If you don't have an API key, you can still complete Steps 1–7 as the human agent. ",
        "Ask your instructor if you need a key.\n",
    ]),

    form_cell(SETUP),
    form_cell(TOOLS),
    form_cell(BUILD_CANDIDATES),

    md_cell([
        "## Time to Be the Agent\n",
        "\n",
        "1. **Select a case** — pick a patient number below\n",
        "2. **Gather evidence** — choose a FHIR query from the dropdown, click Run, review the results\n",
        "3. **Watch your dashboard** — it tracks evidence collected, gaps, and your query log\n",
        "4. **Ask the AI coach** — it suggests one next FHIR query\n",
        "5. **Record your answer** — classify the patient, citing specific FHIR findings\n",
        "6. **Compare with the AI agent** — watch it query the same patient\n",
        "\n",
        "> **Think before you query.** An agent that runs every available tool wastes time. ",
        "Pick the query most likely to change your assessment.\n",
    ]),

    form_cell(SELECT_CASE),

    md_cell([
        "## Gather Evidence\n",
        "\n",
        "Each time you run the cell below, you execute **one FHIR query** — one agent turn. ",
        "Change the dropdown to select which query to run, then click Run.\n",
        "\n",
        "After each query you'll see:\n",
        "- The **FHIR request** that was made\n",
        "- The **results** as a table\n",
        "- Your **Agent Dashboard** showing collected evidence, gaps, and query log\n",
        "\n",
        "> **Run this cell as many times as you want.** Each run is one turn.\n",
    ]),

    form_cell(GATHER_EVIDENCE),

    md_cell([
        "## Ask the AI Coach\n",
        "\n",
        "The AI coach sees the same evidence state you see and suggests one next FHIR query. ",
        "You're still in control of what to actually run.\n",
    ]),

    form_cell(LLM_COACH),

    md_cell([
        "## Record Your Answer\n",
        "\n",
        "When you've gathered enough evidence, record your classification below. ",
        "**Cite specific FHIR findings** — e.g., \"C-peptide was 0.3 ng/mL (Observation), ",
        "patient is on insulin only (MedicationRequest).\"\n",
    ]),

    form_cell(RECORD_ANSWER),

    md_cell([
        "## Watch the AI Agent\n",
        "\n",
        "The AI agent receives the same clinical question and the same FHIR tools. ",
        "Watch which queries it chooses, in what order, and how its reasoning compares to yours.\n",
    ]),

    form_cell(LLM_AGENT),

    form_cell(DEBRIEF),

    md_cell([
        "## Wrap-Up\n",
        "\n",
        "You've experienced the core **agent loop** from the inside:\n",
        "\n",
        "```\n",
        "while not confident_enough:\n",
        "    observe current evidence\n",
        "    choose next FHIR query (GET /Resource?parameters...)\n",
        "    execute the query\n",
        "    update assessment\n",
        "```\n",
        "\n",
        "This is exactly what an AI agent does — the only difference is who chooses the next query.\n",
        "\n",
        "**To investigate another patient:** Go back to Step 4, change the case number, ",
        "and run through the exercise again.\n",
    ]),
]

notebook = build_notebook(cells)
os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
    json.dump(notebook, f, indent=1)
    f.write("\n")

print(f"Wrote {OUTPUT_PATH}")
