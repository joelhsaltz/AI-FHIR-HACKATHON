# Notebook Development Guide

How to build a new clinical education notebook from scratch, using the
agent pipeline and generator pattern. This is the single reference for the
end-to-end workflow — from clinical idea to distributable Colab notebook.

**Audience:** Anyone building a new notebook (faculty, collaborators, or
Claude Code working autonomously). Assumes familiarity with the repo
structure ([ORIENTATION.md](../ORIENTATION.md)) and basic FHIR concepts.

**Current example:** The diabetes management complexity notebook
(`create_prototype_demo.py` → `notebooks/you_are_the_agent_demo.ipynb`)
is the reference implementation. This guide describes the general process;
the diabetes notebook is one instance of it.

---

## Pipeline Overview

```
  Stage 1              Stage 2              Stage 3            Stage 4
  DESIGN               DATA                 BUILD              TEST
  ─────────────────    ─────────────────    ────────────────   ────────────────
  /scenario-design     /synth-data          Write generator    Write smoke test
  (agent)              (agent, if needed)   script (manual)    script (manual)
       │                    │                    │                  │
       ▼                    ▼                    ▼                  ▼
  docs/scenarios/      synthetic-ehr/       create_<name>_     test_<name>_
  <name>.md            assets/<name>.json   notebook.py        notebook.py
                                                │
                                                ▼
                                           notebooks/
                                           <name>.ipynb


  Stage 5              Stage 6              Stage 7            Stage 8
  REVIEW               VERIFY               SIGN-OFF           SHIP
  ─────────────────    ─────────────────    ────────────────   ────────────────
  /nb-preflight        Vertex AI Workbench  Instructor opens   Branch, PR,
  /edu-review          (automated, live     in Colab and       update docs,
  (agents, parallel)   FHIR data)           reviews UX         merge
       │                    │                    │                  │
       ▼                    ▼                    ▼                  ▼
  Fix issues in        Fix issues in        Fix issues in      notebooks/<name>
  generator,           generator,           generator,         on main branch
  regenerate           regenerate           regenerate
```

**Decision branch:** Stage 2 (synthetic data) is only needed when the
existing FHIR server data doesn't support your scenario. The Scenario
Designer agent will flag this if the data isn't available. If the live
server already has the right patients and observations, skip to Stage 3.

**Parallel stages:** Stages 5a (`/nb-preflight`) and 5b (`/edu-review`)
can run in parallel — one checks technical correctness, the other checks
pedagogy. Both consume the scenario design doc and the generated notebook.

---

## Stage 1: Design the Scenario

**What:** Define the clinical question, classification categories, required
FHIR queries, and where ambiguity lives.

**Why:** The scenario design doc is the golden source that every subsequent
stage consumes. A weak scenario produces a notebook that's either trivially
solvable or impossibly hard. Getting this right prevents costly rework in
later stages.

**How:** Invoke the Clinical Scenario Designer agent:
```
/scenario-design
```

The agent thinks from three perspectives simultaneously: clinician (what
evidence matters), dataset architect (what queries are needed), teacher
(is this non-trivial). It has access to ICD-10, PubMed, and bioRxiv MCP
tools for clinical grounding.

This is a conversational process — the agent proposes, you give feedback,
it iterates. Expect 3-5 rounds of refinement.

