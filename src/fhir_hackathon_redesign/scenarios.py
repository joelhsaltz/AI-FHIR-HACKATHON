"""Scenario configuration and state helpers for the notebook-first teaching app."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .fhir import FHIRClient, LOINC, SNOMED


FOLLOW_UP_AGENT_INSTRUCTIONS = """You are helping review patients for diabetes-focused follow-up.

This is an informatics workflow exercise, not a medicine exam.
- gather enough structured evidence before recommending follow-up
- treat diabetes diagnosis, glycemic control, medication complexity, and kidney disease as the core signals
- note that the current synthetic cohort mostly exposes recent ambulatory encounters rather than reliable inpatient admission metadata
- be explicit about uncertainty when the evidence is thin
- in the final answer, cite the concrete evidence you used
"""


TYPE_CLARIFICATION_AGENT_INSTRUCTIONS = """You are helping review a younger patient with diabetes.

This is an evidence-gathering exercise.
- prefer direct evidence over heuristics
- use C-peptide when available
- use medication pattern, BMI, age, and diagnosis history as supporting context
- if evidence is missing or conflicting, say the case is unclear rather than forcing a binary answer
- cite concrete evidence from the tool results in your final answer
"""


FHIR_QUERY_MAPPINGS = [
    {
        "interaction_option": "Find patients by diagnosis",
        "notebook3_tool": "search_conditions",
        "fhir_query": "GET /Condition?code={snomed_code}&_count={max_results}&_format=json",
        "teaching_use": "Build the candidate pool from a diagnosis such as Type 1 or Type 2 diabetes.",
    },
    {
        "interaction_option": "Get demographics",
        "notebook3_tool": "get_patient",
        "fhir_query": "GET /Patient/{patient_id}?_format=json",
        "teaching_use": "Retrieve one patient's name, age, sex, and other basic context.",
    },
    {
        "interaction_option": "Get full problem list",
        "notebook3_tool": "search_all_conditions",
        "fhir_query": "GET /Condition?subject=Patient/{patient_id}&_count={max_results}&_format=json",
        "teaching_use": "Inspect the full diagnosis context for one already selected patient.",
    },
    {
        "interaction_option": "Get labs",
        "notebook3_tool": "search_observations",
        "fhir_query": "GET /Observation?subject=Patient/{patient_id}&code={loinc_code}&_count={max_results}&_sort=-date&_format=json",
        "teaching_use": "Review the most recent HbA1c, C-peptide, BMI, creatinine, or eGFR evidence.",
    },
    {
        "interaction_option": "Get medications",
        "notebook3_tool": "search_medications",
        "fhir_query": "GET /MedicationRequest?subject=Patient/{patient_id}&_count={max_results}&_format=json",
        "teaching_use": "Inspect active diabetes medications and complexity of treatment.",
    },
    {
        "interaction_option": "Get encounters",
        "notebook3_tool": "search_encounters",
        "fhir_query": "GET /Encounter?subject=Patient/{patient_id}&_count={max_results}&_sort=-date&_format=json",
        "teaching_use": "Review encounter metadata and note current cohort limitations around inpatient context.",
    },
]


SCENARIO1_MENU = [
    "Find patients by diagnosis",
    "Review one candidate patient",
    "Get demographics",
    "Get full problem list",
    "Get labs",
    "Get medications",
    "Get encounters",
    "Add patient to follow-up list",
    "Mark patient as not priority",
    "Mark patient as uncertain",
    "Ask the LLM what to do next",
    "Finish and answer",
]


SCENARIO2_MENU = [
    "Get demographics",
    "Get full problem list",
    "Get labs",
    "Get medications",
    "Get encounters",
    "Ask the LLM what to do next",
    "Finish and answer",
]


SCENARIO1_PROMPT_VARIANTS = [
    (
        "Base request",
        "Review patients with diabetes who have recent encounters and identify which patients should be prioritized for endocrine follow-up based on evidence of poor control or diabetes-related complexity.",
    ),
    (
        "Poor-control emphasis",
        "Prioritize diabetic patients whose recent data suggests poor glycemic control, even if complication burden is not yet clear.",
    ),
    (
        "Complexity emphasis",
        "Prioritize diabetic patients whose overall diabetes-related complexity suggests they may benefit from endocrine review, especially if kidney disease or intensive treatment is present.",
    ),
    (
        "Conservative flagging",
        "Only prioritize diabetic patients when the evidence for poor control or diabetes-related complexity is strong enough that endocrine review would likely change management.",
    ),
]


@dataclass(frozen=True)
class ScenarioConfig:
    id: str
    title: str
    framing_text: str
    base_prompt: str
    verdict_labels: list[str]
    evidence_checklist: list[str]
    menu: list[str]
    teaching_notes: list[str] = field(default_factory=list)
    prompt_variants: list[tuple[str, str]] = field(default_factory=list)


@dataclass
class SessionState:
    scenario_id: str
    question: str
    mode: str = "human"
    candidate_pool: list[dict[str, Any]] = field(default_factory=list)
    current_patient_id: str | None = None
    evidence: dict[str, dict[str, Any]] = field(default_factory=dict)
    history: list[dict[str, Any]] = field(default_factory=list)
    missing_evidence: dict[str, list[str]] = field(default_factory=dict)
    follow_up_list: list[dict[str, Any]] = field(default_factory=list)
    patient_decisions: dict[str, dict[str, str]] = field(default_factory=dict)
    final_answer: str | None = None


def build_scenario_configs() -> dict[str, ScenarioConfig]:
    return {
        "scenario1_follow_up": ScenarioConfig(
            id="scenario1_follow_up",
            title="Scenario 1: Endocrine Follow-Up List Construction",
            framing_text=(
                "Students are not being asked to learn medicine here. "
                "They are learning how an agent turns FHIR queries into a candidate list and then into a follow-up workflow recommendation. "
                "Because the current synthetic cohort mostly exposes recent ambulatory encounters, the first implementation uses recent-encounter review rather than claiming reliable inpatient admission metadata."
            ),
            base_prompt=SCENARIO1_PROMPT_VARIANTS[0][1],
            verdict_labels=["Flag", "Do not flag", "Uncertain / needs more review"],
            evidence_checklist=[
                "diabetes diagnosis in the candidate-building step",
                "recent encounter context",
                "HbA1c or other glycemic control evidence",
                "medication complexity",
                "CKD or other diabetes-related complexity",
            ],
            menu=SCENARIO1_MENU,
            teaching_notes=[
                "The first query builds the candidate pool.",
                "The second Condition query reviews one patient's full problem list.",
                "Students should compare how wording changes what evidence feels most important.",
            ],
            prompt_variants=SCENARIO1_PROMPT_VARIANTS,
        ),
        "scenario2_type_clarification": ScenarioConfig(
            id="scenario2_type_clarification",
            title="Scenario 2: Type 1 vs Type 2 Clarification",
            framing_text=(
                "Students review a younger patient cohort where labels may be incomplete or misleading. "
                "The goal is to gather enough evidence to support Type 1, Type 2, or unclear."
            ),
            base_prompt=(
                "Review this younger patient with diabetes and decide whether the case is more consistent with Type 1 diabetes, Type 2 diabetes, or remains unclear based on the available evidence."
            ),
            verdict_labels=["Likely Type 1", "Likely Type 2", "Unclear / needs more review"],
            evidence_checklist=[
                "C-peptide",
                "medication pattern",
                "problem list / diagnosis context",
                "BMI or insulin-resistance context",
            ],
            menu=SCENARIO2_MENU,
            teaching_notes=[
                "Age is supporting context, not the decision by itself.",
                "Unclear is an acceptable answer.",
            ],
        ),
    }


def normalize_patient_reference(reference: str) -> str:
    if not reference:
        return ""
    if "Patient/" in reference:
        return reference.split("Patient/")[-1]
    if reference.startswith("urn:uuid:"):
        return ""
    return reference.split("/")[-1]


def _safe_call(default: Any, fn, *args, **kwargs) -> Any:
    try:
        return fn(*args, **kwargs)
    except Exception:
        return default


def build_follow_up_candidate_pool(
    fhir: FHIRClient,
    *,
    max_results_per_code: int = 40,
    max_candidates: int = 12,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for cohort_label, code in [("Type 2 diabetes", SNOMED["t2d"]), ("Type 1 diabetes", SNOMED["t1d"])]:
        for item in fhir.search_conditions(code, max_results=max_results_per_code)["results"]:
            patient_id = normalize_patient_reference(item.get("patient_reference", ""))
            if not patient_id or patient_id in seen:
                continue
            patient = _safe_call({}, fhir.get_patient, patient_id)
            if not patient:
                continue
            encounters = _safe_call({"results": []}, fhir.search_encounters, patient_id, max_results=1)["results"]
            hba1c_bundle = _safe_call(
                {"results": []},
                fhir.search_observations,
                patient_id,
                LOINC["hba1c"],
                max_results=1,
            )
            meds = _safe_call({"results": []}, fhir.search_medications, patient_id, max_results=10)["results"]
            conditions = _safe_call(
                {"results": []},
                fhir.search_all_conditions,
                patient_id,
                max_results=12,
            )["results"]
            last_hba1c = hba1c_bundle["results"][0]["value"] if hba1c_bundle["results"] else None
            has_ckd = any(row.get("code") == SNOMED["ckd"] for row in conditions)
            insulin_use = any("insulin" in row.get("medication", "").lower() for row in meds)
            encounter = encounters[0] if encounters else {}
            score = 0
            if last_hba1c is not None:
                score += 3 if last_hba1c >= 9 else 2 if last_hba1c >= 7.5 else 0
            if has_ckd:
                score += 1
            if insulin_use:
                score += 1
            if encounter:
                score += 1
            rows.append(
                {
                    "patient_id": patient_id,
                    "seed_group": cohort_label,
                    "name": patient.get("name", ""),
                    "age": patient.get("age"),
                    "gender": patient.get("gender", ""),
                    "encounter_class": encounter.get("class", ""),
                    "encounter_status": encounter.get("status", ""),
                    "encounter_start": encounter.get("period_start", ""),
                    "latest_hba1c": last_hba1c,
                    "insulin_use": insulin_use,
                    "has_ckd": has_ckd,
                    "priority_score": score,
                }
            )
            seen.add(patient_id)
    rows.sort(
        key=lambda row: (
            row.get("priority_score", 0),
            row.get("latest_hba1c") if row.get("latest_hba1c") is not None else -1,
            row.get("encounter_start", ""),
        ),
        reverse=True,
    )
    for index, row in enumerate(rows[:max_candidates], start=1):
        row["candidate_number"] = index
    return rows[:max_candidates]


def build_young_diabetes_candidate_table(
    fhir: FHIRClient,
    *,
    max_age: int = 35,
    per_group: int = 3,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for cohort_label, code in [("Likely Type 1 seed", SNOMED["t1d"]), ("Likely Type 2 seed", SNOMED["t2d"])]:
        for item in fhir.search_conditions(code, max_results=100)["results"]:
            patient_id = normalize_patient_reference(item.get("patient_reference", ""))
            if not patient_id or patient_id in seen:
                continue
            patient = _safe_call({}, fhir.get_patient, patient_id)
            if not patient:
                continue
            age = patient.get("age")
            if age is None or age > max_age:
                continue
            rows.append(
                {
                    "patient_id": patient_id,
                    "seed_group": cohort_label,
                    "name": patient.get("name", ""),
                    "age": age,
                    "gender": patient.get("gender", ""),
                    "birthDate": patient.get("birthDate", ""),
                }
            )
            seen.add(patient_id)
    rows.sort(key=lambda row: (row["seed_group"], row["age"], row["name"]))
    selected: list[dict[str, Any]] = []
    counts: dict[str, int] = {}
    for row in rows:
        group = row["seed_group"]
        counts.setdefault(group, 0)
        if counts[group] >= per_group:
            continue
        counts[group] += 1
        selected.append(row)
    for index, row in enumerate(selected, start=1):
        row["case_number"] = index
    return selected


def initialize_follow_up_state(
    *,
    candidate_pool: list[dict[str, Any]],
    prompt: str | None = None,
    mode: str = "human",
) -> SessionState:
    return SessionState(
        scenario_id="scenario1_follow_up",
        question=prompt or SCENARIO1_PROMPT_VARIANTS[0][1],
        mode=mode,
        candidate_pool=candidate_pool,
        missing_evidence={row["patient_id"]: follow_up_missing_evidence({}) for row in candidate_pool},
    )


def initialize_type_clarification_state(
    patient_row: dict[str, Any],
    *,
    mode: str = "human",
) -> SessionState:
    patient_id = patient_row["patient_id"]
    state = SessionState(
        scenario_id="scenario2_type_clarification",
        question=(
            "Is this younger patient more consistent with Type 1 diabetes, Type 2 diabetes, or still unclear?"
        ),
        mode=mode,
        candidate_pool=[patient_row],
        current_patient_id=patient_id,
        missing_evidence={patient_id: type_clarification_missing_evidence({})},
    )
    return state


def record_step(state: SessionState, tool_name: str, note: str, payload: Any | None = None) -> None:
    state.history.append(
        {
            "step": len(state.history) + 1,
            "tool": tool_name,
            "note": note,
            "payload": payload,
            "patient_id": state.current_patient_id,
        }
    )


def add_evidence(state: SessionState, patient_id: str, evidence_key: str, payload: Any) -> None:
    patient_evidence = state.evidence.setdefault(patient_id, {})
    patient_evidence[evidence_key] = payload
    if state.scenario_id == "scenario1_follow_up":
        state.missing_evidence[patient_id] = follow_up_missing_evidence(patient_evidence)
    else:
        state.missing_evidence[patient_id] = type_clarification_missing_evidence(patient_evidence)


def set_patient_decision(state: SessionState, patient_id: str, label: str, rationale: str) -> None:
    state.patient_decisions[patient_id] = {"label": label, "rationale": rationale}
    state.follow_up_list = [
        item for item in state.follow_up_list if item.get("patient_id") != patient_id
    ]
    if label == "Flag":
        state.follow_up_list.append(
            {
                "patient_id": patient_id,
                "label": label,
                "rationale": rationale,
            }
        )


def follow_up_missing_evidence(evidence: dict[str, Any]) -> list[str]:
    gaps: list[str] = []
    if "demographics" not in evidence:
        gaps.append("basic demographics")
    if "conditions" not in evidence:
        gaps.append("full problem list")
    if "hba1c" not in evidence:
        gaps.append("HbA1c")
    if "medications" not in evidence:
        gaps.append("medication pattern")
    if "encounters" not in evidence:
        gaps.append("encounter context")
    return gaps


def type_clarification_missing_evidence(evidence: dict[str, Any]) -> list[str]:
    gaps: list[str] = []
    if "demographics" not in evidence:
        gaps.append("basic demographics")
    if "conditions" not in evidence:
        gaps.append("problem list / diagnosis context")
    if "c_peptide" not in evidence:
        gaps.append("C-peptide")
    if "medications" not in evidence:
        gaps.append("medication pattern")
    if "bmi" not in evidence:
        gaps.append("BMI / insulin-resistance pattern")
    return gaps


def build_follow_up_coach_state(state: SessionState, patient_id: str) -> dict[str, Any]:
    patient = next((row for row in state.candidate_pool if row["patient_id"] == patient_id), None)
    return {
        "question": state.question,
        "patient": patient,
        "evidence_collected": list(state.evidence.get(patient_id, {}).keys()),
        "missing_evidence": state.missing_evidence.get(patient_id, []),
        "follow_up_list_so_far": state.follow_up_list,
    }


def build_type_clarification_coach_state(state: SessionState) -> dict[str, Any]:
    patient_id = state.current_patient_id or ""
    patient = next((row for row in state.candidate_pool if row["patient_id"] == patient_id), None)
    return {
        "question": state.question,
        "patient": patient,
        "evidence_collected": list(state.evidence.get(patient_id, {}).keys()),
        "missing_evidence": state.missing_evidence.get(patient_id, []),
    }


def build_follow_up_question(patient_row: dict[str, Any], prompt: str) -> str:
    return (
        f"{prompt}\n\n"
        f"Review patient {patient_row['patient_id']} ({patient_row['name']}, age {patient_row['age']}). "
        "Use the available tools to gather evidence. "
        "Your final answer must be one of: Flag, Do not flag, or Uncertain / needs more review. "
        "Cite the evidence behind the recommendation."
    )


def build_type_clarification_question(patient_row: dict[str, Any]) -> str:
    return (
        f"Review patient {patient_row['patient_id']} ({patient_row['name']}, age {patient_row['age']}). "
        "Decide whether the case is more consistent with Type 1 diabetes, Type 2 diabetes, or still unclear. "
        "Use the available tools to gather supporting evidence and cite concrete findings in the final answer."
    )
