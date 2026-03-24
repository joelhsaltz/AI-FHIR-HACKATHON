# Scenario: Diabetes Management Complexity Assessment

**Status:** Redesigned 2026-03-24. Revised 2026-03-24 after FHIR server data
discovery confirmed richer data than assumed (UACR exists, non-DM controls
exist, eGFR has real spread). Replaces the original "Type 1 vs Type 2
Clarification" scenario, which was trivially solvable with one C-peptide query.

**Designed by:** Clinical Scenario Designer agent, with data discovery by
Synthetic Data Architect agent. Approved by Joel.

**Implementation strategy:** Current FHIR server data (1,027 patients) supports
the full scenario design including UACR as "reward for thoroughness" and
non-diabetes controls. A future Phase 2 with purpose-built phenotypes
(in `synthetic-ehr/assets/phenotype_template.json`) would provide even richer
graded CKD staging but is not required for a strong teaching experience.

## Clinical Question

Based on the available evidence, how would you categorize this patient's
diabetes management complexity?

## Classification Categories

- **Routine** — Diabetes present, well-controlled, no significant complications
- **Moderate complexity** — One complicating factor present (suboptimal control,
  reduced kidney function, OR early kidney damage)
- **High complexity** — Multiple complicating factors converging, or a single
  extreme finding that demands specialist attention
- **No diabetes** — Patient does not have a diabetes diagnosis (present in some
  candidates as a verification check)

## Required Evidence Types

| Evidence | FHIR Resource | LOINC/SNOMED | Why Needed |
|----------|--------------|-------------|------------|
| Conditions | Condition | T1D: 46635009, T2D: 44054006 | Confirms diabetes diagnosis exists. Essential for "No diabetes" detection. Without this, all other queries are unanchored |
| HbA1c | Observation | 4548-4 | Glycemic control. >7.5% = suboptimal (complicating factor). >9% = urgently poor. Necessary but not sufficient for any category |
| eGFR | Observation | 33914-3 | Kidney function severity. <60 = CKD stage 3+ (complicating factor). <30 = automatic High. Cannot be inferred from other data |
| UACR | Observation | 14959-1 | Early kidney damage that eGFR misses. ≥30 mg/g = microalbuminuria (complicating factor). ≥300 = macroalbuminuria (automatic High). The key "reward for thoroughness" data point |
| Medications | MedicationRequest | — | Context for interpreting control and regimen. NOT a direct category driver — prevents single-query shortcut via medication list |

## Minimum Queries to Classify Correctly

**3-4 per patient.** No single query resolves any category:
- Conditions alone: tells diagnoses but not severity
- HbA1c alone: tells control but not kidney involvement
- eGFR alone: tells kidney function but not glycemic control
- UACR alone: tells albuminuria but not whether diabetes is even present
- Medications alone: tells regimen complexity but not outcomes (and deliberately
  not a category driver)

Students who stop at 2 queries will miscategorize the T1D patients with
preserved eGFR but elevated UACR.

## Clinical Thresholds

### HbA1c (Glycemic Control)

| Range | Interpretation | Source |
|-------|---------------|--------|
| <7.0% | At ADA target for most adults | ADA Standards of Care 2025 |
| 7.0-7.5% | Slightly above target, acceptable for some | ADA individualization |
| >7.5% | **Suboptimal — complicating factor** | Project threshold (conservative) |
| >9.0% | Urgently poor control | ADA, AACE guidelines |

### eGFR (Kidney Function)

| Range | CKD Stage | Interpretation |
|-------|-----------|---------------|
| ≥90 | G1 | Normal or high |
| 60-89 | G2 | Mildly decreased |
| 45-59 | G3a | Mild-moderate decrease |
| 30-44 | G3b | Moderate-severe decrease |
| 15-29 | G4 | Severely decreased |
| <15 | G5 | Kidney failure |

**Complicating factor threshold:** eGFR <60 (stage 3+). Medication adjustments
become necessary (e.g., metformin dose reduction).

**Automatic High threshold:** eGFR <30 (stage 4+). Most diabetes meds need
dose adjustment or are contraindicated; nephrology referral is standard.

### UACR (Albuminuria)

| Range | Stage | Interpretation |
|-------|-------|---------------|
| <30 mg/g | A1 | Normal |
| 30-299 mg/g | A2 | Moderately increased (microalbuminuria) |
| ≥300 mg/g | A3 | Severely increased (macroalbuminuria) |

**Complicating factor threshold:** UACR ≥30 mg/g (A2). Early kidney damage
that eGFR may not yet reflect.

