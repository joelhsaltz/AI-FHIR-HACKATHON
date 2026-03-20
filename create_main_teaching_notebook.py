#!/usr/bin/env python3
"""Generate the main teaching notebook for the redesigned hackathon.

This produces a self-contained Colab notebook with all code inlined --
no src/ imports, no openai references. Everything uses Anthropic/Claude.
"""

from __future__ import annotations

import json
from pathlib import Path
import uuid


PROJECT_ROOT = Path(__file__).resolve().parent
OUTPUT_PATH = PROJECT_ROOT / "notebooks" / "main_teaching_application.ipynb"


def cell_id() -> str:
    return uuid.uuid4().hex[:8]


def md_cell(source: str) -> dict:
    return {"cell_type": "markdown", "id": cell_id(), "metadata": {}, "source": source}


def code_cell(source: str) -> dict:
    return {
        "cell_type": "code",
        "id": cell_id(),
        "metadata": {},
        "source": source,
        "execution_count": None,
        "outputs": [],
    }


def build_notebook(cells: list[dict]) -> dict:
    return {
        "nbformat": 4,
        "nbformat_minor": 5,
        "metadata": {
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3",
            },
            "language_info": {"name": "python", "version": "3.10.0"},
        },
        "cells": cells,
    }


# ---------------------------------------------------------------------------
# Cell content constants
# ---------------------------------------------------------------------------

SETUP = """\
!pip install -q anthropic requests pandas

import os
import json
from datetime import date, datetime

import pandas as pd
import requests
import urllib3
from IPython.display import Markdown, display

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ── FHIR connection ──
FHIR_BASE = "https://lfh-fhir.eastus2.cloudapp.azure.com:9443/fhir-server/api/v4"
FHIR_SESSION = requests.Session()
FHIR_SESSION.auth = ("fhiruser", "BmI512@ccess")
FHIR_SESSION.verify = False

# ── Anthropic client ──
try:
    from google.colab import userdata
    ANTHROPIC_API_KEY = userdata.get("ANTHROPIC_API_KEY")
except Exception:
    ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")

from anthropic import Anthropic

client = Anthropic(api_key=ANTHROPIC_API_KEY) if ANTHROPIC_API_KEY else None
MODEL = "claude-sonnet-4-20250514"

# ── Verify FHIR connection ──
resp = FHIR_SESSION.get(f"{FHIR_BASE}/metadata", params={"_format": "json"}, timeout=20)
if resp.status_code != 200:
    raise RuntimeError(f"FHIR server connection failed: HTTP {resp.status_code}")

count_resp = FHIR_SESSION.get(
    f"{FHIR_BASE}/Patient",
    params={"_summary": "count", "_format": "json"},
    timeout=20,
)
print("FHIR server ready")
print(f"Patient count: {count_resp.json().get('total', 'unknown')}")
print(f"Anthropic client: {'enabled' if client else 'disabled (set ANTHROPIC_API_KEY)'}")
"""

FHIR_TOOLS = """\
# ── Code dictionaries ──
SNOMED = {
    "t1d": "46635009",
    "t2d": "44054006",
    "ckd": "709044004",
}

LOINC = {
    "hba1c": "4548-4",
    "c_peptide": "1986-9",
    "bmi": "39156-5",
    "creatinine": "2160-0",
    "egfr": "33914-3",
    "uacr": "14959-1",
}

LAB_MENU = {
    "1": ("HbA1c", LOINC["hba1c"]),
    "2": ("C-peptide", LOINC["c_peptide"]),
    "3": ("BMI", LOINC["bmi"]),
    "4": ("Creatinine", LOINC["creatinine"]),
    "5": ("eGFR", LOINC["egfr"]),
    "6": ("Urine albumin/creatinine ratio", LOINC["uacr"]),
}


# ── Helper ──
def compute_age(birth_date):
    if not birth_date:
        return None
    born = datetime.strptime(birth_date, "%Y-%m-%d").date()
    today = date.today()
    return today.year - born.year - ((today.month, today.day) < (born.month, born.day))


# ── FHIR query functions ──
def search_conditions(code, max_results=50):
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


def get_patient(patient_id):
    resp = FHIR_SESSION.get(
        f"{FHIR_BASE}/Patient/{patient_id}",
        params={"_format": "json"},
        timeout=30,
    )
    patient = resp.json()
    name = patient.get("name", [{}])[0]
    return {
        "id": patient.get("id"),
        "name": f"{' '.join(name.get('given', []))} {name.get('family', '')}".strip(),
        "gender": patient.get("gender", ""),
        "birthDate": patient.get("birthDate", ""),
        "age": compute_age(patient.get("birthDate", "")),
    }


def search_observations(patient_id, loinc_code, max_results=5):
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
    rows = []
    for entry in bundle.get("entry", []):
        resource = entry["resource"]
        coding = resource.get("code", {}).get("coding", [{}])[0]
        value_qty = resource.get("valueQuantity", {})
        rows.append({
            "display": coding.get("display", ""),
            "code": coding.get("code", ""),
            "value": value_qty.get("value"),
            "unit": value_qty.get("unit", ""),
            "date": resource.get("effectiveDateTime", ""),
        })
    return {"total": bundle.get("total", 0), "results": rows}


def search_medications(patient_id, max_results=10):
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
    rows = []
    for entry in bundle.get("entry", []):
        resource = entry["resource"]
        med_concept = resource.get("medicationCodeableConcept", {})
        coding = med_concept.get("coding", [{}])[0] if med_concept.get("coding") else {}
        rows.append({
            "medication": coding.get("display") or med_concept.get("text", "unknown"),
            "code": coding.get("code", ""),
            "status": resource.get("status", ""),
            "authoredOn": resource.get("authoredOn", ""),
        })
    return {"total": bundle.get("total", 0), "results": rows}


def search_all_conditions(patient_id, max_results=20):
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


def search_encounters(patient_id, max_results=10):
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


def search_patients(max_results=50):
    resp = FHIR_SESSION.get(
        f"{FHIR_BASE}/Patient",
        params={"_count": max_results, "_format": "json"},
        timeout=30,
    )
    bundle = resp.json()
    rows = []
    for entry in bundle.get("entry", []):
        patient = entry["resource"]
        name = patient.get("name", [{}])[0]
        rows.append({
            "id": patient.get("id"),
            "name": f"{' '.join(name.get('given', []))} {name.get('family', '')}".strip(),
            "gender": patient.get("gender", ""),
            "birthDate": patient.get("birthDate", ""),
            "age": compute_age(patient.get("birthDate", "")),
        })
    return {"total": bundle.get("total", 0), "results": rows}


print("FHIR tool functions loaded")
"""

