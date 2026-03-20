#!/usr/bin/env python3
"""
Generate the redesigned prototype notebook with Colab form cells.

All code cells use cellView: "form" metadata so students never see Python code.
Interaction is via Colab form dropdowns (#@param annotations).
Output uses display(Markdown(...)) for rich rendering.
"""

import json
import os
import uuid


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_PATH = os.path.join(
    SCRIPT_DIR,
    "prototypes",
    "you_are_the_agent_v2.ipynb",
)


def _id():
    return uuid.uuid4().hex[:8]


def md_cell(source):
    return {
        "cell_type": "markdown",
        "id": _id(),
        "metadata": {},
        "source": source if isinstance(source, list) else [source],
    }


def form_cell(source, *, title=None):
    """Code cell with cellView: 'form' metadata. Code is hidden in Colab."""
    lines = source if isinstance(source, list) else [source]
    return {
        "cell_type": "code",
        "id": _id(),
        "metadata": {"cellView": "form"},
        "source": lines,
        "execution_count": None,
        "outputs": [],
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
            "colab": {
                "provenance": [],
                "collapsed_sections": [],
            },
        },
        "cells": cells,
    }


# ---------------------------------------------------------------------------
# String constants for each cell
# ---------------------------------------------------------------------------

SETUP_SILENT = """\
#@title Step 1: Install packages and connect to servers (click Run, then wait)
import subprocess, sys
subprocess.check_call([sys.executable, "-m", "pip", "install", "-q",
                       "anthropic", "requests", "pandas"],
                      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

import os
import json
from datetime import date, datetime

import pandas as pd
import requests
import urllib3
from IPython.display import Markdown, display, HTML

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- FHIR connection ---
FHIR_BASE = "https://lfh-fhir.eastus2.cloudapp.azure.com:9443/fhir-server/api/v4"
FHIR_SESSION = requests.Session()
FHIR_SESSION.auth = ("fhiruser", "BmI512@ccess")
FHIR_SESSION.verify = False

# --- Anthropic client ---
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
display(Markdown("**Setup complete.** Proceed to Step 2."))
"""


VERIFY_CONNECTION = """\
#@title Step 2: Verify connection
resp = FHIR_SESSION.get(f"{FHIR_BASE}/metadata", params={"_format": "json"}, timeout=20)
if resp.status_code != 200:
    display(Markdown("**Connection failed.** Check the server URL and credentials."))
    raise RuntimeError(f"FHIR server connection failed: HTTP {resp.status_code}")

count_resp = FHIR_SESSION.get(
    f"{FHIR_BASE}/Patient",
    params={"_summary": "count", "_format": "json"},
    timeout=20,
)
patient_count = count_resp.json().get("total", "unknown")

status_lines = [
    "## Connection Status",
    "",
    f"| Component | Status |",
    f"|-----------|--------|",
    f"| FHIR Server | Connected |",
    f"| Patient records | {patient_count} |",
    f"| AI Coach | {'Ready' if _anthropic_client else 'Not configured (optional)'} |",
]
display(Markdown("\\n".join(status_lines)))
"""


