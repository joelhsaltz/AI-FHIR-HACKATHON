# Design: Synthetic Data Architect Agent

**Date:** 2026-03-23
**Status:** Draft

## Purpose

Fourth agent in the clinical pipeline. Bridges scenario design documents
(produced by the Clinical Scenario Designer) and the synthetic EHR data
generator (at `synthetic-ehr/`). Collaborates interactively with Joel on
phenotype design — anchor values, distributions, coupling constraints —
and can run test batches to evaluate clinical plausibility.

## Problem

The Clinical Scenario Designer produces clinical phenotype descriptions
(e.g., "patients with low eGFR + high UACR + poor HbA1c"). The synthetic
data generator consumes phenotype JSON configs (anchors, spread, categorical
probabilities). No agent currently translates between these two representations.

Additionally, the generator currently hardcodes 34 diabetes/CKD variables.
New domains (autoimmune, oncology) need different variables. A modular
variable architecture is needed — but that is a **separate generator refactor**,
not part of this agent spec. See "Future: Generator Variable Model Refactor"
at the end.

## Agent Definition

### Identity (AGENT.md — domain-independent)

A clinical data engineer who translates phenotype descriptions into
synthetic patient configurations. Three thinking modes:

- **Clinical translator:** Maps clinical concepts to concrete parameter
  values. "Low C-peptide in Type 1" → anchor 0.3 ng/mL, sd 0.15,
  bounds 0.01-1.0.
- **Data engineer:** Understands the generator's schema — anchors, spread
  distributions (truncnorm vs lognormal), categorical probabilities,
  clinical coupling constraints. Knows the generator's hard constraints
  (BOUNDS, ENUMS, BINARY_FIELDS, apply_relationships() coupling rules,
  non-ESRD eGFR floor of 15).
- **Plausibility checker:** Generates test batches and evaluates whether
  synthetic patients look clinically realistic. Flags implausible
  combinations (e.g., Type 1 diabetes with high C-peptide, or eGFR below
  the generator's floor).

### AGENT.md Frontmatter

```yaml
---
name: synthetic-data-architect
description: >
  Translates clinical phenotype descriptions into synthetic patient
  configurations. Collaborates on phenotype design, runs test generation,
  validates plausibility. Works with any clinical domain the generator supports.
tools:
  - Read
  - Glob
  - Grep
  - Bash
  - mcp__claude_ai_ICD-10_Codes (all tools)
  - mcp__claude_ai_PubMed (all tools)
---
```

### Tools

- Read, Glob, Grep — examine scenario docs, existing phenotypes, generator code
- Bash — run all generator scripts:
  - `synthetic-ehr/scripts/generate_patients.py` — single-phenotype generation
  - `synthetic-ehr/scripts/generate_cohort.py` — multi-phenotype cohort generation
  - `synthetic-ehr/scripts/validate_patients.py` — output plausibility checks
  - `synthetic-ehr/scripts/validate_phenotypes.py` — config schema validation
  - `synthetic-ehr/scripts/add_phenotype.py` — clone + override workflow for new phenotypes
- ICD-10 MCP tools — look up diagnosis codes for new domains
- PubMed MCP tools — find reference ranges and clinical thresholds

Note: `export_fhir_r4_bundle.py` (CSV → FHIR bundle) exists but FHIR export
is out of scope for this agent. The agent produces CSV-stage data only.

### Consumes

- Scenario design docs from `docs/scenarios/` (e.g., `autoimmune-differential.md`,
  `ckd-progression-risk.md`, `cll-follow-up-therapy-selection.md`)
- Phenotype schema at `synthetic-ehr/references/phenotype_schema.md`
- Existing phenotype configs at `synthetic-ehr/assets/phenotype_template.json`
- Generator source code, specifically:
  - `BOUNDS` dict in `generate_patients.py` — valid ranges per variable
  - `ENUMS` dict — valid categorical values (note: race/ethnicity are NOT
    in ENUMS; they are pass-through string anchors with no sampling variation)
  - `BINARY_FIELDS` set — fields with 0/1 probability sampling
  - `apply_relationships()` — coupling constraints (eGFR→CKD stage,
    HbA1c→glucose via ADAG, UACR→albuminuria stage, non-ESRD eGFR floor)
- Existing cohort plan format at `synthetic-ehr/assets/cohort_plan_example.json`:
  ```json
  {"schema_version": "1.0", "cohort_name": "...", "jobs": [
    {"phenotype_id": "...", "n": 100}, ...
  ]}
  ```

### Produces

- **Phenotype JSON configs** — new or extended phenotype definitions,
  following the existing `phenotype_template.json` format. Can use
  `add_phenotype.py` for clone + override workflow.
- **Cohort plan JSON files** — following the existing cohort plan schema
  (`schema_version`, `cohort_name`, `jobs` array with `phenotype_id` + `n`)
- **Variable extension specs** — when a scenario needs variables the
  generator doesn't support yet. Specifies: variable name, type (numeric/
  categorical/binary), bounds, default anchor, coupling constraints, clinical
  rationale. Design only — code changes are a separate implementation task.