CLAUDE_TOOL_SCHEMAS = """\
# ── Claude tool schemas (Anthropic format) ──
tools = [
    {
        "name": "search_conditions",
        "description": (
            "Search for conditions by SNOMED CT code. "
            "Common codes: 46635009 for Type 1 diabetes, "
            "44054006 for Type 2 diabetes, 709044004 for chronic kidney disease."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "SNOMED CT code to search for"},
                "max_results": {"type": "integer", "default": 50},
            },
            "required": ["code"],
        },
    },
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
            "2160-0 creatinine, 33914-3 eGFR, 14959-1 urine albumin/creatinine ratio."
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
    {
        "name": "search_patients",
        "description": "Get a batch of patient demographics.",
        "input_schema": {
            "type": "object",
            "properties": {"max_results": {"type": "integer", "default": 50}},
        },
    },
]

# ── Function dispatch ──
available_functions = {
    "search_conditions": search_conditions,
    "get_patient": get_patient,
    "search_observations": search_observations,
    "search_medications": search_medications,
    "search_all_conditions": search_all_conditions,
    "search_encounters": search_encounters,
    "search_patients": search_patients,
}


def call_tool(name, args):
    fn = available_functions.get(name)
    if fn is None:
        raise KeyError(f"Unknown tool: {name}")
    return fn(**args)


print("Claude tool schemas and dispatcher loaded")
"""

STATE_MANAGEMENT = """\
# ── Evidence gap functions ──
def follow_up_evidence_gaps(evidence):
    gaps = []
    if "demographics" not in evidence:
        gaps.append("basic demographics")
    if "conditions" not in evidence:
        gaps.append("full problem list")
    if "hba1c" not in evidence:
        gaps.append("HbA1c")
    if "medications" not in evidence:
        gaps.append("medication pattern")
    if "encounters" not in evidence:
        gaps.append("encounter context")
    return gaps


def type_clarification_evidence_gaps(evidence):
    gaps = []
    if "demographics" not in evidence:
        gaps.append("basic demographics")
    if "conditions" not in evidence:
        gaps.append("problem list / diagnosis context")
    if "c_peptide" not in evidence:
        gaps.append("C-peptide")
    if "medications" not in evidence:
        gaps.append("medication pattern")
    if "bmi" not in evidence:
        gaps.append("BMI / insulin-resistance pattern")
    return gaps


# ── State helpers ──
def record_step(state, tool_name, note, payload=None):
    state["history"].append({
        "step": len(state["history"]) + 1,
        "tool": tool_name,
        "note": note,
        "payload": payload,
    })


def latest_value(observation_bundle):
    results = observation_bundle.get("results", [])
    if not results:
        return None
    return results[0]


def show_state(state, evidence_gap_fn):
    print("=" * 72)
    print("YOU ARE THE AGENT")
    print("=" * 72)
    print(f"Question: {state['question']}")
    if state.get("patient_label"):
        print(f"Patient: {state['patient_label']} ({state.get('patient_id', '')})")
    print()

    print("Evidence collected so far:")
    evidence = state.get("evidence", {})
    if not evidence:
        print("  None yet")
    else:
        for key, value in evidence.items():
            if key == "demographics":
                print(f"  demographics: age {value.get('age')}, {value.get('gender')}, birthDate {value.get('birthDate')}")
            elif key == "conditions":
                names = [row["condition"] for row in value[:5]]
                print(f"  conditions: {', '.join(names) if names else 'none found'}")
            elif key == "medications":
                meds = [row["medication"] for row in value[:5]]
                print(f"  medications: {', '.join(meds) if meds else 'none found'}")
            elif key == "encounters":
                enc_info = [f"{row.get('type', '')} ({row.get('period_start', '')})" for row in value[:3]]
                print(f"  encounters: {', '.join(enc_info) if enc_info else 'none found'}")
            else:
                latest = value.get("latest") if isinstance(value, dict) else None
                if latest:
                    print(f"  {key}: {latest.get('value')} {latest.get('unit', '')} on {latest.get('date', '')}")
                else:
                    print(f"  {key}: no result found")

    print()
    print("Evidence still missing:")
    missing = evidence_gap_fn(evidence)
    if missing:
        for item in missing:
            print(f"  - {item}")
    else:
        print("  None obvious. You may be ready to answer.")

    print()
    print("Steps taken:")
    if not state["history"]:
        print("  No steps yet")
    else:
        for item in state["history"][-5:]:
            print(f"  Step {item['step']}: {item['tool']} -> {item['note']}")


print("State management loaded")
"""