# All FHIR query functions + state helpers — hidden behind a form cell
TOOLS_AND_HELPERS = """\
#@title Step 3: Load clinical tools (click Run)

# === Clinical coding systems ===
SNOMED = {"t1d": "46635009", "t2d": "44054006", "ckd": "709044004"}
LOINC = {
    "hba1c": "4548-4", "c_peptide": "1986-9", "bmi": "39156-5",
    "creatinine": "2160-0", "egfr": "33914-3", "uacr": "14959-1",
}
LAB_LOOKUP = {
    "HbA1c": LOINC["hba1c"],
    "C-peptide": LOINC["c_peptide"],
    "BMI": LOINC["bmi"],
    "Creatinine": LOINC["creatinine"],
    "eGFR": LOINC["egfr"],
}

# === FHIR query functions ===
def _compute_age(birth_date):
    if not birth_date:
        return None
    born = datetime.strptime(birth_date, "%Y-%m-%d").date()
    today = date.today()
    return today.year - born.year - ((today.month, today.day) < (born.month, born.day))

def _get_patient(patient_id):
    resp = FHIR_SESSION.get(f"{FHIR_BASE}/Patient/{patient_id}", params={"_format": "json"}, timeout=30)
    patient = resp.json()
    name = patient.get("name", [{}])[0]
    return {
        "id": patient.get("id"),
        "name": f"{' '.join(name.get('given', []))} {name.get('family', '')}".strip(),
        "gender": patient.get("gender", ""),
        "birthDate": patient.get("birthDate", ""),
        "age": _compute_age(patient.get("birthDate", "")),
    }

def _search_conditions(code, max_results=50):
    resp = FHIR_SESSION.get(
        f"{FHIR_BASE}/Condition",
        params={"code": code, "_count": max_results, "_format": "json"},
        timeout=30,
    )
    bundle = resp.json()
    rows = []
    for entry in bundle.get("entry", []):
        resource = entry["resource"]
        coding = resource.get("code", {}).get("coding", [{}])[0]
        rows.append({
            "condition_id": resource.get("id"),
            "code": coding.get("code", ""),
            "display": coding.get("display", ""),
            "patient_reference": resource.get("subject", {}).get("reference", ""),
            "clinical_status": resource.get("clinicalStatus", {}).get("coding", [{}])[0].get("code", ""),
        })
    return {"total": bundle.get("total", 0), "results": rows}

def _search_observations(patient_id, loinc_code, max_results=5):
    resp = FHIR_SESSION.get(
        f"{FHIR_BASE}/Observation",
        params={
            "subject": f"Patient/{patient_id}", "code": loinc_code,
            "_count": max_results, "_sort": "-date", "_format": "json",
        },
        timeout=30,
    )
    bundle = resp.json()
    rows = []
    for entry in bundle.get("entry", []):
        resource = entry["resource"]
        coding = resource.get("code", {}).get("coding", [{}])[0]
        value_qty = resource.get("valueQuantity", {})
        rows.append({
            "display": coding.get("display", ""),
            "value": value_qty.get("value"),
            "unit": value_qty.get("unit", ""),
            "date": resource.get("effectiveDateTime", ""),
        })
    return {"total": bundle.get("total", 0), "results": rows}

def _search_medications(patient_id, max_results=10):
    resp = FHIR_SESSION.get(
        f"{FHIR_BASE}/MedicationRequest",
        params={"subject": f"Patient/{patient_id}", "_count": max_results, "_format": "json"},
        timeout=30,
    )
    bundle = resp.json()
    rows = []
    for entry in bundle.get("entry", []):
        resource = entry["resource"]
        med_concept = resource.get("medicationCodeableConcept", {})
        coding = med_concept.get("coding", [{}])[0] if med_concept.get("coding") else {}
        rows.append({
            "medication": coding.get("display") or med_concept.get("text", "unknown"),
            "status": resource.get("status", ""),
            "authoredOn": resource.get("authoredOn", ""),
        })
    return {"total": bundle.get("total", 0), "results": rows}

def _search_all_conditions(patient_id, max_results=20):
    resp = FHIR_SESSION.get(
        f"{FHIR_BASE}/Condition",
        params={"subject": f"Patient/{patient_id}", "_count": max_results, "_format": "json"},
        timeout=30,
    )
    bundle = resp.json()
    rows = []
    for entry in bundle.get("entry", []):
        resource = entry["resource"]
        coding = resource.get("code", {}).get("coding", [{}])[0]
        rows.append({
            "condition": coding.get("display", ""),
            "code": coding.get("code", ""),
            "clinical_status": resource.get("clinicalStatus", {}).get("coding", [{}])[0].get("code", ""),
        })
    return {"total": bundle.get("total", 0), "results": rows}

def _search_encounters(patient_id, max_results=10):
    resp = FHIR_SESSION.get(
        f"{FHIR_BASE}/Encounter",
        params={
            "subject": f"Patient/{patient_id}", "_count": max_results,
            "_sort": "-date", "_format": "json",
        },
        timeout=30,
    )
    bundle = resp.json()
    rows = []
    for entry in bundle.get("entry", []):
        resource = entry["resource"]
        enc_type = resource.get("type", [{}])[0].get("text", "") if resource.get("type") else ""
        rows.append({
            "status": resource.get("status", ""),
            "class": resource.get("class", {}).get("code", ""),
            "type": enc_type,
            "period_start": resource.get("period", {}).get("start", ""),
        })
    return {"total": bundle.get("total", 0), "results": rows}

# === State management ===
_state = {
    "question": "Is this patient more consistent with Type 1 diabetes, Type 2 diabetes, or still unclear?",
    "patient_id": None,
    "patient_label": None,
    "history": [],
    "evidence": {},
    "final_answer": None,
}

def _evidence_gaps():
    ev = _state["evidence"]
    gaps = []
    if "demographics" not in ev:
        gaps.append("Basic demographics")
    if "conditions" not in ev:
        gaps.append("Problem list / diagnosis context")
    if "c_peptide" not in ev:
        gaps.append("C-peptide level")
    if "medications" not in ev:
        gaps.append("Medication pattern")
    if "bmi" not in ev:
        gaps.append("BMI / insulin-resistance pattern")
    return gaps

def _render_state():
    lines = []
    lines.append("---")
    lines.append("## Your Agent Dashboard")
    lines.append("")
    lines.append(f"**Clinical Question:** {_state['question']}")
    if _state["patient_label"]:
        lines.append(f"**Patient:** {_state['patient_label']} (ID: {_state['patient_id']})")
    lines.append("")

    # Evidence collected
    lines.append("### Evidence Collected")
    ev = _state["evidence"]
    if not ev:
        lines.append("*No evidence gathered yet. Use the menu below to start.*")
    else:
        lines.append("")
        lines.append("| Category | Finding |")
        lines.append("|----------|---------|")
        for key, value in ev.items():
            if key == "demographics":
                lines.append(f"| Demographics | Age {value.get('age')}, {value.get('gender')}, DOB {value.get('birthDate')} |")
            elif key == "conditions":
                names = [row["condition"] for row in value[:5]]
                lines.append(f"| Problem List | {', '.join(names) if names else 'None found'} |")
            elif key == "medications":
                meds = [row["medication"] for row in value[:5]]
                lines.append(f"| Medications | {', '.join(meds) if meds else 'None found'} |")
            elif key == "encounters":
                if value:
                    enc = value[0]
                    lines.append(f"| Encounters | Most recent: {enc.get('type', 'Unknown')} ({enc.get('period_start', 'N/A')}) |")
                else:
                    lines.append("| Encounters | None found |")
            else:
                # Lab results
                if isinstance(value, dict) and "latest" in value:
                    latest = value["latest"]
                    if latest:
                        lines.append(f"| {key.replace('_', ' ').title()} | {latest.get('value')} {latest.get('unit', '')} (date: {latest.get('date', 'N/A')}) |")
                    else:
                        lines.append(f"| {key.replace('_', ' ').title()} | No results found |")
        lines.append("")

    # Missing evidence
    gaps = _evidence_gaps()
    lines.append("### Still Needed")
    if gaps:
        for gap in gaps:
            lines.append(f"- {gap}")
    else:
        lines.append("*All key evidence categories covered. You may be ready to answer.*")
    lines.append("")

    # Step history
    lines.append("### Steps Taken")
    if not _state["history"]:
        lines.append("*No steps yet.*")
    else:
        lines.append("")
        lines.append("| # | Action | Note |")
        lines.append("|---|--------|------|")
        for item in _state["history"][-8:]:
            lines.append(f"| {item['step']} | {item['tool']} | {item['note']} |")
    lines.append("")
    lines.append("---")
    return "\\n".join(lines)

# === Claude tool schemas (for LLM agent mode) ===
CLAUDE_TOOLS = [
    {
        "name": "get_patient",
        "description": "Get demographics for a single patient by patient ID.",
        "input_schema": {
            "type": "object",
            "properties": {"patient_id": {"type": "string"}},
            "required": ["patient_id"],
        },
    },
    {
        "name": "search_observations",
        "description": (
            "Search observations for a patient by LOINC code. "
            "Useful codes: 4548-4 HbA1c, 1986-9 C-peptide, 39156-5 BMI, "
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
        "description": "Get medication requests for a patient.",
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
        "description": "Get the full problem list for a patient.",
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
        "description": "Get recent encounters for a patient.",
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

def _tool_runner(fn_name, fn_args):
    dispatch = {
        "get_patient": _get_patient,
        "search_observations": _search_observations,
        "search_medications": _search_medications,
        "search_all_conditions": _search_all_conditions,
        "search_encounters": _search_encounters,
    }
    fn = dispatch.get(fn_name)
    if fn is None:
        return {"error": f"Unknown tool: {fn_name}"}
    return fn(**fn_args)

display(Markdown("**Clinical tools loaded.** Proceed to the next step."))
"""


