# FHIR + AI Hackathon

A three-session hackathon for BMI 512 (Clinical Informatics and AI) teaching FHIR fundamentals and AI agent patterns.

## Quick Start

### 1. Validate the FHIR Server
```bash
python validate_fhir_server.py
```
This checks that `https://launch.smarthealthit.org/v/r4/fhir` has the data needed for all sessions.

### 2. Test in Google Colab
Upload the student notebooks from `notebooks/` to Google Colab and run them:
- `session1_student.ipynb` — No API keys needed (FHIR server only)
- `session2_student.ipynb` — Needs LLM API key (Claude or Azure OpenAI)
- `session3_student.ipynb` — Needs LLM API key (Claude or Azure OpenAI)

### 3. Configure LLM Provider
In Sessions 2 and 3, set `LLM_PROVIDER` at the top of the notebook:
- `"anthropic"` — Uses Claude (set `ANTHROPIC_API_KEY` in Colab Secrets)
- `"azure_openai"` — Uses GPT-4o (set `AZURE_OPENAI_API_KEY` and `AZURE_OPENAI_ENDPOINT` in Colab Secrets)

## File Structure
```
fhir_hackathon/
├── README.md                         # This file
├── validate_fhir_server.py           # Run first: validates FHIR server data
├── build_notebooks.py                # Generator script (re-run to rebuild notebooks)
├── notebooks/
│   ├── session1_student.ipynb        # Session 1: Manual FHIR queries
│   ├── session2_student.ipynb        # Session 2: Observe tool-use agent
│   └── session3_student.ipynb        # Session 3: Open-ended exploration
├── grading/
│   └── grade_session3.py            # Batch grading for Session 3 submissions
├── tests/
│   └── test_agent_loop.py           # Claude API tool-use validation test
└── orientation/                      # Slide decks (to be generated)
    ├── (pre_session1_orientation.pdf)
    ├── (pre_session2_orientation.pdf)
    └── (pre_session3_orientation.pdf)
```

## Session Overview

| Session | Focus | Duration | LLM Needed? |
|---------|-------|----------|-------------|
| 1 | FHIR fundamentals + Claude code generation | 1 hour | No (web UI only) |
| 2 | Observe agent executing same pipeline | 1 hour | Yes (API) |
| 3 | Open-ended exploration + deliverable | 1 hour | Yes (API) |

## FHIR Server
- **URL:** `https://launch.smarthealthit.org/v/r4/fhir`
- **Auth:** None required (open public sandbox)
- **Data:** Synthea-generated synthetic patients
- **Alternate URL:** `https://r4.smarthealthit.org` (same data)

## Clinical Scenario
""Find patients with Type 2 diabetes (SNOMED CT: 44054006), retrieve their most recent HbA1c values (LOINC: 4548-4), and identify those with poor glycemic control (HbA1c > 7.5%)."

**Note:** The FHIR server uses SNOMED CT codes for conditions, not ICD-10."

## Grading
After Session 3, collect `hackathon_session3_*.json` files and run:
```bash
python grading/grade_session3.py /path/to/submissions/
```
Produces a per-student summary and `grading_summary.csv`.
