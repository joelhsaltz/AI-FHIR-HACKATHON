#!/usr/bin/env python3
"""
Generate a prototype notebook for the redesigned Session 2:
"You Are the Agent" for diabetes type clarification in younger patients.
"""

import json
import os
import uuid


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_PATH = os.path.join(
    SCRIPT_DIR,
    "prototypes",
    "session2_you_are_the_agent_type_clarification_prototype.ipynb",
)


def _id():
    return uuid.uuid4().hex[:8]


def md_cell(source):
    return {
        "cell_type": "markdown",
        "id": _id(),
        "metadata": {},
        "source": source,
    }


def code_cell(source):
    return {
        "cell_type": "code",
        "id": _id(),
        "metadata": {},
        "source": source,
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
        },
        "cells": cells,
    }


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

FHIR_BASE = "https://lfh-fhir.eastus2.cloudapp.azure.com:9443/fhir-server/api/v4"
FHIR_SESSION = requests.Session()
FHIR_SESSION.auth = ("fhiruser", "BmI512@ccess")
FHIR_SESSION.verify = False

try:
    from google.colab import userdata
    ANTHROPIC_API_KEY = userdata.get("ANTHROPIC_API_KEY")
except Exception:
    ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")

try:
    from anthropic import Anthropic
except Exception:
    Anthropic = None

client = Anthropic(api_key=ANTHROPIC_API_KEY) if (Anthropic and ANTHROPIC_API_KEY) else None
MODEL = "claude-sonnet-4-20250514"

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
print(f"Anthropic helper: {'enabled' if client else 'disabled'}")
"""


TOOLS = """\
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


def compute_age(birth_date):
    if not birth_date:
        return None
    born = datetime.strptime(birth_date, "%Y-%m-%d").date()
    today = date.today()
    return today.year - born.year - ((today.month, today.day) < (born.month, born.day))


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
        rows.append(
            {
                "condition_id": resource.get("id"),
                "code": coding.get("code", ""),
                "display": coding.get("display", ""),
                "patient_reference": resource.get("subject", {}).get("reference", ""),
                "clinical_status": resource.get("clinicalStatus", {})
                .get("coding", [{}])[0]
                .get("code", ""),
            }
        )
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
        rows.append(
            {
                "display": coding.get("display", ""),
                "code": coding.get("code", ""),
                "value": value_qty.get("value"),
                "unit": value_qty.get("unit", ""),
                "date": resource.get("effectiveDateTime", ""),
            }
        )
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
        rows.append(
            {
                "medication": coding.get("display") or med_concept.get("text", "unknown"),
                "code": coding.get("code", ""),
                "status": resource.get("status", ""),
                "authoredOn": resource.get("authoredOn", ""),
            }
        )
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
        rows.append(
            {
                "condition": coding.get("display", ""),
                "code": coding.get("code", ""),
                "clinical_status": resource.get("clinicalStatus", {})
                .get("coding", [{}])[0]
                .get("code", ""),
            }
        )
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
        rows.append(
            {
                "status": resource.get("status", ""),
                "class": resource.get("class", {}).get("code", ""),
                "type": enc_type,
                "period_start": resource.get("period", {}).get("start", ""),
            }
        )
    return {"total": bundle.get("total", 0), "results": rows}


print("Tool layer loaded")
"""


CASE_BUILDERS = """\
def build_young_diabetes_candidate_table(max_age=35, per_group=4):
    rows = []
    seen = set()
    for label, code in [("Likely T1D cohort", SNOMED["t1d"]), ("Likely T2D cohort", SNOMED["t2d"])]:
        results = search_conditions(code, max_results=80)["results"]
        for item in results:
            patient_id = item["patient_reference"].split("/")[-1]
            if patient_id in seen:
                continue
            patient = get_patient(patient_id)
            age = patient.get("age")
            if age is None or age > max_age:
                continue
            rows.append(
                {
                    "patient_id": patient_id,
                    "seed_group": label,
                    "name": patient.get("name", ""),
                    "age": age,
                    "gender": patient.get("gender", ""),
                    "birthDate": patient.get("birthDate", ""),
                }
            )
            seen.add(patient_id)

    df = pd.DataFrame(rows)
    if df.empty:
        raise ValueError("No candidate patients found with this age threshold.")

    df = df.sort_values(["age", "seed_group", "name"]).reset_index(drop=True)
    picked = []
    for group in df["seed_group"].unique():
        picked.append(df[df["seed_group"] == group].head(per_group))
    out = pd.concat(picked, ignore_index=True)
    out.insert(0, "case_number", range(1, len(out) + 1))
    return out


