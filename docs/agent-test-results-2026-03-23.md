# Agent Test Results — 2026-03-23

## Overview

Tested the Clinical Scenario Designer agent on two scenarios to verify clinical
common sense and domain independence. The agent uses domain-independent AGENT.md
identity + project-brief.md for project context.

## Test 1: CKD Progression Risk (Existing FHIR Dataset)

**Prompt:** "Design a clinical scenario for identifying diabetic patients at risk
of CKD progression, using the data available on our FHIR server."

### Common Sense Checks

| Check | Pass? | Details |
|-------|-------|---------|
| Identifies relevant labs (eGFR, UACR, HbA1c, creatinine) | Yes | All four, plus medications for renoprotective therapy context |
| Recognizes multi-factorial nature | Yes | Designed around KDIGO eGFR × UACR two-axis staging matrix |
| Flags data limitations | Yes | UACR coverage may be sparse, longitudinal eGFR limited, needs server verification |
| Requires 3+ queries per patient | Yes | Minimum 4-5 (eGFR + UACR + HbA1c + medications + problem list) |
| Passes own single-query shortcut test | Yes | Explicitly explains why each single marker is insufficient |
| Designs meaningful ambiguity | Yes | Two-axis staging + missing data creates genuine uncertainty |

### Strengths
- Designed 3-category classification (Refer / Monitor / Insufficient Evidence)
  forcing students to acknowledge data gaps
- Broke out lab queries by specific LOINC code rather than generic "Get labs"
- Included prompt variants (base, complexity emphasis, conservative)
- Provided evidence synthesis rubric with strong/moderate/monitor/insufficient patterns
- Identified that candidate pool should be built CKD-first (not diabetes-first)

### Flags Raised
- Called for live FHIR server verification of eGFR/UACR coverage before implementation
- Noted that longitudinal trend assessment may not be possible with the static dataset
- Recommended designing for cross-sectional multi-marker synthesis rather than trend analysis

### Result: **PASS** — clinically sound, avoids shortcuts, honest about data limitations

---

## Test 2: Autoimmune Differential Diagnosis (New Synthetic Dataset)

**Prompt:** "Design a clinical scenario for differentiating between autoimmune
diseases (SLE, RA, Sjogren's, MCTD) in patients presenting with undifferentiated
autoimmune symptoms. Produce a data requirements specification."

### Common Sense Checks

| Check | Pass? | Details |
|-------|-------|---------|
| Uses ICD-10 MCP tools | Yes | Looked up codes for SLE (M32.x), RA (M05.x/M06.x), Sjogren (M35.0x), MCTD (M35.1), UCTD (M35.9) + 19 comorbidity codes |
| Uses PubMed for diagnostic criteria | Yes | Found 2019 EULAR/ACR SLE criteria, 2010 ACR/EULAR RA criteria, 2016 ACR/EULAR Sjogren criteria, MCTD literature |
| Identifies correct lab panels | Yes | 30+ LOINC-coded observations: autoantibody panel, complement, hematologic, inflammatory markers, renal, muscle enzymes |
| Recognizes genuine diagnostic ambiguity | Yes | Designed overlap syndromes (SLE/MCTD), UCTD as explicit phenotype, seronegative variants |
| Produces usable data spec | Yes | 200 patients, 8 FHIR resource types, 9 phenotypes with distribution, medication discriminators |

### Strengths
- Identified medication patterns as discriminators (methotrexate → RA, mycophenolate → SLE nephritis, pilocarpine → Sjogren)
- Designed difficulty tiers: 4 moderate (classic presentations), 4 hard (atypical/seronegative), 1 very-hard (overlap)
- Specified 8 FHIR resource types including DiagnosticReport, Procedure, AllergyIntolerance
- Raised 6 open design questions for Joel (e.g., should Conditions include final diagnosis or only presenting symptoms?)
- Referenced specific classification criteria (ACR/EULAR) from PubMed search

### Flags Raised
- Asked whether FHIR Conditions should contain the final autoimmune diagnosis
  (chart review exercise) vs. only presenting symptoms (true diagnostic exercise)
- Noted that the scenario requires significantly more complex synthetic data than
  the existing diabetes generator supports

### Result: **PASS** — demonstrates domain independence, uses MCP tools effectively,
produces clinically grounded design with realistic data requirements

---

## Architecture Insight: Synthetic Data Generation Gap

Both scenarios produced clinical phenotype descriptions, but neither produced the
machine-readable phenotype JSON configs needed by the synthetic data generator at
`/Users/joelsaltz/Codex/Synthetic EHR data/synthetic-ehr-phenotype/`.

**Decision (2026-03-23):** Create a fourth agent — **Synthetic Data Architect** —
that bridges scenario design docs and the data generator. It reads scenario designs
from `docs/scenarios/` and the phenotype schema, then produces valid phenotype JSON
configs and cohort plans.

This is documented in the updated architecture plan at
`~/.claude/plans/clinical-agent-architecture.md`.

---

## Summary

| Test | Domain | Data Source | Result |
|------|--------|------------|--------|
| CKD progression risk | Diabetes/nephrology | Existing FHIR server | PASS |
| Autoimmune differential | Rheumatology | New synthetic dataset needed | PASS |
| Domain independence | Cross-domain | N/A | Confirmed — agent uses MCP tools for unfamiliar domains |

## Scenario Docs Produced

- `docs/scenarios/ckd-progression-risk.md`
- `docs/scenarios/autoimmune-differential.md`
- `docs/scenarios/cll-follow-up-therapy-selection.md` (from earlier litmus test)
- `docs/scenarios/diabetes-type-classification.md` (existing, with known issues)