LLM_COACH_AND_AGENT = """\
# ── Agent instructions ──
FOLLOW_UP_AGENT_INSTRUCTIONS = \"\"\"You are helping review patients for diabetes-focused follow-up.

This is an informatics workflow exercise, not a medicine exam.
- gather enough structured evidence before recommending follow-up
- treat diabetes diagnosis, glycemic control, medication complexity, and kidney disease as the core signals
- note that the current synthetic cohort mostly exposes recent ambulatory encounters rather than reliable inpatient admission metadata
- be explicit about uncertainty when the evidence is thin
- in the final answer, cite the concrete evidence you used
\"\"\"

TYPE_CLARIFICATION_AGENT_INSTRUCTIONS = \"\"\"You are helping review a younger patient with diabetes.

This is an evidence-gathering exercise.
- prefer direct evidence over heuristics
- use C-peptide when available
- use medication pattern, BMI, age, and diagnosis history as supporting context
- if evidence is missing or conflicting, say the case is unclear rather than forcing a binary answer
- cite concrete evidence from the tool results in your final answer
\"\"\"


# ── LLM coach (suggests one next step) ──
def summarize_state_for_llm(state, evidence_gap_fn):
    evidence = state.get("evidence", {})
    summary = {
        "question": state["question"],
        "patient_id": state.get("patient_id", ""),
        "evidence": {},
        "history": [
            {"step": item["step"], "tool": item["tool"], "note": item["note"]}
            for item in state["history"]
        ],
        "missing_evidence": evidence_gap_fn(evidence),
    }
    for key, value in evidence.items():
        if key in {"demographics", "medications", "conditions", "encounters"}:
            summary["evidence"][key] = value
        elif isinstance(value, dict) and "latest" in value:
            summary["evidence"][key] = value.get("latest")
        else:
            summary["evidence"][key] = value
    return summary


def suggest_next_step(state, evidence_gap_fn, system_prompt=None):
    if client is None:
        return (
            "Anthropic client not configured. Human mode is still available. "
            "Set ANTHROPIC_API_KEY to enable LLM coaching."
        )

    summary = summarize_state_for_llm(state, evidence_gap_fn)
    prompt = (
        "You are coaching a student who is pretending to be the clinical agent. "
        "Recommend exactly one next action from this list: "
        "Get demographics, Get full problem list, Get labs, Get medications, "
        "Get encounters, Finish and answer. "
        "If the evidence is already sufficient, recommend 'Finish and answer'. "
        "Be concise and explain why.\\n\\n"
        + json.dumps(summary, indent=2, default=str)
    )
    kwargs = {
        "model": MODEL,
        "max_tokens": 300,
        "messages": [{"role": "user", "content": prompt}],
    }
    if system_prompt:
        kwargs["system"] = system_prompt
    response = client.messages.create(**kwargs)
    return "".join(block.text for block in response.content if hasattr(block, "text"))


# ── Full autonomous agent loop ──
def run_agent(question, system_prompt, max_steps=8):
    if client is None:
        raise ValueError("Anthropic client not configured. Set ANTHROPIC_API_KEY.")

    messages = [{"role": "user", "content": question}]
    tool_calls_log = []

    for step in range(1, max_steps + 1):
        response = client.messages.create(
            model=MODEL,
            max_tokens=4096,
            system=system_prompt,
            messages=messages,
            tools=tools,
        )

        # Check for tool use
        tool_use_blocks = [b for b in response.content if b.type == "tool_use"]

        if not tool_use_blocks:
            # No tool calls => final text answer
            answer = "".join(b.text for b in response.content if hasattr(b, "text"))
            return {
                "answer": answer,
                "tool_calls": tool_calls_log,
                "messages": messages,
                "completed": True,
            }

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

        # Execute each tool call and collect results
        tool_results = []
        for block in tool_use_blocks:
            fn_name = block.name
            fn_args = block.input
            try:
                result = call_tool(fn_name, fn_args)
            except Exception as e:
                result = {"error": str(e)}

            tool_calls_log.append({
                "step": step,
                "tool": fn_name,
                "arguments": fn_args,
                "result_preview": str(result)[:300],
            })

            tool_results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": json.dumps(result, default=str),
            })

        # Send tool results back as a user message
        messages.append({"role": "user", "content": tool_results})

    # Reached max steps
    answer = "".join(b.text for b in response.content if hasattr(b, "text"))
    return {
        "answer": answer,
        "tool_calls": tool_calls_log,
        "messages": messages,
        "completed": False,
        "stop_reason": f"max_steps_exceeded:{max_steps}",
    }


print("LLM coach and agent loop loaded")
"""

FHIR_QUERY_MAP = """\
FHIR_QUERY_MAPPINGS = [
    {
        "interaction_option": "Find patients by diagnosis",
        "tool": "search_conditions",
        "fhir_query": "GET /Condition?code={snomed_code}&_count={n}&_format=json",
        "teaching_use": "Build the candidate pool from a diagnosis such as T1D or T2D.",
    },
    {
        "interaction_option": "Get demographics",
        "tool": "get_patient",
        "fhir_query": "GET /Patient/{patient_id}?_format=json",
        "teaching_use": "Retrieve one patient's name, age, sex, and other basic context.",
    },
    {
        "interaction_option": "Get full problem list",
        "tool": "search_all_conditions",
        "fhir_query": "GET /Condition?subject=Patient/{id}&_count={n}&_format=json",
        "teaching_use": "Inspect the full diagnosis context for a selected patient.",
    },
    {
        "interaction_option": "Get labs",
        "tool": "search_observations",
        "fhir_query": "GET /Observation?subject=Patient/{id}&code={loinc}&_count={n}&_sort=-date&_format=json",
        "teaching_use": "Review the most recent HbA1c, C-peptide, BMI, creatinine, or eGFR.",
    },
    {
        "interaction_option": "Get medications",
        "tool": "search_medications",
        "fhir_query": "GET /MedicationRequest?subject=Patient/{id}&_count={n}&_format=json",
        "teaching_use": "Inspect active diabetes medications and treatment complexity.",
    },
    {
        "interaction_option": "Get encounters",
        "tool": "search_encounters",
        "fhir_query": "GET /Encounter?subject=Patient/{id}&_count={n}&_sort=-date&_format=json",
        "teaching_use": "Review encounter metadata and note cohort limitations.",
    },
]

display(pd.DataFrame(FHIR_QUERY_MAPPINGS))
"""

