"""Population-scale ranking helpers for the separate capstone notebook."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
import json
import re
from typing import Any

from .fhir import FHIRClient, LOINC, SNOMED
from .claude_agent import ClaudeClient
from .scenarios import normalize_patient_reference


CAPSTONE_CLASSIFIER_PROMPT = """You are formalizing a clinical informatics prioritization request over synthetic FHIR patient data.

Allowed factor ids:
- has_diabetes
- type1_diabetes
- type2_diabetes
- has_recent_encounter
- hba1c_ge_7_5
- hba1c_ge_9
- insulin_use
- ckd
- age_under_40
- age_over_65
- multiple_diabetes_meds

Return strict JSON with this schema:
{
  "request_type": "rule-translatable" | "judgment-heavy",
  "classification_rationale": "short explanation",
  "display_logic": "human-readable rule or qualitative rubric",
  "scoring_factors": [
    {"factor_id": "allowed_factor", "weight": 1-10, "reason": "why it matters"}
  ]
}

Rules:
- Use only the allowed factor ids.
- If the request contains explicit thresholds, Boolean structure, or very crisp inclusion logic, prefer "rule-translatable".
- If it depends on broad judgment such as likely benefit, likely change in management, or overall complexity, prefer "judgment-heavy".
- Keep scoring_factors short and focused.
"""


CAPSTONE_REVISION_PROMPT = """Update the prioritization logic using the student's plain-language revision.

