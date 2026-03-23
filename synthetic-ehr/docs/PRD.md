# Product Requirements Document (Draft)
## Synthetic EHR Data Generator (Diabetes + Non-ESRD Renal Disease)
Date: February 11, 2026
Status: Draft v0.2
Owner: Joel Saltz + Codex collaboration

## 1. Purpose
Build a fast, transparent proof-of-concept system to generate clinically plausible synthetic patient-level EHR data for teaching and informatics prototyping. The system must prioritize internal clinical realism and reproducibility over real-world prevalence matching.

## 2. Background and Context
The project evolved from a broader synthetic EHR discussion into a focused half-day proof-of-concept. Current direction is a phenotype-first simulator using explicit distributions and relationship rules, with no PHI and no privacy-engineering requirements for this phase.

## 3. Goals
1. Generate synthetic tabular patient records from clinically defined phenotype archetypes.
2. Enforce realistic relationships among glycemic, renal, metabolic, and vital-sign variables.
3. Keep generation deterministic/reproducible via seed and JSON-configured phenotypes.
4. Provide quality checks that detect implausible ranges and inconsistent relationships.
5. Support teaching use cases with explainable phenotype definitions and references.
6. Support physician review with one-patient-at-a-time narrative display.

## 4. Non-Goals (Current Phase)
1. Training GAN/diffusion/LLM generative models.
2. Matching real-world cohort prevalence distributions.
3. Deploying production infrastructure.
4. Handling PHI or privacy-preserving release guarantees.
5. Full FHIR-native pipeline (tracked as future phase).

## 5. Primary Users
1. Clinician informatics educators.
2. Researchers prototyping analytics pipelines on realistic synthetic data.
3. Developers testing downstream ETL, feature extraction, and dashboards.

## 6. In-Scope Data Domain
Focus: diabetes (none/type1/type2) and non-ESRD renal disease.

### 6.1 Variables (current schema)
- patient_id
- age_years
- sex_at_birth
- race
- ethnicity
- bmi_kg_m2
- diabetes_type
- diabetes_duration_years
- systolic_bp_mmhg
- diastolic_bp_mmhg
- heart_rate_bpm
- hba1c_percent
- fasting_glucose_mg_dl
- random_glucose_mg_dl
- c_peptide_ng_ml
- creatinine_mg_dl
- egfr_ml_min_1_73m2
- bun_mg_dl
- urine_albumin_mg_l
- urine_creatinine_mg_dl
- uacr_mg_g
- ldl_mg_dl
- hdl_mg_dl
- triglycerides_mg_dl
- ckd_stage
- albuminuria_stage
- insulin_use
- metformin_use
- sglt2_inhibitor_use
- glp1_ra_use

### 6.2 Exclusions
- ESRD and dialysis are excluded.
- eGFR must remain >= 15.

## 7. Phenotype Set (v1)
Six phenotype classes:
1. metabolic_syndrome_no_dm_ckd
2. early_t2d_no_ckd
3. t2d_obesity_ckd2
4. advanced_t2d_ckd3b
5. t1d_early_nephropathy
6. t1d_poor_control_ckd3a

Phenotypes are defined in JSON with anchors + optional spread + optional categorical probabilities.

## 8. Functional Requirements
### FR-1: Phenotype Configuration
- System shall load phenotype definitions from JSON.
- System shall validate schema structure, required fields, and basic value constraints.

### FR-2: Single-Phenotype Generation
- System shall generate N synthetic rows for a chosen phenotype id.
- System shall support deterministic output via random seed.

### FR-3: Multi-Phenotype Cohort Generation
- System shall generate mixed cohorts from a plan file specifying phenotype_id and n.
- System shall emit summary counts by phenotype and key categories.

### FR-4: Clinical Coupling Rules
System shall enforce/derive relationships, including:
- HbA1c-glucose coherence (ADAG-guided).
- Creatinine/eGFR/age/sex coherence.
- BUN coherence with renal status.
- UACR from urine albumin and urine creatinine.
- CKD stage from eGFR.
- Albuminuria stage from UACR.
- Diabetes-type-specific medication and C-peptide constraints.
- Random glucose usually >= fasting glucose.

### FR-5: Validation
- System shall validate generated datasets for hard errors (range/logic violations).
- System shall report realism warnings for major consistency checks.

### FR-6: Phenotype Authoring Workflow
- System shall support creation of a new phenotype by cloning an existing one and applying override JSON.

### FR-7: Documentation for Teaching
- System shall provide a concise phenotype plausibility brief with references suitable for classroom use.

### FR-8: Physician Narrative Review UI
- System shall provide a local UI that reads generated CSV files and displays one patient narrative at a time.
- UI text shall use clinician-readable language (no internal program identifiers/field names).
- UI shall support previous/next navigation and phenotype filtering.

