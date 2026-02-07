# FHIR + AI Hackathon: Claude Code Build Specification

## Project Overview

Build a complete three-session hackathon for BMI 512 (Clinical Informatics and AI) at Stony Brook University. The hackathon teaches clinical informatics students (mix of MDs with varying CS experience, PhD and MS students from CS and biology backgrounds) how FHIR represents clinical data and how LLMs can be integrated into clinical informatics workflows through tool use / function calling.

**The deliverables are:**
1. Three student Jupyter notebooks (Sessions 1, 2, 3) — Colab-ready
2. Three example completed notebooks showing what a successful student submission looks like
3. A batch grading script for Session 3 deliverables
4. Three orientation slide decks as PDFs (to be built AFTER notebooks are tested)

**All notebooks must be tested against the live FHIR server before delivery.**

---

## ✅ COMPLETION STATUS (Updated Feb 6, 2026)

### Completed and Tested
- ✅ **Task 0:** FHIR server validation complete. Results: 7/10 checks passed (see validation_results.json)
- ✅ **Task 1:** Session 1 student notebook created and tested against live FHIR server
- ✅ **Task 3:** Session 2 student notebook created (Anthropic-only), tested with working agent loop
- ✅ **Task 5:** Session 3 student notebook created (Anthropic-only), tested with 6-tool agent

### Key Changes Made
1. **Simplified to Anthropic-only architecture** - Removed Azure OpenAI dual-provider complexity
2. **Fixed Pydantic SDK serialization issue** - Content blocks are now manually serialized to avoid SDK errors
3. **Updated to SNOMED CT codes** - All condition searches use SNOMED (44054006 for diabetes)
4. **Validated against live FHIR server** - All notebooks tested and working

### Test Scripts Created
- `test_session1.py` - Validates Session 1 notebook functionality (PASSED)
- `test_session2_simplified.py` - Tests Session 2 agent with 36 tool calls (PASSED)
- `test_session3_simplified.py` - Tests Session 3 agent with 6 tools (PASSED)

### Outstanding Tasks
- **Task 2:** Create session1_instructor.ipynb (example completed notebook)
- **Task 4:** Create session2_instructor.ipynb (example completed notebook)
- **Task 6:** Create session3_instructor.ipynb (example completed notebook)
- **Task 7:** Create grade_session3.py (batch grading script)
- **Task 8:** Create orientation PDFs (requires completed notebooks first)

### Known Limitations
- HbA1c threshold updated to 7.5% (from 9%) to ensure students find patients with poor control
- Hypertension SNOMED code (59621000) returns 0 results on FHIR server
- Creatinine observations (LOINC 2160-0) not available for tested patients

---

## Environment & Configuration

### FHIR Server
- **URL:** `https://launch.smarthealthit.org/v/r4/fhir`
- **Auth:** None required (open public server)
- **Data:** Synthea-generated synthetic patients, R4-compliant
- **No other FHIR server should be used.**

### LLM Provider (Anthropic-Only Architecture)
**UPDATE (Feb 2026):** The notebooks have been simplified to use **Anthropic Claude only**. The dual-provider architecture was confusing for students and introduced unnecessary complexity. All notebooks now use:

**Anthropic Claude:**
- SDK: `anthropic` Python package
- Model: `claude-sonnet-4-20250514`
- API key: Read from Colab Secrets (`ANTHROPIC_API_KEY`) or environment variable
- Tool use format: Anthropic's native tool use format (no conversion needed)

### Notebook Environment
- **Platform:** Google Colab
- **Python version:** 3.10+ (Colab default)
- **Pre-installed packages used:** `requests`, `pandas`, `json`, `hashlib`, `datetime`
- **Packages to pip install:** `anthropic`
- **API keys:** Students store keys in Colab's Secrets panel (key icon in left sidebar). The setup cell reads them using:
  ```python
  from google.colab import userdata
  api_key = userdata.get('ANTHROPIC_API_KEY')
  ```
- **For local/Claude Code testing:** Fall back to `os.environ.get()` if `google.colab` is not available.

---

## Task 0: FHIR Server Validation (RUN FIRST)

**Purpose:** Before building any notebooks, validate that the FHIR server has the data we need for the clinical scenario.

**Create file:** `validate_fhir_server.py`

**This script must verify ALL of the following:**

1. **Server is reachable:** `GET {FHIR_BASE}/metadata` returns 200 with `fhirVersion` containing "4"
2. **Condition resources exist for 44054006 (Type 2 Diabetes - SNOMED CT):**
   - `GET {FHIR_BASE}/Condition?code=44054006&_count=20` returns a Bundle with at least 5 entries
   - Each entry has `subject.reference` in the format `Patient/{id}`
   - Extract and store the unique patient IDs
   - **Note:** The server uses SNOMED CT codes, not ICD-10
3. **Patient resources are fetchable:**
   - For each unique patient ID from step 2, `GET {FHIR_BASE}/Patient/{id}` returns 200
   - Each Patient has `name`, `birthDate`, and `gender` fields
4. **Observation resources exist for HbA1c (LOINC 4548-4):**
   - For each patient from step 2, `GET {FHIR_BASE}/Observation?subject=Patient/{id}&code=4548-4&_count=5&_sort=-date` 
   - At least SOME patients should have HbA1c observations (not all will)
   - Observations should have `valueQuantity.value` that is numeric
   - Check if any values are > 7.5 (poor glycemic control)
5. **Additional resources for Session 3 tools:**
   - `GET {FHIR_BASE}/MedicationRequest?subject=Patient/{id}&_count=5` — verify MedicationRequest resources exist for at least some patients
   - `GET {FHIR_BASE}/Encounter?subject=Patient/{id}&_count=5` — verify Encounter resources exist
   - `GET {FHIR_BASE}/Condition?subject=Patient/{id}&_count=20` — verify multiple conditions per patient (for search_all_conditions tool)
6. **Test additional clinical scenarios for Session 3:**
   - `GET {FHIR_BASE}/Condition?code=59621000&_count=10` — Hypertension conditions exist (SNOMED CT)
   - For hypertension patients, check for blood pressure observations (LOINC 85354-9)
   - For diabetes patients, check for creatinine observations (LOINC 2160-0)

