#!/usr/bin/env python3
import argparse
import csv
from collections import Counter

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


def to_float(value, field):
    try:
        return float(value)
    except Exception as exc:
        raise ValueError(f"Non-numeric value in {field}: {value}") from exc


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate generated synthetic EHR rows")
    parser.add_argument("--input", required=True, help="CSV file path")
    args = parser.parse_args()

    rows = []
    with open(args.input, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)

    if not rows:
        raise ValueError("Input file has no rows")

    issues = []
    warnings = []
    dm_counts = Counter()
    ckd_counts = Counter()

    for i, row in enumerate(rows, start=2):
        dm_type = row.get("diabetes_type", "")
        dm_counts[dm_type] += 1
        ckd_counts[row.get("ckd_stage", "")] += 1

        for field, (lo, hi) in BOUNDS.items():
            val = to_float(row.get(field), field)
            if val < lo or val > hi:
                issues.append(f"line {i}: {field} out of bounds ({val}, expected {lo}-{hi})")

        sbp = to_float(row["systolic_bp_mmhg"], "systolic_bp_mmhg")
        dbp = to_float(row["diastolic_bp_mmhg"], "diastolic_bp_mmhg")
        if dbp >= sbp:
            issues.append(f"line {i}: diastolic_bp_mmhg >= systolic_bp_mmhg")

        fasting = to_float(row["fasting_glucose_mg_dl"], "fasting_glucose_mg_dl")
        random_glucose = to_float(row["random_glucose_mg_dl"], "random_glucose_mg_dl")
        if random_glucose < fasting:
            issues.append(f"line {i}: random_glucose_mg_dl < fasting_glucose_mg_dl")
        expected_hba1c = (((0.65 * fasting) + (0.35 * random_glucose)) + 46.7) / 28.7
        hba1c = to_float(row["hba1c_percent"], "hba1c_percent")
        if abs(hba1c - expected_hba1c) > 2.2:
            warnings.append(
                f"line {i}: hba1c_percent ({hba1c:.2f}) far from glucose-implied value ({expected_hba1c:.2f})"
            )

        egfr = to_float(row["egfr_ml_min_1_73m2"], "egfr_ml_min_1_73m2")
        if egfr < 15:
            issues.append(f"line {i}: eGFR < 15 violates non-ESRD scope")
        creatinine = to_float(row["creatinine_mg_dl"], "creatinine_mg_dl")
        expected_creatinine = 0.62 + (110.0 - egfr) / 55.0 + (to_float(row["age_years"], "age_years") - 50.0) / 180.0
        if row.get("sex_at_birth") == "female":
            expected_creatinine -= 0.08
        if abs(creatinine - expected_creatinine) > 0.9:
            warnings.append(
                f"line {i}: creatinine_mg_dl ({creatinine:.2f}) weakly aligned with eGFR ({egfr:.1f})"
            )

        duration = int(float(row["diabetes_duration_years"]))
        if dm_type == "none" and duration != 0:
            issues.append(f"line {i}: diabetes_type=none but diabetes_duration_years != 0")

    print(f"Rows checked: {len(rows)}")
    print(f"Diabetes type counts: {dict(dm_counts)}")
    print(f"CKD stage counts: {dict(ckd_counts)}")
    if warnings:
        print(f"Warnings: {len(warnings)}")
        for w in warnings[:15]:
            print(f"- {w}")
        if len(warnings) > 15:
            print(f"... and {len(warnings) - 15} more warning(s)")
    else:
        print("Warnings: 0")

    if issues:
        print("Validation FAILED")
        for issue in issues[:50]:
            print(f"- {issue}")
        if len(issues) > 50:
            print(f"... and {len(issues) - 50} more")
        raise SystemExit(1)

    print("Validation PASSED")


if __name__ == "__main__":
    main()
