# SPEC.md — Requirements, Scope, and Design Decisions

## Overview

A redesigned educational hackathon for BMI 512 (Clinical Informatics and AI) at
Stony Brook University. The original 3-session format is replaced with 2
notebooks built around "You Are the Agent" pedagogy: students act as the
clinical decision-maker — choosing what FHIR data to query, when they have
enough evidence, and what the final answer is — before watching a Claude agent
do the same thing autonomously. The goal is not to teach Python; it is to build
intuition for what agent loops actually do and why they are hard.

## Target Audience

Clinical informatics fellows and BMI graduate students. The audience is
clinically literate but writes code roughly 5% of the time. Prior experience
with Python, FHIR, or AI agents is not assumed. Students should never be asked
to write or debug code during the session.

## Learning Goals

By the end of the hackathon, students should be able to:

1. Describe an agent loop in plain language (tool call → result → next decision).
2. Choose the next FHIR query to make given a partial patient record and a
   clinical question.
3. Explain why a single data point is not sufficient for clinical classification.
4. Decide when an agent's answer is well-supported versus premature.
5. Compare their own clinical reasoning strategy to an LLM's tool-calling trace.
6. Explain how prompt wording changes what a Claude agent ranks and prioritizes
   (capstone only).

## Notebook Structure

### Notebook 1: Main Teaching Notebook

Two clinical scenarios, each with three modes that students work through in
sequence.

**Scenario 1 — Endocrine Follow-Up List Construction**

The task is to identify which diabetic patients on a practice panel need an
endocrine referral. Students (and the agent) must decide which patients to pull,
what FHIR data to gather for each, and who meets the threshold.

**Scenario 2 — Type 1 vs. Type 2 Diabetes Clarification**

The task is to classify younger patients (age of onset < 40) as T1D or T2D
using available evidence: medication history, lab trends, encounter notes. The
scenario is designed so the right answer is not obvious from a single data
point.

**Three modes (applied to each scenario):**

- **Human mode:** Student works through a menu-driven interface. At each step
  they pick which FHIR data to query next (from a labeled list), see the
  returned result, and decide what to do next — query more, or commit to a
  decision. No code is visible.
- **Hybrid mode:** Same menu interface, but the student can ask Claude for a
  coaching suggestion at any step. Claude recommends a next action and explains
  why, but the student makes the final call.
- **LLM mode:** Claude runs the scenario autonomously using the tool_use API.
  Students watch each tool call and result stream past, then compare the agent's
  strategy and final answer to their own.

After each scenario, students answer a short reflection question about where
their path and the agent's path diverged.

### Notebook 2: Capstone — Population-Scale Prioritization

A population-level exercise in which students direct the agent at scale.

1. **Prompt:** Student writes a plain-language prioritization request
   (e.g., "rank patients by risk of hospitalization in the next 6 months").
2. **Formalization:** Claude converts the request into named scoring factors
   with weights.
3. **Execution:** The agent queries FHIR data for all relevant patients, scores
   each one, and returns a ranked list.
4. **Iteration:** Student refines the plain-language request and re-runs to
   observe how wording changes the rankings.

There is no single correct answer. The exercise is designed to surface how
prompt design drives agent behavior.

## Technical Requirements

### FHIR Server

- URL: `https://lfh-fhir.eastus2.cloudapp.azure.com:9443/fhir-server/api/v4`
- Auth: HTTP Basic (`fhiruser` / `BmI512@ccess`)
- TLS: Self-signed certificate — all requests must use `verify=False`
- Dataset: 1,027 synthetic patients across 6 clinical phenotypes

### LLM

- Provider: Anthropic only
- Model: `claude-sonnet-4-20250514`
- API: tool_use (function calling)
- Key: `ANTHROPIC_API_KEY` stored in Colab Secrets

### FHIR Tools (agent toolkit)

The agent has access to a standard set of FHIR query tools. The exact tool set
will be defined per notebook but will cover at minimum:

- `search_conditions` — search patient conditions by SNOMED code
- `get_patient` — retrieve patient demographics
- `search_observations` — retrieve lab results by LOINC code
- `search_medications` — retrieve active/historical medications
- `search_encounters` — retrieve encounter history

Additional tools may be added for the capstone to support population-scale
queries.

### Coding Systems

- Conditions: SNOMED CT
  - Type 2 Diabetes: `44054006`
  - Type 1 Diabetes: `46635009`
- Labs: LOINC
  - HbA1c: `4548-4`
  - C-peptide: `14648-6`
- HbA1c threshold for poor glycemic control: >7.5% (richer synthetic data
  distribution than the original v1/v2 threshold of 7.0%)

## Clinical Agent Pipeline

### Scope

Four specialized agents support the notebook development workflow:

1. **Clinical Scenario Designer** — designs scenarios for any clinical domain
   (diabetes, CKD, autoimmune, oncology). Applies six evaluation tests
   (single-query shortcut, evidence diversity, ambiguity, clinical plausibility,
   data availability, difficulty calibration). Uses ICD-10 and PubMed MCP tools
   for clinical grounding.

2. **Clinical Education Reviewer** — evaluates whether notebooks deliver on
   learning objectives. Checks for passive observation, trivially solvable tasks,
   false agency, missing feedback. Produces severity-rated issues.

3. **Notebook Implementation Reviewer** — pre-flight technical check plus
   clinical coherence against the scenario design. 10 check categories for
   Colab-specific issues.

4. **Synthetic Data Architect** — translates scenario designs into phenotype
   JSON configs for the data generator. Runs test batches and validates
   plausibility. Flags when new variables are needed for new domains.

### Design Decisions