**Output:** Print a clear summary report:
```
=== FHIR Server Validation Report ===
Server: https://launch.smarthealthit.org/v/r4/fhir
FHIR Version: 4.0.1
Timestamp: 2025-XX-XX

[PASS/FAIL] Server reachable
[PASS/FAIL] Type 2 Diabetes conditions found: N entries, M unique patients
[PASS/FAIL] Patient resources fetchable: N/M succeeded
[PASS/FAIL] HbA1c observations found: N patients have HbA1c data
[PASS/FAIL] HbA1c values > 7.5% found: N patients with poor control
[PASS/FAIL] MedicationRequest resources found
[PASS/FAIL] Encounter resources found
[PASS/FAIL] Multiple conditions per patient found
[PASS/FAIL] Hypertension conditions found
[PASS/FAIL] Blood pressure observations found
[PASS/FAIL] Creatinine observations found

Sample data for notebook development:
  Patient IDs with diabetes + HbA1c data: [list]
  Patient IDs with HbA1c > 7.5%: [list]
  Patient IDs with medications: [list]
```

**Also save the validation results to `validation_results.json`** so subsequent tasks can reference known-good patient IDs if needed for testing.

**CRITICAL:** If any core checks (1-4) fail, STOP and report the issue. Do not proceed to notebook generation.

---

## Task 1: Session 1 Student Notebook

**File:** `session1_student.ipynb`

**Description:** A Google Colab-ready Jupyter notebook for the Session 1 hackathon. Students manually query a FHIR server by asking Claude (web UI) to generate Python code, pasting it into the notebook, and running it. The notebook contains pre-built cells (run as-is) and empty cells (students fill in).

### Clinical Scenario
"Find patients with Type 2 diabetes, retrieve their most recent HbA1c values, and identify those with poor glycemic control (HbA1c > 7.5%)."

### Cell Structure

**Cell 0 — Title and Overview (markdown, pre-built)**
```
# Session 1: FHIR Fundamentals with LLM-Assisted Code Generation

## Clinical Scenario
Find patients with Type 2 diabetes, retrieve their most recent HbA1c values, 
and identify those with poor glycemic control (HbA1c > 7.5%).

## How This Works
- **Pre-built cells** (with code): Just run them (Shift+Enter)
- **Empty cells** (with instructions): Ask Claude to generate the code, paste it in, run it
- **Verification cells**: Run after your code to check your results
- **Markdown cells**: Read for context, fill in where prompted

## What You'll Learn
- How FHIR represents clinical data (resources, references, Bundles)
- How to query a FHIR server using Python
- How to use an LLM to generate working API calls
- Why answering clinical questions requires multi-step FHIR queries
```

**Cell 0b — Clinical Code Reference (markdown, pre-built)**
```
### 📋 Clinical Code Reference

**Note:** This FHIR server uses SNOMED CT codes for conditions, not ICD-10.

| Code | System | Meaning | Used In |
|------|--------|---------|---------|
| 44054006 | SNOMED CT | Type 2 Diabetes Mellitus | Condition search |
| 59621000 | SNOMED CT | Essential Hypertension | (Session 3) |
| 4548-4 | LOINC | Hemoglobin A1c (HbA1c) | Observation search |
| 85354-9 | LOINC | Blood Pressure panel | (Session 3) |
| 2160-0 | LOINC | Creatinine [Mass/volume] in Serum or Plasma | (Session 3) |

**For reference - ICD-10 equivalents:**
- Type 2 Diabetes: E11
- Essential Hypertension: I10

**HbA1c interpretation:**
- < 5.7%: Normal
- 5.7% - 6.4%: Prediabetes
- ≥ 6.5%: Diabetes
- > 7.5%: Poor glycemic control (needs intervention)
```

**Cell 0c — FHIR Resource Relationships (markdown, pre-built)**
```
### 🔗 How FHIR Resources Link Together

Our clinical question requires THREE types of FHIR resources:

```
Condition (code: 44054006 - Type 2 Diabetes, SNOMED CT)
  └─ subject.reference ──→ Patient/{id}
                              ↑
Observation (code: 4548-4 - HbA1c, LOINC)
  └─ subject ─────────────────┘
```

- **Condition** records a diagnosis. It points to the Patient via `subject.reference`.
- **Patient** holds demographics (name, birthdate, gender).
- **Observation** records a lab result or vital sign. It also points to the Patient.

To answer "which diabetic patients have poor HbA1c control?" we must:
1. Search Conditions to find patients with diabetes
2. Follow references to get Patient demographics
3. Search Observations for each patient's HbA1c values
4. Combine and analyze

This multi-step pattern is fundamental to FHIR — clinical facts are stored 
in separate, linked resources.
```

**Cell 1 — Setup (code, pre-built)**
```python
# ============================================================
# SETUP — Run this cell first
# ============================================================
import requests
import json
import pandas as pd
from IPython.display import display, HTML

FHIR_BASE = "https://launch.smarthealthit.org/v/r4/fhir"

def show_json(data, max_lines=30):
    """Pretty-print JSON, truncated for readability."""
    text = json.dumps(data, indent=2)
    lines = text.split('\n')
    if len(lines) > max_lines:
        print('\n'.join(lines[:max_lines]))
        print(f"\n... ({len(lines) - max_lines} more lines, truncated for display)")
    else:
        print(text)

# Verify the server is reachable
resp = requests.get(f"{FHIR_BASE}/metadata", params={"_format": "json"}, timeout=10)
if resp.status_code == 200:
    fhir_version = resp.json().get("fhirVersion", "unknown")
    print(f"✅ Connected to FHIR server: {FHIR_BASE}")
    print(f"   FHIR version: {fhir_version}")
    print(f"   This server contains synthetic (Synthea) patient data.")
    print(f"   No authentication required — it's a public sandbox.")
else:
    print(f"❌ Could not connect to FHIR server. Status: {resp.status_code}")
    print(f"   Check your internet connection and try again.")
```