SCENARIO1_CANDIDATE_BUILDER = """\
# ── Scenario 1: Build follow-up candidate pool ──
# Pulls T1D + T2D patients with priority scoring based on HbA1c, CKD, insulin use

def _safe_call(default, fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except Exception:
        return default


def build_follow_up_candidate_pool(max_results_per_code=40, max_candidates=12):
    rows = []
    seen = set()
    for cohort_label, code in [("Type 2 diabetes", SNOMED["t2d"]), ("Type 1 diabetes", SNOMED["t1d"])]:
        for item in search_conditions(code, max_results=max_results_per_code)["results"]:
            patient_id = item.get("patient_reference", "").split("/")[-1]
            if not patient_id or patient_id in seen:
                continue
            patient = _safe_call({}, get_patient, patient_id)
            if not patient:
                continue
            encounters = _safe_call({"results": []}, search_encounters, patient_id, max_results=1)["results"]
            hba1c_bundle = _safe_call({"results": []}, search_observations, patient_id, LOINC["hba1c"], max_results=1)
            meds = _safe_call({"results": []}, search_medications, patient_id, max_results=10)["results"]
            conditions = _safe_call({"results": []}, search_all_conditions, patient_id, max_results=12)["results"]
            last_hba1c = hba1c_bundle["results"][0]["value"] if hba1c_bundle["results"] else None
            has_ckd = any(row.get("code") == SNOMED["ckd"] for row in conditions)
            insulin_use = any("insulin" in row.get("medication", "").lower() for row in meds)
            encounter = encounters[0] if encounters else {}
            score = 0
            if last_hba1c is not None:
                score += 3 if last_hba1c >= 9 else 2 if last_hba1c >= 7.5 else 0
            if has_ckd:
                score += 1
            if insulin_use:
                score += 1
            if encounter:
                score += 1
            rows.append({
                "patient_id": patient_id,
                "seed_group": cohort_label,
                "name": patient.get("name", ""),
                "age": patient.get("age"),
                "gender": patient.get("gender", ""),
                "encounter_class": encounter.get("class", ""),
                "latest_hba1c": last_hba1c,
                "insulin_use": insulin_use,
                "has_ckd": has_ckd,
                "priority_score": score,
            })
            seen.add(patient_id)
    rows.sort(key=lambda r: (r.get("priority_score", 0), r.get("latest_hba1c") or -1), reverse=True)
    for i, row in enumerate(rows[:max_candidates], start=1):
        row["candidate_number"] = i
    return rows[:max_candidates]


print("Building follow-up candidate pool (this may take a minute)...")
scenario1_candidates = build_follow_up_candidate_pool()
print(f"Found {len(scenario1_candidates)} candidates")
display(pd.DataFrame(scenario1_candidates))
"""

