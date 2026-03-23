# Technical Design Document
## Synthetic EHR Data Generator POC (Diabetes + Non-ESRD Renal)
Date: February 11, 2026
Status: Draft v0.2
Related PRD: `synthetic-ehr/PRD_SYNTHETIC_EHR_POC.md`

## 1. Purpose
Define the technical architecture and implementation details for generating clinically plausible synthetic patient-level EHR records from phenotype configurations.

## 2. Scope
In scope:
- Phenotype-first tabular generation.
- Internal clinical coupling constraints.
- Config and output validation.
- Single-phenotype and mixed-cohort generation.
- Physician-facing narrative review UI for generated CSVs.

Out of scope (this phase):
- PHI handling.
- Learned generative models.
- Longitudinal event simulation.
- FHIR-native storage/deployment.

## 3. Repository Structure
Root: `synthetic-ehr`

- `assets/phenotype_template.json`
- `assets/cohort_plan_example.json`
- `assets/new_phenotype_overrides_example.json`
- `references/phenotype_schema.md`
- `scripts/generate_patients.py`
- `scripts/generate_cohort.py`
- `scripts/validate_patients.py`
- `scripts/validate_phenotypes.py`
- `scripts/add_phenotype.py`
- `SKILL.md`

Teaching release UI/demo artifacts:
- `synthetic-ehr/v1-teaching-release/web/patient_narrative_viewer.html`
- `synthetic-ehr/v1-teaching-release/demo_run.sh`
- `synthetic-ehr/v1-teaching-release/synthetic-ehr-phenotype/assets/cohort_plan_3_per_phenotype.json`
- `synthetic-ehr/v1-teaching-release/demo-output/demo_cohort_3_per_phenotype.csv`

## 4. High-Level Architecture
1. Config layer:
- Phenotype JSON defines variable order, anchors, spread, and categorical probabilities.

2. Sampling layer:
- Numeric fields sampled via truncated normal or log-normal distributions.
- Categorical/binary fields sampled from configured probabilities or anchor defaults.

3. Clinical coupling layer:
- Deterministic post-sampling transforms enforce physiological coherence.

4. Validation layer:
- Config validator checks schema and anchor constraints.
- Output validator checks bounds, logical rules, and realism warnings.

5. Authoring layer:
- New phenotypes created via clone + override workflow.

6. Narrative presentation layer:
- Browser-based local HTML/JS viewer renders one-patient descriptive narratives from CSV.
- Internal IDs/field names are mapped to clinician-readable labels.

## 5. Data Contracts

### 5.1 Phenotype Config Contract
Top-level keys:
- `schema_version` (required, currently `"1.0"`)
- `variables_order` (required list, first item must be `patient_id`)
- `phenotypes` (required non-empty list)

Per phenotype keys:
- `id` (required unique string)
- `name` (required string)
- `anchors` (required object with value for each variable except `patient_id`)
- `spread` (optional object)
- `categorical_probs` (optional object)

Supported spread types:
- `truncnorm` with optional `sd > 0`
- `lognormal` with optional `cv > 0`

### 5.2 Cohort Plan Contract
- `schema_version` (string)
- `cohort_name` (string)
- `jobs` (non-empty list of objects)
- Each job: `phenotype_id` (string), `n` (positive integer)

Compact demo plan:
- `assets/cohort_plan_3_per_phenotype.json` with 3 rows per phenotype (18 total).

## 6. Variable Model

### 6.1 Numeric Boundaries
All core numeric variables are bounded, including:
- age 18-90
- BMI 16-60
- HbA1c 4.0-16.0
- FPG 60-500
- Random glucose 60-700
- eGFR 15-130
- UACR 1-5000
- creatinine 0.3-6.0
- BUN 4-120
(plus vitals and lipid bounds defined in code)

### 6.2 Enumerations
- `sex_at_birth`: male/female
- `diabetes_type`: none/type1/type2
- `ckd_stage`: G1/G2/G3a/G3b/G4
- `albuminuria_stage`: A1/A2/A3
- `insulin_use`: none/basal/bolus/basal_bolus/pump

### 6.3 Binary fields
- `metformin_use`
- `sglt2_inhibitor_use`
- `glp1_ra_use`

## 7. Generation Pipeline

### 7.1 Single-Phenotype Generation (`generate_patients.py`)
1. Load config and select phenotype by id.
2. For each requested row:
- Sample all fields from anchors + variability model.
- Apply clinical coupling rules.
- Round/cast fields to intended numeric types.
- Validate row; reject/resample if invalid.
3. Write CSV in `variables_order` column order.

