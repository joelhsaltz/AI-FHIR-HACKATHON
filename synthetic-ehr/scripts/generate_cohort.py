#!/usr/bin/env python3
import argparse
import csv
import json
import random
from collections import Counter
from typing import Any, Dict, List

import generate_patients as gp


def load_json(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_phenotype_by_id(cfg: Dict[str, Any], phenotype_id: str) -> Dict[str, Any]:
    for p in cfg.get("phenotypes", []):
        if p.get("id") == phenotype_id:
            return p
    raise ValueError(f"Unknown phenotype_id '{phenotype_id}'")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a mixed cohort across multiple phenotypes")
    parser.add_argument("--phenotypes", required=True, help="Path to phenotype JSON")
    parser.add_argument("--plan", required=True, help="Path to cohort plan JSON")
    parser.add_argument("--seed", type=int, default=1, help="Random seed")
    parser.add_argument("--out", required=True, help="Output CSV path")
    parser.add_argument("--summary-out", required=False, help="Optional summary JSON path")
    args = parser.parse_args()

    cfg = load_json(args.phenotypes)
    plan = load_json(args.plan)
    variables = cfg.get("variables_order")
    if not variables:
        raise ValueError("Missing variables_order in phenotype config")

    jobs = plan.get("jobs")
    if not isinstance(jobs, list) or not jobs:
        raise ValueError("Plan must include non-empty jobs array")

    rows: List[Dict[str, Any]] = []
    rng = random.Random(args.seed)
    per_pheno_counter = Counter()
    offset = 0

    for job in jobs:
        phenotype_id = job.get("phenotype_id")
        n = int(job.get("n", 0))
        if not phenotype_id:
            raise ValueError("Each job must include phenotype_id")
        if n <= 0:
            raise ValueError(f"Job for '{phenotype_id}' has invalid n={n}")

        phenotype = get_phenotype_by_id(cfg, phenotype_id)
        for i in range(n):
            pid = f"{phenotype_id}_{offset + i + 1:06d}"
            row = gp.sample_row(phenotype, variables, pid, rng)
            row["patient_id"] = pid
            rows.append(row)
        offset += n
        per_pheno_counter[phenotype_id] += n

    with open(args.out, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=variables)
        writer.writeheader()
        writer.writerows(rows)

    ckd_counts = Counter(row["ckd_stage"] for row in rows)
    dm_counts = Counter(row["diabetes_type"] for row in rows)

    summary = {
        "seed": args.seed,
        "phenotypes_file": args.phenotypes,
        "plan_file": args.plan,
        "rows": len(rows),
        "per_phenotype": dict(per_pheno_counter),
        "diabetes_type_counts": dict(dm_counts),
        "ckd_stage_counts": dict(ckd_counts),
    }

    if args.summary_out:
        with open(args.summary_out, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2)
            f.write("\n")

    print(f"Wrote {len(rows)} rows to {args.out}")
    print(f"Per phenotype counts: {dict(per_pheno_counter)}")
    print(f"Diabetes type counts: {dict(dm_counts)}")
    print(f"CKD stage counts: {dict(ckd_counts)}")


if __name__ == "__main__":
    main()