- Agents are domain-independent (no hardcoded clinical codes in AGENT.md)
- Per-project context via project-brief.md (swappable across projects)
- Scenario design docs are shared artifacts between agents
- Synthetic data generator integrated into repo at `synthetic-ehr/`
- Generated data gitignored; backed up to Box.com

## Delivery Format

- Two self-contained Google Colab notebooks
- No local src/ imports — all code defined inline within the notebook
- Single pip install cell: `pip install anthropic`
- Student and instructor versions of each notebook
- Instructor version includes cell-level annotations explaining the pedagogical
  intent of each section
- No deliverable files or graded JSON exports; the session is assessed through
  in-class discussion and the reflection questions embedded in the notebook

## Design Decisions

### "You Are the Agent" replaces passive observation

The original format asked students to watch an agent run and then experiment
with prompts. Feedback indicated this was passive and felt disconnected from
clinical work. The redesign puts students in the agent role first so they
experience the decision problem before seeing the automated solution.

### Menu-driven interface hides Python

Students in this audience do not benefit from reading Python code. The Human and
Hybrid modes present only clinical choices (labeled menu items) and data returns
(formatted as plain text). The underlying FHIR calls and API logic are hidden in
collapsed or non-displayed cells.

### Two notebooks instead of three sessions

The original three sessions were independent. The redesign consolidates into two
notebooks with a clear pedagogical arc: (1) understand the agent loop at the
patient level, (2) apply it at population scale. This reduces setup overhead and
makes the relationship between sessions explicit.

### Hybrid mode as a stepping stone

Adding a mode where students make decisions but can solicit LLM suggestions
provides a middle ground that the original format lacked. It models how a
clinician might realistically use an AI tool — not replacing judgment, but
getting a second opinion on next steps.

### No deliverable files

The original Session 3 required students to export a JSON report. This added
friction without pedagogical value for this audience. Reflection is done through
in-notebook questions and discussion.

### Anthropic-only

No dual-provider support. Claude's tool_use API is idiomatic for this use case
and keeping a single provider avoids credential management complexity in a
classroom setting.

## Scope

### In scope

- Notebook 1: Main Teaching Notebook (student + instructor versions)
- Notebook 2: Capstone Notebook (student + instructor versions)
- Menu-driven Human and Hybrid mode interfaces
- LLM mode with streamed tool call display
- In-notebook reflection questions
- FHIR server validation utility

### Out of scope

- Graded deliverables or automated scoring
- Multi-provider LLM support
- Local FHIR server fallback (original backup notebook pattern not carried
  forward)
- MCP server wrapping (potential future extension)
- Additional clinical scenarios beyond the two defined above

## Verification Pipeline

### Two-Stage Verification

1. **Automated (Vertex AI Workbench + Jupyter MCP):** Programmatic cell
   execution with structured output capture (text/HTML/Markdown). A Google Cloud
   Vertex AI Workbench instance (`fhir-hackathon-instance`, e2-standard-4) runs
   notebook cells via SSH tunnel + Jupyter MCP. Claude Code hooks auto-start the
   instance before MCP calls and auto-stop it on session end. Evaluates 7 of 10
   checklist items (task complexity, case variety, FHIR visibility, feedback
   quality, activity flow, game mechanics, clinical plausibility).

2. **Manual (Instructor review in Colab):** Three visual items require Colab's
   rendering engine: UI clarity (dropdown widgets), dashboard readability
   (rendered HTML/CSS), code hidden (cellView: form). Instructor reviews these
   after automated testing passes.

### Why Vertex AI Replaced Playwright

The original pipeline used Playwright browser automation to open notebooks in
Colab, run cells, and take screenshots. This was replaced due to:
- Auth expiry (Google session cookies expire frequently)
- Fragile shadow DOM handling (Colab uses web components)
- Slow iteration (upload -> open -> run -> screenshot per fix cycle)

Vertex AI provides stable SSH-based auth, structured output instead of pixel
screenshots, and faster iteration (no upload/screenshot cycle).

Full test results: `docs/vertex-ai-test-results.md`

## Current Status

### Phase 0 Prototype: Complete

The demo prototype (`prototypes/you_are_the_agent_demo.ipynb`) is built and
verified:
- 19 cells (9 code, 10 markdown), all code hidden behind Colab form cells
- Two activities: human agent (dropdown-driven) + AI agent (prompt-driven)
- Stratified candidate pool: round-robin selection produces ~4/3/3 mix across
  T1D, T2D, and no-diabetes phenotypes
- Verified on Vertex AI Workbench with live FHIR data (1,027 patients)
- Local smoke test: 16/16 passing

### Open Design Issues

1. **Combined dropdown UI** — query actions and classification in the same
   dropdown is not intuitive for students
2. **Task too simple** — C-peptide alone differentiates T1D vs T2D, defeating
   the multi-query agent loop pedagogy
3. **Student perspective review** — need automated evaluation of notebook UX,
   not just technical correctness

### Remaining Phases

- Phase 1: Main teaching notebook (two scenarios, three modes each)
- Phase 2: Capstone notebook (population-scale prioritization)
- Phase 3-6: Instructor versions, smoke tests, documentation

## Known Constraints

- Self-signed TLS certificate on the SBU FHIR server requires `verify=False`
  in all requests; students should be told this is a dev environment, not
  production practice.
- Synthetic patient data (Synthea) may have sparse lab histories for some
  patients; scenarios should be designed to handle missing observations
  gracefully rather than erroring.
- Colab session timeouts can interrupt long-running population queries in the
  capstone; the capstone should include a progress indicator and checkpoint
  logic.
- Vertex AI Workbench cannot render Colab form widgets (`#@param` dropdowns);
  3 of 10 verification checklist items require manual Colab review.