### 7.2 Mixed-Cohort Generation (`generate_cohort.py`)
1. Load phenotype config and cohort plan.
2. For each plan job, sample `n` rows using shared seeded RNG.
3. Concatenate rows, write one CSV.
4. Emit summary counts by phenotype, diabetes type, and CKD stage.

### 7.3 Narrative Viewer (`patient_narrative_viewer.html`)
1. User uploads generated CSV in browser.
2. CSV parsed client-side (no network dependency).
3. One patient displayed at a time as narrative + clinician-labeled details.
4. Previous/next controls and phenotype filter supported.

## 8. Clinical Coupling Rules (Current Implementation)
In `scripts/generate_patients.py`:

1. Basic physiologic ordering:
- `diastolic_bp_mmhg < systolic_bp_mmhg`
- `random_glucose_mg_dl >= fasting_glucose_mg_dl` (usually enforced)

2. HbA1c-glucose coherence:
- Compute glucose-based expected A1c using ADAG relation:
  - `expected_hba1c = (estimated_avg_glucose + 46.7) / 28.7`
  - where `estimated_avg_glucose = 0.65 * fasting + 0.35 * random`
- Blend sampled A1c toward expected value and clamp to bounds.

3. Renal chemistry coherence:
- Expected creatinine derived from eGFR, age, sex offset.
- BUN adjusted based on creatinine and reduced eGFR burden.

4. Urine coherence:
- `uacr_mg_g = 100 * urine_albumin_mg_l / urine_creatinine_mg_dl`

5. Staging derivations:
- `ckd_stage` derived from eGFR thresholds.
- `albuminuria_stage` derived from UACR thresholds.

6. Metabolic coupling:
- TG rises with BMI and glycemic burden.
- HDL inversely coupled to TG and adiposity.

7. BP coupling:
- SBP/DBP adjusted via age, BMI, and CKD burden effects.

8. Diabetes-type constraints:
- `diabetes_type = none`:
  - duration = 0
  - insulin and diabetes meds off
  - A1c capped to non-diabetes range
- `diabetes_type = type1`:
  - duration >= 1
  - insulin cannot be none
  - C-peptide upper-limited with longer duration
- `diabetes_type = type2`:
  - duration >= 1
  - C-peptide floor enforced
  - insulin pump remapped to basal_bolus

9. Non-ESRD guardrail:
- eGFR is clamped to >= 15 for all outputs.

## 9. Validation Design

### 9.1 Config Validation (`validate_phenotypes.py`)
Checks:
- Schema/version/required sections.
- Unique phenotype ids.
- Complete anchors for all required variables.
- Anchor type/range/enum validity.
- `spread` and `categorical_probs` structural correctness.
- Probability maps numeric and positive-sum.

### 9.2 Output Validation (`validate_patients.py`)
Hard error checks:
- Numeric bounds.
- Enum validity.
- Binary validity.
- BP and glucose ordering checks.
- Diabetes-none duration rule.
- Non-ESRD eGFR rule.

Realism warnings:
- A1c far from glucose-implied value.
- Creatinine weakly aligned with eGFR/age/sex expectation.

Current template target:
- 0 hard errors
- 0 warnings on standard demo cohort.

## 10. Determinism and Reproducibility
- All sampling uses `random.Random(seed)`.
- Same inputs + seed -> same outputs.
- Mixed cohort generation uses single RNG stream across jobs to remain deterministic.

## 11. Interfaces and CLI Contracts

### 11.1 `generate_patients.py`
Args:
- `--phenotypes` (required)
- `--phenotype-id` (required)
- `--n` (default 100)
- `--seed` (default 1)
- `--out` (required)

### 11.2 `generate_cohort.py`
Args:
- `--phenotypes` (required)
- `--plan` (required)
- `--seed` (default 1)
- `--out` (required)
- `--summary-out` (optional)

### 11.3 `validate_patients.py`
Args:
- `--input` (required)

### 11.4 `validate_phenotypes.py`
Args:
- `--phenotypes` (required)

### 11.5 `add_phenotype.py`
Args:
- `--phenotypes` (required)
- `--base-id` (required)
- `--new-id` (required)
- `--new-name` (required)
- `--overrides` (optional)
- `--out` (optional)

### 11.6 Narrative Viewer UI
- File: `synthetic-ehr/v1-teaching-release/web/patient_narrative_viewer.html`
- Input: generated CSV from current schema.
- Behavior:
  - one-record-at-a-time narrative
  - clinician-readable phenotype names and medication text
  - no programmatic labels in narrative text

