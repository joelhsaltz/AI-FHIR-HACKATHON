# TECHNICAL.md — Architecture and Implementation Guide

This is the deep technical reference for the FHIR Clinical Education Notebook
Framework. For requirements and design decisions, see [SPEC.md](SPEC.md).

---

## Architecture Overview

### Framework Architecture

```
Scenario Design Doc (docs/scenarios/*.md)
        │
        ├──→ Generator Script (create_*.py) ──→ Notebook (.ipynb)
        │                                            │
        ├──→ Synthetic Data Architect ──→ Phenotype configs     │
        │         (synthetic-ehr/assets/)             │
        │                                             ↓
        │                                    Smoke Test (test_*.py)
        │                                             │
        │                                             ↓
        │                                    Vertex AI Workbench
        │                                    (live FHIR verification)
        │                                             │
        │                                             ↓
        └──→ Reviewers (edu-review, nb-preflight) ──→ Instructor Review
```

### What Is Fixed vs. What Varies

**Fixed across all use cases:** FHIR server connection (R4, configurable via
`.env`), generator pattern (string constants, cell helpers, `json.dump()`),
verification pipeline (smoke test, Vertex AI, instructor review), agent
pipeline (four agents with shared communication protocol), notebook boilerplate
(pip install, FHIR connection check, tool definitions).

**Varies per use case:** Clinical question and classification categories,
activity structure and pedagogy, FHIR tools needed, UI pattern, state
management schema.

### Notebook Runtime Architecture (Example)

The current "You Are the Agent" prototype uses a two-activity design. This is
one pedagogical pattern, not the archetype.

```
Activity 1 (Human Mode):
  Student → Colab dropdown → Python (hidden) → FHIR Server → Formatted output
                                                                   ↓
                                                            Agent Dashboard

Activity 2 (AI Agent Mode):
  Student prompt → Provider Adapter → LLM API (tool calls) → tool dispatch → FHIR Server
                        ↑                                                         ↓
                        └──────────────────── tool results ──────────────────────┘
```

