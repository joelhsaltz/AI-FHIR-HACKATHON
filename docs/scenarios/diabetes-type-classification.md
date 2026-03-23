# Scenario: Diabetes Type Classification

**Status:** Active — known issues being addressed

**Clinical question:** Is this younger patient with diabetes more consistent
with Type 1 diabetes, Type 2 diabetes, or unclear based on available evidence?

**Classification categories:** Likely Type 1 / Likely Type 2 / Unclear — needs more review

**Required evidence types:**
- C-peptide (Observation, LOINC 1986-9) — endogenous insulin production;
  low = Type 1, normal/high = Type 2. Currently the strongest single discriminator.
- Medication pattern (MedicationRequest) — insulin-only vs insulin + oral agents
  vs oral agents only. Medication complexity is a supporting signal.
- Problem list (Condition) — diabetes diagnosis codes, comorbidities.
  Note: diagnosis codes are scrambled in student view to prevent trivial lookup.
- BMI (Observation, LOINC 39156-5) — higher BMI more common in Type 2.
  A supporting signal, not diagnostic alone.
- Demographics (Patient) — age, gender. Age of onset is relevant context.

**Minimum queries to classify correctly:** Currently 1 (C-peptide alone) — THIS IS THE PROBLEM

**Where ambiguity lives:** The scenario SHOULD have ambiguity in:
- Patients with missing C-peptide data (must reason from other evidence)
- Type 2 on insulin (superficially resembles Type 1)
- Borderline C-peptide values
- Conflicting evidence (e.g., low C-peptide but T2D diagnosis code)
Currently, ambiguity is insufficient because C-peptide is always available and clearly discriminating.

**Data requirements:**
- Young diabetic patients (age <= 35) with both Type 1 and Type 2
- C-peptide values that are sometimes missing or borderline
- Medication data including insulin and oral agents
- BMI data as supporting evidence
- 6-10 candidates with a mix of clear and ambiguous cases

**Potential shortcuts to block:**
- C-peptide alone: currently solves the task with one query
- Seed group labels: the candidate table includes seed group info that reveals the answer
- Pre-computed evidence: the candidate table should show only demographics, not clinical data

**Difficulty assessment:** Currently TOO EASY for target audience.
Goal: Medium difficulty requiring 3-4 queries per patient.

**Known issues (from litmus tests, 2026-03-23):**
1. C-peptide is trivially discriminating — one query solves the task
2. Candidate table may show seed group labels that reveal the answer
3. No cases where C-peptide is missing or ambiguous
4. Evidence checklist tells students exactly what to query (reduces agency)
5. Combined dropdown mixes query selection and classification (confusing UI)

**Recommended redesign directions:**
- Introduce patients with missing C-peptide (forces multi-evidence reasoning)
- Include Type 2 on insulin patients (creates genuine Type 1 vs Type 2 confusion)
- Strip pre-computed evidence from candidate table
- Separate investigation and classification into distinct UI elements