def initialize_case(candidate_row):
    return {
        "question": (
            "Is this patient more consistent with Type 1 diabetes, "
            "Type 2 diabetes, or still unclear?"
        ),
        "patient_id": candidate_row["patient_id"],
        "patient_label": candidate_row["name"],
        "history": [],
        "evidence": {},
        "final_answer": None,
    }


candidate_df = build_young_diabetes_candidate_table(max_age=35, per_group=3)
display(candidate_df)
"""


STATE_HELPERS = """\
def record_step(state, tool_name, note, payload=None):
    state["history"].append(
        {
            "step": len(state["history"]) + 1,
            "tool": tool_name,
            "note": note,
            "payload": payload,
        }
    )


def evidence_gaps(state):
    gaps = []
    if "demographics" not in state["evidence"]:
        gaps.append("basic demographics")
    if "conditions" not in state["evidence"]:
        gaps.append("problem list / diagnosis context")
    if "c_peptide" not in state["evidence"]:
        gaps.append("C-peptide")
    if "medications" not in state["evidence"]:
        gaps.append("medication pattern")
    if "bmi" not in state["evidence"]:
        gaps.append("BMI / insulin-resistance pattern")
    return gaps


def latest_value(observation_bundle):
    results = observation_bundle.get("results", [])
    if not results:
        return None
    return results[0]


def show_state(state):
    print("=" * 72)
    print("YOU ARE THE AGENT")
    print("=" * 72)
    print(f"Question: {state['question']}")
    print(f"Patient: {state['patient_label']} ({state['patient_id']})")
    print()

    print("Evidence collected so far:")
    if not state["evidence"]:
        print("  None yet")
    else:
        for key, value in state["evidence"].items():
            if key == "demographics":
                print(
                    f"  demographics: age {value.get('age')}, "
                    f"{value.get('gender')}, birthDate {value.get('birthDate')}"
                )
            elif key == "conditions":
                names = [row["condition"] for row in value[:5]]
                print(f"  conditions: {', '.join(names) if names else 'none found'}")
            elif key == "medications":
                meds = [row["medication"] for row in value[:5]]
                print(f"  medications: {', '.join(meds) if meds else 'none found'}")
            else:
                latest = value.get("latest")
                if latest:
                    print(
                        f"  {key}: {latest.get('value')} {latest.get('unit', '')} "
                        f"on {latest.get('date', '')}"
                    )
                else:
                    print(f"  {key}: no result found")

    print()
    print("Evidence still missing:")
    missing = evidence_gaps(state)
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


def choose_case(case_number):
    row = candidate_df[candidate_df["case_number"] == case_number]
    if row.empty:
        raise ValueError("Unknown case number")
    return initialize_case(row.iloc[0].to_dict())
"""


TURN_ENGINE = """\
def run_menu():
    print()
    print("Choose your next action:")
    print("  1. Get demographics")
    print("  2. Get full problem list")
    print("  3. Get labs")
    print("  4. Get medications")
    print("  5. Get encounters")
    print("  6. Ask the LLM what to do next")
    print("  7. Finish and answer")
    return input("Enter 1-7: ").strip()


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
    reason = input(
        f"Why are you choosing '{action_name}' now? "
        "(short note, or press Enter to skip): "
    ).strip()
    return reason or "no note entered"


def show_dataframe(title, rows):
    print()
    print(title)
    if not rows:
        print("  No rows found")
        return
    display(pd.DataFrame(rows))