- **Test generation results** — small batches with plausibility assessment

### SKILL.md Orchestration

The SKILL.md at `.claude/skills/synthetic-data-architect/SKILL.md` should:

**When to invoke:**
- After a scenario design doc is produced and approved
- When Joel wants to create or modify phenotype configs
- When exploring what variables a new domain would need
- Trigger phrases: "design phenotypes", "generate test data", "phenotype config",
  `/synth-data`, `/phenotype-design`

**Context assembly:**
1. Read `.claude/agents/synthetic-data-architect/AGENT.md` (identity)
2. Read `.claude/agents/project-brief.md` (project context)
3. Read the relevant scenario doc from `docs/scenarios/`
4. Read `synthetic-ehr/references/phenotype_schema.md` (schema)
5. Read `synthetic-ehr/assets/phenotype_template.json` (existing phenotypes)

**Interaction mode:** Direct conversation (like the Scenario Designer).
Joel collaborates interactively on phenotype parameter tuning.

## Interaction Workflow

1. Joel points the agent at a scenario doc or describes a clinical domain
2. Agent reads the scenario design and existing phenotype configs
3. If new variables are needed: agent produces a variable extension spec
   and notes that the generator needs code changes before those variables
   can be used. Continues with existing variables where possible.
4. Agent proposes phenotypes with anchor values, spreads, and categorical
   probabilities — Joel refines interactively
5. Agent writes phenotype config (using `add_phenotype.py` or direct JSON),
   runs `validate_phenotypes.py` to check schema validity
6. Agent generates a test batch (10-20 patients) via `generate_patients.py`,
   runs `validate_patients.py`
7. Agent shows sample patients, flags clinically implausible values
8. Iterate until phenotypes look right
9. Agent produces final phenotype JSON + cohort plan via `generate_cohort.py`

## Information Flow (Updated Pipeline)

```
Joel ←→ Clinical Scenario Designer
              │
              ▼ writes
        docs/scenarios/<name>.md
              │
        ┌─────┼─────────┐
        ▼     ▼         ▼
  Education  Synthetic   Implementation
  Reviewer   Data        Reviewer
  (reads)    Architect   (reads)
              │
              ▼ produces
        phenotype JSON + cohort plan
              │
              ▼ runs
        generate_cohort.py
              │
              ▼ outputs
        synthetic-ehr/generated/*.csv
              │
              ▼ exports (separate task)
        export_fhir_r4_bundle.py → FHIR bundle → load to server
```

## File Structure

```
.claude/agents/synthetic-data-architect/
└── AGENT.md                            # Domain-independent identity

.claude/skills/synthetic-data-architect/
└── SKILL.md                            # Orchestration layer
```

The agent works against the existing `synthetic-ehr/` directory as-is.
No new directories or files are required in the generator.

## What the Agent Does NOT Do

- Does not refactor the generator scripts (code changes handed off)
- Does not design clinical scenarios (that's the Scenario Designer)
- Does not evaluate pedagogy (that's the Education Reviewer)
- Does not review notebook implementations (that's the Implementation Reviewer)
- Does not load data into FHIR servers or run FHIR bundle export
- Does not modify the generator's BOUNDS, ENUMS, or coupling constraints
  directly — it produces specs that a developer implements

## Verification

1. AGENT.md is domain-independent (no hardcoded codes or domain terms)
2. Agent can read an existing scenario doc and propose phenotype configs
3. Agent can run the generator and produce valid test patients
4. Agent flags when new variables are needed for a new domain
5. Phenotype configs produced by the agent pass `validate_phenotypes.py`
6. Test patients produced from those configs pass `validate_patients.py`
7. Agent correctly flags clinically implausible phenotype configs (e.g.,
   Type 1 diabetes with C-peptide anchor of 4.0, or eGFR anchor below 15)

## Future: Generator Variable Model Refactor (Separate Spec)

The current generator hardcodes 34 diabetes/CKD variables. To support new
domains (autoimmune, oncology), the generator needs a modular architecture:

- **Core variables** shared across all scenarios: demographics,
  common labs (BMP, lipids)
- **Domain extensions** added per scenario: diabetes-specific labs and meds,
  autoimmune panels, oncology markers

This is a significant code change to `generate_patients.py` (BOUNDS, ENUMS,
apply_relationships(), validation logic) and is NOT part of this agent spec.
The agent can design the target variable architecture and produce the spec;
implementation is a separate task.

Until the refactor is done, the agent works against the existing 34-variable
schema. For domains that need new variables, the agent produces a variable
extension spec documenting what's needed, then the generator is extended
before phenotype configs can be created for that domain.
