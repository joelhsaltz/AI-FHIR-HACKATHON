# Scenario: Diabetes Management Complexity Assessment

**Status:** Redesigned 2026-03-24 — replaces the original "Type 1 vs Type 2
Clarification" scenario, which was trivially solvable with one C-peptide query.

**Designed by:** Clinical Scenario Designer agent, approved by Joel.

## Clinical Question

Based on the available evidence, how would you categorize this patient's
diabetes management complexity?

## Classification Categories

- **Routine** — Diabetes present, well-controlled, no significant complications,
  straightforward medication regimen
- **Moderate complexity** — One or more complicating factors (suboptimal control,
  early kidney involvement, multi-drug regimen) but no convergence of multiple
  red flags
- **High complexity** — Multiple complicating factors that together demand
  specialist-level attention
- **No diabetes** — Patient does not have a diabetes diagnosis (present in some
  candidates as a verification check)

## Required Evidence Types

| Evidence | FHIR Resource | LOINC/SNOMED | Why Needed |
|----------|--------------|-------------|------------|
| HbA1c | Observation | 4548-4 | Glycemic control — necessary but not sufficient for any category. >7.5% suboptimal, >9% urgently poor |
| Medications | MedicationRequest | — | Regimen complexity. Insulin type, oral agent count, combination patterns. Complex regimen ≠ complex patient (good control on complex meds = Routine) |
| eGFR or Creatinine | Observation | 33914-3 or 2160-0 | Kidney function — hidden complicating factor. <60 = CKD stage 3+. Cannot be inferred from other data |
| Conditions | Condition | SNOMED | Confirms diabetes diagnosis and reveals CKD coding. Essential for "No diabetes" detection |
| UACR | Observation | 14959-1 | Early kidney damage that eGFR misses. >30 mg/g = microalbuminuria, >300 mg/g = macroalbuminuria. The key "reward for thoroughness" data point |

## Minimum Queries to Classify Correctly

**3-4 per patient.** No single query resolves any category:
- HbA1c alone: tells control status but not kidney involvement or medication burden
- eGFR alone: tells kidney function but not glycemic control
- Medications alone: tells regimen complexity but not outcomes
- Conditions alone: tells diagnoses but not severity

Students who stop at 2 queries will miscategorize the edge cases.

## Phenotype-to-Category Mapping

| Phenotype | Expected Category | Why | Teaching Value |
|-----------|------------------|-----|----------------|
| Early T2D, no CKD (A1c ~7.2, metformin, eGFR ~88) | **Routine** | Controlled, simple regimen, intact kidneys | Clear case — builds confidence |
| Metabolic syndrome, no DM (A1c ~6.0, no DM diagnosis) | **No diabetes** | No diabetes diagnosis exists | Trap — student must verify diagnosis before classifying |
| T1D early nephropathy (A1c ~7.8, insulin, eGFR ~82, UACR ~78) | **Moderate (ambiguous)** | Suboptimal A1c + early kidney damage, but eGFR preserved | Key pedagogical moment: eGFR looks fine, UACR reveals hidden damage. Students who skip UACR miscategorize |
| T2D obesity CKD2 (A1c ~8.4, insulin+metformin+SGLT2i, eGFR ~68, UACR ~120) | **Moderate to High (ambiguous)** | Poor control + multi-drug regimen + early CKD + albuminuria | Genuinely ambiguous boundary case. Reasonable students disagree |
| Advanced T2D CKD3b (A1c ~8.0, basal-bolus, eGFR ~38, UACR ~420) | **High** | Poor control + advanced CKD + complex regimen + metformin contraindicated | Clear High — multiple converging red flags |
| T1D poor control CKD3a (A1c ~9.1, basal-bolus, eGFR ~52, UACR ~360) | **High** | Very poor control + significant CKD + macroalbuminuria | Clear High — students need multiple queries to see how many factors pile up |

## Where Genuine Ambiguity Lives