def run_human_turn(state):
    choice = run_menu()
    patient_id = state["patient_id"]

    if choice == "1":
        reason = ask_why("Get demographics")
        result = get_patient(patient_id)
        state["evidence"]["demographics"] = result
        record_step(state, "get_patient", reason, result)
        show_dataframe("Demographics", [result])
        return state

    if choice == "2":
        reason = ask_why("Get full problem list")
        result = search_all_conditions(patient_id)
        state["evidence"]["conditions"] = result["results"]
        record_step(state, "search_all_conditions", reason, result["results"])
        show_dataframe("Problem list", result["results"])
        return state

    if choice == "3":
        label, code = choose_lab()
        reason = ask_why(f"Get lab: {label}")
        result = search_observations(patient_id, code)
        state["evidence"][label.lower().replace('-', '_').replace(' ', '_')] = {
            "bundle": result,
            "latest": latest_value(result),
        }
        record_step(state, "search_observations", f"{label}; {reason}", result["results"])
        show_dataframe(f"{label} results", result["results"])
        return state

    if choice == "4":
        reason = ask_why("Get medications")
        result = search_medications(patient_id)
        state["evidence"]["medications"] = result["results"]
        record_step(state, "search_medications", reason, result["results"])
        show_dataframe("Medications", result["results"])
        return state

    if choice == "5":
        reason = ask_why("Get encounters")
        result = search_encounters(patient_id)
        state["evidence"]["encounters"] = result["results"]
        record_step(state, "search_encounters", reason, result["results"])
        show_dataframe("Encounters", result["results"])
        return state

    if choice == "6":
        reason = ask_why("Ask the LLM what to do next")
        suggestion = suggest_next_step(state)
        record_step(state, "llm_coach", reason, suggestion)
        print()
        print("LLM suggestion:")
        print(suggestion)
        return state

    if choice == "7":
        classification = input(
            "Final answer? Enter 'Likely Type 1', 'Likely Type 2', or 'Unclear': "
        ).strip()
        rationale = input("What evidence supports your answer? ").strip()
        state["final_answer"] = {
            "classification": classification,
            "rationale": rationale,
        }
        record_step(state, "finish", classification, state["final_answer"])
        print()
        print("Answer saved.")
        return state

    raise ValueError("Unknown menu choice")
"""


LLM_HELPER = """\
def summarize_state_for_llm(state):
    summary = {
        "question": state["question"],
        "patient_id": state["patient_id"],
        "evidence": {},
        "history": [
            {"step": item["step"], "tool": item["tool"], "note": item["note"]}
            for item in state["history"]
        ],
        "missing_evidence": evidence_gaps(state),
    }
    for key, value in state["evidence"].items():
        if key in {"demographics", "medications", "conditions", "encounters"}:
            summary["evidence"][key] = value
        else:
            summary["evidence"][key] = value.get("latest")
    return summary


def suggest_next_step(state):
    if client is None:
        return (
            "Anthropic client not configured. Human mode is still available. "
            "If you want LLM coaching, set ANTHROPIC_API_KEY first."
        )

    prompt = {
        "question": state["question"],
        "allowed_actions": [
            "Get demographics",
            "Get full problem list",
            "Get labs",
            "Get medications",
            "Get encounters",
            "Finish and answer",
        ],
        "state": summarize_state_for_llm(state),
    }

    response = client.messages.create(
        model=MODEL,
        max_tokens=300,
        messages=[
            {
                "role": "user",
                "content": (
                    "You are coaching a student who is pretending to be the agent. "
                    "Given the current evidence state, recommend exactly one next action "
                    "from the allowed actions list and briefly explain why. "
                    "If the evidence is already sufficient, recommend 'Finish and answer'.\\n\\n"
                    + json.dumps(prompt, indent=2)
                ),
            }
        ],
    )
    return "".join(block.text for block in response.content if hasattr(block, "text"))
"""


PLAYGROUND = """\
# Pick a case number from the table above, then run this cell.
state = choose_case(1)
show_state(state)
"""


MANUAL_TURNS = """\
# Run this cell repeatedly. Each time, you will choose the next action.
state = run_human_turn(state)
show_state(state)
"""


COMPARISON = """\
print("Final answer recorded:")
display(state.get("final_answer"))

