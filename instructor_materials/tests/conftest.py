"""Shared fixtures and FHIR tool functions for all notebook tests."""

import os
import json
import time
import pytest
import requests

FHIR_BASE = "https://launch.smarthealthit.org/v/r4/fhir"
MODEL = "claude-sonnet-4-20250514"

# Retry settings for the public FHIR test server (intermittent 500/502 errors)
MAX_RETRIES = 3
RETRY_DELAY = 5  # seconds


# ---------------------------------------------------------------------------
# Pytest markers and skip logic
# ---------------------------------------------------------------------------

def pytest_configure(config):
    config.addinivalue_line("markers", "requires_api_key: test needs ANTHROPIC_API_KEY")


def pytest_collection_modifyitems(config, items):
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        skip_api = pytest.mark.skip(reason="ANTHROPIC_API_KEY not set")
        for item in items:
            if "requires_api_key" in item.keywords:
                item.add_marker(skip_api)


# ---------------------------------------------------------------------------
# Retry-capable HTTP helper (public FHIR servers have intermittent outages)
# ---------------------------------------------------------------------------

def fhir_get(url, params=None, timeout=15):
    """GET with retries for transient FHIR server errors."""
    for attempt in range(MAX_RETRIES):
        resp = requests.get(url, params=params, timeout=timeout)
        if resp.status_code < 500:
            return resp
        if attempt < MAX_RETRIES - 1:
            time.sleep(RETRY_DELAY)
    return resp  # return last response even if still failing


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def fhir_base():
    return FHIR_BASE


@pytest.fixture(scope="session")
def anthropic_client():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        pytest.skip("ANTHROPIC_API_KEY not set")
    from anthropic import Anthropic
    return Anthropic(api_key=api_key)


# ---------------------------------------------------------------------------
# FHIR tool functions (shared across sessions 1-3)
# ---------------------------------------------------------------------------

def search_conditions(code: str, max_results: int = 20) -> dict:
    """Search for Condition resources by diagnosis code (SNOMED CT or ICD-10)."""
    resp = fhir_get(f"{FHIR_BASE}/Condition",
        params={"code": code, "_count": max_results, "_format": "json"})
    resp.raise_for_status()
    bundle = resp.json()
    results = []
    for entry in bundle.get("entry", []):
        r = entry["resource"]
        coding = r.get("code", {}).get("coding", [{}])[0]
        results.append({
            "condition_id": r.get("id", ""),
            "patient_reference": r.get("subject", {}).get("reference", ""),
            "code": coding.get("code", ""),
            "code_display": coding.get("display", ""),
            "onset": r.get("onsetDateTime", "unknown")
        })
    return {"total": bundle.get("total", len(results)), "results": results}


def get_patient(patient_id: str) -> dict:
    """Retrieve a single Patient resource by FHIR ID. Returns demographics."""
    resp = fhir_get(f"{FHIR_BASE}/Patient/{patient_id}",
        params={"_format": "json"})
    resp.raise_for_status()
    p = resp.json()
    name = p.get("name", [{}])[0]
    return {
        "id": p.get("id", patient_id),
        "name": f"{' '.join(name.get('given', []))} {name.get('family', '')}".strip(),
        "birthDate": p.get("birthDate", "unknown"),
        "gender": p.get("gender", "unknown")
    }


def search_observations(patient_id: str, loinc_code: str, max_results: int = 5) -> dict:
    """Search Observations for a patient by LOINC code. Most recent first."""
    resp = fhir_get(f"{FHIR_BASE}/Observation",
        params={
            "subject": f"Patient/{patient_id}",
            "code": loinc_code,
            "_sort": "-date",
            "_count": max_results,
            "_format": "json"
        })
    resp.raise_for_status()
    bundle = resp.json()
    results = []
    for entry in bundle.get("entry", []):
        r = entry["resource"]
        value_qty = r.get("valueQuantity", {})
        results.append({
            "date": r.get("effectiveDateTime", "unknown"),
            "value": value_qty.get("value", "N/A"),
            "unit": value_qty.get("unit", "")
        })
    return {"patient_id": patient_id, "loinc_code": loinc_code, "results": results}