**Automatic High threshold:** UACR ≥300 mg/g (A3). Significant kidney damage
requiring aggressive management.

### Medications (Context Only)

Medications are deliberately NOT a direct category threshold. This prevents
students from classifying based on a single MedicationRequest query.
Medications provide context:
- Insulin pump or basal-bolus = complex regimen, but if A1c controlled and
  kidneys OK → still Routine
- Multiple orals + insulin = progressed disease, but category depends on
  control and kidney markers
- No diabetes meds on a diabetes patient = data gap, worth discussion

## Ground Truth Logic (Scoring Rules)

These rules are deterministic. No clinical judgment at scoring time.

### Step 1: Check for Diabetes Diagnosis

Query Condition resources for SNOMED 46635009 (T1D) and 44054006 (T2D).
- If NEITHER present → **No diabetes**. Stop.
- If T1D or T2D present → proceed to Step 2.

### Step 2: Count Complicating Factors

Query HbA1c, eGFR, and UACR. Use most recent value for each.

| Factor | Threshold | Count as 1 if... |
|--------|-----------|-------------------|
| Poor glycemic control | HbA1c >7.5% | Most recent HbA1c exceeds 7.5 |
| Reduced kidney function | eGFR <60 | Most recent eGFR below 60 |
| Albuminuria | UACR ≥30 mg/g | Most recent UACR is 30 or above |

### Step 3: Check for Extreme Single Findings

Regardless of factor count:
- eGFR <30 → **High complexity**. Stop.
- UACR ≥300 → **High complexity**. Stop.

### Step 4: Assign Category by Factor Count

| Factor Count | Category |
|-------------|----------|
| 0 | **Routine** |
| 1 | **Moderate complexity** |
| 2 or 3 | **High complexity** |

### Scoring Student Answers

| Student Answer vs Ground Truth | Result |
|-------------------------------|--------|
| Exact match | Correct |
| Off by one category (e.g., Moderate when High) | Partially correct — feedback shows what evidence was missed |
| Off by two+ categories | Incorrect |
| Any diabetes category for No-DM patient | Incorrect — "Check the diagnosis first" |
| No diabetes for a diabetes patient | Incorrect — "This patient does have a diabetes diagnosis" |

### Feedback Guidance

When students answer incorrectly, hint at the missed evidence without giving
the answer:
- Missed UACR: "The eGFR looks preserved, but there is another kidney marker worth investigating."
- Missed eGFR: "You've assessed glycemic control — have you checked kidney function?"
- Missed conditions: "Did you verify whether this patient has a diabetes diagnosis?"
- Missed HbA1c: "You know the diagnosis, but what about glycemic control?"

## Actual Server Data (Verified 2026-03-24)

### Patient Groups

| Group | N | Conditions | Key Lab Characteristics |
|-------|---|-----------|------------------------|
| T1D | 249 | T1D + CKD (100%) | C-peptide 0.03-0.27, A1c 6.8-9.6, eGFR 46.6-96.0, UACR 65-395 |
| T2D | 630 | T2D + CKD (99.8%) | C-peptide 1.62-5.23, A1c 6.2-9.0, eGFR 29.3-99.2, UACR 21-441 |
| No DM | 148 | No diabetes codes | A1c 5.46-6.15, eGFR 89.8-93.8, UACR 15-18 |

**Critical finding:** CKD is coded for 1,015/1,027 patients. CKD
presence/absence is NOT a useful discriminator. CKD **severity** (eGFR)
is the discriminator.

### Lab Availability

ALL six labs (HbA1c, C-peptide, BMI, creatinine, eGFR, UACR) exist for ALL
patient groups with adequate spread across clinical thresholds.

### Medication Patterns

- T1D: 100% insulin (60% pump, 40% basal-bolus)
- T2D: metformin (70%), SGLT2i (60%), insulin basal (40%), GLP-1 RA (10%)
- No-DM: No diabetes medications

## Where Genuine Ambiguity Lives

### Case Type 1: T1D with preserved eGFR but elevated UACR (core teaching case)

T1D patients have median eGFR 82.5 (looks fine) but median UACR 79.5
(A2 stage, early kidney damage). Students who check only eGFR classify as
Routine. Students who also check UACR catch the hidden damage and correctly
bump to Moderate.

This is exactly how early diabetic nephropathy presents clinically — eGFR
is preserved while albuminuria is already abnormal. The KDIGO guidelines use
both eGFR AND UACR for precisely this reason.

### Case Type 2: T2D with A1c near 7.5% (boundary control)

T2D A1c ranges 6.2-9.0. Patients near 7.5% create threshold tension — a
real-world informatics challenge of applying categorical rules to continuous
data.