**Cell 2 — Your First FHIR Query (code, pre-built)**
```python
# ============================================================
# YOUR FIRST FHIR QUERY — Fetching Patient resources
# ============================================================
# A FHIR search is just an HTTP GET request with URL parameters.
# Let's fetch 3 Patient resources to see what they look like.

resp = requests.get(f"{FHIR_BASE}/Patient", params={"_count": 3, "_format": "json"})
bundle = resp.json()

print(f"Response type: {bundle['resourceType']}")  # Always "Bundle" for search results
print(f"Total patients on server: {bundle.get('total', 'unknown')}")
print(f"Entries returned in this page: {len(bundle.get('entry', []))}")
print()

# Look at the first patient resource
print("--- First Patient Resource ---")
first_patient = bundle["entry"][0]["resource"]
show_json(first_patient)
```

**Cell 2b — Understanding Bundles (markdown, pre-built)**
```
### 🔍 What Did We Just See?

The FHIR server returned a **Bundle** — a container for search results. Key structure:

- `resourceType`: "Bundle" — tells you this is a search result container
- `total`: How many resources matched your search on the entire server
- `entry`: An array (list) of results. Each entry contains a `resource`.

Inside each Patient resource:
- `id`: The unique identifier (e.g., "abc123"). Other resources use this to REFERENCE this patient.
- `name`: Array of name objects with `given` (first name) and `family` (last name)
- `birthDate`: Date of birth
- `gender`: "male" or "female"

**The URL pattern for FHIR search:**
`{server}/Patient?_count=3` means "give me up to 3 Patient resources"

You'll use this same pattern with Condition and Observation resources next.
```

**Cell 3 — Generating a Condition Search with Claude (markdown, pre-built)**
```
### ✏️ Step 1: Find Patients with Type 2 Diabetes

Now you'll use Claude to write a FHIR query. Open the Claude web interface and enter this prompt:

> Write Python code using the `requests` library to search for Condition
> resources with SNOMED CT code 44054006 (Type 2 diabetes) on the FHIR server at
> https://launch.smarthealthit.org/v/r4/fhir. Limit to 20 results. For each condition
> found, extract and print:
> - The condition resource ID
> - The patient reference (from subject.reference)
> - The display name of the condition
> - The onset date (from onsetDateTime)
> Also collect all unique patient references into a Python set called `patient_refs`.

**Paste Claude's response in the cell below and run it.**
```

**Cell 3b — Empty code cell for student**
(Completely empty — student pastes Claude-generated code here)

**Cell 3c — Verification (code, pre-built)**
```python
# ============================================================
# VERIFICATION — Check your Condition search results
# ============================================================
try:
    print(f"✅ Found {len(patient_refs)} unique patients with Type 2 diabetes")
    print(f"   Example references: {list(patient_refs)[:5]}")
    print(f"\n   These references tell us WHICH patients have diabetes.")
    print(f"   Next: we'll FOLLOW these references to get their demographics.")
    
    # Store for later use
    patient_ids = [ref.split("/")[-1] for ref in patient_refs if "/" in ref]
    print(f"\n   Extracted patient IDs: {patient_ids[:5]}...")
except NameError:
    print("⚠️  Variable 'patient_refs' not found.")
    print("   Make sure your code in the cell above creates a set called 'patient_refs'")
    print("   containing strings like 'Patient/abc123'")
    print()
    print("   If Claude's code used a different variable name, either:")
    print("   1. Rename it to 'patient_refs' and re-run, or")
    print("   2. Run this fallback code to continue:")
    print()
    print("   # --- Fallback: uncomment and run if needed ---")
    print("   # resp = requests.get(f'{FHIR_BASE}/Condition',")
    print("   #     params={'code': '44054006', '_count': 20})")
    print("   # bundle = resp.json()")
    print("   # patient_refs = set()")
    print("   # for entry in bundle.get('entry', []):")
    print("   #     ref = entry['resource'].get('subject', {}).get('reference', '')")
    print("   #     if ref: patient_refs.add(ref)")
    print("   # patient_ids = [ref.split('/')[-1] for ref in patient_refs]")
```

**Cell 4 — Following References (markdown, pre-built)**
```
### ✏️ Step 2: Get Patient Demographics

Each Condition resource points to a Patient via `subject.reference` (e.g., "Patient/abc123").
Now we need to FOLLOW those references to get each patient's name, birthdate, and gender.

Ask Claude:

> I have a Python list called `patient_ids` containing FHIR patient IDs like
> ["abc123", "def456"]. Write Python code that fetches each Patient resource
> from the FHIR server at https://launch.smarthealthit.org/v/r4/fhir/Patient/{id} and
> extracts their full name (combining given and family name), birth date,
> and gender. Store the results in a list of dictionaries called `patients` 
> where each dict has keys: "id", "name", "birthDate", "gender". Print 
> each patient as you fetch them.

**Paste Claude's response in the cell below.**
```

**Cell 4b — Empty code cell for student**

**Cell 4c — Formatted Output (code, pre-built)**
```python
# ============================================================
# PATIENT DEMOGRAPHICS TABLE
# ============================================================
try:
    df_patients = pd.DataFrame(patients)
    print(f"✅ Retrieved demographics for {len(df_patients)} patients:\n")
    display(df_patients)
    
    print(f"\nNotice: each patient has an 'id' — this is what we'll use to")
    print(f"search for their lab results next.")
except NameError:
    print("⚠️  Variable 'patients' not found.")
    print("   Make sure your code creates a list called 'patients'")
    print("   Each item should be a dict with keys: id, name, birthDate, gender")
    print()
    print("   If stuck, ask Claude to fix your code or use a different variable name.")
```

**Cell 5 — Getting Observations (markdown, pre-built)**
```
### ✏️ Step 3: Retrieve HbA1c Lab Values

This is the critical step. For EACH patient, we search for Observation resources 
with LOINC code 4548-4 (HbA1c). We want only the most recent result.

Ask Claude:

> I have a Python list called `patients` where each item is a dictionary with
> an "id" key containing a FHIR patient ID. For each patient, write Python
> code to search for Observation resources at
> https://launch.smarthealthit.org/v/r4/fhir/Observation with parameters:
> - subject: Patient/{id}
> - code: 4548-4
> - _sort: -date  
> - _count: 1
> Extract the date (effectiveDateTime), numeric value (valueQuantity.value), 
> and unit (valueQuantity.unit) from the most recent observation.
> Store results in a list called `observations` where each dict has keys: 
> "patient_id", "date", "value", "unit". If a patient has no HbA1c 
> observation, include them with value "N/A". Print progress as you go.

**Paste Claude's response below.**
```