def search_medications(patient_id: str, max_results: int = 10) -> dict:
    """Search MedicationRequest resources for a patient."""
    resp = fhir_get(f"{FHIR_BASE}/MedicationRequest",
        params={"subject": f"Patient/{patient_id}", "_count": max_results,
                "_sort": "-date", "_format": "json"})
    resp.raise_for_status()
    bundle = resp.json()
    results = []
    for entry in bundle.get("entry", []):
        r = entry["resource"]
        med = r.get("medicationCodeableConcept", {}).get("coding", [{}])[0]
        results.append({
            "medication": med.get("display", "unknown"),
            "code": med.get("code", ""),
            "status": r.get("status", "unknown"),
            "authored_on": r.get("authoredOn", "unknown")
        })
    return {"patient_id": patient_id, "results": results}


def search_encounters(patient_id: str, max_results: int = 10) -> dict:
    """Search Encounter resources for a patient."""
    resp = fhir_get(f"{FHIR_BASE}/Encounter",
        params={"subject": f"Patient/{patient_id}", "_count": max_results,
                "_sort": "-date", "_format": "json"})
    resp.raise_for_status()
    bundle = resp.json()
    results = []
    for entry in bundle.get("entry", []):
        r = entry["resource"]
        enc_type = r.get("type", [{}])[0].get("coding", [{}])[0]
        period = r.get("period", {})
        results.append({
            "encounter_type": enc_type.get("display", "unknown"),
            "class": r.get("class", {}).get("code", "unknown"),
            "status": r.get("status", "unknown"),
            "period_start": period.get("start", "unknown"),
            "period_end": period.get("end", "unknown")
        })
    return {"patient_id": patient_id, "results": results}


def search_all_conditions(patient_id: str, max_results: int = 20) -> dict:
    """Search for ALL Condition resources for a patient (full problem list)."""
    resp = fhir_get(f"{FHIR_BASE}/Condition",
        params={"subject": f"Patient/{patient_id}", "_count": max_results,
                "_format": "json"})
    resp.raise_for_status()
    bundle = resp.json()
    results = []
    for entry in bundle.get("entry", []):
        r = entry["resource"]
        coding = r.get("code", {}).get("coding", [{}])[0]
        clinical_status = r.get("clinicalStatus", {}).get("coding", [{}])[0]
        results.append({
            "condition": coding.get("display", "unknown"),
            "code": coding.get("code", ""),
            "system": coding.get("system", ""),
            "onset": r.get("onsetDateTime", "unknown"),
            "clinical_status": clinical_status.get("code", "unknown")
        })
    return {"patient_id": patient_id, "results": results}


# ---------------------------------------------------------------------------
# Tool schema definitions (Anthropic native format)
# ---------------------------------------------------------------------------

SESSION2_TOOLS = [
    {
        "name": "search_conditions",
        "description": "Search for patient Condition resources on the FHIR server by diagnosis code (SNOMED CT or ICD-10). Returns a list of conditions with patient references, codes, and onset dates. Use this to find patients with a specific diagnosis.",
        "input_schema": {
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "Diagnosis code. Examples: '44054006' for Type 2 diabetes (SNOMED CT), '59621000' for hypertension (SNOMED CT)."},
                "max_results": {"type": "integer", "description": "Maximum number of results. Default 20.", "default": 20}
            },
            "required": ["code"]
        }
    },
    {
        "name": "get_patient",
        "description": "Retrieve a single Patient resource by their FHIR patient ID. Returns demographics including full name, birth date, and gender. Use this after getting a patient reference from another resource.",
        "input_schema": {
            "type": "object",
            "properties": {
                "patient_id": {"type": "string", "description": "The FHIR Patient resource ID (the part after 'Patient/' in a reference)."}
            },
            "required": ["patient_id"]
        }
    },
    {
        "name": "search_observations",
        "description": "Search for Observation resources (lab results, vital signs) for a specific patient by LOINC code. Returns values sorted by date with most recent first. Common LOINC codes: '4548-4' for HbA1c, '85354-9' for blood pressure, '2160-0' for creatinine.",
        "input_schema": {
            "type": "object",
            "properties": {
                "patient_id": {"type": "string", "description": "The FHIR Patient ID to search observations for"},
                "loinc_code": {"type": "string", "description": "LOINC code for the observation type. Examples: '4548-4' (HbA1c), '85354-9' (blood pressure), '2160-0' (creatinine)"},
                "max_results": {"type": "integer", "description": "Maximum results to return. Default 5.", "default": 5}
            },
            "required": ["patient_id", "loinc_code"]
        }
    }
]

SESSION2_FUNCTIONS = {
    "search_conditions": search_conditions,
    "get_patient": get_patient,
    "search_observations": search_observations,
}