BUILD_CANDIDATES = """\
#@title Step 4: Build candidate pool
display(Markdown("*Searching for younger patients with diabetes...*"))

_candidate_rows = []
_seen_patients = set()
for _label, _code in [("Likely T1D cohort", SNOMED["t1d"]), ("Likely T2D cohort", SNOMED["t2d"])]:
    _results = _search_conditions(_code, max_results=80)["results"]
    for _item in _results:
        _pid = _item["patient_reference"].split("/")[-1]
        if _pid in _seen_patients:
            continue
        _pat = _get_patient(_pid)
        _age = _pat.get("age")
        if _age is None or _age > 35:
            continue
        _candidate_rows.append({
            "Case #": len(_candidate_rows) + 1,
            "Name": _pat.get("name", ""),
            "Age": _age,
            "Gender": _pat.get("gender", ""),
            "Seed Group": _label,
            "_patient_id": _pid,
        })
        _seen_patients.add(_pid)

# Keep up to 3 per group
_final_candidates = []
_group_counts = {}
for _row in sorted(_candidate_rows, key=lambda r: (r["Seed Group"], r["Age"])):
    _g = _row["Seed Group"]
    _group_counts.setdefault(_g, 0)
    if _group_counts[_g] >= 3:
        continue
    _group_counts[_g] += 1
    _row["Case #"] = len(_final_candidates) + 1
    _final_candidates.append(_row)

_candidate_df = pd.DataFrame(_final_candidates)
_candidate_display = _candidate_df[["Case #", "Name", "Age", "Gender", "Seed Group"]]

display(Markdown("## Your Patient Candidates"))
display(Markdown(
    "These younger patients have a diabetes diagnosis in their record. "
    "The **Seed Group** shows which diagnosis code brought them into the pool "
    "-- but that label might not be the whole story. Your job is to gather "
    "evidence and decide for yourself."
))
display(_candidate_display.style.hide(axis="index"))
"""