**Cell 5b — Empty code cell for student**

**Cell 5c — Combined Analysis (code, pre-built)**
```python
# ============================================================
# COMBINED ANALYSIS — Identify Poor Glycemic Control
# ============================================================
try:
    df_obs = pd.DataFrame(observations)
    
    # Merge with patient demographics
    df_patients_str = df_patients.copy()
    df_patients_str["id"] = df_patients_str["id"].astype(str)
    df_obs["patient_id"] = df_obs["patient_id"].astype(str)
    
    df_merged = df_obs.merge(df_patients_str, left_on="patient_id", right_on="id", how="left")
    
    # Convert HbA1c values to numeric (handle N/A and missing)
    df_merged["hba1c_numeric"] = pd.to_numeric(df_merged["value"], errors="coerce")
    
    # Flag poor glycemic control
    df_merged["poor_control"] = df_merged["hba1c_numeric"].apply(
        lambda x: "🔴 Yes" if pd.notna(x) and x > 7.5 
                  else ("🟢 No" if pd.notna(x) else "⚪ No data"))
    
    # Display results
    display_cols = ["name", "birthDate", "gender", "date", "value", "unit", "poor_control"]
    available_cols = [c for c in display_cols if c in df_merged.columns]
    
    print("📊 Patients with Type 2 Diabetes — HbA1c Results:\n")
    display(df_merged[available_cols])
    
    # Summary statistics
    has_data = df_merged["hba1c_numeric"].notna()
    poor = (df_merged["hba1c_numeric"] > 7.5) & has_data
    
    print(f"\n📈 Summary:")
    print(f"   Total patients with Type 2 diabetes: {len(df_merged)}")
    print(f"   Patients with HbA1c data: {has_data.sum()}")
    print(f"   🔴 Poor glycemic control (HbA1c > 7.5%): {poor.sum()}")
    print(f"   🟢 Adequate control: {(has_data & ~poor).sum()}")
    print(f"   ⚪ No HbA1c data available: {(~has_data).sum()}")
    
    if poor.sum() > 0:
        print(f"\n   Patients needing follow-up:")
        for _, row in df_merged[poor].iterrows():
            print(f"     • {row.get('name', 'Unknown')}: HbA1c = {row['value']}%")
            
except NameError as e:
    print(f"⚠️  Error: {e}")
    print("   Make sure you've run the previous cells successfully.")
    print("   Required variables: 'observations' (list of dicts) and 'df_patients' (DataFrame)")
except Exception as e:
    print(f"⚠️  Unexpected error: {e}")
    print("   This might mean the data format was different than expected.")
    print("   Ask Claude to help debug, or ask the instructor.")
```

**Cell 6 — LLM Summarization (markdown, pre-built)**
```
### ✏️ Step 4: Generate a Clinical Summary

We now have structured data in a table. The final step: translate this into 
a narrative that a clinician or patient could read.

**Copy the table output above** and paste it into the Claude web interface with this prompt:

> Here is a table of patients with Type 2 diabetes and their most recent HbA1c 
> values. Write a brief clinical summary suitable for a care coordinator. 
> Identify patients with poor glycemic control (HbA1c > 7.5%) and note they may 
> need follow-up. Format it as 2-3 short paragraphs. Use ONLY the data in the 
> table — do not add any information that is not present.

**Paste Claude's summary in the markdown cell below.**
```

**Cell 6b — Empty markdown cell for student to paste summary**

**Cell 7 — Session 1 Reflection (markdown, pre-built)**
```
### 🧠 What You Just Built

You manually executed a **three-step clinical data pipeline**:

1. **Condition search** → Found patients with Type 2 diabetes (SNOMED CT: 44054006)
2. **Patient lookup** → Retrieved demographics by following `subject.reference`
3. **Observation search** → Got HbA1c lab values (LOINC: 4548-4) for each patient

You used an LLM (Claude) in two distinct roles:
- **Code generation** — Claude wrote the Python / FHIR queries for you
- **Summarization** — Claude translated structured data into clinical narrative

**Key insight:** The LLM never touched the FHIR server directly. YOUR CODE did 
the querying. The LLM helped you write the code and interpret the results. This 
separation between planning/interpretation (LLM) and execution (code) is 
critical for safety and correctness in clinical systems.

**Next session:** What if the LLM could orchestrate these same steps 
*autonomously* — deciding which queries to run and in what order? That's 
called **tool use**, and it's the foundation of AI agents.

### Save this notebook — you'll reference it in Session 2.
```

### Important Implementation Notes for Session 1
- All pre-built code cells must run without errors when `patient_refs` and `patients` don't exist yet (verification cells handle NameError gracefully)
- The verification cells provide fallback instructions so students can continue even if their Claude-generated code uses different variable names
- Do NOT include any Azure OpenAI or Anthropic API calls — Session 1 only uses `requests` against the FHIR server
- The notebook must work in Google Colab without any API keys

---

## Task 2: Session 1 Example Completed Notebook

**File:** `session1_example_completed.ipynb`

**Description:** A fully worked version of Session 1 showing what a successful student submission looks like.

### Requirements
- Start from `session1_student.ipynb` and fill in ALL empty cells
- **Cell 3b (Condition search):** Write realistic Claude-generated code. It should:
  - Use `requests.get` with params `{"code": "44054006", "_count": 20}`
  - Loop through `bundle["entry"]` extracting condition details
  - Build a `patient_refs` set
  - Include a comment like `# Generated by Claude` at the top
  - Be slightly imperfect in style (the way an LLM would write it, not hand-optimized) — e.g., maybe it doesn't handle the edge case of missing `onsetDateTime`, or uses a slightly verbose approach
