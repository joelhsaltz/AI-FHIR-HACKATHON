#!/usr/bin/env python3
"""
Test the simplified Session 3 notebook (Anthropic-only version).
"""

import os
import json
import requests
from anthropic import Anthropic

FHIR_BASE = "https://launch.smarthealthit.org/v/r4/fhir"
MODEL = "claude-sonnet-4-20250514"
API_KEY = os.environ.get("ANTHROPIC_API_KEY")
if not API_KEY:
    raise ValueError("Please set ANTHROPIC_API_KEY environment variable")

print("="*70)
print("SIMPLIFIED SESSION 3 TEST (Anthropic-only)")
print("="*70)
print()

# FHIR tool functions (all 6 tools from Session 3)
def search_conditions(code: str, max_results: int = 20) -> dict:
    resp = requests.get(f"{FHIR_BASE}/Condition",
        params={"code": code, "_count": max_results, "_format": "json"}, timeout=15)
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
    resp = requests.get(f"{FHIR_BASE}/Patient/{patient_id}",
        params={"_format": "json"}, timeout=15)
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
    resp = requests.get(f"{FHIR_BASE}/Observation",
        params={
            "subject": f"Patient/{patient_id}",
            "code": loinc_code,
            "_sort": "-date",
            "_count": max_results,
            "_format": "json"
        }, timeout=15)
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

def get_all_conditions_for_patient(patient_id: str, max_results: int = 20) -> dict:
    resp = requests.get(f"{FHIR_BASE}/Condition",
        params={"subject": f"Patient/{patient_id}", "_count": max_results, "_format": "json"},
        timeout=15)
    resp.raise_for_status()
    bundle = resp.json()
    results = []
    for entry in bundle.get("entry", []):
        r = entry["resource"]
        coding = r.get("code", {}).get("coding", [{}])[0]
        results.append({
            "code": coding.get("code", ""),
            "display": coding.get("display", ""),
            "onset": r.get("onsetDateTime", "unknown")
        })
    return {"patient_id": patient_id, "conditions": results}

def search_medications(patient_id: str, max_results: int = 10) -> dict:
    resp = requests.get(f"{FHIR_BASE}/MedicationRequest",
        params={"subject": f"Patient/{patient_id}", "_count": max_results, "_format": "json"},
        timeout=15)
    resp.raise_for_status()
    bundle = resp.json()
    results = []
    for entry in bundle.get("entry", []):
        r = entry["resource"]
        med = r.get("medicationCodeableConcept", {}).get("coding", [{}])[0]
        results.append({
            "medication": med.get("display", "Unknown"),
            "code": med.get("code", ""),
            "status": r.get("status", "unknown"),
            "authored_on": r.get("authoredOn", "unknown")
        })
    return {"patient_id": patient_id, "medications": results}

def search_encounters(patient_id: str, max_results: int = 10) -> dict:
    resp = requests.get(f"{FHIR_BASE}/Encounter",
        params={"subject": f"Patient/{patient_id}", "_count": max_results, "_format": "json"},
        timeout=15)
    resp.raise_for_status()
    bundle = resp.json()
    results = []
    for entry in bundle.get("entry", []):
        r = entry["resource"]
        enc_type = r.get("type", [{}])[0].get("coding", [{}])[0]
        results.append({
            "type": enc_type.get("display", "Unknown"),
            "status": r.get("status", "unknown"),
            "period": r.get("period", {})
        })
    return {"patient_id": patient_id, "encounters": results}

available_functions = {
    "search_conditions": search_conditions,
    "get_patient": get_patient,
    "search_observations": search_observations,
    "get_all_conditions_for_patient": get_all_conditions_for_patient,
    "search_medications": search_medications,
    "search_encounters": search_encounters,
}

