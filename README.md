# FHIR + AI Hackathon

> **Learn clinical informatics and AI agent patterns through hands-on FHIR data exploration**

An educational hackathon for BMI 512 (Clinical Informatics and AI) at Stony Brook
University. Students learn FHIR data querying and AI agent patterns using a "You
Are the Agent" pedagogy — acting as the clinical decision-maker before watching a
Claude agent do the same thing autonomously.

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![FHIR R4](https://img.shields.io/badge/FHIR-R4-green.svg)](https://www.hl7.org/fhir/)
[![Claude Sonnet 4](https://img.shields.io/badge/Claude-Sonnet%204-purple.svg)](https://www.anthropic.com/claude)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## Overview

Students with mixed backgrounds (MDs, PhD students, MS students from CS and
biology) work through a Colab notebook where they:

1. **Act as the agent** — Choose which FHIR queries to run, gather evidence,
   classify patients with diabetes phenotypes, get immediate feedback
2. **Prompt an AI agent** — Write a plain-language prompt, watch Claude
   autonomously query the same FHIR data, compare its strategy to their own

The notebook uses Colab form cells (`#@param` dropdowns) so students interact
purely via menus — no code writing required.

### Current Status

**Phase 0 prototype** built and verified. The demo notebook
(`prototypes/you_are_the_agent_demo.ipynb`) runs end-to-end in both Google
Colab and Vertex AI Workbench against live FHIR data with 1,027 synthetic
patients.

Open design issues from instructor review:
- Combined dropdown UI (query + classify in one menu) is confusing
- Task is too simple — C-peptide alone differentiates T1D vs T2D
- Need richer phenotype scenarios requiring multi-query reasoning

---

## Learning Objectives

By completing this hackathon, students will:

1. Describe an agent loop in plain language (tool call -> result -> next decision)
2. Choose the next FHIR query given a partial patient record and a clinical question
3. Explain why a single data point is not sufficient for clinical classification
4. Decide when an agent's answer is well-supported versus premature
5. Compare their own clinical reasoning strategy to an LLM's tool-calling trace

---

## Quick Start

### For Students

1. Open the notebook in Google Colab (link provided by instructor)
2. Add your `ANTHROPIC_API_KEY` to Colab Secrets (key icon in left sidebar)
3. Run cells top-to-bottom — all interaction is via dropdown menus

### For Instructors / Developers

```bash
# Clone the repository
git clone https://github.com/joelhsaltz/AI-FHIR-HACKATHON.git
cd AI-FHIR-HACKATHON

# Set your API key
cp .env.example .env
# Edit .env and add: ANTHROPIC_API_KEY=your_key_here

# Validate the FHIR server
python instructor_materials/validate_fhir_server.py

# Generate the demo prototype notebook
python create_prototype_demo.py

# Run the smoke test (16 cells, live FHIR data)
python test_demo_notebook.py
```

---

## Clinical Scenario

**Classification task:** Given a working-age adult from the FHIR server, classify
them as Type 1 diabetes, Type 2 diabetes, or no diabetes.

Students have access to 5 FHIR query tools:

| Tool | FHIR Endpoint | What it returns |
|------|---------------|-----------------|
| Get demographics | `GET /Patient/{id}` | Age, gender, DOB |
| Get problem list | `GET /Condition?subject=Patient/{id}` | Conditions (diabetes diagnoses scrambled) |
| Get lab values | `GET /Observation?subject=Patient/{id}&code={loinc}` | HbA1c, C-peptide, BMI, eGFR |
| Get medications | `GET /MedicationRequest?subject=Patient/{id}` | Treatment regimen |
| Get encounters | `GET /Encounter?subject=Patient/{id}` | Visit history |

The candidate pool uses stratified selection (round-robin across T1D, T2D, and
no-diabetes groups) to ensure phenotype variety.

### Key Clinical Codes

| Code | System | Meaning |
|------|--------|---------|
| 46635009 | SNOMED CT | Type 1 Diabetes Mellitus |
| 44054006 | SNOMED CT | Type 2 Diabetes Mellitus |
| 4548-4 | LOINC | HbA1c |
| 1986-9 | LOINC | C-peptide |
| 39156-5 | LOINC | BMI |
| 33914-3 | LOINC | eGFR |

---

## Notebook Verification

Notebooks are verified using a two-stage pipeline:

### Stage 1: Automated (Vertex AI Workbench + Jupyter MCP)

A Google Cloud Vertex AI Workbench instance provides programmatic cell execution
with structured output capture. Claude Code hooks auto-start the instance before
any Jupyter MCP call and auto-stop it when the session ends.

```
generate notebook (create_prototype_demo.py)
  -> validate locally (nb_validate.py + smoke test)
  -> execute via Jupyter MCP (all cells, structured output)
  -> Claude reviews text/HTML/Markdown outputs
  -> fix issues in generator -> regenerate -> re-execute -> iterate
```

**Infrastructure:**
- Vertex AI instance: `fhir-hackathon-instance` (e2-standard-4, us-east4)
- SSH tunnel: localhost:8888 -> remote:8080 (Jupyter)
- MCP server: `uvx mcp-jupyter` with `REQUEST_TIMEOUT=180`
- Auto-start hook: `setup_vertex.sh` (PreToolUse on `mcp__jupyter__*`)
- Auto-stop hook: `stop_vertex.sh` (Stop hook on session end)

**What it verifies (7/10 checklist items):**
Task complexity, case variety, FHIR visibility, feedback quality, activity flow,
game mechanics, clinical plausibility.

### Stage 2: Manual (Instructor Review in Colab)

Three visual items require Colab's rendering engine and cannot be verified
programmatically: UI clarity (dropdown widgets), dashboard readability (rendered
HTML/CSS), code hidden (cellView: form). The instructor reviews these in Colab
after automated testing passes.

### Legacy: Playwright-Based Colab Automation

The original verification pipeline used Playwright browser automation to open
notebooks in Colab, run all cells, and take screenshots. This was replaced by
Vertex AI Workbench due to persistent auth expiry, fragile shadow DOM handling,
and slow iteration cycles. The Playwright tools remain at `scripts/colab-tools/`
for reference but are no longer the primary verification path.

---

## Clinical Agent Pipeline

Four domain-independent AI agents support scenario design and notebook development:

| Agent | Purpose | Invoke |
|-------|---------|--------|
| Clinical Scenario Designer | Design clinical scenarios for any domain | `/scenario-design` |
| Clinical Education Reviewer | Evaluate notebook pedagogy | `/edu-review` |
| Notebook Implementation Reviewer | Pre-flight technical + coherence check | `/nb-preflight` |
| Synthetic Data Architect | Generate phenotype configs for synthetic data | `/synth-data` |

Agents use a three-layer context model: domain-independent identity (AGENT.md) +
per-project context (project-brief.md) + session-specific clinical references.

### Synthetic Data Generation

The `synthetic-ehr/` directory contains a phenotype-driven patient generator
(pure Python, no dependencies). Currently supports 6 diabetes/CKD phenotypes.

```bash
python3 synthetic-ehr/scripts/validate_phenotypes.py --phenotypes synthetic-ehr/assets/phenotype_template.json
python3 synthetic-ehr/scripts/generate_cohort.py --phenotypes <json> --plan <json> --seed 42 --out output.csv
```

---

## Repository Structure

```
fhir-hackathon/
├── prototypes/                     # Phase 0 prototype notebooks
│   └── you_are_the_agent_demo.ipynb
├── src/fhir_hackathon_redesign/    # Core Python modules
│   ├── fhir.py                     # FHIR client + Claude tool schemas
│   ├── scenarios.py                # Scenario configs, state management
│   ├── config.py                   # Settings (API keys, FHIR creds)
│   ├── claude_agent.py             # Claude agent loop
│   └── capstone.py                 # Population ranking helpers
├── create_prototype_demo.py        # Generator for demo prototype notebook
├── test_demo_notebook.py           # Smoke test harness (16 cells, live FHIR)
├── setup_vertex.sh                 # Vertex AI instance start + SSH tunnel
├── stop_vertex.sh                  # Vertex AI instance stop + cleanup
├── synthetic-ehr/                  # Synthetic patient data generator
│   ├── scripts/                    # Generation + validation scripts
│   ├── assets/                     # Phenotype configs
│   └── generated/                  # Output data (gitignored)
├── scripts/colab-tools/            # Playwright-based Colab automation (legacy)
├── docs/                           # Design documents + scenario briefs
│   ├── scenarios/                  # Clinical scenario design docs
│   └── vertex-ai-test-results.md   # Vertex AI capability test report
├── .claude/agents/                 # Clinical agent identities
├── .claude/skills/                 # Agent orchestration skills
├── archive/                        # Old v1/v2/v3 materials
├── student_materials/              # Student-facing materials
├── instructor_materials/           # Instructor materials + FHIR validator
└── docs/                           # Design and architecture docs
```

---

## FHIR Server

| Setting | Value |
|---------|-------|
| URL | `https://lfh-fhir.eastus2.cloudapp.azure.com:9443/fhir-server/api/v4` |
| Auth | HTTP Basic (`fhiruser` / `BmI512@ccess`) |
| TLS | Self-signed certificate (`verify=False`) |
| Dataset | 1,027 synthetic patients across 6 phenotypes |
| FHIR Version | R4 (4.0.1) |

---

## Technical Details

See [TECHNICAL.md](TECHNICAL.md) for architecture, implementation details, and
the Vertex AI infrastructure setup.

See [SPEC.md](SPEC.md) for requirements, scope, and design decisions.

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## Acknowledgments

- **Stony Brook University** Department of Biomedical Informatics
- **Anthropic** for Claude and tool use capabilities
- **HL7** for the FHIR specification
- **Synthea** for synthetic patient data generation patterns