The Provider Adapter normalizes differences between Anthropic and OpenAI tool
calling formats. See [API-Agnostic Provider Support](#api-agnostic-provider-support)
for the implementation.

### Agent Pipeline

```
/scenario-design ──→ docs/scenarios/<name>.md
                            │
        ┌───────────────────┼───────────────────┐
        ↓                   ↓                   ↓
/synth-data          Generator Script     /nb-preflight
(phenotype configs)  (notebook)           /edu-review
```

---

## Generator Pattern

### How Generators Work

Generator scripts produce `.ipynb` files programmatically. All notebook code
is defined as string constants in the generator. The reference implementation
is `create_prototype_demo.py`.

**Three helper functions** (copy these into any new generator):

- `md_cell(source)` — creates a Markdown cell
- `form_cell(source)` — creates a code cell with `cellView: "form"` metadata
  (code hidden from students). Splits source into individual lines for Colab's
  `#@param` parser.
- `build_notebook(cells)` — wraps a cell list in nbformat 4 with Colab metadata

**String constants** for each cell's code, using `r"""..."""` to avoid escape
issues. Each begins with `#@title Step N: ...` for Colab's form renderer.
**Note:** Raw strings are correct for code cells but not for strings passed to
`display(Markdown(...))` — raw strings produce literal `\n` instead of newlines.
See `docs/LESSONS_LEARNED.md` § Colab-Specific Gotchas.

```python
SETUP = r"""
#@title Step 1: Connect to the FHIR server
AI_PROVIDER = "Anthropic" #@param ["Anthropic", "OpenAI"]
import subprocess, sys
# Install only the selected provider's SDK
_provider_pkg = {"Anthropic": "anthropic", "OpenAI": "openai"}[AI_PROVIDER]
subprocess.check_call(
    [sys.executable, "-m", "pip", "install", "-q", _provider_pkg, "requests", "pandas"],
    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
)
# ... FHIR connection, provider adapter, connectivity check ...
""".strip()
```

**Cell assembly** at the bottom — arrange cells in order and write JSON:

```python
cells = [
    md_cell("# Title\n\n..."),
    form_cell(SETUP),
    form_cell(TOOLS),
    # ... activity-specific cells ...
]
nb = build_notebook(cells)
with open(OUTPUT_PATH, "w") as f:
    json.dump(nb, f, indent=1)
```

### Creating a New Generator

1. **Start from the scenario design document** (`docs/scenarios/<name>.md`).
2. **Copy the shared cell groups** from an existing generator:

   | Cell | Purpose |
   |------|---------|
   | Title markdown | Notebook title and clinical context |
   | Setup + connection | pip install, imports, FHIR client, connectivity check |
   | Tool definitions | FHIR query functions, tool schemas, tool dispatch |
   | Validation | Quick FHIR query to confirm data access |

3. **Define activity-specific cells.** These vary entirely by use case.
4. **Add scenario-specific FHIR tools** if needed (see Adding Tools below).
5. **Define ground truth** via `_get_ground_truth(patient_id)` for scoring.
6. **Write a corresponding smoke test** (see below).
7. **Register** in CLAUDE.md's Key Commands and Key Files tables.

### Smoke Test Pattern

Each generator has a smoke test (e.g., `test_demo_notebook.py`) that:
- Loads the generated `.ipynb` and extracts code cells with titles
- Creates a shared namespace for sequential `exec()` execution
- Strips `#@param` annotations and replaces with concrete test values
- Skips LLM-dependent cells (agent runs, summaries)
- Applies per-cell timeouts via `signal.SIGALRM` (180s for setup, 60s for queries)
- Reports PASS/FAIL per cell with timing

The smoke test validates technical correctness but does NOT replace Colab
verification.

---

## FHIR Tool Definitions

### Standard Tool Set

| Function | FHIR Endpoint | Purpose |
|----------|---------------|---------|
| `_get_patient(patient_id)` | `GET /Patient/{id}` | Demographics (age, gender, DOB) |
| `_search_all_conditions(patient_id)` | `GET /Condition?subject=...` | Problem list (diabetes codes scrambled) |
| `_search_observations(patient_id, loinc_code)` | `GET /Observation?subject=...&code=...` | Lab values (HbA1c, C-peptide, BMI, eGFR, UACR) |
| `_search_medications(patient_id)` | `GET /MedicationRequest?subject=...` | Treatment regimen |
| `_search_encounters(patient_id)` | `GET /Encounter?subject=...` | Visit history |
| `_search_conditions(code)` | `GET /Condition?code=...` | Population search by diagnosis code |
| `_fhir_get(path, params)` | `GET /<path>` | Low-level GET with display URL generation |

All functions return `(fhir_url, result)` where `fhir_url` is a human-readable
query string for the student-facing FHIR query banner.

### Condition Scrambling

`_search_all_conditions()` replaces diabetes-specific SNOMED codes (46635009,
44054006) with plausible non-diabetes conditions (hypertension, hyperlipidemia,
asthma, etc.). Uses a deterministic seed per patient (MD5 hash of patient ID)
so the same patient always gets the same replacement conditions.

### Candidate Pool Stratification

Round-robin selection across three groups (T1D, T2D, no_diabetes):
1. Query FHIR for patients with T1D/T2D conditions
2. Query FHIR for non-diabetic patients
3. Group by phenotype, shuffle within each group
4. Round-robin pick until 10 candidates (~4/3/3 distribution)

### Adding Scenario-Specific Tools

To add a tool beyond the standard set:

1. Define the Python function following the `(fhir_url, result)` return pattern
2. Add a Claude tool schema to `CLAUDE_TOOLS` (Anthropic `input_schema` format)
3. Register in `_tool_runner()` for agent dispatch
4. Register in `_tool_to_fhir_display()` for the query log

Tool schemas use a **provider-neutral format** with `"parameters"` instead of
Anthropic's `"input_schema"`. The provider adapter converts to each provider's
native format at call time:

```python
{
    "name": "search_observations",
    "description": "FHIR query: GET /Observation?subject=Patient/{id}&code={loinc}...",
    "parameters": {
        "type": "object",
        "properties": {
            "patient_id": {"type": "string"},
            "loinc_code": {"type": "string"},
        },
        "required": ["patient_id", "loinc_code"],
    },
}
```

The adapter converts `"parameters"` to `"input_schema"` for Anthropic and wraps
in `{"type": "function", "function": {...}}` for OpenAI. See
[API-Agnostic Provider Support](#api-agnostic-provider-support) for details.

### Agent Loop

The AI agent uses a standard tool-calling loop: send context + tools to the LLM,
execute tool calls via `_tool_runner()`, append tool results, repeat until text
response or `max_steps`. The provider adapter normalizes tool call and tool
result serialization for each provider. Content blocks are manually serialized
to plain dicts to avoid Pydantic serialization errors.

---

## API-Agnostic Provider Support

### Why a Custom Adapter (Not LangChain)

LangChain was evaluated and rejected for three reasons:

1. **Too heavy for Colab.** LangChain pulls in 50+ transitive dependencies.
   Colab `pip install` for the full chain takes 30-60 seconds and pollutes the
   student's environment with packages they'll never see or understand.
2. **Unstable API.** LangChain's abstractions change frequently. A notebook
   that works today may break next semester when LangChain updates.
3. **Too many abstraction layers.** Students are learning how AI agents work.
   A 3-function adapter they can read (if they look) is better than a framework
   that hides the mechanics.

The adapter is intentionally thin: three functions, ~80 lines of code, inlined
in the generated notebook's setup cell.

### Architecture

The provider adapter sits between the agent loop and the LLM API. All
provider-specific logic is isolated in three functions:

```
Agent loop (provider-agnostic)
       │
       ├── _llm_create(messages, system, tools) → (text, tool_calls, raw_response)
       ├── _llm_serialize_assistant(raw_response) → message dict
       └── _llm_format_tool_results(results) → list of message dicts
       │
       ├── Anthropic: messages.create() with input_schema, tool_use/tool_result
       └── OpenAI: chat.completions.create() with functions, tool_calls/tool role
```

### The Three Functions

**`_llm_create(messages, system, tools, max_tokens=4096)`**

Sends a message to the LLM and returns a normalized tuple:
- `text` — the model's text response (empty string if tool calls only)
- `tool_calls` — list of `{"id", "name", "arguments"}` dicts (provider-neutral)
- `raw_response` — the provider's raw response object (for serialization)

Provider differences handled:
- Anthropic uses a separate `system` parameter; OpenAI prepends a system message
- Anthropic uses `input_schema` in tool definitions; OpenAI uses nested
  `{"type": "function", "function": {"parameters": ...}}`
- Anthropic returns `content` blocks with `type: "tool_use"`; OpenAI returns
  `tool_calls` on the message object

**`_llm_serialize_assistant(raw_response)`**

Converts the provider's raw response into a message dict for the conversation
history. Each provider has its own message format:
- Anthropic: `{"role": "assistant", "content": [{"type": "text"}, {"type": "tool_use", "id", "name", "input"}]}`
- OpenAI: `{"role": "assistant", "content": "...", "tool_calls": [{"id", "type": "function", "function": {"name", "arguments"}}]}`

**`_llm_format_tool_results(results)`**

Converts tool execution results into message(s) for the conversation history:
- Input: `[{"call_id": "...", "output": "..."}]` (provider-neutral)
- Anthropic: Single user message with `tool_result` content blocks
- OpenAI: One message per tool result with `role: "tool"` and `tool_call_id`

### Provider Selection Flow

In the generated notebook, provider selection happens in Step 1:

1. Student selects `AI_PROVIDER` from the Colab dropdown (`"Anthropic"` or `"OpenAI"`)
2. Only the selected provider's SDK is `pip install`ed (faster, smaller footprint)
3. The API key is loaded from Colab Secrets using the provider-specific name
   (`ANTHROPIC_API_KEY` or `OPENAI_API_KEY`)
4. The LLM client is initialized with the appropriate SDK class
5. The three adapter functions dispatch on `_PROVIDER` (lowercase string)

Activity 1 (human agent mode) does not use the LLM client at all — students
query FHIR directly. The provider selection only matters for Activity 2.

### Tool Schema Format

Tool schemas use a **provider-neutral format** stored in `CLAUDE_TOOLS`:

```python
CLAUDE_TOOLS = [
    {
        "name": "get_patient",
        "description": "...",
        "parameters": {                    # Not "input_schema"
            "type": "object",
            "properties": {...},
            "required": [...]
        }
    }
]
```

The adapter converts at call time:
- **Anthropic:** `{"name", "description", "input_schema": tool["parameters"]}`
- **OpenAI:** `{"type": "function", "function": {"name", "description", "parameters": tool["parameters"]}}`

### Default Models

| Provider | Default Model | Rationale |
|----------|---------------|-----------|
| Anthropic | `claude-sonnet-4-20250514` | Best tool-use accuracy, strong clinical reasoning |
| OpenAI | `gpt-4.1-mini` | Good balance of cost, speed, and tool-use capability |

Models are set in `_DEFAULT_MODELS` in the setup cell. To change the default
for a deployment, edit the generator's `SETUP` constant.

### Verified Behavior

Both providers tested end-to-end on Vertex AI Workbench against live FHIR data
(2026-03-28):

| Provider | Accuracy | Avg Queries | Tool Calling | Message Serialization |
|----------|----------|-------------|--------------|----------------------|
| Anthropic | 6/6 (100%) | 6.3 | Works | Works |
| OpenAI | 4/6 (67%) | 5.0 | Works | Works |

OpenAI's lower accuracy reflects clinical reasoning differences (missed
complexity indicators), not technical failures. The adapter, tool calling,
and message serialization work identically for both providers.

---

## State Management

### Session State Dictionary

The prototype uses `_state` as the single source of truth. All cells read from
and write to this dictionary:

```python
_state = {
    "question": "...",           # Clinical question
    "num_cases": 0,              # How many cases to work
    "case_patients": [],         # List of candidate dicts
    "current_case_idx": 0,       # Current case
    "patient_id": None,          # Current patient ID
    "patient_label": None,       # Display name
    "history": [],               # Query log [{step, fhir_query, note}]
    "evidence": {},              # Evidence by category name
    "correct_answer": None,      # Ground truth
    "human_results": [],         # Activity 1 results (accumulates)
    "agent_runs": [],            # Activity 2 results
    "agent_prompt": "",          # Student's prompt
}
```

- `evidence` is keyed by category (e.g., `"hba1c"`, `"conditions"`), not by
  FHIR resource type, because multiple categories map to Observation.
- `history` and `evidence` reset when advancing to the next case;
  `human_results` accumulates across cases.

### Agent Dashboard

`_render_dashboard()` reads `_state["evidence"]` and renders a Markdown table
showing collected evidence (grouped by FHIR resource type), an evidence counter
(`3 of 8 query types used`), and the query log. Updated after every query.

### Adapting for New Use Cases

New scenarios define their own `_state` schema. Keep `evidence` and `history`
for iterative querying scenarios. Add scoring fields appropriate to the
activity. Implement a dashboard or summary function for student feedback.

---

## Clinical Agent Pipeline

### Three-Layer Context Model

```
Layer 1: AGENT.md      — permanent, domain-independent identity
         .claude/agents/<name>/AGENT.md

Layer 2: project-brief.md — per-project context (course, FHIR server, codes)
         .claude/agents/project-brief.md

Layer 3: Session context — per-conversation (task, constraints, references)
```

Agent identities are reusable. A different course uses the same AGENT.md files
with a different project-brief.md.

### The Four Agents

**1. Clinical Scenario Designer** (`/scenario-design`)
Identity: `.claude/agents/clinical-scenario-designer/AGENT.md`
Tools: Read, Glob, Grep, WebSearch, WebFetch, ICD-10 MCP, PubMed MCP, bioRxiv MCP

Designs clinical scenarios from three perspectives: clinician (what evidence
matters), dataset architect (what queries are needed), teacher (is this
non-trivial). Applies six evaluation tests: single-query shortcut, evidence
type diversity, ambiguity, clinical plausibility, data availability, difficulty
calibration.

*Decides:* Clinical question, categories, evidence types, difficulty.
*Does not decide:* Code, cell layout, data generation parameters.
*Produces:* `docs/scenarios/<name>.md`
*Escalates:* Data availability (to Synth Data), difficulty calibration (to Edu Review).

**2. Synthetic Data Architect** (`/synth-data`)
Identity: `.claude/agents/synthetic-data-architect/AGENT.md`
Tools: Read, Glob, Grep, Bash, ICD-10 MCP, PubMed MCP

Translates scenario designs into phenotype configs: anchors, spread
distributions, categorical probabilities, coupling constraints. Runs test
batches and validates clinical plausibility.

*Decides:* Phenotype parameters, cohort composition, coupling constraints.
*Does not decide:* Clinical question, categories, pedagogy.
*Produces:* Phenotype JSON configs, cohort plans, variable extension specs.
*Escalates:* Missing generator variables (produces spec), ambiguous anchors (to Scenario Designer).

**3. Clinical Education Reviewer** (`/edu-review`)
Identity: `.claude/agents/clinical-education-reviewer/AGENT.md`
Tools: Read, Glob, Grep, WebSearch, WebFetch, ICD-10 MCP, PubMed MCP

Evaluates pedagogy using the "Bored or Baffled" framework. Checks for:
passive observation, trivially solvable tasks, missing feedback, false agency,
opaque AI, code walls. Produces severity-rated reviews (`blocks-learning`,
`reduces-engagement`, `cosmetic`).

*Decides:* Learning quality, activity design, difficulty calibration.
*Does not decide:* Clinical thresholds, code, technical correctness.
*Escalates:* Clinical accuracy (to Scenario Designer), technical UX issues (to Impl Reviewer).

**4. Notebook Implementation Reviewer** (`/nb-preflight`)
Identity: `.claude/agents/notebook-implementation-reviewer/AGENT.md`
Tools: Read, Glob, Grep, WebSearch

Checks 10 categories: form/widget syntax, string escaping, cell dependencies,
Run All compatibility, package installation, secrets handling, data query
patterns, output/display, code visibility, generator consistency. Also performs
clinical coherence check against the scenario design document.

*Decides:* Technical correctness, Colab compatibility, scenario coherence.
*Does not decide:* Pedagogy, scenario design, data generation.
*Escalates:* Tech/pedagogy conflicts (to Edu Reviewer), scenario drift (to Scenario Designer).
*Run BEFORE Colab verification* — no point verifying rendering of broken code.

### Inter-Agent Communication Protocol

**Primary shared artifact:** Scenario design documents (`docs/scenarios/*.md`).
The Scenario Designer produces them; all other agents consume them.

**Cross-domain decisions** use files in `agent-history/`:

| Directory | Purpose | Format |
|-----------|---------|--------|
| `comms/queries/` | Decisions outside an agent's domain | `<timestamp>-<from>-to-<target>.md` |
| `comms/responses/` | Answered queries | `<timestamp>-<responder>-re-<query>.md` |
| `sessions/` | Cross-conversation context | `<agent>-<topic>.md` |

**Decision boundary rule:** Agents flag decisions outside their domain rather
than making them. The cost of a false alarm is one query file. The cost of a
wrong assumption is a broken teaching experience.

### End-to-End Workflow

1. `/scenario-design` produces `docs/scenarios/<name>.md`
2. `/synth-data` consumes scenario doc, produces phenotype configs + patient data
3. Generator script consumes scenario doc + data, produces notebook
4. `/nb-preflight` checks technical correctness and clinical coherence
5. `/edu-review` evaluates pedagogical quality
6. Smoke test + Vertex AI verification with live FHIR data
7. Instructor reviews, merges, distributes

---

## Synthetic EHR Data Pipeline

Located at `synthetic-ehr/`. Pure stdlib Python, no external dependencies.

### Phenotype Config Format

```json
{
  "variables_order": ["age", "sex_at_birth", "hba1c", "..."],
  "phenotypes": [{
    "id": "clear_type1",
    "name": "Clear Type 1 Diabetes",
    "anchors": {"age": 28, "hba1c": 8.5, "c_peptide": 0.3},
    "spread": {"age": {"dist": "truncnorm", "sd": 8}},
    "categorical_probs": {"insulin_use": {"yes": 0.95, "no": 0.05}}
  }]
}
```

**Coupling constraints** (in `generate_patients.py`): eGFR determines CKD
stage, HbA1c aligns with glucose via ADAG, UACR determines albuminuria stage.
Non-ESRD floor: eGFR clamped at >= 15.

### Pipeline Commands

```bash
# Validate config
python3 synthetic-ehr/scripts/validate_phenotypes.py --phenotypes <config.json>

# Generate cohort
python3 synthetic-ehr/scripts/generate_cohort.py \
    --phenotypes <config.json> --plan <plan.json> --seed 42 \
    --out <output.csv> --summary-out <summary.json>

# Validate output
python3 synthetic-ehr/scripts/validate_patients.py --input <output.csv>

# Export to FHIR R4
python3 synthetic-ehr/scripts/export_fhir_r4_bundle.py \
    --input <output.csv> --output-dir <bundle-dir/>
```

### Adding Phenotypes

Use `add_phenotype.py` for clone-and-override from existing phenotypes. For
new domains requiring new variables, the Synthetic Data Architect produces a
variable extension spec documenting new variables, types, bounds, and coupling
rules. The FHIR server currently has 6 diabetes/CKD phenotypes loaded
(1,027 patients). Additional phenotype configs exist in the pipeline but are
not yet loaded to the server.

---

## Verification Infrastructure

### Vertex AI Workbench

Replaces Playwright-based Colab automation with programmatic cell execution
and structured output capture.

| Component | Value |
|-----------|-------|
| Instance | `fhir-hackathon-instance` (e2-standard-4) |
| GCP Project | `joel-vertex-project` |
| Zone | Auto-discovered via `gcloud compute instances list` |
| Jupyter | Port 8080 (remote) tunneled to 8888 (local) |
| MCP Server | `uvx mcp-jupyter` with `REQUEST_TIMEOUT=180` |
| Idle Shutdown | 60 min via `idle-timeout-seconds` metadata |

### Important: Workbench Instances Are Managed Resources

**Never use `gcloud compute instances start/stop/delete` on Workbench instances.**
The Notebooks API places a mutation lock on the underlying Compute Engine VM.
Even `roles/owner` gets a 403. Use `gcloud workbench instances start/stop` for
mutations. Read-only `gcloud compute` commands (describe, list, ssh) still work.
The `/colab-mcp` skill and `setup_vertex.sh` handle this correctly.

### Lifecycle Scripts

**`setup_vertex.sh`** — runs as a PreToolUse hook before any `mcp__jupyter__*`
call:
1. Fast-path: if localhost:8888 responds, exit (<100ms)
2. Discover instance across zones (single `gcloud compute instances list`)
3. Start if stopped, wait up to 150s
4. Open SSH tunnel (`gcloud compute ssh -- -L 8888:localhost:8080 -N -f`)
5. Health-check Jupyter API with retries

**`stop_vertex.sh`** — runs as a Stop hook when Claude Code exits. Kills the
SSH tunnel only; the VM auto-stops after 60 min idle.

### Claude Code Hooks

In `.claude/settings.local.json`:
- **PreToolUse** (`mcp__jupyter__.*`): `bash setup_vertex.sh --quiet`
  — auto-starts instance and tunnel before any Jupyter MCP call
- **PreToolUse** (`mcp__google-personal__create_drive_file`):
  `bash scripts/check_notebook_verified.sh` — blocks `.ipynb` uploads
  unless a `.last_verified_<notebook>` timestamp exists and is newer than
  the notebook file. Prevents distributing unverified notebooks.
- **PreToolUse** (`Bash`): `bash scripts/check_gcloud_workbench.sh`
  — blocks `gcloud compute instances start/stop` on Workbench instances.
  Workbench instances are managed resources; the Compute Engine API returns
  403 even for project owners. Must use `gcloud workbench instances` or
  `setup_vertex.sh`.
- **Stop** (all): `bash stop_vertex.sh`

### MCP Capabilities

Four tools: `setup_notebook`, `query_notebook`, `modify_notebook_cells`,
`execute_notebook_code`. Output types: `text/plain`, `text/html`,
`text/markdown`, `stream`, `error` (with traceback).

### Limitations

- **REQUEST_TIMEOUT**: default 10s too short; set to 180 for FHIR/LLM cells
- **install_packages**: MCP's `uv pip` fails without venv; use `subprocess.run`
- **#@param dropdowns**: do not render in Jupyter; simulate by editing defaults
- **3 of 10 checks** (widget appearance, dashboard rendering, code visibility)
  require manual Colab review

### Legacy Playwright Tools

Moved to `archive/colab-tools/` — superseded by Vertex AI. The skill at
`.claude/skills/colab-notebook-tools/` still works for visual checks if needed.

---

## FHIR Server Configuration

### Default Server (SBU LinuxForHealth)

| Setting | Value |
|---------|-------|
| URL | `https://lfh-fhir.eastus2.cloudapp.azure.com:9443/fhir-server/api/v4` |
| Auth | HTTP Basic (`fhiruser` / `BmI512@ccess`) |
| TLS | Self-signed certificate (`verify=False`) |
| Dataset | 1,027 synthetic patients across 6 phenotypes |
| FHIR Version | 4.0.1 (SNOMED CT for conditions, LOINC for observations) |

### Connecting a Different FHIR Server

1. Update `.env` with new URL, credentials, and TLS setting
2. Update the generator's `SETUP` constant (hardcode for student notebooks)
3. Run `python scripts/validate_fhir_server.py` to verify
4. Update SNOMED/LOINC codes in `TOOLS` if the server uses different vocabularies
5. Generate synthetic data if the server lacks appropriate patients

---

## Debugging Guide

### Common Issues

**"Connection failed. Check server URL and credentials."**
FHIR server may be down. Run `python scripts/validate_fhir_server.py`.

**Cell timeout in Vertex AI (empty output)**
`REQUEST_TIMEOUT` must be >= 180. Check the Jupyter MCP config.

**"AI Agent: Not configured" in connection status table**
Missing API key for the selected provider. In Colab: add `ANTHROPIC_API_KEY` or
`OPENAI_API_KEY` to Secrets sidebar. In Vertex AI: set as environment variable.
Make sure the key matches the provider selected in the dropdown.

**All candidates are the same phenotype**
Round-robin logic may have regressed. Check `_by_group` sizes in debug output.

**Agent hits max_steps without final answer**
Try a more specific prompt or increase `max_steps`.

**Stale SSH tunnel (port 8888 occupied, Jupyter unresponsive)**
`setup_vertex.sh` handles this automatically. Manual fix: `lsof -ti :8888 | xargs kill`.

**Vertex AI instance not found**
Verify project ID (`joel-vertex-project`) and run `gcloud compute instances list`.

### Debugging Agent Behavior

1. Check the agent's **query log** in notebook output — look for missing
   queries, wrong LOINC codes, premature classification
2. Check the **system prompt** in the generator's `RUN_AI_AGENT` constant —
   threshold or category definition may need adjustment
3. Check **`max_steps`** — agent may be forced into early classification
4. Compare with **`_get_ground_truth()`** — if agent consistently disagrees,
   the ground truth logic may need revision

### Modifying Notebooks

1. Edit the generator script, not the `.ipynb`
2. `python create_prototype_demo.py` to regenerate
3. `python test_demo_notebook.py` for local smoke test
4. Verify in Vertex AI via Jupyter MCP
5. Final visual review in Colab by instructor