print()
print("Step log:")
display(pd.DataFrame(state["history"]))
"""


cells = [
    md_cell(
        "# Session 2 Prototype: You Are the Agent\\n\\n"
        "## Scenario\\n\\n"
        "You are reviewing a younger patient with diabetes. Your job is to decide "
        "whether the case looks more like **Type 1 diabetes**, **Type 2 diabetes**, "
        "or is still **unclear** based on the available evidence.\\n\\n"
        "This notebook is a prototype for a redesigned Session 2. The key idea is "
        "that **you temporarily play the role of the agent**. Instead of watching "
        "an LLM call tools, you decide what tool to use next and when you know "
        "enough to stop."
    ),
    md_cell(
        "## What You Are Practicing\\n\\n"
        "By the end of this prototype, students should be able to:\\n\\n"
        "- describe an agent loop in plain language\\n"
        "- choose the next tool based on missing evidence\\n"
        "- explain why one datapoint is not enough\\n"
        "- decide when an answer is well supported versus premature\\n"
        "- optionally compare their decisions with an LLM coach"
    ),
    md_cell(
        "## How This Prototype Works\\n\\n"
        "Each turn has the same structure:\\n\\n"
        "1. Review the current evidence state\\n"
        "2. Choose the next tool from a menu\\n"
        "3. See the result in a human-readable form\\n"
        "4. Decide whether to continue or finish\\n\\n"
        "The student does **not** need to write Python function calls. "
        "The interaction is menu-based."
    ),
    code_cell(SETUP),
    code_cell(TOOLS),
    md_cell(
        "## Build a Small Candidate Pool\\n\\n"
        "The cell below creates a small set of younger diabetes cases pulled from "
        "the synthetic FHIR server. These are the patients students can inspect "
        "during the exercise."
    ),
    code_cell(CASE_BUILDERS),
    md_cell(
        "## Load the Agent State Helpers\\n\\n"
        "These helper functions keep track of the current question, what evidence "
        "has been collected, what is still missing, and which steps have already "
        "been taken."
    ),
    code_cell(STATE_HELPERS),
    md_cell(
        "## Turn Engine\\n\\n"
        "This is the plain-language menu that the student sees. It maps simple "
        "choices like `Get labs` or `Get medications` to the underlying tool calls."
    ),
    code_cell(TURN_ENGINE),
    md_cell(
        "## Optional LLM Coach\\n\\n"
        "This helper does **not** run the whole task automatically. It only suggests "
        "what the next step should be if the student wants to compare their own "
        "reasoning with an LLM's recommendation."
    ),
    code_cell(LLM_HELPER),
    md_cell(
        "## Start a Case\\n\\n"
        "Pick a case number from the candidate table and initialize the state. "
        "For the prototype, the starter cell uses case `1`, but you can change it."
    ),
    code_cell(PLAYGROUND),
    md_cell(
        "## Take Turns as the Agent\\n\\n"
        "Run the next cell repeatedly. On each turn, decide what tool to use next.\\n\\n"
        "The recommended student workflow is:\\n\\n"
        "1. Get demographics\\n"
        "2. Get the full problem list\\n"
        "3. Get the most discriminating labs, especially C-peptide\\n"
        "4. Check medications\\n"
        "5. Decide whether the answer is strong enough or still unclear"
    ),
    code_cell(MANUAL_TURNS),
    md_cell(
        "## Compare and Debrief\\n\\n"
        "Once a final answer has been recorded, run the last cell to review the "
        "step log. In a teaching session, this is where the class can compare:\\n\\n"
        "- which evidence different students chose first\\n"
        "- where students stopped\\n"
        "- whether the answer was well supported\\n"
        "- how the LLM's suggested next step differed from the student's"
    ),
    code_cell(COMPARISON),
]


notebook = build_notebook(cells)
os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
    json.dump(notebook, f, indent=1)
    f.write("\n")

print(f"Wrote {OUTPUT_PATH}")
