#!/usr/bin/env python3
import argparse
import copy
import json
from typing import Any, Dict


def load_json(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: str, payload: Dict[str, Any]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
        f.write("\n")


def deep_merge(base: Dict[str, Any], patch: Dict[str, Any]) -> Dict[str, Any]:
    out = copy.deepcopy(base)
    for k, v in patch.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def get_pheno(cfg: Dict[str, Any], pheno_id: str) -> Dict[str, Any]:
    for p in cfg.get("phenotypes", []):
        if p.get("id") == pheno_id:
            return p
    raise ValueError(f"Phenotype '{pheno_id}' not found")


def validate_new_phenotype(cfg: Dict[str, Any], pheno: Dict[str, Any]) -> None:
    required = {"id", "name", "anchors"}
    missing = required - set(pheno.keys())
    if missing:
        raise ValueError(f"New phenotype missing required keys: {sorted(missing)}")

    vars_order = cfg.get("variables_order", [])
    if not vars_order:
        raise ValueError("Config missing variables_order")

    missing_anchors = [v for v in vars_order if v != "patient_id" and v not in pheno["anchors"]]
    if missing_anchors:
        raise ValueError(
            "New phenotype has incomplete anchors. Missing: " + ", ".join(missing_anchors)
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Add a new phenotype by cloning and patching an existing one")
    parser.add_argument("--phenotypes", required=True, help="Path to phenotype JSON")
    parser.add_argument("--base-id", required=True, help="Existing phenotype id to clone")
    parser.add_argument("--new-id", required=True, help="New phenotype id")
    parser.add_argument("--new-name", required=True, help="New phenotype name")
    parser.add_argument(
        "--overrides",
        required=False,
        help=(
            "Path to JSON object with partial overrides. "
            "Supports keys like anchors/spread/categorical_probs or top-level fields."
        ),
    )
    parser.add_argument("--out", required=False, help="Output JSON path (default: overwrite input)")
    args = parser.parse_args()

    cfg = load_json(args.phenotypes)
    phenos = cfg.get("phenotypes", [])

    if any(p.get("id") == args.new_id for p in phenos):
        raise ValueError(f"New id '{args.new_id}' already exists")

    base = get_pheno(cfg, args.base_id)
    new_pheno = copy.deepcopy(base)
    new_pheno["id"] = args.new_id
    new_pheno["name"] = args.new_name

    if args.overrides:
        patch = load_json(args.overrides)
        if not isinstance(patch, dict):
            raise ValueError("Overrides file must contain a JSON object")
        new_pheno = deep_merge(new_pheno, patch)

    validate_new_phenotype(cfg, new_pheno)

    cfg["phenotypes"].append(new_pheno)
    out_path = args.out if args.out else args.phenotypes
    write_json(out_path, cfg)

    print(f"Added phenotype '{args.new_id}' to {out_path}")


if __name__ == "__main__":
    main()