SCENARIO1_HUMAN_MODE = """\
# ── Scenario 1: Human mode state and turn engine ──
scenario1_state = None
SCENARIO1_PROMPT = (
    "Review patients with diabetes who have recent encounters and identify "
    "which patients should be prioritized for endocrine follow-up based on "
    "evidence of poor control or diabetes-related complexity."
)

SCENARIO1_VERDICT_LABELS = ["Flag", "Do not flag", "Uncertain / needs more review"]


def scenario1_select_patient(candidate_number):
    global scenario1_state
    match = [r for r in scenario1_candidates if r.get("candidate_number") == candidate_number]
    if not match:
        raise ValueError(f"Unknown candidate number: {candidate_number}")
    row = match[0]
    scenario1_state = {
        "question": SCENARIO1_PROMPT,
        "patient_id": row["patient_id"],
        "patient_label": row["name"],
        "history": [],
        "evidence": {},
        "follow_up_list": [],
        "patient_decisions": {},
        "final_answer": None,
    }
    print(f"Selected patient: {row['name']} ({row['patient_id']})")
    show_state(scenario1_state, follow_up_evidence_gaps)


def scenario1_show():
    if scenario1_state is None:
        print("Run scenario1_select_patient(candidate_number) first.")
        return
    show_state(scenario1_state, follow_up_evidence_gaps)
    if scenario1_state.get("follow_up_list"):
        print()
        print("Follow-up list so far:")
        display(pd.DataFrame(scenario1_state["follow_up_list"]))


def show_dataframe(title, rows):
    print()
    print(title)
    if not rows:
        print("  No rows found")
        return
    display(pd.DataFrame(rows))


def choose_lab():
    print()
    print("Which lab do you want?")
    for key, value in LAB_MENU.items():
        print(f"  {key}. {value[0]}")
    choice = input("Enter lab number: ").strip()
    if choice not in LAB_MENU:
        raise ValueError("Unknown lab choice")
    return LAB_MENU[choice]


def ask_why(action_name):
    reason = input(f"Why '{action_name}'? (short note, or Enter to skip): ").strip()
    return reason or "no note entered"


def scenario1_human_turn():
    if scenario1_state is None:
        raise ValueError("Run scenario1_select_patient(candidate_number) first.")
    patient_id = scenario1_state["patient_id"]

    print()
    print("Choose your next action:")
    print("  1.  Find patients by diagnosis")
    print("  2.  Review a different candidate")
    print("  3.  Get demographics")
    print("  4.  Get full problem list")
    print("  5.  Get labs")
    print("  6.  Get medications")
    print("  7.  Get encounters")
    print("  8.  Add patient to follow-up list")
    print("  9.  Mark patient as not priority")
    print("  10. Mark patient as uncertain")
    print("  11. Ask the LLM what to do next")
    print("  12. Finish")
    choice = input("Enter 1-12: ").strip()

    if choice == "1":
        code_input = input("SNOMED code (or t1d/t2d/ckd shorthand): ").strip()
        code = SNOMED.get(code_input, code_input)
        reason = ask_why("Find patients")
        result = search_conditions(code)
        record_step(scenario1_state, "search_conditions", reason, result["results"][:5])
        show_dataframe(f"Conditions (code={code})", result["results"][:10])

    elif choice == "2":
        num = int(input("Candidate number: ").strip())
        scenario1_select_patient(num)

    elif choice == "3":
        reason = ask_why("Get demographics")
        result = get_patient(patient_id)
        scenario1_state["evidence"]["demographics"] = result
        record_step(scenario1_state, "get_patient", reason, result)
        show_dataframe("Demographics", [result])

    elif choice == "4":
        reason = ask_why("Get full problem list")
        result = search_all_conditions(patient_id)
        scenario1_state["evidence"]["conditions"] = result["results"]
        record_step(scenario1_state, "search_all_conditions", reason, result["results"])
        show_dataframe("Problem list", result["results"])

    elif choice == "5":
        label, code = choose_lab()
        reason = ask_why(f"Get lab: {label}")
        result = search_observations(patient_id, code)
        key = label.lower().replace("-", "_").replace(" ", "_")
        scenario1_state["evidence"][key] = {"bundle": result, "latest": latest_value(result)}
        record_step(scenario1_state, "search_observations", f"{label}; {reason}", result["results"])
        show_dataframe(f"{label} results", result["results"])

    elif choice == "6":
        reason = ask_why("Get medications")
        result = search_medications(patient_id)
        scenario1_state["evidence"]["medications"] = result["results"]
        record_step(scenario1_state, "search_medications", reason, result["results"])
        show_dataframe("Medications", result["results"])

    elif choice == "7":
        reason = ask_why("Get encounters")
        result = search_encounters(patient_id)
        scenario1_state["evidence"]["encounters"] = result["results"]
        record_step(scenario1_state, "search_encounters", reason, result["results"])
        show_dataframe("Encounters", result["results"])

    elif choice == "8":
        rationale = input("Why flag this patient for follow-up? ").strip()
        scenario1_state["patient_decisions"][patient_id] = {"label": "Flag", "rationale": rationale}
        scenario1_state["follow_up_list"].append({
            "patient_id": patient_id,
            "name": scenario1_state["patient_label"],
            "label": "Flag",
            "rationale": rationale,
        })
        record_step(scenario1_state, "Flag", rationale)
        print("Patient added to follow-up list.")

    elif choice == "9":
        rationale = input("Why is this patient not priority? ").strip()
        scenario1_state["patient_decisions"][patient_id] = {"label": "Do not flag", "rationale": rationale}
        record_step(scenario1_state, "Do not flag", rationale)
        print("Patient marked as not priority.")

    elif choice == "10":
        rationale = input("Why uncertain? ").strip()
        scenario1_state["patient_decisions"][patient_id] = {"label": "Uncertain", "rationale": rationale}
        record_step(scenario1_state, "Uncertain", rationale)
        print("Patient marked as uncertain.")

    elif choice == "11":
        reason = ask_why("Ask the LLM")
        suggestion = suggest_next_step(scenario1_state, follow_up_evidence_gaps, FOLLOW_UP_AGENT_INSTRUCTIONS)
        record_step(scenario1_state, "llm_coach", reason, suggestion)
        print()
        print("LLM suggestion:")
        print(suggestion)

    elif choice == "12":
        scenario1_state["final_answer"] = "Review complete"
        record_step(scenario1_state, "finish", "Review complete")
        print("Scenario 1 review complete.")

    else:
        print("Unknown choice. Try again.")
        return

    scenario1_show()
"""

SCENARIO1_LLM_MODE = """\
# ── Scenario 1: LLM mode ──
def scenario1_run_llm(candidate_number=1):
    match = [r for r in scenario1_candidates if r.get("candidate_number") == candidate_number]
    if not match:
        raise ValueError(f"Unknown candidate number: {candidate_number}")
    patient_row = match[0]
    question = (
        f"{SCENARIO1_PROMPT}\\n\\n"
        f"Review patient {patient_row['patient_id']} ({patient_row['name']}, age {patient_row['age']}). "
        "Use the available tools to gather evidence. "
        "Your final answer must be one of: Flag, Do not flag, or Uncertain / needs more review. "
        "Cite the evidence behind the recommendation."
    )
    print(f"Running autonomous agent for patient {patient_row['name']}...")
    result = run_agent(question, FOLLOW_UP_AGENT_INSTRUCTIONS, max_steps=8)
    print()
    print("Agent answer:")
    print(result["answer"])
    print()
    print("Tool call trace:")
    display(pd.DataFrame(result["tool_calls"]))
    return result


# Pick a candidate number from the table above:
# scenario1_llm_result = scenario1_run_llm(1)
"""