- **Cell 4b (Patient demographics):** Realistic code that loops through `patient_ids`, fetches each Patient, extracts name/birthDate/gender into the `patients` list
- **Cell 5b (Observations):** Realistic code that loops through patients and fetches HbA1c observations, building the `observations` list. Should handle the case where a patient has no observations.
- **Cell 6b (Summary):** A realistic clinician-friendly summary paragraph, as if pasted from Claude. Should reference specific patient names and HbA1c values from the actual data retrieved.
- **Every cell must execute in sequence without errors against the live FHIR server.**
- Run all cells and capture output. The notebook should show real output from the FHIR server.

---

## Task 3: Session 2 Student Notebook

**File:** `session2_student.ipynb`

**Description:** Session 2 hackathon notebook. Students observe an AI agent executing the same clinical pipeline from Session 1 autonomously using tool use.

### Cell Structure

**Cell 0 — Title and Overview (markdown, pre-built)**
Content: Welcome to Session 2, recap of Session 1 (you were the orchestrator, now the LLM takes over), explanation of tool use concept with the boxes-and-arrows diagram, the important distinction that the LLM requests function calls but your code executes them.

**Cell 0b — ICD-10 / LOINC Reference (markdown, pre-built)**
Same cheat sheet as Session 1.

**Cell 1 — Setup and LLM Configuration (code, pre-built)**
```python
# ============================================================
# SETUP — Anthropic API and FHIR Server
# ============================================================
import os, json, requests
from anthropic import Anthropic

# ---- API Key Setup ----
# Try to get API key from Colab Secrets first, then environment variable
try:
    from google.colab import userdata
    api_key = userdata.get("ANTHROPIC_API_KEY")
except (ImportError, Exception):
    api_key = os.environ.get("ANTHROPIC_API_KEY")

if not api_key:
    raise ValueError("Set ANTHROPIC_API_KEY in Colab Secrets or environment")

# ---- Initialize Anthropic Client ----
client = Anthropic(api_key=api_key)
MODEL = "claude-sonnet-4-20250514"

# ---- FHIR Server ----
FHIR_BASE = "https://launch.smarthealthit.org/v/r4/fhir"

print(f"✅ LLM: Anthropic Claude ({MODEL})")
print(f"✅ FHIR server: {FHIR_BASE}")
```

**CRITICAL IMPLEMENTATION NOTE:** The agent loop must manually serialize Pydantic content blocks to avoid SDK errors. When appending the assistant's response to messages, use this pattern:

```python
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
```

This serialization fix prevents `TypeError: argument 'by_alias': 'NoneType' object cannot be converted to 'PyBool'` errors that occur when passing Pydantic objects directly.

**Cell 2 — FHIR Tool Functions (code, pre-built)**
Same three functions as Session 1: `search_conditions`, `get_patient`, `search_observations`. Identical implementations. Include the smoke test at the bottom.

**Cell 3 — Tool Schemas (code, pre-built)**
Define tool schemas in Anthropic's native format. Include the `available_functions` dict. Print the tool menu.

Example format:
```python
tools = [
    {
        "name": "search_conditions",
        "description": "Search for patient Condition resources...",
        "input_schema": {
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "SNOMED CT code..."},
                "max_results": {"type": "integer", "description": "Max results", "default": 20}
            },
            "required": ["code"]
        }
    },
    # ... other tools
]
```

**Cell 3b — Understanding Schemas (markdown, pre-built)**
Explains what schemas are, that the LLM only sees descriptions not code, and why good descriptions matter.

**Cell 4 — Prediction Exercise (markdown, student fills in)**
Students predict the tool call sequence before running the agent. Five specific prediction questions with "YOUR PREDICTION:" placeholders.

**Cell 5 — System Prompt (code, pre-built)**
Define and display the system prompt. Include explanatory comments.

**Cell 6 — Agent Loop Execution (code, pre-built)**
The main agent execution cell. Implements the tool use loop with Anthropic's API. Must:
- Print clear step-by-step trace showing each tool call
- Manually serialize content blocks (see Cell 1 note)
- Handle both tool_use and text content blocks
- Execute tool calls via the `available_functions` dict
- Loop until the agent provides a final text response (no more tool_use blocks)

The clinical question is hardcoded (not student-editable): "Find patients with Type 2 diabetes and their most recent HbA1c values. Which patients have poor glycemic control (HbA1c > 7.5%)?"

**Cell 7 — Trace Analysis (code, pre-built)**
Displays the tool call sequence as a formatted table. Shows counts by function name.

**Cell 8 — Compare to Predictions (markdown, student fills in)**
Four specific comparison questions with "YOUR ANSWER:" placeholders. Questions should prompt students to think about WHY the agent made each decision.

**Cell 9 — Full Conversation Anatomy (code, pre-built)**
Displays every message in the conversation history with role labels and content previews. Shows Anthropic's message structure with content blocks.

**Cell 10 — Takeaways (markdown, pre-built)**
Summary of what they saw, the agent loop pattern, critical design decisions, preview of Session 3.

---

## Task 4: Session 2 Example Completed Notebook

**File:** `session2_example_completed.ipynb`

**Description:** Fully executed version of Session 2 with real agent traces.

### Requirements
- Run the agent against the live FHIR server and capture actual trace output
- Fill in all student prediction and reflection cells with realistic sample answers
- Predictions should be mostly correct (a good student would predict the right sequence)
- Reflection answers should demonstrate understanding of why the agent made each choice
- The trace should show the expected pattern: search_conditions → get_patient (multiple) → search_observations (multiple) → final summary
- All cells must show real output

---

## Task 5: Session 3 Student Notebook

**File:** `session3_student.ipynb`

**Description:** Session 3 hackathon notebook with expanded tool set and open-ended exploration.

### Cell Structure

**Cell 0 — Title and Overview (markdown, pre-built)**
Content: Welcome to Session 3, recap, goals (2 questions, find a failure, document it).

**Cell 0b — ICD-10 / LOINC Reference (markdown, pre-built)**
Extended cheat sheet with additional codes relevant to the new tools.

**Cell 1 — Setup (code, pre-built)**
Same Anthropic API setup as Session 2. Includes the serialization fix for content blocks.