SESSION3_TOOLS = SESSION2_TOOLS + [
    {
        "name": "search_medications",
        "description": "Search for MedicationRequest resources for a patient. Returns medication names, codes, statuses, and dates. Use this to find what medications a patient has been prescribed.",
        "input_schema": {
            "type": "object",
            "properties": {
                "patient_id": {"type": "string", "description": "The FHIR Patient ID"},
                "max_results": {"type": "integer", "description": "Maximum results. Default 10.", "default": 10}
            },
            "required": ["patient_id"]
        }
    },
    {
        "name": "search_encounters",
        "description": "Search for Encounter resources (office visits, emergency visits, hospitalizations) for a patient. Returns encounter types, dates, and statuses. Use this to understand a patient's visit history.",
        "input_schema": {
            "type": "object",
            "properties": {
                "patient_id": {"type": "string", "description": "The FHIR Patient ID"},
                "max_results": {"type": "integer", "description": "Maximum results. Default 10.", "default": 10}
            },
            "required": ["patient_id"]
        }
    },
    {
        "name": "search_all_conditions",
        "description": "Search for ALL Condition resources for a specific patient (their complete problem list). Returns condition names, codes, onset dates, and clinical status. Use this to get a patient's full medical history of diagnoses.",
        "input_schema": {
            "type": "object",
            "properties": {
                "patient_id": {"type": "string", "description": "The FHIR Patient ID"},
                "max_results": {"type": "integer", "description": "Maximum results. Default 20.", "default": 20}
            },
            "required": ["patient_id"]
        }
    }
]

SESSION3_FUNCTIONS = {
    **SESSION2_FUNCTIONS,
    "search_medications": search_medications,
    "search_encounters": search_encounters,
    "search_all_conditions": search_all_conditions,
}

SYSTEM_PROMPT = """You are a clinical data assistant with access to a FHIR server
containing synthetic patient data.

When asked a clinical question, use the available tools to query the FHIR server
and build up the data needed to answer. Think step by step:

1. First, identify what diagnosis or condition is relevant and search for it
2. Extract patient references from the conditions found
3. Retrieve patient demographics (name, birthdate, gender) for each patient
4. Look up relevant observations (lab values, vitals) for each patient
5. Synthesize a clear, accurate summary based ONLY on the data you retrieved

Rules:
- NEVER invent or assume data that was not returned by a tool call
- If a query returns no results, state that explicitly
- Always identify patients by name when demographics are available
- When comparing values to clinical thresholds, show the actual values
- Be concise but thorough — include all relevant findings"""


# ---------------------------------------------------------------------------
# Agent loop helper (used by session 2 and 3 tests)
# ---------------------------------------------------------------------------

def run_agent(client, question, tools, available_functions,
              system_prompt=SYSTEM_PROMPT, max_steps=15):
    """Run the tool-use agent loop. Returns (final_answer, tool_calls_log)."""
    tool_calls_log = []
    step = 0
    messages = [{"role": "user", "content": question}]

    while step < max_steps:
        step += 1

        response = client.messages.create(
            model=MODEL,
            max_tokens=4096,
            system=system_prompt,
            tools=tools,
            messages=messages
        )

        tool_use_blocks = [b for b in response.content if b.type == "tool_use"]
        text_blocks = [b for b in response.content if b.type == "text"]

        if not tool_use_blocks:
            final = "\n".join(b.text for b in text_blocks)
            return final, tool_calls_log

        # Serialize content blocks to avoid Pydantic SDK issues
        assistant_content = []
        for block in response.content:
            if block.type == "text":
                assistant_content.append({"type": "text", "text": block.text})
            elif block.type == "tool_use":
                assistant_content.append({
                    "type": "tool_use",
                    "id": block.id,
                    "name": block.name,
                    "input": block.input
                })

        messages.append({"role": "assistant", "content": assistant_content})
        tool_results = []

        for block in tool_use_blocks:
            fn_name = block.name
            fn_args = block.input
            tool_calls_log.append({
                "step": step,
                "function": fn_name,
                "arguments": fn_args
            })

            try:
                result = available_functions[fn_name](**fn_args)
                result_str = json.dumps(result, default=str)
            except Exception as e:
                result_str = json.dumps({"error": str(e)})

            tool_results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": result_str
            })

        messages.append({"role": "user", "content": tool_results})

    return "Max steps reached without final answer", tool_calls_log