SCENARIO2_CANDIDATE_BUILDER = """\
# ── Scenario 2: Build young diabetes candidate table ──
def build_young_diabetes_candidate_table(max_age=35, per_group=3):
    rows = []
    seen = set()
    for label, code in [("Likely T1D seed", SNOMED["t1d"]), ("Likely T2D seed", SNOMED["t2d"])]:
        results = search_conditions(code, max_results=100)["results"]
        for item in results:
            patient_id = item.get("patient_reference", "").split("/")[-1]
            if not patient_id or patient_id in seen:
                continue
            patient = _safe_call({}, get_patient, patient_id)
            if not patient:
                continue
            age = patient.get("age")
            if age is None or age > max_age:
                continue
            rows.append({
                "patient_id": patient_id,
                "seed_group": label,
                "name": patient.get("name", ""),
                "age": age,
                "gender": patient.get("gender", ""),
                "birthDate": patient.get("birthDate", ""),
            })
            seen.add(patient_id)

    rows.sort(key=lambda r: (r["seed_group"], r["age"], r["name"]))
    selected = []
    counts = {}
    for row in rows:
        group = row["seed_group"]
        counts.setdefault(group, 0)
        if counts[group] >= per_group:
            continue
        counts[group] += 1
        selected.append(row)
    for i, row in enumerate(selected, start=1):
        row["case_number"] = i
    return selected


print("Building young diabetes candidate table...")
scenario2_candidates = build_young_diabetes_candidate_table(max_age=35, per_group=3)
print(f"Found {len(scenario2_candidates)} candidates")
display(pd.DataFrame(scenario2_candidates))
"""

SCENARIO2_HUMAN_MODE = """\
# ── Scenario 2: Human mode state and turn engine ──
scenario2_state = None


def scenario2_select_case(case_number):
    global scenario2_state
    match = [r for r in scenario2_candidates if r.get("case_number") == case_number]
    if not match:
        raise ValueError(f"Unknown case number: {case_number}")
    row = match[0]
    scenario2_state = {
        "question": (
            "Is this younger patient more consistent with Type 1 diabetes, "
            "Type 2 diabetes, or still unclear?"
        ),
        "patient_id": row["patient_id"],
        "patient_label": row["name"],
        "history": [],
        "evidence": {},
        "final_answer": None,
    }
    print(f"Selected case: {row['name']} ({row['patient_id']})")
    show_state(scenario2_state, type_clarification_evidence_gaps)


def scenario2_show():
    if scenario2_state is None:
        print("Run scenario2_select_case(case_number) first.")
        return
    show_state(scenario2_state, type_clarification_evidence_gaps)


def scenario2_human_turn():
    if scenario2_state is None:
        raise ValueError("Run scenario2_select_case(case_number) first.")
    patient_id = scenario2_state["patient_id"]

    print()
    print("Choose your next action:")
    print("  1. Get demographics")
    print("  2. Get full problem list")
    print("  3. Get labs")
    print("  4. Get medications")
    print("  5. Get encounters")
    print("  6. Ask the LLM what to do next")
    print("  7. Finish and answer")
    choice = input("Enter 1-7: ").strip()

    if choice == "1":
        reason = ask_why("Get demographics")
        result = get_patient(patient_id)
        scenario2_state["evidence"]["demographics"] = result
        record_step(scenario2_state, "get_patient", reason, result)
        show_dataframe("Demographics", [result])

    elif choice == "2":
        reason = ask_why("Get full problem list")
        result = search_all_conditions(patient_id)
        scenario2_state["evidence"]["conditions"] = result["results"]
        record_step(scenario2_state, "search_all_conditions", reason, result["results"])
        show_dataframe("Problem list", result["results"])

    elif choice == "3":
        label, code = choose_lab()
        reason = ask_why(f"Get lab: {label}")
        result = search_observations(patient_id, code)
        key = label.lower().replace("-", "_").replace(" ", "_")
        scenario2_state["evidence"][key] = {"bundle": result, "latest": latest_value(result)}
        record_step(scenario2_state, "search_observations", f"{label}; {reason}", result["results"])
        show_dataframe(f"{label} results", result["results"])

    elif choice == "4":
        reason = ask_why("Get medications")
        result = search_medications(patient_id)
        scenario2_state["evidence"]["medications"] = result["results"]
        record_step(scenario2_state, "search_medications", reason, result["results"])
        show_dataframe("Medications", result["results"])

    elif choice == "5":
        reason = ask_why("Get encounters")
        result = search_encounters(patient_id)
        scenario2_state["evidence"]["encounters"] = result["results"]
        record_step(scenario2_state, "search_encounters", reason, result["results"])
        show_dataframe("Encounters", result["results"])

    elif choice == "6":
        reason = ask_why("Ask the LLM")
        suggestion = suggest_next_step(scenario2_state, type_clarification_evidence_gaps, TYPE_CLARIFICATION_AGENT_INSTRUCTIONS)
        record_step(scenario2_state, "llm_coach", reason, suggestion)
        print()
        print("LLM suggestion:")
        print(suggestion)

    elif choice == "7":
        classification = input("Final answer? Enter 'Likely Type 1', 'Likely Type 2', or 'Unclear': ").strip()
        rationale = input("What evidence supports your answer? ").strip()
        scenario2_state["final_answer"] = {"classification": classification, "rationale": rationale}
        record_step(scenario2_state, "finish", classification, scenario2_state["final_answer"])
        print()
        print("Answer saved.")

    else:
        print("Unknown choice. Try again.")
        return

    scenario2_show()
"""