**Inputs:** A clinical teaching goal (can be vague: "I want students to
learn about kidney disease progression").

**Outputs:** `docs/scenarios/<name>.md` — a structured design doc.

**Six quality tests** (every scenario must pass all six):

1. **No single-query shortcut.** No single FHIR query resolves any category.
   Students must combine multiple queries.
2. **Evidence type diversity.** Requires 2-3 different FHIR resource types
   (e.g., Conditions + Observations + Medications).
3. **Ambiguity and uncertainty.** At least 2 cases with genuinely defensible
   disagreement among reasonable clinicians.
4. **Clinical plausibility.** A real clinician would approach it this way.
5. **Data availability.** The FHIR server actually contains the needed
   distinctions (or synthetic data can be generated).
6. **Difficulty calibration.** Matches target learners' sophistication and
   available time.

**If it fails:** If the agent flags data availability issues, proceed to
Stage 2 (synthetic data). If the scenario fails the single-query shortcut
test, redesign the classification categories to require more evidence.
See `docs/LESSONS_LEARNED.md` for concrete examples of scenario design
failures and how they were fixed.

**Decision boundaries:** The Scenario Designer decides clinical question,
categories, evidence types, and difficulty. It does NOT decide code
structure, cell layout, or data generation parameters.

**Example:** `docs/scenarios/diabetes-type-classification.md`

---

## Stage 2: Generate Synthetic Data (If Needed)

**What:** Translate the scenario design into phenotype configurations that
the synthetic EHR generator can use to produce realistic patient data.

**Why:** The live FHIR server may not have patients with the right
combination of conditions, observations, and medications for your scenario.
Synthetic data fills this gap with clinically plausible patients whose
characteristics are controlled by phenotype configs.

**How:** Invoke the Synthetic Data Architect agent:
```
/synth-data
```

The agent reads your scenario design doc and maps clinical requirements to
data parameters: anchor values, distributions, categorical probabilities,
and coupling constraints between variables.

**When to skip:** If the existing FHIR server data already supports your
scenario (the Scenario Designer will tell you), skip directly to Stage 3.
The diabetes complexity notebook uses the existing 1,027 patients on the
SBU teaching server — no synthetic data was needed.

**Inputs:**
- Approved scenario design doc (`docs/scenarios/<name>.md`)
- Phenotype schema reference (`synthetic-ehr/references/phenotype_schema.md`)
- Existing phenotype configs (`synthetic-ehr/assets/phenotype_template.json`)

**Outputs:**
- Phenotype JSON config at `synthetic-ehr/assets/<name>_phenotypes.json`
- Cohort plan at `synthetic-ehr/assets/<name>_cohort_plan.json`
- Test batch (10-20 patients) validated for clinical plausibility

**Validation pipeline:**
```bash
# Validate phenotype config
python3 synthetic-ehr/scripts/validate_phenotypes.py --phenotypes <config.json>

# Generate test cohort
python3 synthetic-ehr/scripts/generate_cohort.py \
  --phenotypes <config.json> --plan <plan.json> --seed 42 --out test.csv

# Validate generated patients
python3 synthetic-ehr/scripts/validate_patients.py --input test.csv

# Export to FHIR bundles (when ready for upload)
python3 synthetic-ehr/scripts/export_fhir_r4_bundle.py --input cohort.csv
```

**If it fails:** If generated patients don't look clinically plausible,
adjust anchor values and coupling constraints. The agent can run test
batches and flag implausible combinations.

**Decision boundaries:** The Data Architect decides phenotype parameters,
cohort composition, and coupling constraints. It does NOT decide the
clinical question, categories, or pedagogy.

---

## Stage 3: Write the Generator Script

**What:** Build a Python script that produces a self-contained Colab
notebook as a `.ipynb` file.

**Why:** Notebooks are generated, never hand-edited. This ensures
reproducibility (regenerate after any change), consistency (shared cell
groups are copied, not retyped), and testability (the generator is
ordinary Python that can be diffed and reviewed).

**How:** This is manual engineering, not an agent task. Copy the pattern
from `create_prototype_demo.py` and modify for your scenario.

**Generator pattern:**
1. Define cell content as string constants (`r"""..."""`)
2. Use three helpers: `md_cell(source)`, `form_cell(source)`, `build_notebook(cells)`
3. Assemble cells in presentation order as a Python list
4. Write as JSON via `json.dump()` to `notebooks/<name>.ipynb`

**Shared cell groups** (copy from `create_prototype_demo.py`):
- Package installation (provider-specific pip install with output suppressed)
- Setup + FHIR connection + provider adapter (3 functions)
- Tool definitions (FHIR query functions + provider-neutral tool schemas)
- Validation cell (quick query to confirm data access)

Activity-specific cells come after the shared groups and vary entirely by
use case. The framework does not constrain what comes after setup.

**Inputs:**
- Scenario design doc (defines what the notebook should teach)
- `create_prototype_demo.py` (reference implementation to copy from)
- Phenotype configs (if synthetic data was generated)

**Outputs:**
- `create_<name>_notebook.py` at the repo root
- `notebooks/<name>.ipynb` (generated by running the script)

**Key conventions:**
- All code cells use `cellView: "form"` — students never see Python
- FHIR query banners are visible — students are learning FHIR, not hiding it
- FHIR credentials are hardcoded (teaching server, not secrets)
- LLM API key comes from Colab Secrets
- Provider dropdown in Step 1 (Anthropic or OpenAI)

**If it fails:** Fix the generator script, never the notebook directly.
Regenerate and re-test.

**Reference:** [TECHNICAL.md](../TECHNICAL.md) has the full generator
pattern guide with code examples.

---

## Stage 4: Write the Smoke Test

**What:** Build a test harness that runs the notebook's code cells
programmatically against the live FHIR server.

**Why:** Catches broken imports, bad FHIR queries, and cell dependency
issues before you spend time on Colab verification. Fast feedback loop
(~60 seconds) vs. full Colab verification (~15 minutes).

**How:** Follow the pattern in `test_demo_notebook.py`.

**Smoke test pattern:**
1. Load the `.ipynb` file and extract code cells
2. Strip `#@param` annotations (replace with test values)
3. Run each cell via `exec()` in a shared namespace
4. Per-cell timeouts: 180s for agent/setup cells, 60s for query cells
5. Skip LLM-dependent cells (agent loop requires API calls)
6. Report PASS/FAIL per cell with timing

**Inputs:**
- Generated notebook (`notebooks/<name>.ipynb`)
- Live FHIR server (not a mock — see verification rules)

**Outputs:**
- `test_<name>_notebook.py` at the repo root
- PASS/FAIL report per cell

```bash
# Run the smoke test
python test_<name>_notebook.py
```

**If it fails:** Fix the generator script, regenerate the notebook, re-run
the smoke test. Common failures: missing imports in cell dependencies,
FHIR query parameters that return empty results, string escaping issues
in form cells.

---

## Stage 5: Review (Agents, Parallel)

Two agents review the notebook independently. They can run in parallel
because they check different things and both consume the same inputs
(scenario design doc + generated notebook).

### 5a: Implementation Review

**What:** Technical pre-flight check across 10 categories.

**Why:** Catches Colab-specific issues that would otherwise require
browser-based debugging: form cell syntax, string escaping, cell
dependencies, Run All compatibility, package installation, secrets
handling, data query patterns, output/display, code visibility, and
generator consistency. Also checks clinical coherence against the
scenario design doc.

**How:**
```
/nb-preflight
```

**Inputs:**
- Generated notebook (`.ipynb`)
- Generator script (`create_*.py`)
- Scenario design doc (`docs/scenarios/<name>.md`)

**Outputs:** Structured review with pass/fail per category.

**If it fails:** Fix issues in the generator script, regenerate, re-run
`/nb-preflight`. Run this BEFORE `/edu-review` — no point checking
pedagogy of broken code.

### 5b: Education Review

**What:** Evaluates whether the notebook delivers on its learning
objectives.

**Why:** Technical correctness does not equal good teaching. A notebook
can execute perfectly but still bore students (too easy, passive
observation) or baffle them (too hard, missing context). The "Bored or
Baffled" framework catches these issues before students see the notebook.

**How:**
```
/edu-review
```

**Inputs:**
- Generated notebook (`.ipynb`)
- Scenario design doc (`docs/scenarios/<name>.md`)
- Generator script (`create_*.py`)

**Outputs:** Severity-rated review:
- **Blocks learning** — must fix before distribution
- **Reduces engagement** — should fix
- **Cosmetic** — nice to fix

**If it fails:** Redesign the activity structure in the generator script.
Common issues: trivially solvable tasks, passive observation without
agency, missing feedback on student actions, opaque AI reasoning.

**Decision boundaries:** Education Reviewer decides learning quality,
activity design, and difficulty calibration. It does NOT decide clinical
thresholds, code structure, or technical implementation.

---

## Stage 6: Verify on Vertex AI

**What:** Execute all cells against the live FHIR server in a Jupyter
environment that matches Colab's behavior.

**Why:** Local smoke tests catch code errors but miss Colab-specific
rendering issues (form cells, markdown, widget behavior). Verification
against live data confirms the notebook works end-to-end as students
will experience it. "It should work" is not verification.

**How:** Use the Vertex AI Workbench setup:
```
/colab-mcp
```
Or manually: `bash setup_vertex.sh` to start the instance and SSH tunnel.

**Inputs:**
- Generated notebook (`notebooks/<name>.ipynb`)
- Live FHIR server with appropriate patient data
- API key for LLM provider (in `.env`)

**Outputs:** Cell-by-cell execution results with output capture.

**Change-specific verification:** After verification, confirm each specific
change from the implementation is present in the output. Write a checklist
of every user-visible change, check each one off. If any item is not
confirmed, verification is NOT complete.

**If it fails:** Fix the generator script, regenerate, re-verify. If the
FHIR server is down or Vertex AI is unavailable, STOP and ask — never
substitute a lesser form of verification.

**What does NOT count as verified:**
- `nbconvert --execute` passing locally
- "The code looks correct"
- Running cells in a local Jupyter instance
- Testing against a mock or local FHIR server

---

## Stage 7: Instructor Sign-Off

**What:** Manual review in Google Colab for the student experience.

**Why:** Automated verification confirms the code works. Manual review
confirms the *experience* works: Does the markdown render clearly? Are the
dropdown menus intuitive? Is the pacing right? Does the feedback make
sense? These are human judgments that automation can't make.

**How:** Open the notebook in Colab (upload to Drive or use the GitHub
link), run all cells, and evaluate from the student's perspective.

**Inputs:** Verified notebook (passed Stage 6)

**Outputs:** Approval or list of issues to fix in the generator.

---

## Stage 8: Ship

**What:** Commit, branch, PR, merge, update documentation.

**How:**
```bash
# Create branch
git checkout -b codex/<scenario-name>

# Commit generator, test, and notebook
git add create_<name>_notebook.py test_<name>_notebook.py notebooks/<name>.ipynb
git commit -m "Add <scenario-name> notebook"

# Push and create PR
git push -u origin codex/<scenario-name>
gh pr create --title "Add <scenario-name> notebook"

# After approval, merge
gh pr merge <number> --merge
git checkout main && git pull
```

**Shipping checklist:**
- [ ] Generator script committed (`create_<name>_notebook.py`)
- [ ] Smoke test committed (`test_<name>_notebook.py`)
- [ ] Generated notebook committed (`notebooks/<name>.ipynb`)
- [ ] Scenario design doc committed (`docs/scenarios/<name>.md`)
- [ ] README.md updated with "Open in Colab" badge for new notebook
- [ ] GETTING_STARTED.md badge added
- [ ] CHANGELOG.md updated
- [ ] CLAUDE.md Key Files table updated (if applicable)
- [ ] Colab link tested (open badge URL, verify it loads)

---

## Quick Reference

| Stage | Agent? | Trigger | Input | Output |
|-------|--------|---------|-------|--------|
| 1. Design | Clinical Scenario Designer | `/scenario-design` | Clinical teaching goal | `docs/scenarios/<name>.md` |
| 2. Data | Synthetic Data Architect | `/synth-data` | Scenario doc | `synthetic-ehr/assets/<name>.json` |
| 3. Build | None (manual) | — | Scenario doc, reference generator | `create_<name>_notebook.py` → `notebooks/<name>.ipynb` |
| 4. Test | None (manual) | — | Generated notebook | `test_<name>_notebook.py` |
| 5a. Review | Notebook Impl Reviewer | `/nb-preflight` | Notebook + scenario doc | Technical review |
| 5b. Review | Clinical Edu Reviewer | `/edu-review` | Notebook + scenario doc | Pedagogy review |
| 6. Verify | None (Vertex AI) | `/colab-mcp` | Notebook + live FHIR | Execution results |
| 7. Sign-off | None (manual) | — | Verified notebook | Approval |
| 8. Ship | None (git) | — | All artifacts | PR merged to main |

---

## Further Reading

| Document | What it covers |
|----------|---------------|
| [TECHNICAL.md](../TECHNICAL.md) | Generator pattern deep-dive, FHIR tool definitions, provider adapter |
| [SPEC.md](../SPEC.md) | Scenario template specification, notebook specification, 6 quality tests |
| [LESSONS_LEARNED.md](LESSONS_LEARNED.md) | Concrete failures and what we learned: scenario design, Colab gotchas, verification |
| [TEACHING_APPLICATION_PLAN.md](TEACHING_APPLICATION_PLAN.md) | Pedagogical framework: human → hybrid → LLM progression |
| `.claude/agents/*/AGENT.md` | Each agent's identity, evaluation framework, decision boundaries |
| `.claude/skills/*/SKILL.md` | Orchestration: when to invoke, context to pass, integration with other skills |
