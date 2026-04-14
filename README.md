# FHIR Clinical Education Notebook Framework

> **Generate self-contained Colab notebooks that teach clinical informatics
> through hands-on FHIR data querying**

A framework for clinical informatics instructors who want to teach FHIR data
querying and AI agent concepts using real (or synthetic) patient data. Fork the
repo, point it at your FHIR server, and generate notebooks for your course.

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![FHIR R4](https://img.shields.io/badge/FHIR-R4-green.svg)](https://www.hl7.org/fhir/)
[![Claude Sonnet 4](https://img.shields.io/badge/Claude-Sonnet%204-purple.svg)](https://www.anthropic.com/claude)
[![GPT-4.1 mini](https://img.shields.io/badge/GPT--4.1_mini-supported-74aa9c.svg)](https://openai.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/joelhsaltz/AI-FHIR-HACKATHON/blob/main/notebooks/you_are_the_agent_demo.ipynb)

---

## Start Here

**Want to try the notebook?**
[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/joelhsaltz/AI-FHIR-HACKATHON/blob/main/notebooks/you_are_the_agent_demo.ipynb)
One click, no setup. Add your API key to Colab Secrets (see [instructions](#for-students)) and run.

**Want to generate or customize notebooks?**
See [GETTING_STARTED.md](GETTING_STARTED.md) — a focused walkthrough from clone to creating your own scenario.

**Student?**
Your instructor will share a Colab link. You just need an API key — see [For Students](#for-students) below.

---

## What This Is

This repository produces Google Colab notebooks where students explore FHIR
data to answer clinical questions. Every notebook connects to a FHIR R4 server,
presents a clinical scenario, and guides students through structured activities.
All code is hidden behind Colab form cells — students interact through menus
and dropdowns, never Python.

**FHIR is the constant.** The clinical question changes, the activity structure
changes, the pedagogical pattern changes — but the underlying data layer is
always FHIR resources retrieved through standard queries.

### Current Notebook: "You Are the Agent"

Students manually perform an AI agent's job (choosing FHIR queries, interpreting
results, classifying patients), then write a prompt for an AI agent to do the
same thing autonomously and compare strategies. The scenario is diabetes
management complexity assessment. Students choose their AI provider (Anthropic
or OpenAI) via a dropdown.

### For Students

1. Open the notebook link your instructor provides (Google Colab)
2. Add your API key to Colab Secrets (key icon in left sidebar):
   - **Anthropic users:** add `ANTHROPIC_API_KEY`
   - **OpenAI users:** add `OPENAI_API_KEY`
   - Toggle **Notebook access** ON for the secret
3. In Step 1, select your **AI Provider** from the dropdown
4. Run cells top-to-bottom — all interaction is via dropdown menus

> Step 1 validates your API key immediately. If there's a problem, you'll see
> a clear error with instructions. Activity 1 works without an API key;
> Activity 2 requires one.

---

## For Faculty: Generate and Customize

### Run the existing notebook locally

```bash
# 1. Clone the repository
git clone https://github.com/joelhsaltz/AI-FHIR-HACKATHON.git
cd AI-FHIR-HACKATHON

# 2. Configure credentials
cp .env.example .env
# Edit .env — add your ANTHROPIC_API_KEY or OPENAI_API_KEY

# 3. Validate the FHIR server
python scripts/validate_fhir_server.py

# 4. Generate the notebook
python create_prototype_demo.py
# Output: notebooks/you_are_the_agent_demo.ipynb

# 5. Run the smoke test
python test_demo_notebook.py
```

### Create a new scenario

See [GETTING_STARTED.md](GETTING_STARTED.md) for the full walkthrough, or
the short version:

1. **Design the scenario** — `docs/scenarios/<name>.md` (or use `/scenario-design`)
2. **Generate synthetic data** (if needed) — `synthetic-ehr/` pipeline
3. **Write a generator script** — follow `create_prototype_demo.py`
4. **Write a smoke test** — follow `test_demo_notebook.py`
5. **Verify in Colab** — generate, upload, run all cells against live FHIR data

> **Guardrails for Claude Code users:** Hooks enforce verification before
> distribution and block incorrect Vertex AI commands. See
> [TECHNICAL.md](TECHNICAL.md#claude-code-hooks).

---

## How It Works

```
Scenario design doc          Generator script           Google Colab
(docs/scenarios/*.md)   -->  (create_*.py)         -->  Self-contained notebook
                                                        (all code hidden, form cells)
        |                           |
        v                           v
  Phenotype configs          Smoke test script
  (synthetic-ehr/)           (test_*_notebook.py)
```

---

## Architecture at a Glance

### What's shared across all use cases

- **FHIR connection** — Client initialization, connectivity test, credential handling
- **Tool definitions** — Standard FHIR query tools (`get_patient`, `search_conditions`,
  `search_observations`, `search_medications`, `search_encounters`) with
  provider-neutral tool schemas
- **Provider adapter** — Three-function abstraction layer supporting Anthropic and
  OpenAI with unified tool calling semantics
- **Generator pattern** — String constants, cell assembly, `json.dump()` to `.ipynb`
- **Verification pipeline** — Local smoke test + automated Colab execution
- **Agent pipeline** — Four specialized agents for scenario design and review

### What varies per use case

- **Activity structure** — The cell sequence after setup depends on the educational design
- **Clinical tools** — Scenarios may add domain-specific tools (e.g., `search_uacr`
  for kidney assessment)
- **Pedagogy** — "You Are the Agent" is one pattern; future use cases define their own

### Repository Structure

```
fhir-hackathon/
├── notebooks/                      # Distributable notebooks (current artifacts)
│   └── you_are_the_agent_demo.ipynb
├── create_prototype_demo.py        # Generator: diabetes complexity notebook
├── test_demo_notebook.py           # Smoke test (16 cells, live FHIR)
├── synthetic-ehr/                  # Synthetic patient data pipeline
│   ├── scripts/                    # Generation + validation scripts
│   ├── assets/                     # Phenotype configs (JSON)
│   └── generated/                  # Output data (gitignored)
├── docs/                           # Design documents
│   ├── scenarios/                  # Scenario design docs (shared artifacts)
│   ├── LESSONS_LEARNED.md          # Institutional knowledge
│   └── run_agent_explained.md      # Agent loop explainer for students
├── scripts/                        # Utility scripts
│   ├── validate_fhir_server.py     # FHIR server validation
│   ├── check_notebook_verified.sh  # PreToolUse hook
│   └── check_gcloud_workbench.sh   # PreToolUse hook
├── .claude/agents/                 # Clinical agent identities (AGENT.md)
├── .claude/skills/                 # Agent orchestration skills
├── tests/vertex_ai/                # Vertex AI test notebooks
└── archive/                        # Old v1/v2/v3 materials, legacy tools
```

---

## Clinical Agent Pipeline

Four specialized agents support the end-to-end workflow from scenario idea to
shipped notebook. Each has a domain-independent identity (`AGENT.md`) plus
per-project context (`project-brief.md`). Agents communicate through scenario
design documents and query/response files.

| Agent | Trigger | What it does |
|-------|---------|-------------|
| **Clinical Scenario Designer** | `/scenario-design` | Designs clinical scenarios: question, evidence requirements, difficulty calibration, ambiguity placement. Has access to ICD-10, PubMed, and bioRxiv for clinical grounding. |
| **Synthetic Data Architect** | `/synth-data` | Translates scenario designs into phenotype configs for the synthetic EHR generator. Maps clinical requirements to data parameters. |
| **Clinical Education Reviewer** | `/edu-review` | Evaluates whether a notebook delivers on its learning objectives. Applies the "Bored or Baffled" framework. Produces severity-rated review. |
| **Notebook Implementation Reviewer** | `/nb-preflight` | Pre-flight technical check: form syntax, cell dependencies, Run All compatibility, clinical coherence against the scenario design. |

The full agent architecture, decision boundaries, and communication protocol are
documented in [SPEC.md](SPEC.md#clinical-agent-pipeline) and
[TECHNICAL.md](TECHNICAL.md#clinical-agent-pipeline).

---

## Existing Scenarios

| Scenario | Clinical Question | Status | Design Doc |
|----------|------------------|--------|------------|
| Diabetes management complexity | How complex is this patient's diabetes management? | Prototype built and verified | [`diabetes-type-classification.md`](docs/scenarios/diabetes-type-classification.md) |
| Autoimmune differential | Differential diagnosis with overlapping autoimmune features | Designed, not implemented | [`autoimmune-differential.md`](docs/scenarios/autoimmune-differential.md) |
| CKD progression risk | Risk stratification for chronic kidney disease progression | Designed, not implemented | [`ckd-progression-risk.md`](docs/scenarios/ckd-progression-risk.md) |
| CLL follow-up therapy | Therapy selection for chronic lymphocytic leukemia follow-up | Designed, not implemented | [`cll-follow-up-therapy-selection.md`](docs/scenarios/cll-follow-up-therapy-selection.md) |

---

## AI Provider Support

Notebooks support both **Anthropic** (Claude) and **OpenAI** (GPT) as AI
providers for agent activities. Students select their provider via a dropdown
in Step 1 — no code changes needed.

| Provider | Model | Secret Name | Notes |
|----------|-------|-------------|-------|
| **Anthropic** | `claude-sonnet-4-20250514` | `ANTHROPIC_API_KEY` | Default. Best clinical reasoning accuracy in testing. |
| **OpenAI** | `gpt-4.1-mini` | `OPENAI_API_KEY` | Widely available. Many students already have OpenAI keys. |

**Activity 1** (human agent mode) does not require an API key — it uses only
FHIR queries. **Activity 2** (AI agent mode) requires a key for the selected
provider.

The provider dropdown controls everything: which SDK is installed, which API
key is loaded from Colab Secrets, and how tool calls are serialized. Students
using different providers in the same class will see the same FHIR queries and
clinical data but may see different agent reasoning strategies.

**For instructors:** Both providers are verified end-to-end against live FHIR
data. The choice depends on what keys your students have access to. If your
institution provides OpenAI keys, students can use those. If students have
Anthropic keys, they get slightly better clinical reasoning accuracy (100% vs
67% on the diabetes complexity benchmark with default prompts), but either
provider produces a valid learning experience.

**Azure AI Foundry note:** If your institution provides OpenAI access through
Azure AI Foundry, those keys use the `AzureOpenAI` client class with an
endpoint URL and API version. The current framework uses the standard `OpenAI`
client. For now, use a direct OpenAI key (from platform.openai.com) or an
Anthropic key. Azure support is planned for a future update.

---

## Prerequisites

| Requirement | Details |
|-------------|---------|
| **Python** | 3.10+ |
| **FHIR R4 server** | Any FHIR R4 server with patient data. The SBU teaching server is pre-configured. |
| **AI API key** | Anthropic or OpenAI key for AI agent activities. Students add theirs via Colab Secrets. |
| **Google Colab** | Student delivery platform. Free tier is sufficient. |

---

## Configuration

All configuration is in a `.env` file at the repository root. Copy the example
and fill in your values:

```bash
cp .env.example .env
```

| Variable | Required | Default | Purpose |
|----------|----------|---------|---------|
| `ANTHROPIC_API_KEY` | One of these | — | Claude API key for AI agent activities |
| `OPENAI_API_KEY` | required | — | OpenAI API key (alternative to Anthropic) |
| `FHIR_BASE` | No | SBU teaching server | FHIR R4 server base URL |
| `FHIR_USERNAME` | No | `fhiruser` | HTTP Basic auth username |
| `FHIR_PASSWORD` | No | `BmI512@ccess` | HTTP Basic auth password |

At least one API key is required for Activity 2 (AI agent mode). Activity 1
works without any API key.

To connect your own FHIR server, update the three `FHIR_*` variables. The server
must support FHIR R4 and contain patient data for your scenarios. See
[TECHNICAL.md](TECHNICAL.md#fhir-server-configuration) for details.

In generated notebooks, the teaching server credentials are hardcoded to minimize
student setup friction. Students only need to provide their API key (`ANTHROPIC_API_KEY`
or `OPENAI_API_KEY`) via Colab Secrets and select their provider in the dropdown.

---

## Learning Objectives

Across all scenarios, students develop:

1. Conceptual understanding of FHIR as a data standard — resources, queries,
   what you can and cannot ask for
2. Ability to choose the next query given a partial patient record and a clinical
   question
3. Understanding that single data points are rarely sufficient for clinical
   decisions
4. Awareness of AI agent mechanics — tool calls, evidence gathering, reasoning
   chains
5. Ability to evaluate whether an AI agent's clinical reasoning is well-supported

Individual scenarios add their own learning goals (e.g., "explain why kidney
function complicates diabetes management").

---

## Key Commands

```bash
# Generate and test the demo notebook
python create_prototype_demo.py
python test_demo_notebook.py

# Validate FHIR server connectivity
python scripts/validate_fhir_server.py

# Synthetic data pipeline
python3 synthetic-ehr/scripts/validate_phenotypes.py \
  --phenotypes synthetic-ehr/assets/phenotype_template.json
python3 synthetic-ehr/scripts/generate_cohort.py \
  --phenotypes <json> --plan <json> --seed 42 --out output.csv
```

---

## Further Reading

| Document | What it covers |
|----------|---------------|
| [SPEC.md](SPEC.md) | Framework requirements, scenario template specification, design decisions, verification standards |
| [TECHNICAL.md](TECHNICAL.md) | Architecture deep-dive, generator pattern guide, agent pipeline details, FHIR tool definitions, Vertex AI infrastructure |
| [docs/LESSONS_LEARNED.md](docs/LESSONS_LEARNED.md) | Institutional knowledge: infrastructure pivots, Colab gotchas, verification failures, scenario design pitfalls |

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file
for details.

---

## Acknowledgments

- **Stony Brook University** Department of Biomedical Informatics
- **Anthropic** for Claude and tool use capabilities
- **OpenAI** for GPT model access and tool use capabilities
- **HL7** for the FHIR specification
- **Synthea** for synthetic patient data generation patterns