1. **T1D early nephropathy** — eGFR ~82 (preserved, looks reassuring), but UACR
   ~78 (A2 stage, early damage). Students who check only eGFR classify as Routine.
   Students who also check UACR see the albuminuria and should bump to Moderate.
   This is the core teaching moment: the same patient looks different depending on
   how many evidence sources you check.

2. **T2D obesity CKD2** — Sits on the Moderate/High boundary. eGFR ~68 (mildly
   decreased, not alarming individually), but A1c ~8.4 (poor) + 3+ medications +
   UACR ~120 (A2 stage). A student could defensibly argue either Moderate or High.
   Both answers are acceptable if supported by evidence.

3. **Spread-induced variation** — Stochastic phenotype spread creates natural
   case-to-case difficulty. An early T2D patient whose A1c spread pushes to 8.0+
   with a UACR that lands at 35 (just crossing microalbuminuria threshold) becomes
   harder to classify than the anchor would suggest.

4. **Non-diabetes controls** — Metabolic syndrome patients in the candidate pool
   test whether students verify the diabetes diagnosis before classifying.

## Clinical Context Card (Required in Notebook)

**Audience note:** BMI 512 has two student populations — clinical informatics
fellows (completed residency, fluent in clinical concepts) and PhD/MS biomedical
informatics students (may not know diabetes management details). The notebook
MUST include a clinical reference section before Activity 1 that covers:

- What HbA1c measures and what the thresholds mean (>7.5% suboptimal, >9% poor)
- What eGFR measures and what the thresholds mean (<60 = CKD stage 3+)
- What UACR measures and why it matters (early kidney damage even when eGFR is OK)
- Why kidney function complicates diabetes management (medication changes, specialist referral)
- What the categories mean in plain language

This is NOT a collapsible or skippable section — it should be visible to all
students. Clinical fellows will skim it in 30 seconds; PhD/MS students will
use it as a reference throughout the activity.

## Candidate Pool Construction

- Show ONLY demographics (name, age, gender) in the candidate table
- NO pre-computed clinical data (no A1c, no CKD flag, no insulin indicator)
- NO seed group or phenotype labels
- Include patients from at least 4 of the 6 phenotypes
- Include at least 1 non-diabetes control (metabolic syndrome)
- Shuffle order to prevent phenotype clustering
- 6-8 patients total: 2 clear cases, 2-3 ambiguous cases, 1 non-DM control, 1-2 additional

## Potential Shortcuts to Block

- **A1c alone:** Tells control but not complexity
- **Conditions alone:** Tells diagnoses but not severity
- **Medications alone:** Tells regimen complexity but not outcomes
- **Candidate table giving away the answer:** Demographics only, no clinical data
- **Evidence checklist:** Remove the prescriptive "Key evidence to look for" section
  that told students C-peptide was the answer. Let students decide what to query.

## Difficulty Assessment

**Medium** for BMI 512 informatics trainees. Classification categories are
intuitive with the clinical context card. The challenge is in gathering enough
evidence to distinguish edge cases, not in understanding what the categories
mean. 3-5 minutes per patient, 6-8 patients, 20-35 minutes for the activity.

## Self-Evaluation (Six Tests)

1. **Single-Query Shortcut:** PASS — no single query resolves any category
2. **Evidence Type Diversity:** PASS — requires Observations (multiple LOINC codes), MedicationRequests, and Conditions
3. **Ambiguity and Uncertainty:** PASS — T1D early nephropathy and T2D obesity CKD2 have genuinely defensible boundary answers
4. **Clinical Plausibility:** PASS — complexity assessment is a standard clinical workflow (ADA Standards of Care)
5. **Data Availability:** PASS — all required data types exist in the synthetic cohort
6. **Difficulty Calibration:** PASS — medium difficulty, appropriate for mixed-background audience with clinical context card

## Previous Design (Superseded)

The original "Type 1 vs Type 2 Clarification" scenario was retired because:
- C-peptide alone solved classification with one query
- No genuinely ambiguous cases existed in the data
- The task failed the single-query shortcut test
- It did not teach iterative evidence gathering

See `docs/agent-test-results-2026-03-23.md` for the full litmus test analysis.