SELECT_CASE = """\
#@title Step 5: Select a case to investigate
case_number = 1 #@param {type:"integer"}

if case_number < 1 or case_number > len(_final_candidates):
    display(Markdown(f"**Invalid case number.** Choose between 1 and {len(_final_candidates)}."))
else:
    _selected = _final_candidates[case_number - 1]
    _state["patient_id"] = _selected["_patient_id"]
    _state["patient_label"] = f"{_selected['Name']} (Age {_selected['Age']}, {_selected['Gender']})"
    _state["history"] = []
    _state["evidence"] = {}
    _state["final_answer"] = None

    display(Markdown(f"## Case {case_number} Selected"))
    display(Markdown(
        f"**Patient:** {_state['patient_label']}\\n\\n"
        f"**Your question:** {_state['question']}\\n\\n"
        "Use the **Gather Evidence** cell below to start investigating. "
        "Change the dropdown, click Run, and review what comes back."
    ))
"""


GATHER_EVIDENCE = """\
#@title Step 6: Gather evidence (change dropdown, click Run, repeat)
action = "Get demographics" #@param ["Get demographics", "Get full problem list", "Get labs", "Get medications", "Get encounters"]
lab_type = "HbA1c" #@param ["HbA1c", "C-peptide", "BMI", "Creatinine", "eGFR"]

if _state["patient_id"] is None:
    display(Markdown("**Select a case first** (Step 5 above)."))
else:
    _pid = _state["patient_id"]
    _result_md = ""

    if action == "Get demographics":
        _result = _get_patient(_pid)
        _state["evidence"]["demographics"] = _result
        _state["history"].append({"step": len(_state["history"]) + 1, "tool": "Get demographics", "note": f"Age {_result.get('age')}, {_result.get('gender')}"})
        _result_md = (
            f"### Demographics\\n\\n"
            f"| Field | Value |\\n|-------|-------|\\n"
            f"| Name | {_result.get('name')} |\\n"
            f"| Age | {_result.get('age')} |\\n"
            f"| Gender | {_result.get('gender')} |\\n"
            f"| Date of Birth | {_result.get('birthDate')} |"
        )

    elif action == "Get full problem list":
        _result = _search_all_conditions(_pid)
        _state["evidence"]["conditions"] = _result["results"]
        _names = [r["condition"] for r in _result["results"][:8]]
        _state["history"].append({"step": len(_state["history"]) + 1, "tool": "Get problem list", "note": f"{len(_result['results'])} conditions found"})
        if _result["results"]:
            _rows_md = "\\n".join(f"| {r['condition']} | {r['clinical_status']} |" for r in _result["results"][:10])
            _result_md = f"### Problem List\\n\\n| Condition | Status |\\n|-----------|--------|\\n{_rows_md}"
        else:
            _result_md = "### Problem List\\n\\n*No conditions found.*"

    elif action == "Get labs":
        _loinc = LAB_LOOKUP.get(lab_type)
        if _loinc is None:
            display(Markdown(f"**Unknown lab type:** {lab_type}"))
        else:
            _result = _search_observations(_pid, _loinc)
            _ev_key = lab_type.lower().replace("-", "_").replace(" ", "_")
            _latest = _result["results"][0] if _result["results"] else None
            _state["evidence"][_ev_key] = {"bundle": _result, "latest": _latest}
            if _latest:
                _note = f"{_latest.get('value')} {_latest.get('unit', '')} on {_latest.get('date', 'N/A')}"
            else:
                _note = "No results"
            _state["history"].append({"step": len(_state["history"]) + 1, "tool": f"Get labs: {lab_type}", "note": _note})
            if _result["results"]:
                _rows_md = "\\n".join(
                    f"| {r.get('value', 'N/A')} {r.get('unit', '')} | {r.get('date', 'N/A')} |"
                    for r in _result["results"][:5]
                )
                _result_md = f"### {lab_type} Results\\n\\n| Value | Date |\\n|-------|------|\\n{_rows_md}"
            else:
                _result_md = f"### {lab_type} Results\\n\\n*No {lab_type} results found for this patient.*"

    elif action == "Get medications":
        _result = _search_medications(_pid)
        _state["evidence"]["medications"] = _result["results"]
        _meds = [r["medication"] for r in _result["results"][:5]]
        _state["history"].append({"step": len(_state["history"]) + 1, "tool": "Get medications", "note": f"{len(_result['results'])} medications found"})
        if _result["results"]:
            _rows_md = "\\n".join(f"| {r['medication']} | {r['status']} | {r.get('authoredOn', 'N/A')} |" for r in _result["results"][:10])
            _result_md = f"### Medications\\n\\n| Medication | Status | Date |\\n|------------|--------|------|\\n{_rows_md}"
        else:
            _result_md = "### Medications\\n\\n*No medications found.*"

    elif action == "Get encounters":
        _result = _search_encounters(_pid)
        _state["evidence"]["encounters"] = _result["results"]
        _state["history"].append({"step": len(_state["history"]) + 1, "tool": "Get encounters", "note": f"{len(_result['results'])} encounters found"})
        if _result["results"]:
            _rows_md = "\\n".join(
                f"| {r.get('type', 'N/A')} | {r.get('class', '')} | {r.get('status', '')} | {r.get('period_start', 'N/A')} |"
                for r in _result["results"][:8]
            )
            _result_md = f"### Encounters\\n\\n| Type | Class | Status | Date |\\n|------|-------|--------|------|\\n{_rows_md}"
        else:
            _result_md = "### Encounters\\n\\n*No encounters found.*"

    if _result_md:
        display(Markdown(_result_md))
    display(Markdown(_render_state()))
"""


