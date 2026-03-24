# Session: Data-Informed Scenario Revision

- **Date:** 2026-03-24
- **Task:** Revise Phase 1 mapping using Synthetic Data Architect's FHIR server discovery
- **Status:** Complete
- **Agent:** Clinical Scenario Designer

## What Changed

The Synthetic Data Architect queried the live FHIR server and found the data is
significantly richer than assumed. Three major changes to the scenario mapping:

1. **UACR incorporated into Phase 1** — T1D median UACR 79.5 (elevated), T2D
   median 25.0 (normal). The "hidden damage" teaching mechanism works NOW.
2. **Non-DM controls included** — 148 patients with no diabetes diagnosis.
3. **CKD severity replaces CKD presence** — 99% of patients have CKD coded,
   so presence is meaningless. eGFR thresholds (<60, <30) are the discriminators.

## Ground Truth Logic (Deterministic)

1. No T1D/T2D condition → No diabetes
2. Count complicating factors: A1c >7.5, eGFR <60, UACR ≥30
3. Extreme findings override: eGFR <30 → High, UACR ≥300 → High
4. Factor count: 0 = Routine, 1 = Moderate, 2+ = High

## Key Design Decisions

- Medications are deliberately NOT a category driver (prevents single-query shortcut)
- 7.5% A1c threshold is conservative (ADA target is 7.0, but 7.5 avoids over-classification)
- UACR ≥30 threshold aligns with KDIGO A2 stage
- Feedback hints at missed evidence without giving the answer

## All Six Tests: PASS

Data Availability upgraded from CONDITIONAL to PASS after server verification.
Ambiguity upgraded from PARTIAL PASS to PASS (UACR mechanism works with current data).

## Artifacts Updated

- `docs/scenarios/diabetes-type-classification.md` — complete rewrite of mapping