**Cell 2 — Expanded Tool Set (code, pre-built)**
All 6 FHIR tool functions:
1. `search_conditions(code, max_results)` — search by diagnosis code
2. `get_patient(patient_id)` — get single patient demographics
3. `search_observations(patient_id, loinc_code, max_results)` — get lab/vital results
4. `search_medications(patient_id, max_results)` — get medication orders
5. `search_encounters(patient_id, max_results)` — get visit/hospitalization history
6. `search_all_conditions(patient_id, max_results)` — get full problem list for a patient

Include a smoke test that calls each function once and confirms it works.

**Cell 3 — Tool Schemas and Registration (code, pre-built)**
All 6 tool schemas in Anthropic's native format. Updated `available_functions` dict. Print the full tool menu.

**Cell 4 — System Prompt (code, pre-built)**
Updated system prompt that references all 6 tools and gives the agent more general guidance (since questions are open-ended). The prompt should instruct the agent to think step-by-step, use only data from tools, and handle cases where no data is found.

**Cell 5 — Question Ideas (markdown, pre-built)**
A menu of suggested questions in three categories: straightforward, complex, and edge cases. Same as in the plan above.

**Cell 6 — Agent Runner: Question 1 (code, student edits question)**
```python
# ⬇️ ENTER YOUR FIRST CLINICAL QUESTION HERE
user_question_1 = ""  # ← TYPE YOUR QUESTION

assert user_question_1, "Please enter a question above before running this cell"
```
Followed by the agent loop that stores results in `answer_1`, `tool_calls_1`, `messages_1`.

**Cell 7 — Trace Summary for Question 1 (code, pre-built)**
Displays the tool call sequence for the first run.

**Cell 8 — Run Agent Helper Function (code, pre-built)**
The `run_agent(question)` helper function for convenient re-use.

**Cell 9 — Agent Runner: Question 2 (code, student edits question)**
```python
# ⬇️ ENTER YOUR SECOND CLINICAL QUESTION
user_question_2 = ""  # ← TYPE YOUR QUESTION (try something different!)
```
Uses `run_agent()` and stores results in `answer_2`, `tool_calls_2`.

**Cell 10 — Trace Summary for Question 2 (code, pre-built)**

**Cell 11 — Failure Analysis (markdown, student fills in)**
Detailed prompt asking students to describe a failure or surprising behavior they observed, with specific sub-questions: what happened, what was expected, why it happened, how to fix it.

**Cell 12 — Deliverable Generation (code, pre-built)**
Generates the JSON report with:
- student_id (prompted via input())
- timestamp
- Both questions, tool call sequences, and final answers
- Verification hash
- Saves to file

Must handle missing runs gracefully (if student only completed one question, still generates a partial report with a warning).

**Cell 13 — Final Reflection (markdown, student fills in)**
Three reflection questions:
1. What surprised you most about agent behavior?
2. When would you trust an agent like this with real clinical data? What safeguards?
3. How does tool use relate to MCP? (What does MCP standardize that our notebook left ad hoc?)

---

## Task 6: Session 3 Example Completed Notebook

**File:** `session3_example_completed.ipynb`

### Requirements
- **Run 1:** A straightforward question that succeeds. Suggested: "Find patients with Type 2 diabetes and list their current medications. Are any patients on insulin?"
- **Run 2:** A question that produces an interesting failure or surprising behavior. Suggested: "Which patients are the sickest?" (vague — observe how the agent interprets this) OR "Find patients at risk for diabetic complications" (requires clinical reasoning the agent may lack)
- Fill in the failure analysis with a realistic student-quality writeup that identifies the specific failure mode
- Fill in all reflection questions
- Generate and include the JSON deliverable
- All cells must show real output from live FHIR server

---

## Task 7: Batch Grading Script

**File:** `grade_session3.py`

**Description:** Command-line Python script that reads all `hackathon_session3_*.json` files from a specified directory and produces a grading summary.

### Usage
```bash
python grade_session3.py /path/to/submissions/
```

### Checks Performed
1. JSON is valid and parseable
2. `student_id` field is present and non-empty
3. At least 2 runs present in `runs` array
4. Each run has:
   - Non-empty `question`
   - Non-empty `tool_calls` list (at least 1 tool call)
   - Tool calls use only valid function names: `search_conditions`, `get_patient`, `search_observations`, `search_medications`, `search_encounters`, `search_all_conditions`
5. `verification_hash` matches SHA-256 of the tool calls data
6. No two students have identical question + tool_call_sequence combinations (flag potential copying)

### Output
1. Print a per-student summary to stdout:
```
Student: jsmith    Runs: 2  Tool calls: 12  Unique tools: 4  Hash: ✅  Status: PASS
Student: jdoe      Runs: 1  Tool calls: 3   Unique tools: 2  Hash: ✅  Status: WARN (only 1 run)
Student: alee      Runs: 0  Tool calls: 0   Unique tools: 0  Hash: N/A Status: FAIL (no runs)
```

2. Save `grading_summary.csv` with columns: student_id, num_runs, total_tool_calls, unique_tools_used, tools_list, hash_valid, status, notes

3. If duplicates detected, print a warning section at the end listing the suspicious pairs.

---

## Task 8: Orientation Slide Decks (PDFs)

**NOTE:** Build these AFTER Tasks 1-6 are complete and tested, since the slides need real screenshots from the working notebooks.

### File: `pre_session1_orientation.pdf`

**Slide-style PDF, approximately 15-20 pages.** Each page = one slide concept with large text and visuals.

**Content outline (from the agreed plan):**

