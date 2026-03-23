#!/usr/bin/env python3
import argparse
import json
from typing import Any, Dict, List

NUMERIC_BOUNDS = {
    "age_years": (18, 90),
    "bmi_kg_m2": (16, 60),
    "diabetes_duration_years": (0, 65),
    "systolic_bp_mmhg": (80, 240),
    "diastolic_bp_mmhg": (40, 140),
    "heart_rate_bpm": (40, 180),
    "hba1c_percent": (4.0, 16.0),
    "fasting_glucose_mg_dl": (60, 500),
    "random_glucose_mg_dl": (60, 700),
    "c_peptide_ng_ml": (0.01, 10.0),
    "creatinine_mg_dl": (0.3, 6.0),
    "egfr_ml_min_1_73m2": (15, 130),
    "bun_mg_dl": (4, 120),
    "urine_albumin_mg_l": (1, 3000),
    "urine_creatinine_mg_dl": (5, 400),
    "uacr_mg_g": (1, 5000),
    "ldl_mg_dl": (20, 300),
    "hdl_mg_dl": (10, 120),
    "triglycerides_mg_dl": (30, 1500),
}

ENUM_ALLOWED = {
    "sex_at_birth": {"male", "female"},
    "race": {"White", "Black", "Asian", "Other"},
    "ethnicity": {"Hispanic", "Non-Hispanic"},
    "diabetes_type": {"none", "type1", "type2"},
    "ckd_stage": {"G1", "G2", "G3a", "G3b", "G4"},
    "albuminuria_stage": {"A1", "A2", "A3"},
    "insulin_use": {"none", "basal", "bolus", "basal_bolus", "pump"},
}

BINARY_FIELDS = {"metformin_use", "sglt2_inhibitor_use", "glp1_ra_use"}


def load_json(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def validate_prob_map(name: str, probs: Dict[str, Any], errors: List[str]) -> None:
    if not isinstance(probs, dict) or not probs:
        errors.append(f"{name}: probabilities must be a non-empty object")
        return
    total = 0.0
    for k, v in probs.items():
        try:
            fv = float(v)
        except Exception:
            errors.append(f"{name}: probability for '{k}' is not numeric")
            continue
        if fv < 0:
            errors.append(f"{name}: probability for '{k}' is negative")
        total += fv
    if total <= 0:
        errors.append(f"{name}: probability sum must be > 0")


def validate_phenotype(cfg: Dict[str, Any], pheno: Dict[str, Any], errors: List[str]) -> None:
    pid = pheno.get("id", "<missing-id>")
    anchors = pheno.get("anchors")
    if not isinstance(anchors, dict):
        errors.append(f"{pid}: missing or invalid anchors object")
        return

    vars_order = cfg.get("variables_order", [])
    for var in vars_order:
        if var == "patient_id":
            continue
        if var not in anchors:
            errors.append(f"{pid}: missing anchor for '{var}'")
            continue

        value = anchors[var]
        if var in NUMERIC_BOUNDS:
            lo, hi = NUMERIC_BOUNDS[var]
            try:
                fv = float(value)
            except Exception:
                errors.append(f"{pid}: anchor '{var}' not numeric")
                continue
            if fv < lo or fv > hi:
                errors.append(f"{pid}: anchor '{var}' out of bounds ({fv}, expected {lo}-{hi})")

        if var in ENUM_ALLOWED and value not in ENUM_ALLOWED[var]:
            errors.append(f"{pid}: anchor '{var}' invalid enum value '{value}'")

        if var in BINARY_FIELDS:
            try:
                iv = int(value)
            except Exception:
                errors.append(f"{pid}: anchor '{var}' must be 0/1")
                continue
            if iv not in (0, 1):
                errors.append(f"{pid}: anchor '{var}' must be 0/1")

    spread = pheno.get("spread", {})
    if spread and not isinstance(spread, dict):
        errors.append(f"{pid}: spread must be an object")
    elif isinstance(spread, dict):
        for var, spec in spread.items():
            if var not in vars_order:
                errors.append(f"{pid}: spread variable '{var}' is not in variables_order")
                continue
            if not isinstance(spec, dict):
                errors.append(f"{pid}: spread for '{var}' must be an object")
                continue
            dist = spec.get("dist", "truncnorm")
            if dist not in {"truncnorm", "lognormal"}:
                errors.append(f"{pid}: spread '{var}' dist must be truncnorm or lognormal")
            if dist == "truncnorm" and "sd" in spec:
                try:
                    if float(spec["sd"]) <= 0:
                        errors.append(f"{pid}: spread '{var}' sd must be > 0")
                except Exception:
                    errors.append(f"{pid}: spread '{var}' sd must be numeric")
            if dist == "lognormal" and "cv" in spec:
                try:
                    if float(spec["cv"]) <= 0:
                        errors.append(f"{pid}: spread '{var}' cv must be > 0")
                except Exception:
                    errors.append(f"{pid}: spread '{var}' cv must be numeric")

    categorical = pheno.get("categorical_probs", {})
    if categorical and not isinstance(categorical, dict):
        errors.append(f"{pid}: categorical_probs must be an object")
    elif isinstance(categorical, dict):
        for var, probs in categorical.items():
            if var not in vars_order:
                errors.append(f"{pid}: categorical_probs variable '{var}' is not in variables_order")
                continue
            validate_prob_map(f"{pid}:categorical_probs:{var}", probs, errors)


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate phenotype JSON config")
    parser.add_argument("--phenotypes", required=True, help="Path to phenotype JSON")
    args = parser.parse_args()

    cfg = load_json(args.phenotypes)
    errors: List[str] = []

    if cfg.get("schema_version") != "1.0":
        errors.append("schema_version must be '1.0'")

    vars_order = cfg.get("variables_order")
    if not isinstance(vars_order, list) or not vars_order:
        errors.append("variables_order must be a non-empty list")
    elif vars_order[0] != "patient_id":
        errors.append("variables_order must start with 'patient_id'")

    phenos = cfg.get("phenotypes")
    if not isinstance(phenos, list) or not phenos:
        errors.append("phenotypes must be a non-empty list")
        phenos = []

    seen = set()
    for p in phenos:
        pid = p.get("id")
        if not pid:
            errors.append("phenotype missing id")
            continue
        if pid in seen:
            errors.append(f"duplicate phenotype id '{pid}'")
        seen.add(pid)
        validate_phenotype(cfg, p, errors)

    if errors:
        print("Validation FAILED")
        for e in errors:
            print(f"- {e}")
        raise SystemExit(1)

    print(f"Validation PASSED for {len(phenos)} phenotype(s)")


if __name__ == "__main__":
    main()