### Case Type 3: T2D with low eGFR

T2D eGFR goes as low as 29.3. A T2D patient with controlled A1c but eGFR
of 35 has one complicating factor (eGFR <60) but is also near the automatic
High threshold (eGFR <30). Students must apply specific thresholds.

### Case Type 4: No-DM controls ("is this even diabetes?")

148 patients with no diabetes diagnosis but normal labs. Students who start
with labs might investigate before realizing there's no diabetes diagnosis
to begin with. Teaches: verify diagnoses before interpreting lab values.

### Clear Cases (for confidence calibration)

- No-DM: A1c 5.46-6.15, no diabetes codes → clearly No diabetes
- T2D with A1c <7.0, eGFR >80, UACR <25 → clearly Routine
- T1D with A1c >8.5, eGFR <50, UACR >100 → clearly High

## Candidate Pool Construction

- Show ONLY demographics (name, age, gender) in the candidate table
- NO pre-computed clinical data (no A1c, no CKD flag, no insulin indicator)
- NO seed group or phenotype labels
- Include patients from ALL three condition groups (T1D, T2D, No-DM)
- Shuffle order to prevent grouping
- **6-8 patients total.** Recommended mix:
  - 1-2 No-DM controls
  - 2-3 T2D patients (spanning Routine to High via A1c and eGFR variation)
  - 2-3 T1D patients (at least one with preserved eGFR but elevated UACR)
- Must include at least: one clear Routine, one Moderate, one High, one
  No-diabetes, and one T1D-UACR ambiguity case

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
- The KDIGO heat map concept: risk depends on BOTH eGFR and albuminuria

This is NOT a collapsible or skippable section — it should be visible to all
students. Clinical fellows will skim it in 30 seconds; PhD/MS students will
use it as a reference throughout the activity.

## Potential Shortcuts to Block

- **HbA1c alone:** Tells control but not kidney involvement
- **Conditions alone:** CKD is universal (99%), so presence is meaningless. Must check eGFR for severity
- **eGFR alone:** Misses early kidney damage that UACR catches
- **Medications alone:** Deliberately not a category driver
- **Candidate table giving away the answer:** Demographics only, no clinical data
- **Prescriptive evidence checklist:** Removed. Let students decide what to query

## Difficulty Assessment

**Medium** for BMI 512 informatics trainees. Classification categories are
intuitive with the clinical context card. The challenge is in gathering enough
evidence to distinguish edge cases, not in understanding what the categories
mean. 3-5 minutes per patient, 6-8 patients, 20-35 minutes for the activity.

## Self-Evaluation (Six Tests)

1. **Single-Query Shortcut:** PASS — no single query resolves any category.
   Conditions are useless alone (CKD is universal). HbA1c misses kidneys.
   eGFR misses early damage (UACR). Medications deliberately not a driver.
2. **Evidence Type Diversity:** PASS — requires Conditions + Observations
   (HbA1c + eGFR + UACR = 3 LOINC codes) + MedicationRequests for context.
   Three FHIR resource types, four distinct clinical data elements.
3. **Ambiguity and Uncertainty:** PASS — T1D-UACR hidden damage case is
   genuine ambiguity. T2D boundary cases near 7.5% A1c. No-DM controls as
   verification traps. Mix of clear and ambiguous cases.
4. **Clinical Plausibility:** PASS — complexity assessment using HbA1c + eGFR
   + UACR is standard clinical practice (ADA Standards of Care, KDIGO guidelines).
5. **Data Availability:** PASS — ALL required labs exist on server with adequate
   spread across all thresholds. Verified by direct FHIR queries 2026-03-24.
6. **Difficulty Calibration:** PASS — medium difficulty, appropriate for mixed
   audience with clinical context card.

## Future Improvement: Purpose-Built Phenotypes

The aspirational phenotypes in `synthetic-ehr/assets/phenotype_template.json`
would provide:
- Graded CKD staging (G2 vs G3a vs G3b with distinct eGFR/UACR values)
- More controlled spread around threshold boundaries
- Purpose-designed ambiguity cases
- Metabolic syndrome without diabetes as explicit non-DM controls

These are deferred — the current data supports a strong scenario as-is.

## Previous Design (Superseded)

The original "Type 1 vs Type 2 Clarification" scenario was retired because:
- C-peptide alone solved classification with one query
- No genuinely ambiguous cases existed in the data
- The task failed the single-query shortcut test
- It did not teach iterative evidence gathering

See `docs/agent-test-results-2026-03-23.md` for the full litmus test analysis.
