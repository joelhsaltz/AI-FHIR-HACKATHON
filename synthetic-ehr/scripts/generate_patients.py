#!/usr/bin/env python3
import argparse
import csv
import json
import math
import random
from typing import Any, Dict, List

BOUNDS = {
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

ENUMS = {
    "sex_at_birth": {"male", "female"},
    "diabetes_type": {"none", "type1", "type2"},
    "ckd_stage": {"G1", "G2", "G3a", "G3b", "G4"},
    "albuminuria_stage": {"A1", "A2", "A3"},
    "insulin_use": {"none", "basal", "bolus", "basal_bolus", "pump"},
}

BINARY_FIELDS = {"metformin_use", "sglt2_inhibitor_use", "glp1_ra_use"}


def clamp(value: float, low: float, high: float) -> float:
    return min(max(value, low), high)


def truncnorm(rng: random.Random, mean: float, sd: float, low: float, high: float) -> float:
    sd = max(sd, 1e-6)
    for _ in range(100):
        x = rng.gauss(mean, sd)
        if low <= x <= high:
            return x
    return min(max(mean, low), high)


def lognormal_from_mean_cv(rng: random.Random, mean: float, cv: float) -> float:
    mean = max(mean, 1e-6)
    cv = max(cv, 1e-4)
    sigma2 = math.log(1.0 + cv * cv)
    sigma = math.sqrt(sigma2)
    mu = math.log(mean) - 0.5 * sigma2
    return math.exp(rng.gauss(mu, sigma))


def weighted_choice(rng: random.Random, probs: Dict[str, float]) -> str:
    total = sum(max(v, 0.0) for v in probs.values())
    if total <= 0:
        return list(probs.keys())[0]
    r = rng.random() * total
    acc = 0.0
    for k, v in probs.items():
        acc += max(v, 0.0)
        if r <= acc:
            return k
    return list(probs.keys())[-1]


def derive_ckd_stage(egfr: float) -> str:
    if egfr >= 90:
        return "G1"
    if egfr >= 60:
        return "G2"
    if egfr >= 45:
        return "G3a"
    if egfr >= 30:
        return "G3b"
    return "G4"


def derive_albuminuria_stage(uacr: float) -> str:
    if uacr < 30:
        return "A1"
    if uacr < 300:
        return "A2"
    return "A3"


def maybe_float(x: Any) -> bool:
    try:
        float(x)
        return True
    except Exception:
        return False


def sample_numeric(var: str, anchor: float, spread: Dict[str, Any], rng: random.Random) -> float:
    low, high = BOUNDS[var]
    spec = spread.get(var, {})
    dist = spec.get("dist", "truncnorm")

    if dist == "lognormal":
        cv = float(spec.get("cv", 0.2))
        x = lognormal_from_mean_cv(rng, float(anchor), cv)
    else:
        default_sd = max(abs(float(anchor)) * 0.08, 1.0)
        sd = float(spec.get("sd", default_sd))
        x = truncnorm(rng, float(anchor), sd, low, high)

    return min(max(x, low), high)


def apply_relationships(row: Dict[str, Any], rng: random.Random) -> None:
    age = float(row["age_years"])
    bmi = float(row["bmi_kg_m2"])
    dm_duration = float(row["diabetes_duration_years"])
    dm_type = row["diabetes_type"]

    if row["diastolic_bp_mmhg"] >= row["systolic_bp_mmhg"]:
        row["diastolic_bp_mmhg"] = max(40.0, row["systolic_bp_mmhg"] - abs(rng.gauss(8, 3)))

    if row["random_glucose_mg_dl"] < row["fasting_glucose_mg_dl"]:
        row["random_glucose_mg_dl"] = row["fasting_glucose_mg_dl"] + abs(rng.gauss(18, 8))

    # Align HbA1c with glucose using the ADAG relationship:
    # eAG (mg/dL) ~= 28.7 * HbA1c - 46.7.
    fasting = float(row["fasting_glucose_mg_dl"])
    random_glucose = float(row["random_glucose_mg_dl"])
    estimated_avg_glucose = (0.65 * fasting) + (0.35 * random_glucose)
    expected_hba1c = (estimated_avg_glucose + 46.7) / 28.7
    row["hba1c_percent"] = clamp(
        (0.7 * float(row["hba1c_percent"])) + (0.3 * expected_hba1c) + rng.gauss(0.0, 0.18),
        *BOUNDS["hba1c_percent"],
    )

    # Renal consistency: eGFR and creatinine should move inversely.
    sex_offset = -0.08 if row["sex_at_birth"] == "female" else 0.0
    egfr = float(row["egfr_ml_min_1_73m2"])
    expected_creatinine = 0.62 + (110.0 - egfr) / 55.0 + (age - 50.0) / 180.0 + sex_offset
    row["creatinine_mg_dl"] = clamp(
        (0.2 * float(row["creatinine_mg_dl"])) + (0.8 * expected_creatinine) + rng.gauss(0.0, 0.04),
        *BOUNDS["creatinine_mg_dl"],
    )

    # BUN tracks reduced kidney function and higher creatinine.
    expected_bun = 8.0 + (4.2 * float(row["creatinine_mg_dl"])) + max(0.0, 90.0 - egfr) * 0.17
    row["bun_mg_dl"] = clamp(
        (0.45 * float(row["bun_mg_dl"])) + (0.55 * expected_bun) + rng.gauss(0.0, 2.0),
        *BOUNDS["bun_mg_dl"],
    )

    # Prefer internal consistency between spot urine measures and UACR.
    uacr = 100.0 * float(row["urine_albumin_mg_l"]) / max(float(row["urine_creatinine_mg_dl"]), 1e-3)
    row["uacr_mg_g"] = clamp(uacr, *BOUNDS["uacr_mg_g"])

    row["ckd_stage"] = derive_ckd_stage(float(row["egfr_ml_min_1_73m2"]))
    row["albuminuria_stage"] = derive_albuminuria_stage(row["uacr_mg_g"])

    # Metabolic coupling: TG tracks BMI and hyperglycemia; HDL inversely tracks TG.
    insulin_resistance_score = max(0.0, bmi - 24.0) * 1.8 + max(0.0, row["hba1c_percent"] - 5.7) * 16.0
    expected_tg = 95.0 + insulin_resistance_score
    row["triglycerides_mg_dl"] = clamp(
        (0.55 * float(row["triglycerides_mg_dl"])) + (0.45 * expected_tg) + rng.gauss(0.0, 14.0),
        *BOUNDS["triglycerides_mg_dl"],
    )
    expected_hdl = 58.0 - 0.055 * float(row["triglycerides_mg_dl"]) - 0.35 * max(0.0, bmi - 28.0)
    row["hdl_mg_dl"] = clamp(
        (0.6 * float(row["hdl_mg_dl"])) + (0.4 * expected_hdl) + rng.gauss(0.0, 2.2),
        *BOUNDS["hdl_mg_dl"],
    )

    # Blood pressure trends up with age, adiposity, and CKD severity.
    ckd_burden = max(0.0, 90.0 - egfr) / 12.0
    expected_sbp = 112.0 + (age - 40.0) * 0.55 + max(0.0, bmi - 25.0) * 0.85 + ckd_burden
    row["systolic_bp_mmhg"] = clamp(
        (0.55 * float(row["systolic_bp_mmhg"])) + (0.45 * expected_sbp) + rng.gauss(0.0, 5.0),
        *BOUNDS["systolic_bp_mmhg"],
    )
    expected_dbp = 68.0 + max(0.0, bmi - 24.0) * 0.45 + min(10.0, (age - 45.0) * 0.15)
    row["diastolic_bp_mmhg"] = clamp(
        (0.6 * float(row["diastolic_bp_mmhg"])) + (0.4 * expected_dbp) + rng.gauss(0.0, 4.0),
        *BOUNDS["diastolic_bp_mmhg"],
    )
    if row["diastolic_bp_mmhg"] >= row["systolic_bp_mmhg"]:
        row["diastolic_bp_mmhg"] = max(40.0, row["systolic_bp_mmhg"] - abs(rng.gauss(9, 2.5)))

    if dm_type == "none":
        row["diabetes_duration_years"] = 0
        row["insulin_use"] = "none"
        row["metformin_use"] = 0
        row["sglt2_inhibitor_use"] = 0
        row["glp1_ra_use"] = 0
        row["hba1c_percent"] = min(row["hba1c_percent"], 6.4)
        row["c_peptide_ng_ml"] = clamp(max(float(row["c_peptide_ng_ml"]), 1.0), *BOUNDS["c_peptide_ng_ml"])
    elif dm_type == "type1":
        row["diabetes_duration_years"] = max(row["diabetes_duration_years"], 1)
        if row["insulin_use"] == "none":
            row["insulin_use"] = "basal_bolus"
        cpep_t1d_upper = max(0.05, 0.55 - 0.015 * dm_duration)
        row["c_peptide_ng_ml"] = min(float(row["c_peptide_ng_ml"]), cpep_t1d_upper)
        row["metformin_use"] = int(row["metformin_use"])
        row["sglt2_inhibitor_use"] = int(row["sglt2_inhibitor_use"])
        row["glp1_ra_use"] = int(row["glp1_ra_use"])
    else:
        row["diabetes_duration_years"] = max(row["diabetes_duration_years"], 1)
        t2d_floor = max(0.3, 2.2 - 0.055 * dm_duration)
        row["c_peptide_ng_ml"] = max(float(row["c_peptide_ng_ml"]), t2d_floor)
        if row["insulin_use"] == "pump":
            row["insulin_use"] = "basal_bolus"

    row["c_peptide_ng_ml"] = clamp(float(row["c_peptide_ng_ml"]), *BOUNDS["c_peptide_ng_ml"])

    # Non-ESRD scope guard.
    row["egfr_ml_min_1_73m2"] = max(float(row["egfr_ml_min_1_73m2"]), 15.0)
    row["ckd_stage"] = derive_ckd_stage(float(row["egfr_ml_min_1_73m2"]))


def row_is_valid(row: Dict[str, Any]) -> bool:
    for k, (low, high) in BOUNDS.items():
        v = row.get(k)
        if not maybe_float(v):
            return False
        f = float(v)
        if f < low or f > high:
            return False

    for k, values in ENUMS.items():
        if row.get(k) not in values:
            return False

    for k in BINARY_FIELDS:
        if int(row.get(k, -1)) not in (0, 1):
            return False

    if row["diastolic_bp_mmhg"] >= row["systolic_bp_mmhg"]:
        return False
    if row["random_glucose_mg_dl"] < row["fasting_glucose_mg_dl"]:
        return False
    if row["diabetes_type"] == "none" and row["diabetes_duration_years"] != 0:
        return False
    if row["egfr_ml_min_1_73m2"] < 15:
        return False

    return True


def normalize_binary(value: Any) -> int:
    if isinstance(value, bool):
        return int(value)
    s = str(value).strip().lower()
    if s in {"1", "true", "yes"}:
        return 1
    return 0


def sample_row(
    phenotype: Dict[str, Any],
    variables: List[str],
    pid: str,
    rng: random.Random,
    max_attempts: int = 50,
) -> Dict[str, Any]:
    anchors = phenotype["anchors"]
    spread = phenotype.get("spread", {})
    cat_probs = phenotype.get("categorical_probs", {})

    for _ in range(max_attempts):
        row: Dict[str, Any] = {"patient_id": pid}
        for var in variables:
            if var == "patient_id":
                continue
            anchor = anchors.get(var)
            if anchor is None:
                raise ValueError(f"Missing anchor for variable '{var}' in phenotype '{phenotype['id']}'")

            if var in BOUNDS:
                row[var] = sample_numeric(var, float(anchor), spread, rng)
                if var == "diabetes_duration_years":
                    row[var] = int(round(row[var]))
            elif var in BINARY_FIELDS:
                if var in cat_probs:
                    row[var] = int(weighted_choice(rng, cat_probs[var]))
                else:
                    row[var] = normalize_binary(anchor)
            elif var in ENUMS:
                if var in cat_probs:
                    row[var] = weighted_choice(rng, cat_probs[var])
                else:
                    row[var] = anchor
            else:
                row[var] = anchor

        apply_relationships(row, rng)

        for k in BINARY_FIELDS:
            row[k] = int(row[k])

        # Keep most outputs as integers where clinically typical.
        for k in [
            "age_years",
            "systolic_bp_mmhg",
            "diastolic_bp_mmhg",
            "heart_rate_bpm",
            "fasting_glucose_mg_dl",
            "random_glucose_mg_dl",
            "bun_mg_dl",
            "urine_albumin_mg_l",
            "urine_creatinine_mg_dl",
            "uacr_mg_g",
            "ldl_mg_dl",
            "hdl_mg_dl",
            "triglycerides_mg_dl",
            "diabetes_duration_years",
        ]:
            row[k] = int(round(float(row[k])))

        for k in ["bmi_kg_m2", "hba1c_percent", "c_peptide_ng_ml", "creatinine_mg_dl", "egfr_ml_min_1_73m2"]:
            row[k] = round(float(row[k]), 2)

        if row_is_valid(row):
            return row

    raise RuntimeError(f"Failed to generate a valid row for phenotype '{phenotype['id']}' after {max_attempts} attempts")


def load_phenotype(path: str, phenotype_id: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        cfg = json.load(f)

    phenos = cfg.get("phenotypes", [])
    for p in phenos:
        if p.get("id") == phenotype_id:
            return {"config": cfg, "phenotype": p}

    available = ", ".join(p.get("id", "<missing-id>") for p in phenos)
    raise ValueError(f"Unknown phenotype_id '{phenotype_id}'. Available: {available}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate phenotype-driven synthetic EHR patients")
    parser.add_argument("--phenotypes", required=True, help="Path to phenotype JSON")
    parser.add_argument("--phenotype-id", required=True, help="Phenotype id from JSON")
    parser.add_argument("--n", type=int, default=100, help="Number of patients")
    parser.add_argument("--seed", type=int, default=1, help="Random seed")
    parser.add_argument("--out", required=True, help="Output CSV path")
    parser.add_argument("--summary-out", required=False, help="Optional summary JSON path")
    args = parser.parse_args()

    if args.n <= 0:
        raise ValueError("--n must be positive")

    loaded = load_phenotype(args.phenotypes, args.phenotype_id)
    cfg = loaded["config"]
    phenotype = loaded["phenotype"]
    variables = cfg.get("variables_order")
    if not variables:
        raise ValueError("Missing 'variables_order' in phenotype config")

    rng = random.Random(args.seed)
    rows = []
    for i in range(args.n):
        pid = f"{args.phenotype_id}_{i + 1:06d}"
        rows.append(sample_row(phenotype, variables, pid, rng))

    with open(args.out, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=variables)
        writer.writeheader()
        writer.writerows(rows)

    if args.summary_out:
        from collections import Counter
        summary = {
            "seed": args.seed,
            "phenotypes_file": args.phenotypes,
            "phenotype_id": args.phenotype_id,
            "rows": len(rows),
            "diabetes_type_counts": dict(Counter(r["diabetes_type"] for r in rows)),
            "ckd_stage_counts": dict(Counter(r["ckd_stage"] for r in rows)),
        }
        with open(args.summary_out, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2)
            f.write("\n")

    print(f"Wrote {len(rows)} rows to {args.out}")


if __name__ == "__main__":
    main()