LLM_COACH = """\
#@title Step 7: Ask the AI Coach for a suggestion (optional)

if _state["patient_id"] is None:
    display(Markdown("**Select a case first** (Step 5 above)."))
elif _anthropic_client is None:
    display(Markdown(
        "**AI Coach not available.** To enable it, add your `ANTHROPIC_API_KEY` "
        "to Colab Secrets (key icon in the sidebar).\\n\\n"
        "You can still complete the exercise without it -- the AI Coach is optional."
    ))
else:
    display(Markdown("*Asking the AI coach...*"))
    _coach_state = {
        "question": _state["question"],
        "patient_id": _state["patient_id"],
        "evidence_collected": list(_state["evidence"].keys()),
        "missing_evidence": _evidence_gaps(),
        "steps_taken": len(_state["history"]),
    }
    _coach_response = _anthropic_client.messages.create(
        model=MODEL,
        max_tokens=300,
        messages=[{
            "role": "user",
            "content": (
                "You are coaching a clinical informatics student who is acting as "
                "an agent reviewing a diabetes case. Given the current state, recommend "
                "exactly one next action from this list: Get demographics, Get full "
                "problem list, Get labs (specify which), Get medications, Get encounters, "
                "or Finish and answer. Be concise and explain why in 2-3 sentences.\\n\\n"
                + json.dumps(_coach_state, indent=2)
            ),
        }],
    )
    _suggestion = "".join(block.text for block in _coach_response.content if hasattr(block, "text"))
    display(Markdown(f"## AI Coach Suggestion\\n\\n{_suggestion}"))
"""