1. Title slide: "FHIR + AI Hackathon — Session 1 Orientation"
2. The Big Picture: pipeline diagram (English → AI → FHIR → Data → Summary)
3. Three-Session Arc: Session 1 (manual), Session 2 (observe agent), Session 3 (explore)
4. What is an API?: URL → Server → Response diagram. Screenshot of browser hitting the FHIR server (capture from validation script or notebook output)
5. JSON in 3 Minutes: Simple example (person with name, age, hobbies). Annotated with curly braces = object, square brackets = list, key:value pairs
6. JSON → FHIR: Side-by-side of simple JSON and a FHIR Patient resource. "Same structure, just more fields"
7. FHIR Essentials — Resources: Patient, Condition, Observation. One visual card per resource showing key fields.
8. FHIR Essentials — References: How Condition.subject.reference → Patient/{id}. The relationship diagram.
9. FHIR Essentials — Bundles: Search results come in Bundles. Show the structure: Bundle → entry[] → resource.
10. The Clinical Scenario: "Find patients with Type 2 diabetes, get their HbA1c values, identify poor control." Map this to the three query steps.
11. Google Colab Refresher: Screenshot of Colab interface. Code cells vs markdown cells. Shift+Enter to run. Variables persist across cells.
12. Colab Secrets: Screenshot of the Secrets panel (key icon). "Store your API keys here in Session 2."
13. Using Claude as Your Code Generator: Screenshot of Claude web UI. The workflow: describe what you want → Claude generates Python → paste into Colab → run → inspect results.
14. ICD-10 / LOINC Reference Table: The cheat sheet.
15. What to Expect: "Open the notebook. Work through cells in order. Ask for help." Show the notebook structure briefly.

**For screenshots:** Generate them by running the actual notebook and FHIR queries. Capture:
- A FHIR Patient JSON response (from the validation script or Cell 2 output)
- A Bundle structure showing entries
- The Colab interface (can use a representative screenshot or diagram)
- The Claude web UI (can use a representative diagram showing the prompt → response flow)

If actual Colab screenshots are not capturable from this environment, create clean diagrams or annotated text representations instead. The instructor will supplement with live demos.

### File: `pre_session2_orientation.pdf`

**Approximately 12-15 pages.**

1. Title slide: "FHIR + AI Hackathon — Session 2 Orientation"
2. Session 1 Recap: "You were the orchestrator" — the three manual steps
3. Today's Shift: "The LLM takes over orchestration"
4. What is Tool Use?: The doctor/nurse metaphor. Doctor (LLM) can't access EHR. Nurse (tools) looks things up. Doctor interprets results.
5. The Tool Use Loop: Diagram with boxes and arrows: Question → LLM examines tools → LLM requests function call → Code executes function → Results back to LLM → LLM decides next step → ... → Final answer
6. Tool Schemas Explained: Side-by-side of the Python function and its JSON schema. Highlight: the LLM only sees the schema, never the code. Annotate the three parts: name, description, parameters.
7. Why Descriptions Matter: "If the schema says 'Search for observations' but doesn't mention LOINC codes, the LLM won't know to pass a LOINC code." Good vs bad description example.
8. The System Prompt: Show the actual system prompt from the notebook. "This tells the LLM how to think — like giving a doctor a clinical protocol."
9. System Prompt vs Tool Schema: "Schema = WHAT tools exist. System prompt = HOW to use them. Both matter."
10. What to Expect Today: "Same clinical scenario as Session 1. Your job: predict what the agent will do, then verify. It should feel predictable — that's the point."
11. The Prediction Exercise: Preview the prediction questions. "Think through the steps before you run the agent."

### File: `pre_session3_orientation.pdf`

**Approximately 18-22 pages (the longest deck, covering MCP).**

1. Title: "FHIR + AI Hackathon — Session 3 Orientation"
2. Sessions 1 & 2 Recap: "Manual → Observed automation. Today: you drive."
3. New Tools Available: Visual menu of all 6 tools with brief descriptions
4. The Expanded Menu: "More tools = more decisions for the agent = more ways to succeed AND fail"
5-8. **Failure Modes (4 slides, one per failure type):**
   - Slide 5: Hallucination — screenshot from a test run where the agent's summary includes data not present in tool results. Annotate with red highlights on the fabricated content and show the actual tool output alongside.
   - Slide 6: Wrong Tool Choice — screenshot showing a trace where the agent called an inappropriate tool. Annotate the decision point.
   - Slide 7: Premature Termination — screenshot showing an incomplete answer. "The agent answered after 1 tool call when it needed 3."
   - Slide 8: Over-querying — screenshot showing redundant calls. "The agent fetched the same patient twice."
9. Why Failures Matter Clinically: "A hallucinated lab value, a missed patient, a wrong medication — these have consequences. Your role as informaticists: build AND evaluate."
10-11. **The Portability Problem (2 slides):**
    - Slide 10: "What we hard-coded" — diagram of Session 2 architecture. Tool schemas in Python dict, functions in same notebook, agent loop wired manually.
    - Slide 11: "What if we want to share these tools?" Three pain points: schemas embedded in code (not discoverable), transport is ad hoc (JSON strings in a notebook), no standard discovery protocol.
12-14. **MCP Introduction (3 slides):**
    - Slide 12: "MCP: Model Context Protocol" — what it solves. A standard for: tool description (schemas), tool discovery (server advertises capabilities), tool invocation (standardized transport).
    - Slide 13: Side-by-side diagram: "Our notebook" vs "MCP architecture". Our notebook: Agent Loop ↔ Python Functions ↔ FHIR API. MCP: MCP Client ↔ MCP Server ↔ FHIR API. "The shapes are the same. MCP standardizes the connections."
    - Slide 14: "What would our FHIR tools look like as an MCP server?" Conceptual sketch (not code): server exposes search_conditions, get_patient, etc. Any MCP client (Claude Desktop, IDE plugin, custom app) can discover and use them. "You built the hard part — the tools. MCP is just the packaging."
15. MCP Key Insight: "MCP standardizes HOW tools are called, not HOW WELL the LLM uses them. The failure modes you saw? MCP doesn't fix those. Good schemas, good prompts, and good evaluation do."
16. Your Goals Today: Run 2+ questions, find a failure, document it.
17. The Deliverable: Explain the JSON report and reflection questions. Mention the MCP question.
18. Looking Ahead: "A possible Session 4: actually build an MCP server wrapping these FHIR tools."

**For failure mode screenshots:** These must come from actual Session 3 test runs. When building the Session 3 example completed notebook (Task 6), deliberately capture:
- An agent trace that shows hallucination in the summary
- A trace with a suboptimal tool choice
- A trace where the agent stopped early
- A trace with redundant calls

If clean examples of all four don't naturally occur, they can be provoked by using vague or adversarial questions.

---

## Build Order

Execute tasks in this order:

