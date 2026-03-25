# TECHNICAL.md — Architecture and Implementation Guide

## Architecture Overview

### "You Are the Agent" Notebook

```
Activity 1 (Human Mode):
  Student → Colab dropdown menu → Python (hidden) → FHIR Server → Formatted output
                                                                     ↓
                                                              Agent Dashboard
                                                          (evidence + query log)

Activity 2 (AI Agent Mode):
  Student prompt → Claude API (tool_use) → Python tool dispatch → FHIR Server
                        ↑                                            ↓
                        └──────────── tool_result ───────────────────┘
                                          ↓
                                   Comparison table
                              (human accuracy vs agent accuracy)
```

### Notebook Generation Pipeline

Notebooks are generated programmatically — never hand-edited.

```
create_prototype_demo.py → prototypes/you_are_the_agent_demo.ipynb
                                ↓
                      test_demo_notebook.py (local smoke test)
                                ↓
                      Vertex AI Workbench (live FHIR verification)
                                ↓
                      Colab (instructor manual review)
```

## Key Components

### FHIR Tool Functions

Six Python functions wrapping FHIR REST API calls, defined inline in the
generated notebook (no `src/` imports):

| Function | FHIR Endpoint | Purpose |
|----------|---------------|---------|
| `_get_patient(patient_id)` | `GET /Patient/{id}` | Demographics (age, gender, DOB) |
| `_search_all_conditions(patient_id)` | `GET /Condition?subject=...` | Problem list (diabetes codes scrambled) |
| `_search_observations(patient_id, loinc_code)` | `GET /Observation?subject=...&code=...` | Lab values (HbA1c, C-peptide, BMI, eGFR) |
| `_search_medications(patient_id)` | `GET /MedicationRequest?subject=...` | Treatment regimen |
| `_search_encounters(patient_id)` | `GET /Encounter?subject=...` | Visit history |
| `_search_conditions(code)` | `GET /Condition?code=...` | Population search by diagnosis code |

### Condition Scrambling

To prevent answer leakage from the problem list, `_search_all_conditions()` replaces
diabetes-specific SNOMED codes (46635009, 44054006) with plausible non-diabetes
conditions (hypertension, hyperlipidemia, asthma, etc.). Uses a deterministic seed
per patient so the same patient always gets the same fake conditions.

### Candidate Pool Stratification

The candidate pool builder (cell 8) uses round-robin selection across three groups:

1. Query FHIR for patients with T1D conditions (SNOMED 46635009)
2. Query FHIR for patients with T2D conditions (SNOMED 44054006)
3. Query FHIR for non-diabetic patients (no diabetes condition codes)
4. Group by `_group`, shuffle within each group
5. Round-robin pick: T1D -> T2D -> no_diabetes -> repeat until 10 candidates

This produces a ~4/3/3 distribution across phenotypes, verified on live FHIR
data (pool sizes: 46 T1D, 32 T2D, 11 no_diabetes from 1,027 patients).

### Agent Dashboard

The `_render_dashboard()` function produces a Markdown summary showing:
- Current case number and clinical question
- Evidence collected (by FHIR resource type: Patient, Condition, Observation, etc.)
- Still-needed evidence categories with query hints
- Query log (actual FHIR endpoints called)

Updated after every query action and displayed via `display(Markdown(...))`.

### Tool Schemas (Claude API)

Defined in Anthropic's native format for Activity 2 (AI agent mode):

```python
{
    "name": "search_observations",
    "description": "FHIR query: GET /Observation?subject=Patient/{id}&code={loinc}...",
    "input_schema": {
        "type": "object",
        "properties": {
            "patient_id": {"type": "string"},
            "loinc_code": {"type": "string"},
        },
        "required": ["patient_id", "loinc_code"],
    },
}
```

The `_tool_runner()` dispatch maps tool names to local functions. The
`_tool_to_fhir_display()` function converts tool calls to human-readable FHIR
URLs for the agent's query log.

### Agent Loop

The AI agent in Activity 2 uses a standard tool_use loop:

1. Send patient context + prompt + tool schemas to Claude
2. Claude responds with `tool_use` blocks (requesting FHIR queries)
3. Execute each tool call via `_tool_runner()`
4. Append `tool_result` to messages
5. Repeat until Claude responds with text (classification) or hits `max_steps`

Content blocks are manually serialized to plain dicts to avoid Pydantic
serialization errors with the Anthropic SDK.

## FHIR Server

| Setting | Value |
|---------|-------|
| URL | `https://lfh-fhir.eastus2.cloudapp.azure.com:9443/fhir-server/api/v4` |
| Auth | HTTP Basic (`fhiruser` / `BmI512@ccess`) |
| TLS | Self-signed certificate (`verify=False`) |
| Dataset | 1,027 synthetic patients across 6 phenotypes |
| FHIR Version | 4.0.1 |

The server is SBU LinuxForHealth with Synthea-generated synthetic data. Uses
SNOMED CT for conditions (not ICD-10).

## Vertex AI Workbench — Notebook Verification Infrastructure

### Why Vertex AI

The original verification pipeline used Playwright browser automation to open
notebooks in Google Colab, run cells, and take screenshots. This had persistent
problems: auth expiry (Google session cookies), fragile shadow DOM handling,
slow iteration (upload -> open -> run -> screenshot per fix cycle).

Vertex AI Workbench + Jupyter MCP replaces this with programmatic cell execution
and structured output capture (text/HTML/Markdown instead of pixel screenshots).

### Infrastructure