RECORD_ANSWER = """\
#@title Step 8: Record your answer
classification = "Likely Type 1" #@param ["Likely Type 1", "Likely Type 2", "Unclear / needs more review"]
rationale = "" #@param {type:"string"}

if _state["patient_id"] is None:
    display(Markdown("**Select a case first** (Step 5 above)."))
elif not rationale.strip():
    display(Markdown("**Please enter a rationale** explaining what evidence supports your answer."))
else:
    _state["final_answer"] = {
        "classification": classification,
        "rationale": rationale.strip(),
    }
    _state["history"].append({
        "step": len(_state["history"]) + 1,
        "tool": "Final answer",
        "note": classification,
    })

    display(Markdown(
        f"## Your Answer Recorded\\n\\n"
        f"**Patient:** {_state['patient_label']}\\n\\n"
        f"**Classification:** {classification}\\n\\n"
        f"**Rationale:** {rationale}\\n\\n"
        f"**Steps taken:** {len(_state['history'])}\\n\\n"
        "---\\n\\n"
        "*Scroll down to see how the AI agent handles the same case.*"
    ))
"""


LLM_AGENT = """\
#@title Step 9: Watch the AI agent work the same case

if _state["patient_id"] is None:
    display(Markdown("**Select a case first** (Step 5 above)."))
elif _anthropic_client is None:
    display(Markdown(
        "**AI Agent not available.** Add your `ANTHROPIC_API_KEY` to Colab Secrets "
        "to see the autonomous agent comparison."
    ))
else:
    _agent_pid = _state["patient_id"]
    _agent_question = (
        f"Review patient {_agent_pid} ({_state['patient_label']}). "
        "Decide whether this case is more consistent with Type 1 diabetes, "
        "Type 2 diabetes, or still unclear. Use the available tools to gather "
        "evidence. Cite specific findings in your final answer."
    )
    _agent_system = (
        "You are a clinical data assistant working against a FHIR server with "
        "synthetic patient data. Prefer direct evidence over heuristics. Use "
        "C-peptide when available. If evidence is conflicting, say unclear."
    )

    display(Markdown("## AI Agent Run\\n\\n*The AI agent is now investigating the same patient...*\\n"))

    _agent_messages = [{"role": "user", "content": _agent_question}]
    _agent_tool_log = []

    for _agent_step in range(1, 9):
        _agent_resp = _anthropic_client.messages.create(
            model=MODEL,
            max_tokens=4096,
            system=_agent_system,
            messages=_agent_messages,
            tools=CLAUDE_TOOLS,
        )

        _tool_blocks = [b for b in _agent_resp.content if b.type == "tool_use"]

        if not _tool_blocks:
            _final_text = "".join(b.text for b in _agent_resp.content if hasattr(b, "text"))
            break

        _assistant_content = []
        for _b in _agent_resp.content:
            if _b.type == "text":
                _assistant_content.append({"type": "text", "text": _b.text})
            elif _b.type == "tool_use":
                _assistant_content.append({"type": "tool_use", "id": _b.id, "name": _b.name, "input": _b.input})
        _agent_messages.append({"role": "assistant", "content": _assistant_content})

        _tool_results = []
        for _tb in _tool_blocks:
            _tr = _tool_runner(_tb.name, _tb.input)
            _agent_tool_log.append({
                "Step": _agent_step,
                "Tool": _tb.name,
                "Arguments": str(_tb.input)[:80],
            })
            display(Markdown(f"**Step {_agent_step}:** Called `{_tb.name}` with `{json.dumps(_tb.input)[:60]}...`"))
            _tool_results.append({
                "type": "tool_result",
                "tool_use_id": _tb.id,
                "content": json.dumps(_tr, default=str),
            })
        _agent_messages.append({"role": "user", "content": _tool_results})
    else:
        _final_text = "(Agent reached maximum steps without a final answer)"

    display(Markdown("---"))
    display(Markdown(f"### AI Agent's Answer\\n\\n{_final_text}"))
    display(Markdown(f"### AI Agent's Tool Calls\\n"))
    if _agent_tool_log:
        display(pd.DataFrame(_agent_tool_log).style.hide(axis="index"))
"""


