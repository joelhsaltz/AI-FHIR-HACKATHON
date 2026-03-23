---
name: synthetic-ehr-phenotype
description: Create and maintain phenotype-driven synthetic EHR generators for diabetes and non-ESRD renal disease. Use when defining phenotype JSON files, generating synthetic patients, validating plausibility, or drafting new phenotypes from clinical descriptions.
---

# Synthetic EHR Phenotype Skill

Use this skill for a phenotype-first synthetic EHR workflow.

## Scope
- Python-based synthetic data generation
- Diabetes (none/type1/type2) + non-ESRD renal disease
- Phenotype JSON as source of truth
- Reproducible generation with seeded randomness
- Built-in plausibility and consistency checks

## Workflow
1. Start from `assets/phenotype_template.json`.
2. Edit or add phenotype definitions (anchors, spread, categorical probabilities).
3. Generate data with `scripts/generate_patients.py`.
4. Validate output with `scripts/validate_patients.py`.
5. Iterate on phenotype parameters until checks pass and clinical relationships look reasonable.

## Files
- Schema reference: `references/phenotype_schema.md`
- Template phenotype config: `assets/phenotype_template.json`
- Cohort generation plan example: `assets/cohort_plan_example.json`
- Override example for creating a new phenotype: `assets/new_phenotype_overrides_example.json`
- New phenotype helper: `scripts/add_phenotype.py`
- Generator: `scripts/generate_patients.py`
- Validator: `scripts/validate_patients.py`
- Phenotype config validator: `scripts/validate_phenotypes.py`
- Multi-phenotype cohort generator: `scripts/generate_cohort.py`

## Commands
```bash
python3 scripts/validate_phenotypes.py --phenotypes assets/phenotype_template.json

python3 scripts/add_phenotype.py \
  --phenotypes assets/phenotype_template.json \
  --base-id t2d_obesity_ckd2 \
  --new-id t2d_obesity_ckd3a_variant \
  --new-name "Type 2 diabetes obesity CKD3a variant" \
  --overrides assets/new_phenotype_overrides_example.json \
  --out /tmp/phenotypes_plus_one.json

python3 scripts/generate_patients.py \
  --phenotypes /tmp/phenotypes_plus_one.json \
  --phenotype-id t2d_obesity_ckd3a_variant \
  --n 200 \
  --seed 7 \
  --out /tmp/t2d_obesity_ckd3a_variant.csv

python3 scripts/validate_patients.py --input /tmp/t2d_obesity_ckd3a_variant.csv

python3 scripts/generate_cohort.py \
  --phenotypes assets/phenotype_template.json \
  --plan assets/cohort_plan_example.json \
  --seed 17 \
  --out /tmp/mixed_diabetes_renal_demo.csv \
  --summary-out /tmp/mixed_diabetes_renal_demo_summary.json

python3 scripts/validate_patients.py --input /tmp/mixed_diabetes_renal_demo.csv
```

## Notes
- Keep `ckd_stage` derived from `egfr_ml_min_1_73m2`.
- Keep `albuminuria_stage` derived from `uacr_mg_g`.
- Keep non-ESRD assumption: generated rows must stay above eGFR 15.
- For new phenotype drafting with LLM/API, require JSON validation before use in generation.