## 12. Test Plan
1. Unit-level spot tests (manual script-based for POC):
- Validate each script on happy path.
- Validate script failures on malformed configs.

2. Integration tests (CLI sequence):
- Validate template phenotype config.
- Generate single phenotype cohort.
- Validate generated single-phenotype CSV.
- Generate mixed cohort.
- Validate mixed cohort CSV.

3. Teaching artifact tests:
- Extract at least two sample patients per phenotype.
- Verify plausibility brief references current phenotype definitions.

## 13. Requirement Traceability (PRD -> Implementation)
| PRD Requirement | Implementation Location |
|---|---|
| FR-1 Phenotype configuration load + validation | `scripts/validate_phenotypes.py`, `scripts/generate_patients.py`, `scripts/generate_cohort.py` |
| FR-2 Single-phenotype generation | `scripts/generate_patients.py` (`main`, `sample_row`) |
| FR-3 Mixed-cohort generation + summary | `scripts/generate_cohort.py` |
| FR-4 Clinical coupling rules | `scripts/generate_patients.py` (`apply_relationships`, stage derivation helpers) |
| FR-5 Output validation + realism warnings | `scripts/validate_patients.py` |
| FR-6 Phenotype authoring workflow | `scripts/add_phenotype.py` + `assets/new_phenotype_overrides_example.json` |
| FR-7 Teaching documentation | `synthetic-ehr/PHENOTYPE_PLAUSIBILITY_BRIEF_SHORT.md` |
| FR-8 Physician narrative review UI | `synthetic-ehr/v1-teaching-release/web/patient_narrative_viewer.html` |
| PRD AC-1 config gate | `scripts/validate_phenotypes.py` |
| PRD AC-2/3 generation gates | `scripts/generate_patients.py`, `scripts/generate_cohort.py` |
| PRD AC-4/5 quality gates | `scripts/validate_patients.py` |
| PRD AC-6 sample extraction review | Operational check from generated CSV (`patient_id` prefix by phenotype) |

## 14. Performance Expectations
- Typical runtime for 900-row mixed cohort: under 1 second on local laptop (observed in this environment).
- Memory footprint negligible for v1-scale datasets.

## 15. Failure Modes and Handling
1. Missing phenotype id -> explicit available-id error.
2. Missing anchors -> immediate error naming variable.
3. Repeated invalid samples -> capped retries then failure.
4. Malformed probabilities -> config validation failure.
5. Out-of-bounds numeric outputs -> rejected via row validation.

## 16. Security and Data Safety
- No PHI ingestion.
- Local file-based execution only.
- No network dependency required for generation.

## 17. Versioning and Release Plan
For v1 teaching release, freeze a bundle containing:
- phenotype template JSON
- cohort plan JSON
- generation + validation scripts
- schema reference
- plausibility brief
- PRD and technical design docs

Suggested release tag convention:
- `teaching-v1.0`

## 18. Change Control (Pre-Release Tuning)
1. Change classes:
- `Minor config change`: anchor/spread/probability edits in phenotype JSON.
- `Rule change`: equation/constraint changes in `scripts/generate_patients.py`.
- `Validation change`: new or modified checks in validators.

2. Required process for any change:
- Run `validate_phenotypes.py` on updated config.
- Regenerate standard mixed cohort with fixed seed and plan.
- Run `validate_patients.py`; hard errors must be zero.
- Compare realism warnings to baseline; warnings cannot increase for release candidates.
- Update teaching brief if phenotype semantics changed.
- Record date + short rationale in project notes.

3. Freeze policy for teaching release:
- Freeze scripts, phenotype config, cohort plan, and docs together.
- Do not edit frozen artifacts without bumping release tag (`teaching-v1.x`).

## 19. Planned Future Enhancements
1. Structured report generator (`report_cohort.py`).
2. FHIR mapping/export module.
3. Optional API-assisted phenotype drafting with strict validation gating.
4. Longitudinal patient trajectory simulation.

## 20. Grounding References
1. NIDDK diabetes/prediabetes testing criteria.
2. NIDDK A1c overview.
3. Nathan et al. ADAG relationship (Diabetes Care 2008).
4. KDIGO 2024 CKD guideline.
5. CKD-EPI creatinine framework (NKF).
6. AHA/NHLBI metabolic syndrome statement.
7. Harmonized metabolic syndrome criteria.
8. ACC/AHA 2017 blood pressure guideline summary.
9. Jones & Hattersley on C-peptide utility.
