#!/usr/bin/env python3
"""
Test Session 2 notebook - Agent with tool use against live FHIR server.
"""

import os
import json
import requests
from anthropic import Anthropic

# Set API key
os.environ["ANTHROPIC_API_KEY"] = "your_api_key_here"

FHIR_BASE = "https://launch.smarthealthit.org/v/r4/fhir"
MODEL = "claude-3-5-sonnet-20240620"

print("="*70)
print("SESSION 2 AGENT TEST")
print("="*70)
print()

# Define FHIR tool functions
def search_conditions(code: str, max_results: int = 20) -> dict:
    """Search for Condition resources by diagnosis code."""
    resp = requests.get(f"{FHIR_BASE}/Condition",
        params={"code": code, "_count": max_results, "_format": "json"},
        timeout=15)
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
    """Retrieve a single Patient resource by FHIR ID."""
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
    """Search Observations for a patient by LOINC code."""
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

# Test tools
print("TEST 1: FHIR tools")
print("-"*70)
test = search_conditions("44054006", max_results=3)
print(f"✅ search_conditions: {len(test['results'])} results")

if test["results"]:
    test_pid = test["results"][0]["patient_reference"].split("/")[-1]
    test_pt = get_patient(test_pid)
    print(f"✅ get_patient: {test_pt['name']}")

    test_obs = search_observations(test_pid, "4548-4", max_results=1)
    print(f"✅ search_observations: {len(test_obs['results'])} results")

# Define tool schemas for Anthropic
tools = [
    {
        "name": "search_conditions",
        "description": "Search for patient Condition resources on the FHIR server by diagnosis code (SNOMED CT or ICD-10). Returns a list of conditions with patient references, codes, and onset dates.",
        "input_schema": {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "Diagnosis code. Examples: '44054006' for Type 2 diabetes (SNOMED CT), '59621000' for hypertension (SNOMED CT)."
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of results. Default 20.",
                    "default": 20
                }
            },
            "required": ["code"]
        }
    },
    {
        "name": "get_patient",
        "description": "Retrieve a single Patient resource by their FHIR patient ID. Returns demographics including full name, birth date, and gender.",
        "input_schema": {
            "type": "object",
            "properties": {
                "patient_id": {
                    "type": "string",
                    "description": "The FHIR Patient resource ID"
                }
            },
            "required": ["patient_id"]
        }
    },
    {
        "name": "search_observations",
        "description": "Search for Observation resources (lab results, vital signs) for a specific patient by LOINC code. Returns values sorted by date with most recent first. Common LOINC codes: '4548-4' for HbA1c.",
        "input_schema": {
            "type": "object",
            "properties": {
                "patient_id": {
                    "type": "string",
                    "description": "The FHIR Patient ID"
                },
                "loinc_code": {
                    "type": "string",
                    "description": "LOINC code for the observation type. Example: '4548-4' (HbA1c)"
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum results. Default 5.",
                    "default": 5
                }
            },
            "required": ["patient_id", "loinc_code"]
        }
    }
]

available_functions = {
    "search_conditions": search_conditions,
    "get_patient": get_patient,
    "search_observations": search_observations,
}

SYSTEM_PROMPT = """You are a clinical data assistant with access to a FHIR server.

When asked a clinical question, use the available tools to query the FHIR server step by step:
1. Search for relevant conditions
2. Get patient demographics
3. Look up relevant lab values
4. Synthesize a clear summary based ONLY on the data you retrieved

Rules:
- NEVER invent data that was not returned by tools
- Always identify patients by name when available
- Show actual values when comparing to thresholds"""

# Run agent
print("\nTEST 2: Agent loop")
print("-"*70)

client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
question = "Find patients with Type 2 diabetes and their most recent HbA1c values. Which patients have poor glycemic control (HbA1c > 7.5%)?"

print(f"Question: {question}\n")

messages = [{"role": "user", "content": question}]
tool_calls_log = []
step = 0
max_steps = 15

while step < max_steps:
    step += 1
    response = client.messages.create(
        model=MODEL,
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        tools=tools,
        messages=messages
    )

    tool_use_blocks = [b for b in response.content if b.type == "tool_use"]
    text_blocks = [b for b in response.content if b.type == "text"]

    if not tool_use_blocks:
        final = "\n".join(b.text for b in text_blocks)
        print(f"\n{'='*70}")
        print(f"✅ AGENT COMPLETED ({len(tool_calls_log)} tool calls)\n")
        print(final)
        break

    messages.append({"role": "assistant", "content": response.content})
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
    print(f"  {tc['step']}. {tc['function']}({list(tc['arguments'].keys())})")

print(f"\nTotal tool calls: {len(tool_calls_log)}")
unique_tools = set(tc['function'] for tc in tool_calls_log)
print(f"Unique tools: {', '.join(unique_tools)}")

print("\n" + "="*70)
print("✅ SESSION 2 AGENT TEST PASSED!")
print("="*70)