## 9. Non-Functional Requirements
1. Reproducibility: identical seed + config => identical output.
2. Transparency: all rules and thresholds readable in source/config.
3. Local execution: runs on a standard laptop with Python.
4. Speed: cohort generation (<= 1,000 rows) should run in seconds.
5. Safety: no PHI inputs required.

## 10. Current Software Artifacts
Root: `synthetic-ehr`

- `assets/phenotype_template.json`
- `assets/cohort_plan_example.json`
- `assets/new_phenotype_overrides_example.json`
- `scripts/generate_patients.py`
- `scripts/generate_cohort.py`
- `scripts/validate_patients.py`
- `scripts/validate_phenotypes.py`
- `scripts/add_phenotype.py`
- `references/phenotype_schema.md`
- `SKILL.md`

Teaching brief:
- `synthetic-ehr/PHENOTYPE_PLAUSIBILITY_BRIEF_SHORT.md`

Teaching release snapshot:
- `synthetic-ehr/v1-teaching-release`
- Includes: frozen configs/scripts/docs, demo runner, compact demo outputs, physician narrative web viewer.

## 11. Inputs and Outputs
### Inputs
- Phenotype JSON config.
- Optional cohort plan JSON.
- Command line params: phenotype id (or plan), n, seed, output path.

### Outputs
- CSV synthetic patient dataset.
- Optional summary JSON (for mixed cohort generation).
- Validation report to stdout (errors + warnings).
- Optional clinician-facing narrative review via local HTML UI.

## 12. Quality and Acceptance Criteria (v1)
Release candidate is acceptable when all checks pass:
1. Phenotype config check:
   - `python3 scripts/validate_phenotypes.py --phenotypes assets/phenotype_template.json`
   - Expected: pass.
2. Single-phenotype generation check:
   - Each of the 6 phenotype ids can generate at least 100 rows with no hard validation failures.
3. Mixed-cohort generation check:
   - `python3 scripts/generate_cohort.py --phenotypes assets/phenotype_template.json --plan assets/cohort_plan_example.json --seed 17 --out /tmp/mixed_diabetes_renal_demo.csv --summary-out /tmp/mixed_diabetes_renal_demo_summary.json`
   - Expected: CSV and summary JSON written successfully.
4. Dataset validation check:
   - `python3 scripts/validate_patients.py --input /tmp/mixed_diabetes_renal_demo.csv`
   - Expected: no hard errors.
5. Realism-warning target for template cohort:
   - Current gate: 0 warnings for provided phenotype template and cohort plan.
6. Teaching-readiness check:
   - At least 2 sample patients per phenotype class can be extracted and reviewed.
   - Plausibility brief is present and up to date.
7. Physician UI check:
   - Narrative viewer loads generated CSV.
   - Viewer text uses clinician-readable terms.
   - Viewer supports one-record navigation and phenotype filter.

## 13. Risks and Mitigations
1. Risk: Overconstrained equations create unrealistic homogenization.
   - Mitigation: Keep per-variable spread and phenotype-specific variability tunable.
2. Risk: Hidden contradictions between anchors and derived rules.
   - Mitigation: re-derive stage fields and validate every run.
3. Risk: Misinterpretation as real population simulator.
   - Mitigation: explicit documentation that prevalence realism is out of scope.
4. Risk: Educational overconfidence in synthetic outputs.
   - Mitigation: include references, caveats, and transparent assumptions.

## 14. Future Phases (Not in v1)
1. FHIR export/mapping layer and local FHIR server integration.
2. Optional API-assisted phenotype drafting with strict validator gating.
3. Longitudinal trajectories (multi-visit timelines).
4. More disease domains and medication detail.

## 15. Requirement Decisions (Locked for v1)
1. Race/ethnicity handling:
   - Keep broad and phenotype-anchored; do not enforce population-prevalence calibration in v1.
2. Medication semantics:
   - Interpret medication fields as current-use indicators only (binary except categorical `insulin_use`).
   - Do not model dose/intensity tiers in v1.
3. Renal realism level:
   - Keep current strict coupling (eGFR-creatinine-BUN + UACR-derived albuminuria stage).
   - Do not implement longitudinal renal progression logic in v1.
4. Default demo cohort plan:
   - Use the existing intentionally skewed plan in `assets/cohort_plan_example.json` to emphasize phenotype contrasts for teaching.
5. Release artifact strategy:
   - Freeze a versioned teaching release bundle after final tuning:
     - phenotype config
     - cohort plan
     - generator/validator scripts
     - plausibility brief

## 16. References (Grounding)
1. NIDDK diabetes/prediabetes testing criteria.
2. NIDDK A1c test overview.
3. Nathan et al., ADAG relationship, Diabetes Care 2008.
4. KDIGO 2024 CKD guideline.
5. CKD-EPI 2021 creatinine equation framework (NKF).
6. AHA/NHLBI metabolic syndrome statement (Grundy et al.).
7. Harmonized metabolic syndrome criteria (Alberti et al.).
8. ACC/AHA 2017 BP guideline summary.
9. Jones & Hattersley review on C-peptide utility.