DEBRIEF_DISPLAY = """\
#@title Step 10: Compare your reasoning with the AI

display(Markdown("## Comparison & Reflection"))

if _state["final_answer"]:
    display(Markdown(
        f"### Your Answer\\n\\n"
        f"**Classification:** {_state['final_answer']['classification']}\\n\\n"
        f"**Rationale:** {_state['final_answer']['rationale']}\\n\\n"
        f"**Total steps:** {len(_state['history'])}"
    ))

display(Markdown(
    "### Discussion Questions\\n\\n"
    "1. **Evidence strategy:** Did you and the AI gather the same evidence? "
    "In what order?\\n"
    "2. **Stopping point:** Did you gather more or less evidence than the AI? "
    "Was either approach premature?\\n"
    "3. **Key signal:** What was the single most informative piece of evidence?\\n"
    "4. **Uncertainty:** Did either you or the AI express appropriate uncertainty "
    "when the evidence was ambiguous?\\n"
    "5. **Agent loop:** Now that you\\'ve played the agent, can you describe the "
    "loop in your own words? (observe state -> choose tool -> update state -> repeat)"
))

if _state["history"]:
    display(Markdown("### Your Step Log"))
    display(pd.DataFrame(_state["history"]).style.hide(axis="index"))
"""


# ---------------------------------------------------------------------------
# Assemble notebook
# ---------------------------------------------------------------------------