SCENARIO2_LLM_MODE = """\
# ── Scenario 2: LLM mode ──
def scenario2_run_llm(case_number=1):
    match = [r for r in scenario2_candidates if r.get("case_number") == case_number]
    if not match:
        raise ValueError(f"Unknown case number: {case_number}")
    patient_row = match[0]
    question = (
        f"Review patient {patient_row['patient_id']} ({patient_row['name']}, age {patient_row['age']}). "
        "Decide whether the case is more consistent with Type 1 diabetes, Type 2 diabetes, or still unclear. "
        "Use the available tools to gather supporting evidence and cite concrete findings in the final answer."
    )
    print(f"Running autonomous agent for case {patient_row['name']}...")
    result = run_agent(question, TYPE_CLARIFICATION_AGENT_INSTRUCTIONS, max_steps=8)
    print()
    print("Agent answer:")
    print(result["answer"])
    print()
    print("Tool call trace:")
    display(pd.DataFrame(result["tool_calls"]))
    return result


# Pick a case number from the table above:
# scenario2_llm_result = scenario2_run_llm(1)
"""

REPLAY_AND_COMPARISON = """\
# ── Replay and comparison ──
# After completing both human and LLM runs, compare them here.

def show_replay(state, label="Human"):
    print(f"=== {label} mode replay ===")
    if state is None:
        print("  No state recorded.")
        return
    print(f"  Steps taken: {len(state.get('history', []))}")
    if state.get("final_answer"):
        print(f"  Final answer: {state['final_answer']}")
    if state.get("history"):
        display(pd.DataFrame(state["history"]))


def compare_approaches(human_state, llm_result, scenario_label=""):
    print("=" * 72)
    print(f"Comparison: {scenario_label}")
    print("=" * 72)
    print()

    print("Human mode:")
    if human_state:
        print(f"  Steps: {len(human_state.get('history', []))}")
        print(f"  Evidence keys: {list(human_state.get('evidence', {}).keys())}")
        print(f"  Final answer: {human_state.get('final_answer', 'not recorded')}")
    else:
        print("  Not completed.")

    print()
    print("LLM mode:")
    if llm_result:
        print(f"  Tool calls: {len(llm_result.get('tool_calls', []))}")
        print(f"  Completed: {llm_result.get('completed', False)}")
        print(f"  Answer preview: {llm_result.get('answer', '')[:300]}")
    else:
        print("  Not completed.")

    print()
    print("Discussion prompts:")
    print("  - Did you and the LLM gather the same evidence?")
    print("  - Did you reach the same conclusion?")
    print("  - Where did your strategies diverge?")
    print("  - What would you do differently next time?")


# Example usage (uncomment after completing both modes):
# show_replay(scenario1_state, "Human")
# show_replay(scenario2_state, "Human")
# compare_approaches(scenario2_state, scenario2_llm_result, "Scenario 2: Type Clarification")
"""


