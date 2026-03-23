# Phenotype JSON Schema (Pragmatic)

This project uses a compact JSON schema for phenotype-driven sampling.

## Top-level structure
```json
{
  "schema_version": "1.0",
  "variables_order": ["patient_id", "age_years", "..."],
  "phenotypes": [
    {
      "id": "t2d_obesity_ckd2",
      "name": "Type 2 diabetes with obesity and CKD G2/A2",
      "anchors": {"age_years": 58, "...": "..."},
      "spread": {
        "age_years": {"dist": "truncnorm", "sd": 6},
        "triglycerides_mg_dl": {"dist": "lognormal", "cv": 0.30}
      },
      "categorical_probs": {
        "insulin_use": {"none": 0.30, "basal": 0.45, "bolus": 0.05, "basal_bolus": 0.20, "pump": 0.00},
        "metformin_use": {"0": 0.15, "1": 0.85}
      }
    }
  ]
}
```

## Required fields per phenotype
- `id`: machine-safe unique string.
- `name`: human-readable title.
- `anchors`: baseline values for all generated fields except `patient_id`.

## Optional fields per phenotype
- `spread`: per-variable noise model.
  - `{"dist":"truncnorm","sd":X}` for approximately symmetric variables.
  - `{"dist":"lognormal","cv":X}` for positive skewed variables.
- `categorical_probs`: category probabilities for enums/binaries.

## Core consistency rules
- `ckd_stage` is derived from `egfr_ml_min_1_73m2`.
- `albuminuria_stage` is derived from `uacr_mg_g`.
- `uacr_mg_g` is derived from urine albumin and creatinine when possible.
- `random_glucose_mg_dl` should usually be at least `fasting_glucose_mg_dl`.
- `diabetes_type = none` implies:
  - `diabetes_duration_years = 0`
  - `insulin_use = none`
  - `metformin_use = 0`
  - `sglt2_inhibitor_use = 0`
  - `glp1_ra_use = 0`
- Non-ESRD assumption: eGFR must be >= 15.

## Practical guidance
- Start with 5 to 10 phenotypes.
- Set realistic variability by variable type; do not reuse one SD everywhere.
- Validate after every change with `scripts/validate_patients.py`.