cells = [
    # Welcome
    md_cell([
        "# You Are the Agent\n",
        "\n",
        "## A Clinical Decision-Making Exercise\n",
        "\n",
        "In this exercise, **you temporarily play the role of a clinical AI agent.** ",
        "You have a patient to review and a clinical question to answer. ",
        "Your tools are queries against an electronic health record (FHIR server). ",
        "Your job is to:\n",
        "\n",
        "1. **Choose** which evidence to gather\n",
        "2. **Review** what comes back\n",
        "3. **Decide** when you have enough to answer\n",
        "4. **Record** your classification with supporting evidence\n",
        "\n",
        "Then you'll watch an AI agent handle the same case and compare strategies.\n",
        "\n",
        "> **No coding required.** Every step uses dropdown menus and Run buttons. ",
        "The code behind each cell is hidden -- focus on the clinical reasoning, not the Python.\n",
    ]),

    # Learning objectives
    md_cell([
        "## What You'll Practice\n",
        "\n",
        "By the end of this exercise you should be able to:\n",
        "\n",
        "- Describe an **agent loop** in plain language ",
        "(observe → decide → act → update → repeat)\n",
        "- Choose the **next query** based on what evidence is still missing\n",
        "- Explain why a **single datapoint** is not enough for classification\n",
        "- Decide when evidence is **sufficient** versus when you need more\n",
        "- Compare your strategy with an AI agent's approach\n",
    ]),

    # Scenario framing
    md_cell([
        "## The Clinical Scenario\n",
        "\n",
        "**Setting:** You are an informatics fellow helping review a cohort of ",
        "younger patients (age ≤ 35) with a diabetes diagnosis.\n",
        "\n",
        "**Problem:** Some of these patients may have been labeled with the wrong ",
        "diabetes type, or the label may be incomplete. Type 1 and Type 2 diabetes ",
        "require different management strategies, so accurate classification matters.\n",
        "\n",
        "**Your task:** For each patient, gather evidence from the EHR and decide:\n",
        "- **Likely Type 1** — evidence supports autoimmune diabetes\n",
        "- **Likely Type 2** — evidence supports insulin resistance pattern\n",
        "- **Unclear** — evidence is insufficient or conflicting\n",
        "\n",
        "**Key evidence to look for:**\n",
        "- C-peptide level (low → Type 1, normal/high → Type 2)\n",
        "- Medication pattern (insulin-only vs. oral agents)\n",
        "- BMI (lower → Type 1, higher → Type 2, but not definitive)\n",
        "- Problem list context (other autoimmune conditions, complications)\n",
    ]),

    # Setup (silent)
    form_cell(SETUP_SILENT),

    # Verify
    form_cell(VERIFY_CONNECTION),

    # Tools & helpers (hidden)
    form_cell(TOOLS_AND_HELPERS),

    # Build candidates
    form_cell(BUILD_CANDIDATES),

    # Instructions before case selection
    md_cell([
        "## Time to Be the Agent\n",
        "\n",
        "You now have a pool of patients. Here's how the exercise works:\n",
        "\n",
        "1. **Select a case** — pick a patient number below\n",
        "2. **Gather evidence** — use the dropdown menu to query the EHR, one step at a time\n",
        "3. **Watch your dashboard** — it shows what you've collected and what's still missing\n",
        "4. **Ask the AI coach** (optional) — get a suggestion for your next step\n",
        "5. **Record your answer** — when you have enough evidence, make your call\n",
        "6. **Compare with the AI** — watch the AI agent work the same case\n",
        "\n",
        "> **Tip:** There is no single \"right\" order. But think about which evidence ",
        "would be most informative *before* you gather it.\n",
    ]),

    # Select case
    form_cell(SELECT_CASE),

    # Evidence gathering instructions
    md_cell([
        "## Gather Evidence\n",
        "\n",
        "Use the cell below to query the patient's record. ",
        "**Change the dropdown** to select a different action, then **click Run** again.\n",
        "\n",
        "After each query, your **Agent Dashboard** updates to show:\n",
        "- What evidence you've collected so far\n",
        "- What categories are still missing\n",
        "- Your step history\n",
        "\n",
        "> **Run this cell as many times as you want** — each run is one \"agent turn.\"\n",
    ]),

    # Gather evidence (repeatable)
    form_cell(GATHER_EVIDENCE),

    # LLM coach
    md_cell([
        "## Optional: Ask the AI Coach\n",
        "\n",
        "If you want a second opinion on what to do next, run the cell below. ",
        "The AI coach sees the same evidence state you see and suggests one next action.\n",
        "\n",
        "This is **not** the same as having the AI do the whole task. You're still in control.\n",
    ]),

    form_cell(LLM_COACH),

    # Record answer
    md_cell([
        "## Record Your Answer\n",
        "\n",
        "When you've gathered enough evidence, use the cell below to record your classification.\n",
        "\n",
        "**Important:** Write a brief rationale explaining *which specific evidence* supports your answer. ",
        "\"I think it's Type 1\" is not enough — cite the findings.\n",
    ]),

    form_cell(RECORD_ANSWER),

    # LLM comparison
    md_cell([
        "## Watch the AI Agent\n",
        "\n",
        "Now let's see how an AI agent handles the same case. The agent will:\n",
        "\n",
        "1. Read the same clinical question\n",
        "2. Choose its own tools and gather evidence\n",
        "3. Decide when it has enough information\n",
        "4. Give its classification with supporting evidence\n",
        "\n",
        "Watch the tool calls as they happen and compare with your approach.\n",
    ]),

    form_cell(LLM_AGENT),

    # Debrief
    form_cell(DEBRIEF_DISPLAY),

    # Final reflection
    md_cell([
        "## Wrap-Up\n",
        "\n",
        "You've just experienced the core **agent loop** from the inside:\n",
        "\n",
        "```\n",
        "while not confident_enough:\n",
        "    observe current evidence state\n",
        "    choose the most informative next query\n",
        "    execute the query\n",
        "    update your evidence and assessment\n",
        "```\n",
        "\n",
        "This is exactly what AI agents do — the only difference is who's making the decisions.\n",
        "\n",
        "**To investigate another patient:** Go back to Step 5, change the case number, ",
        "and run through the exercise again. Each case has different evidence patterns.\n",
    ]),
]


notebook = build_notebook(cells)
os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
    json.dump(notebook, f, indent=1)
    f.write("\n")

print(f"Wrote {OUTPUT_PATH}")