def main() -> None:
    cells = [
        # ── 1. Title + Learning Arc ──
        md_cell(
            "# You Are the Agent: Clinical Data Review with FHIR and Claude\n\n"
            "## The \"You Are the Agent\" Pedagogy\n\n"
            "In a typical AI agent demo, you watch the LLM call tools and produce an answer. "
            "That is like watching someone else drive. In this notebook, **you drive first**.\n\n"
            "The learning arc has three modes:\n\n"
            "| Mode | Who decides what tool to call? | Who interprets the result? |\n"
            "|------|-------------------------------|---------------------------|\n"
            "| **Human** | You (the student) | You |\n"
            "| **Hybrid** | You, but you can ask the LLM for a suggestion | You |\n"
            "| **LLM** | The LLM (autonomous agent loop) | The LLM |\n\n"
            "By playing the role of the agent first, you develop intuition for:\n"
            "- What evidence is needed before making a clinical informatics decision\n"
            "- How FHIR queries map to the questions you want to answer\n"
            "- When you have gathered enough evidence to stop\n"
            "- How an LLM agent's strategy compares to your own\n\n"
            "## Two Scenarios\n\n"
            "1. **Scenario 1: Endocrine Follow-Up List Construction** -- "
            "Build a list of diabetes patients who should be prioritized for follow-up.\n"
            "2. **Scenario 2: Type 1 vs Type 2 Clarification** -- "
            "Review younger patients and decide whether the evidence supports T1D, T2D, or unclear."
        ),

        # ── 2. Setup Cell ──
        md_cell("## Setup\n\nInstall dependencies, connect to FHIR server, and initialize the Anthropic client."),
        code_cell(SETUP),

        # ── 3. FHIR Tool Functions ──
        md_cell(
            "## FHIR Tool Functions\n\n"
            "These functions query the synthetic FHIR server. Each one maps to a "
            "specific FHIR REST interaction. You will use these as the \"tools\" in "
            "both human mode (via the menu) and LLM mode (via the agent loop)."
        ),
        code_cell(FHIR_TOOLS),

        # ── 4. Claude Tool Schemas ──
        md_cell(
            "## Claude Tool Schemas\n\n"
            "These are the same functions described in the format that Claude's API expects. "
            "The `tools` list tells Claude what it can call, and `call_tool` dispatches the call."
        ),
        code_cell(CLAUDE_TOOL_SCHEMAS),

        # ── 5. State Management + Evidence Tracking ──
        md_cell(
            "## State Management and Evidence Tracking\n\n"
            "These helpers track what evidence you have collected, what is still missing, "
            "and the history of your steps. The `show_state` function gives you a dashboard view."
        ),
        code_cell(STATE_MANAGEMENT),

        # ── 6. LLM Coach + Agent Loop ──
        md_cell(
            "## LLM Coach and Agent Loop\n\n"
            "Two capabilities:\n"
            "- **`suggest_next_step`**: Asks Claude to recommend one next action (coaching mode, for Hybrid)\n"
            "- **`run_agent`**: Runs a full autonomous agent loop where Claude calls tools and produces a final answer (LLM mode)\n\n"
            "The agent loop follows the battle-tested pattern:\n"
            "- Client-side message history (no server-side state)\n"
            "- Serialize assistant content as dicts for message history\n"
            "- Tool results sent as user messages with `tool_result` blocks"
        ),
        code_cell(LLM_COACH_AND_AGENT),

        # ── 7. FHIR Query Mapping Table ──
        md_cell(
            "## FHIR Query Mapping Table\n\n"
            "This table makes the connection between the menu options you see in human mode "
            "and the actual FHIR REST queries being executed. The key distinction: "
            "`search_conditions` builds the candidate population (by diagnosis code), while "
            "`search_all_conditions` reviews one patient's full problem list."
        ),
        code_cell(FHIR_QUERY_MAP),

        # ── 8. Scenario 1: Follow-Up List Construction ──
        md_cell(
            "---\n"
            "# Scenario 1: Endocrine Follow-Up List Construction\n\n"
            "You are reviewing patients with diabetes who have recent encounters. "
            "Your goal is to identify which patients should be prioritized for endocrine "
            "follow-up based on evidence of poor control or diabetes-related complexity.\n\n"
            "The candidate pool is pre-built with a priority score based on HbA1c level, "
            "CKD presence, and insulin use. You will review individual patients."
        ),
        md_cell(
            "### Build the Candidate Pool\n\n"
            "This cell queries the FHIR server for diabetes patients and scores them. "
            "It may take a minute to run."
        ),
        code_cell(SCENARIO1_CANDIDATE_BUILDER),

        md_cell(
            "### Human Mode: Select a Patient and Start Reviewing\n\n"
            "1. Run the cell below to select a patient from the candidate table.\n"
            "2. Then run the turn engine cell repeatedly to gather evidence."
        ),
        code_cell(
            "# Pick a candidate number from the table above\n"
            "scenario1_select_patient(1)"
        ),
        md_cell(
            "### Human Mode: Take Turns as the Agent\n\n"
            "**Run this cell repeatedly.** Each time, choose what tool to use next.\n\n"
            "Recommended workflow:\n"
            "1. Get demographics\n"
            "2. Get the full problem list\n"
            "3. Get HbA1c\n"
            "4. Check medications\n"
            "5. Check encounters\n"
            "6. Decide: Flag, Do not flag, or Uncertain"
        ),
        code_cell(SCENARIO1_HUMAN_MODE + "\nscenario1_human_turn()"),

        md_cell(
            "### Hybrid Mode\n\n"
            "In Hybrid mode, you still drive, but you can ask Claude for a suggestion "
            "at any time by choosing option 11 in the menu above. The LLM sees your "
            "current evidence state and recommends one next action.\n\n"
            "This is the same menu -- just use option 11 when you want coaching."
        ),

        md_cell(
            "### LLM Mode: Let Claude Run Autonomously\n\n"
            "Now let Claude handle the same task. Compare its strategy and conclusion "
            "with your own."
        ),
        code_cell(SCENARIO1_LLM_MODE),

        # ── 9. Scenario 2: Type 1 vs Type 2 Clarification ──
        md_cell(
            "---\n"
            "# Scenario 2: Type 1 vs Type 2 Clarification\n\n"
            "You are reviewing younger patients (age <= 35) with diabetes. "
            "Diabetes type labels in the EHR may be incomplete or misleading. "
            "Your goal is to gather enough evidence to support a classification of "
            "**Type 1**, **Type 2**, or **Unclear**.\n\n"
            "Key evidence to look for:\n"
            "- **C-peptide** (direct evidence of insulin production)\n"
            "- **Medication pattern** (insulin-only vs oral agents)\n"
            "- **BMI** (insulin resistance context)\n"
            "- **Age of onset** and **diagnosis history**"
        ),
        md_cell(
            "### Build the Candidate Table\n\n"
            "This cell finds younger patients with T1D or T2D diagnoses."
        ),
        code_cell(SCENARIO2_CANDIDATE_BUILDER),

        md_cell(
            "### Human Mode: Select a Case and Start Reviewing"
        ),
        code_cell(
            "# Pick a case number from the table above\n"
            "scenario2_select_case(1)"
        ),
        md_cell(
            "### Human Mode: Take Turns as the Agent\n\n"
            "**Run this cell repeatedly.** Each time, choose what tool to use next.\n\n"
            "Recommended workflow:\n"
            "1. Get demographics\n"
            "2. Get the full problem list\n"
            "3. Get C-peptide (the most discriminating lab)\n"
            "4. Check medications\n"
            "5. Consider BMI for insulin-resistance context\n"
            "6. Decide: Likely Type 1, Likely Type 2, or Unclear"
        ),
        code_cell(SCENARIO2_HUMAN_MODE + "\nscenario2_human_turn()"),

        md_cell(
            "### LLM Mode: Let Claude Run Autonomously\n\n"
            "Now let Claude handle the same case. Compare its strategy and conclusion "
            "with your own."
        ),
        code_cell(SCENARIO2_LLM_MODE),

        # ── 10. Replay + Comparison ──
        md_cell(
            "---\n"
            "# Replay and Comparison\n\n"
            "After completing human and LLM runs for either scenario, use the cells "
            "below to compare approaches.\n\n"
            "Discussion questions:\n"
            "- Did you and the LLM gather the same evidence?\n"
            "- Did you reach the same conclusion?\n"
            "- Where did your strategies diverge?\n"
            "- What would you do differently next time?"
        ),
        code_cell(REPLAY_AND_COMPARISON),
    ]

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    nb = build_notebook(cells)
    OUTPUT_PATH.write_text(json.dumps(nb, indent=1) + "\n")
    print(f"Wrote {OUTPUT_PATH}")
    print(f"Total cells: {len(cells)}")


if __name__ == "__main__":
    main()