1. **Task 0: Validate FHIR server** — Stop if critical checks fail
2. **Task 1: Session 1 student notebook** — Build and test all pre-built cells against live server
3. **Task 2: Session 1 example completed notebook** — Fill in student cells, run end-to-end
4. **Task 3: Session 2 student notebook** — Build with dual-provider abstraction, test with Anthropic API
5. **Task 4: Session 2 example completed notebook** — Run agent, capture trace
6. **Task 5: Session 3 student notebook** — Build with expanded tools, test with Anthropic API
7. **Task 6: Session 3 example completed notebook** — Run multiple scenarios, capture failures
8. **Task 7: Batch grading script** — Build and test against Session 3 example output
9. **Task 8: Orientation PDFs** — Build using screenshots from completed notebooks

---

## Testing Checklist

Before delivering any notebook, verify:

- [x] All pip install cells work in Colab
- [x] FHIR server queries return expected data
- [x] All pre-built cells execute without errors in sequence
- [x] Verification cells handle NameError gracefully
- [x] Anthropic API integration works with claude-sonnet-4-20250514
- [x] Content block serialization fix prevents SDK errors
- [x] Agent loop terminates (doesn't hit MAX_STEPS for normal queries)
- [x] Agent produces clinically reasonable summaries
- [x] Tool call traces print clearly
- [ ] Deliverable JSON generates correctly (Session 3 - needs testing)
- [ ] Grading script correctly validates the generated JSON (Task 7 - not yet created)
- [ ] Notebooks are saved with output visible (for example notebooks - Task 2, 4, 6)
- [x] Student notebooks have empty cells actually empty (no leftover test code)

---

## File Manifest

```
fhir_ai_hackathon/
├── validate_fhir_server.py          # Task 0: Server validation
├── validation_results.json           # Task 0: Output
├── notebooks/
│   ├── session1_student.ipynb        # Task 1: Student notebook
│   ├── session1_example_completed.ipynb  # Task 2: Example
│   ├── session2_student.ipynb        # Task 3: Student notebook
│   ├── session2_example_completed.ipynb  # Task 4: Example
│   ├── session3_student.ipynb        # Task 5: Student notebook
│   └── session3_example_completed.ipynb  # Task 6: Example
├── grading/
│   └── grade_session3.py            # Task 7: Grading script
└── orientation/
    ├── pre_session1_orientation.pdf  # Task 8
    ├── pre_session2_orientation.pdf  # Task 8
    └── pre_session3_orientation.pdf  # Task 8
```

---

## Appendix A: Anthropic Tool Use Format Reference

**UPDATE (Feb 2026):** The notebooks now use Anthropic's native tool use format exclusively. This appendix documents the format and includes notes on key differences from OpenAI for reference.

**Tool Definition (Anthropic format):**
```json
{
    "name": "search_conditions",
    "description": "Search for Condition resources by diagnosis code.",
    "input_schema": {
        "type": "object",
        "properties": {
            "code": {"type": "string", "description": "Diagnosis code"},
            "max_results": {"type": "integer", "description": "Max results", "default": 20}
        },
        "required": ["code"]
    }
}
```

**Key differences from OpenAI format:**
- Anthropic uses `input_schema` instead of `parameters`
- Anthropic tools are a flat list (no `type: "function"` wrapper, no nested `function` key)
- Anthropic tool results use `tool_result` content blocks with `tool_use_id`
- Anthropic assistant messages contain `tool_use` content blocks (not `tool_calls`)

**Note:** Since the notebooks are Anthropic-only, no format conversion is needed. Tools are defined directly in Anthropic's format.

**Anthropic message flow with serialization fix:**
```python
# Request
response = client.messages.create(
    model=MODEL,
    max_tokens=4096,
    system=system_prompt,
    tools=tools,  # Anthropic format
    messages=messages  # [{"role": "user", "content": "..."}]
)

# Check for tool use
tool_use_blocks = [b for b in response.content if b.type == "tool_use"]
text_blocks = [b for b in response.content if b.type == "text"]

if not tool_use_blocks:
    # Final answer
    final = "\n".join(b.text for b in text_blocks)
else:
    # Serialize content blocks to avoid SDK errors
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

    # Execute tools and send results back
    tool_results = []
    for block in tool_use_blocks:
        result = available_functions[block.name](**block.input)
        tool_results.append({
            "type": "tool_result",
            "tool_use_id": block.id,
            "content": json.dumps(result, default=str)
        })

    messages.append({"role": "user", "content": tool_results})
```

## Appendix B: FHIR Query Patterns Reference

Quick reference for the FHIR queries used across all sessions:

| Query | URL Pattern | Returns |
|-------|-------------|---------|
| Search conditions by code | `GET /Condition?code=44054006&_count=20` | Bundle of Conditions (SNOMED CT) |
| Get single patient | `GET /Patient/{id}` | Single Patient resource |
| Search observations by patient + LOINC | `GET /Observation?subject=Patient/{id}&code=4548-4&_sort=-date&_count=5` | Bundle of Observations |
| Search medications by patient | `GET /MedicationRequest?subject=Patient/{id}&_count=10&_sort=-date` | Bundle of MedicationRequests |
| Search encounters by patient | `GET /Encounter?subject=Patient/{id}&_count=10&_sort=-date` | Bundle of Encounters |
| Search all conditions for patient | `GET /Condition?subject=Patient/{id}&_count=20` | Bundle of Conditions |
| Search conditions by code (hypertension) | `GET /Condition?code=59621000&_count=20` | Bundle of Conditions (SNOMED CT) |

## Appendix C: FHIR Server Coding Systems

**IMPORTANT:** The FHIR server at https://launch.smarthealthit.org/v/r4/fhir uses **SNOMED CT codes for conditions**, not ICD-10. All condition searches must use SNOMED CT codes.

| Condition | SNOMED CT (USE THIS) | ICD-10 (Reference only) |
|-----------|----------------------|-------------------------|
| Type 2 Diabetes | 44054006 | E11 |
| Hypertension | 59621000 | I10 |
| Prediabetes | 15777000 | R73.03 |

**For observations (lab values, vitals):** The server uses LOINC codes as expected.