| Component | Value |
|-----------|-------|
| Instance | `fhir-hackathon-instance` (e2-standard-4) |
| GCP Project | `joel-vertex-project` |
| Zone | `us-east4-a` (with fallback to us-east4-b, us-east1-b, us-central1-f) |
| Internal Jupyter Port | 8080 |
| Local Tunnel Port | 8888 |
| MCP Server | `uvx mcp-jupyter` with `REQUEST_TIMEOUT=180` |

### Lifecycle Automation

**`setup_vertex.sh`** — auto-starts the Vertex AI instance and SSH tunnel:
1. Fast-path: if localhost:8888 already responds, exit immediately (<100ms)
2. Find instance across GCP zones, create if not found
3. Start instance if stopped, wait up to 150s
4. Open SSH tunnel (local 8888 -> remote 8080)
5. Health-check Jupyter API with retries

**`stop_vertex.sh`** — stops instance and kills tunnel when session ends.

### Claude Code Hooks

Configured in `.claude/settings.local.json`:
- **PreToolUse** (`mcp__jupyter__*`): runs `setup_vertex.sh --quiet` before any
  Jupyter MCP call — ensures instance is running and tunnel is up
- **Stop**: runs `stop_vertex.sh` when Claude Code exits — conserves credits

### MCP Capabilities

The Jupyter MCP provides 4 tools:
- `setup_notebook` — create or open a notebook
- `query_notebook` — read cell source, outputs, kernel state
- `modify_notebook_cells` — add/edit/delete cells, with optional execution
- `execute_notebook_code` — run arbitrary code in the kernel

Output types returned: `text/plain`, `text/html`, `text/markdown`, `stream`
(stdout/stderr), `error` (with structured ename/evalue/traceback).

### Limitations

- **REQUEST_TIMEOUT**: default 10s causes long-running cells (FHIR queries,
  Claude API calls) to lose output. Fixed with `REQUEST_TIMEOUT=180`.
- **`install_packages`**: MCP's `uv pip` fails without a venv. Use
  `subprocess.run([sys.executable, "-m", "pip", "install", ...])` instead.
- **Colab form cells**: `#@param` dropdowns don't render in Jupyter. Simulate
  by editing the default value in the cell source and re-executing.
- **3 of 10 checklist items** (ui_clarity, dashboard_readability, code_hidden)
  require manual Colab review — they depend on Colab's rendering engine.

Full test results: [docs/vertex-ai-test-results.md](docs/vertex-ai-test-results.md)

## Colab Notebook Tools (Legacy)

The Playwright-based Colab automation tools remain at `scripts/colab-tools/`
for reference. Key scripts:

| Script | Purpose |
|--------|---------|
| `auth_setup.py` | One-time Google sign-in (persistent context + anti-detection args) |
| `colab_screenshot.py` | Run cells + 5-position viewport screenshots |
| `colab_common.py` | Shared Playwright utilities (auth, dialogs, scroll) |
| `nb_validate.py` | Notebook structure + syntax validation |
| `nb_exec_harness.py` | Generic exec() harness for local testing |
| `student_review.py` | Screenshot-based pedagogy review via Claude API |

These tools are superseded by Vertex AI Workbench for automated verification
but may still be useful for final visual checks in Colab.

## Clinical Agent Pipeline

### Three-Layer Context Model

```
Layer 1: AGENT.md — permanent, domain-independent agent identity
Layer 2: project-brief.md — per-project context, auto-loaded
Layer 3: Session context — per-conversation, provided by user
```

Four agents at `.claude/agents/<name>/AGENT.md`:

| Agent | Role | Produces |
|-------|------|----------|
| Clinical Scenario Designer | Design clinical scenarios | `docs/scenarios/*.md` |
| Clinical Education Reviewer | Evaluate pedagogy | Severity-rated review |
| Notebook Implementation Reviewer | Technical + clinical coherence | Pre-flight report |
| Synthetic Data Architect | Phenotype configs for data generation | Phenotype JSON + cohort plans |

### Synthetic EHR Data Generator

Located at `synthetic-ehr/`. Pure stdlib Python, no external dependencies.

Phenotype config format: JSON with anchors (central values), spread (distribution
parameters), and categorical_probs. Clinical coupling layer enforces coherence
(eGFR -> CKD stage, HbA1c -> glucose via ADAG, UACR -> albuminuria stage).

Current phenotypes: 6 diabetes/CKD phenotypes + 3 CKD progression variants.

## Debugging Guide

### Common Issues

**"Connection failed. Check server URL and credentials."**
- FHIR server may be down. Run `python instructor_materials/validate_fhir_server.py`
  to check. If unreachable, ask the SBU admin.

**Cell timeout in Vertex AI (empty output, but cell ran in kernel)**
- Check `REQUEST_TIMEOUT` in the Jupyter MCP config. Must be >= 180 for cells
  that make multiple FHIR queries or Claude API calls.

**"Set ANTHROPIC_API_KEY in Colab Secrets or environment"**
- In Colab: add key to Secrets (key icon in sidebar), name `ANTHROPIC_API_KEY`
- In Vertex AI: set `ANTHROPIC_API_KEY` as an environment variable on the instance

**All candidates are the same phenotype**
- The stratified selection in cell 8 should produce a ~4/3/3 mix. If all candidates
  are the same type, the round-robin logic may have regressed. Check `_by_group`
  sizes in the debug output.

**Agent hits max_steps without final answer**
- Question may be too broad. Try a more specific prompt or increase `max_steps`.

### Modifying Notebooks

1. Edit the generator script (`create_prototype_demo.py`), not the `.ipynb` directly
2. Run `python create_prototype_demo.py` to regenerate
3. Run `python test_demo_notebook.py` for local smoke test
4. Verify in Vertex AI via Jupyter MCP (structured output check)
5. Final visual review in Colab by instructor