Return strict JSON using the same schema as before. Keep the logic internally consistent and keep to the allowed factor ids only.
"""


FACTOR_DESCRIPTIONS = {
    "has_diabetes": "Patient has Type 1 or Type 2 diabetes in the condition list.",
    "type1_diabetes": "Patient has a Type 1 diabetes condition.",
    "type2_diabetes": "Patient has a Type 2 diabetes condition.",
    "has_recent_encounter": "Patient has at least one recent encounter in the server data.",
    "hba1c_ge_7_5": "Most recent HbA1c is at least 7.5%.",
    "hba1c_ge_9": "Most recent HbA1c is at least 9.0%.",
    "insulin_use": "Active medication list includes insulin.",
    "ckd": "Problem list includes chronic kidney disease.",
    "age_under_40": "Patient age is under 40 years.",
    "age_over_65": "Patient age is over 65 years.",
    "multiple_diabetes_meds": "Medication list contains more than one diabetes medication.",
}


@dataclass
class RankingRunState:
    request_text: str
    request_type: str
    classification_rationale: str
    proposed_formalization: dict[str, Any]
    locked_run_logic: dict[str, Any] | None = None
    patient_scores: list[dict[str, Any]] = field(default_factory=list)


def _extract_json_object(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    fence_match = re.search(r"```(?:json)?\s*(\{.*\})\s*```", cleaned, re.DOTALL)
    if fence_match:
        cleaned = fence_match.group(1)
    return json.loads(cleaned)


def _fallback_formalization(request_text: str) -> dict[str, Any]:
    lowered = request_text.lower()
    if any(token in lowered for token in ["if", "only", "threshold", "above", ">=", "at least", "hba1c"]):
        request_type = "rule-translatable"
        display_logic = (
            "Prioritize patients with diabetes plus recent encounters, and add weight for HbA1c >= 7.5, insulin use, and CKD."
        )
    else:
        request_type = "judgment-heavy"
        display_logic = (
            "Prioritize patients whose overall diabetes-related complexity suggests higher need for endocrine review."
        )
    return {
        "request_type": request_type,
        "classification_rationale": "Fallback formalization used because the model response could not be parsed as JSON.",
        "display_logic": display_logic,
        "scoring_factors": [
            {"factor_id": "has_diabetes", "weight": 4, "reason": "endocrine follow-up only makes sense when diabetes is present"},
            {"factor_id": "has_recent_encounter", "weight": 2, "reason": "focus on patients with recent contact in the data"},
            {"factor_id": "hba1c_ge_7_5", "weight": 3, "reason": "poor glycemic control"},
            {"factor_id": "insulin_use", "weight": 2, "reason": "treatment complexity"},
            {"factor_id": "ckd", "weight": 2, "reason": "diabetes-related complexity"},
        ],
    }


def classify_prioritization_request(
    client: ClaudeClient,
    request_text: str,
) -> dict[str, Any]:
    response_text = client.create_text_response(
        prompt=f"Student request:\n{request_text}",
        system=CAPSTONE_CLASSIFIER_PROMPT,
        max_tokens=700,
    )
    try:
        parsed = _extract_json_object(response_text)
    except Exception:
        parsed = _fallback_formalization(request_text)
    parsed["request_text"] = request_text
    return parsed


def revise_prioritization_logic(
    client: ClaudeClient,
    request_text: str,
    current_logic: dict[str, Any],
    revision_text: str,
) -> dict[str, Any]:
    prompt = (
        f"Original request:\n{request_text}\n\n"
        f"Current logic:\n{json.dumps(current_logic, indent=2)}\n\n"
        f"Student revision:\n{revision_text}"
    )
    response_text = client.create_text_response(
        prompt=prompt,
        system=CAPSTONE_REVISION_PROMPT,
        max_tokens=700,
    )
    try:
        parsed = _extract_json_object(response_text)
    except Exception:
        parsed = current_logic
    parsed["request_text"] = request_text
    parsed["revision_text"] = revision_text
    return parsed


def collect_population_snapshot(
    fhir: FHIRClient,
    *,
    max_population: int = 1200,
    max_results_per_condition: int = 1200,
    max_workers: int = 12,
) -> list[dict[str, Any]]:
    patients = fhir.search_patients(max_results=max_population)["results"]
    t1d_ids = {
        normalize_patient_reference(row["patient_reference"])
        for row in fhir.search_conditions(SNOMED["t1d"], max_results=max_results_per_condition)["results"]
    }
    t2d_ids = {
        normalize_patient_reference(row["patient_reference"])
        for row in fhir.search_conditions(SNOMED["t2d"], max_results=max_results_per_condition)["results"]
    }
    ckd_ids = {
        normalize_patient_reference(row["patient_reference"])
        for row in fhir.search_conditions(SNOMED["ckd"], max_results=max_results_per_condition)["results"]
    }
    diabetes_ids = t1d_ids | t2d_ids

    diabetes_patients = [row for row in patients if row["id"] in diabetes_ids]

    def fetch_one(patient_row: dict[str, Any]) -> dict[str, Any]:
        patient_id = patient_row["id"]
        encounters = fhir.search_encounters(patient_id, max_results=1)["results"]
        meds = fhir.search_medications(patient_id, max_results=10)["results"]
        hba1c = fhir.search_observations(patient_id, LOINC["hba1c"], max_results=1)["results"]
        encounter = encounters[0] if encounters else {}
        latest_hba1c = hba1c[0]["value"] if hba1c else None
        diabetes_med_names = [
            row.get("medication", "")
            for row in meds
            if any(token in row.get("medication", "").lower() for token in ["insulin", "metformin", "glip", "semaglut", "liraglut", "empaglif", "dapaglif"])
        ]
        return {
            "patient_id": patient_id,
            "name": patient_row.get("name", ""),
            "age": patient_row.get("age"),
            "gender": patient_row.get("gender", ""),
            "has_diabetes": patient_id in diabetes_ids,
            "type1_diabetes": patient_id in t1d_ids,
            "type2_diabetes": patient_id in t2d_ids,
            "ckd": patient_id in ckd_ids,
            "has_recent_encounter": bool(encounter),
            "encounter_class": encounter.get("class", ""),
            "encounter_status": encounter.get("status", ""),
            "encounter_start": encounter.get("period_start", ""),
            "latest_hba1c": latest_hba1c,
            "insulin_use": any("insulin" in name.lower() for name in diabetes_med_names),
            "multiple_diabetes_meds": len(set(diabetes_med_names)) > 1,
            "medications": diabetes_med_names[:5],
        }

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        enriched = list(pool.map(fetch_one, diabetes_patients))

    non_diabetes_rows = [
        {
            "patient_id": row["id"],
            "name": row.get("name", ""),
            "age": row.get("age"),
            "gender": row.get("gender", ""),
            "has_diabetes": False,
            "type1_diabetes": False,
            "type2_diabetes": False,
            "ckd": row["id"] in ckd_ids,
            "has_recent_encounter": False,
            "encounter_class": "",
            "encounter_status": "",
            "encounter_start": "",
            "latest_hba1c": None,
            "insulin_use": False,
            "multiple_diabetes_meds": False,
            "medications": [],
        }
        for row in patients
        if row["id"] not in diabetes_ids
    ]
    return enriched + non_diabetes_rows


def evaluate_factor(patient: dict[str, Any], factor_id: str) -> bool:
    if factor_id == "has_diabetes":
        return bool(patient.get("has_diabetes"))
    if factor_id == "type1_diabetes":
        return bool(patient.get("type1_diabetes"))
    if factor_id == "type2_diabetes":
        return bool(patient.get("type2_diabetes"))
    if factor_id == "has_recent_encounter":
        return bool(patient.get("has_recent_encounter"))
    if factor_id == "hba1c_ge_7_5":
        return patient.get("latest_hba1c") is not None and patient["latest_hba1c"] >= 7.5
    if factor_id == "hba1c_ge_9":
        return patient.get("latest_hba1c") is not None and patient["latest_hba1c"] >= 9.0
    if factor_id == "insulin_use":
        return bool(patient.get("insulin_use"))
    if factor_id == "ckd":
        return bool(patient.get("ckd"))
    if factor_id == "age_under_40":
        return patient.get("age") is not None and patient["age"] < 40
    if factor_id == "age_over_65":
        return patient.get("age") is not None and patient["age"] > 65
    if factor_id == "multiple_diabetes_meds":
        return bool(patient.get("multiple_diabetes_meds"))
    return False


def score_population(
    population: list[dict[str, Any]],
    logic: dict[str, Any],
    *,
    top_n: int = 25,
) -> list[dict[str, Any]]:
    ranked: list[dict[str, Any]] = []
    scoring_factors = logic.get("scoring_factors", [])
    for patient in population:
        contributions: list[dict[str, Any]] = []
        total_score = 0
        for factor in scoring_factors:
            factor_id = factor.get("factor_id")
            weight = int(factor.get("weight", 0))
            if not factor_id or factor_id not in FACTOR_DESCRIPTIONS:
                continue
            if evaluate_factor(patient, factor_id):
                total_score += weight
                contributions.append(
                    {
                        "factor_id": factor_id,
                        "weight": weight,
                        "reason": factor.get("reason", FACTOR_DESCRIPTIONS[factor_id]),
                    }
                )
        if total_score <= 0:
            continue
        summary_bits = [f"{item['factor_id']} (+{item['weight']})" for item in contributions[:4]]
        ranked.append(
            {
                **patient,
                "score": total_score,
                "contributions": contributions,
                "summary_reason": ", ".join(summary_bits) if summary_bits else "No strong positive signals",
            }
        )
    ranked.sort(
        key=lambda row: (
            row["score"],
            row.get("latest_hba1c") if row.get("latest_hba1c") is not None else -1,
            row.get("encounter_start", ""),
        ),
        reverse=True,
    )
    return ranked[:top_n]


def build_score_details_rows(ranked_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    details: list[dict[str, Any]] = []
    for row in ranked_rows:
        if not row.get("contributions"):
            details.append(
                {
                    "patient_id": row["patient_id"],
                    "name": row["name"],
                    "score": row["score"],
                    "factor_id": "",
                    "weight": "",
                    "reason": "",
                }
            )
            continue
        for contribution in row["contributions"]:
            details.append(
                {
                    "patient_id": row["patient_id"],
                    "name": row["name"],
                    "score": row["score"],
                    "factor_id": contribution["factor_id"],
                    "weight": contribution["weight"],
                    "reason": contribution["reason"],
                }
            )
    return details