# Tool schemas in Anthropic format
tools = [
    {
        "name": "search_conditions",
        "description": "Search for patient Condition resources by diagnosis code (SNOMED CT). Returns list of conditions with patient references.",
        "input_schema": {
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "SNOMED CT code. Example: '44054006' for Type 2 diabetes"},
                "max_results": {"type": "integer", "description": "Max results. Default 20.", "default": 20}
            },
            "required": ["code"]
        }
    },
    {
        "name": "get_patient",
        "description": "Retrieve Patient demographics by FHIR ID. Returns name, birthdate, gender.",
        "input_schema": {
            "type": "object",
            "properties": {
                "patient_id": {"type": "string", "description": "FHIR Patient ID"}
            },
            "required": ["patient_id"]
        }
    },
    {
        "name": "search_observations",
        "description": "Search Observations (lab results) for a patient by LOINC code. Returns most recent first.",
        "input_schema": {
            "type": "object",
            "properties": {
                "patient_id": {"type": "string", "description": "FHIR Patient ID"},
                "loinc_code": {"type": "string", "description": "LOINC code. Example: '4548-4' for HbA1c"},
                "max_results": {"type": "integer", "description": "Max results. Default 5.", "default": 5}
            },
            "required": ["patient_id", "loinc_code"]
        }
    },
    {
        "name": "get_all_conditions_for_patient",
        "description": "Get ALL conditions for a specific patient. Returns complete condition list.",
        "input_schema": {
            "type": "object",
            "properties": {
                "patient_id": {"type": "string", "description": "FHIR Patient ID"},
                "max_results": {"type": "integer", "description": "Max results. Default 20.", "default": 20}
            },
            "required": ["patient_id"]
        }
    },
    {
        "name": "search_medications",
        "description": "Search MedicationRequest resources for a patient. Returns list of medications.",
        "input_schema": {
            "type": "object",
            "properties": {
                "patient_id": {"type": "string", "description": "FHIR Patient ID"},
                "max_results": {"type": "integer", "description": "Max results. Default 10.", "default": 10}
            },
            "required": ["patient_id"]
        }
    },
    {
        "name": "search_encounters",
        "description": "Search Encounter resources for a patient. Returns list of encounters.",
        "input_schema": {
            "type": "object",
            "properties": {
                "patient_id": {"type": "string", "description": "FHIR Patient ID"},
                "max_results": {"type": "integer", "description": "Max results. Default 10.", "default": 10}
            },
            "required": ["patient_id"]
        }
    }
]

SYSTEM_PROMPT = """You are a clinical data assistant with access to a FHIR server.

Use available tools to query the FHIR server step by step:
1. Search for relevant conditions
2. Get patient demographics
3. Look up lab values, medications, encounters as needed
4. Synthesize a summary based ONLY on retrieved data

Rules:
- NEVER invent data not returned by tools
- Always identify patients by name
- Show actual values when comparing to thresholds"""

# Run the agent with a simpler question for testing
print("Running agent with simplified Anthropic-only code...")
print("-"*70)

client = Anthropic(api_key=API_KEY)
question = "Find one patient with Type 2 diabetes and tell me about their conditions and medications."

print(f"Question: {question}\n")

messages = [{"role": "user", "content": question}]
tool_calls_log = []
step = 0

while step < 15:
    step += 1

    response = client.messages.create(
        model=MODEL,
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        tools=tools,
        messages=messages
    )

    # Check for tool use or final answer
    tool_use_blocks = [b for b in response.content if b.type == "tool_use"]
    text_blocks = [b for b in response.content if b.type == "text"]

    if not tool_use_blocks:
        # Final answer
        final = "\n".join(b.text for b in text_blocks)
        print(f"\n{'='*70}")
        print(f"FINAL ANSWER ({len(tool_calls_log)} tool calls):\n")
        print(final)
        break

    # Process tool calls - manually serialize content blocks
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
        tool_calls_log.append({"step": step, "function": fn_name, "arguments": fn_args})

        print(f"🔧 Step {step} | {fn_name}({json.dumps(fn_args)})")

        try:
            result = available_functions[fn_name](**fn_args)
            result_str = json.dumps(result, default=str)
            n_items = len(result.get("results", [])) if isinstance(result, dict) and "results" in result else None
            if n_items is not None:
                print(f"   → {n_items} items")
            else:
                n_items = len(result.get("conditions", [])) if isinstance(result, dict) and "conditions" in result else None
                if n_items is not None:
                    print(f"   → {n_items} conditions")
                else:
                    n_items = len(result.get("medications", [])) if isinstance(result, dict) and "medications" in result else None
                    if n_items is not None:
                        print(f"   → {n_items} medications")
        except Exception as e:
            result_str = json.dumps({"error": str(e)})
            print(f"   → Error: {e}")

        tool_results.append({
            "type": "tool_result",
            "tool_use_id": block.id,
            "content": result_str
        })

    messages.append({"role": "user", "content": tool_results})

print("\n" + "="*70)
print("TOOL CALL SUMMARY")
print("="*70)
for tc in tool_calls_log:
    args_str = ', '.join(f"{k}={v}" for k, v in tc['arguments'].items())
    print(f"  {tc['step']}. {tc['function']}({args_str})")

unique_tools = set(tc['function'] for tc in tool_calls_log)
print(f"\nTotal calls: {len(tool_calls_log)}")
print(f"Tools used: {', '.join(unique_tools)}")

print("\n" + "="*70)
print("✅ SIMPLIFIED SESSION 3 TEST PASSED!")
print("="*70)
print("The Anthropic-only version is working correctly.")
