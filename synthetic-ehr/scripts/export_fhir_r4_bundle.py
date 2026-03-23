#!/usr/bin/env python3
import argparse
import csv
import json
import uuid
from datetime import date
from decimal import Decimal
from typing import Dict, List, Tuple


UUID_NAMESPACE = uuid.UUID("2df290f0-07ed-4d43-b6ff-7266e6023076")


def urn_for(patient_id: str, resource_key: str) -> str:
    return f"urn:uuid:{uuid.uuid5(UUID_NAMESPACE, f'{patient_id}:{resource_key}')}"


def to_int(row: Dict[str, str], key: str) -> int:
    return int(float(row[key]))


def to_float(row: Dict[str, str], key: str) -> float:
    return float(row[key])


def to_bool_flag(row: Dict[str, str], key: str) -> bool:
    return to_int(row, key) == 1


def quantity(value: float, unit: str, code: str, system: str = "http://unitsofmeasure.org") -> Dict[str, object]:
    if isinstance(value, float):
        value = float(Decimal(str(value)))
    return {
        "value": value,
        "unit": unit,
        "system": system,
        "code": code,
    }


def mk_entry(full_url: str, resource: Dict[str, object], resource_type: str) -> Dict[str, object]:
    return {
        "fullUrl": full_url,
        "resource": resource,
        "request": {
            "method": "POST",
            "url": resource_type,
        },
    }


def patient_resource(row: Dict[str, str], index: int, effective_date: str) -> Tuple[str, Dict[str, object]]:
    patient_id = row["patient_id"]
    age_years = to_int(row, "age_years")
    gender = "male" if row["sex_at_birth"].strip().lower() == "male" else "female"
    birth_year = max(1920, date.fromisoformat(effective_date).year - age_years)
    month = (index % 12) + 1
    day = (index % 27) + 1

    full_url = urn_for(patient_id, "patient")
    resource = {
        "resourceType": "Patient",
        "identifier": [
            {
                "system": "urn:synthetic-ehr:patient-id",
                "value": patient_id,
            }
        ],
        "active": True,
        "name": [
            {
                "use": "official",
                "family": f"Synthetic{index + 1}",
                "given": ["Patient"],
            }
        ],
        "gender": gender,
        "birthDate": f"{birth_year:04d}-{month:02d}-{day:02d}",
    }
    return full_url, resource


def encounter_resource(patient_ref: str, row: Dict[str, str], effective_date: str) -> Tuple[str, Dict[str, object]]:
    patient_id = row["patient_id"]
    full_url = urn_for(patient_id, "encounter")
    resource = {
        "resourceType": "Encounter",
        "status": "finished",
        "class": {
            "system": "http://terminology.hl7.org/CodeSystem/v3-ActCode",
            "code": "AMB",
            "display": "ambulatory",
        },
        "subject": {"reference": patient_ref},
        "period": {
            "start": f"{effective_date}T09:00:00Z",
            "end": f"{effective_date}T09:45:00Z",
        },
    }
    return full_url, resource


def condition_resources(patient_ref: str, encounter_ref: str, row: Dict[str, str], effective_date: str) -> List[Tuple[str, Dict[str, object]]]:
    out = []
    patient_id = row["patient_id"]

    diabetes_type = row["diabetes_type"]
    if diabetes_type == "type1":
        out.append(
            (
                urn_for(patient_id, "condition-diabetes"),
                {
                    "resourceType": "Condition",
                    "clinicalStatus": {
                        "coding": [
                            {
                                "system": "http://terminology.hl7.org/CodeSystem/condition-clinical",
                                "code": "active",
                            }
                        ]
                    },
                    "verificationStatus": {
                        "coding": [
                            {
                                "system": "http://terminology.hl7.org/CodeSystem/condition-ver-status",
                                "code": "confirmed",
                            }
                        ]
                    },
                    "code": {
                        "coding": [
                            {
                                "system": "http://snomed.info/sct",
                                "code": "46635009",
                                "display": "Type 1 diabetes mellitus",
                            }
                        ]
                    },
                    "subject": {"reference": patient_ref},
                    "encounter": {"reference": encounter_ref},
                    "onsetDateTime": effective_date,
                },
            )
        )
    elif diabetes_type == "type2":
        out.append(
            (
                urn_for(patient_id, "condition-diabetes"),
                {
                    "resourceType": "Condition",
                    "clinicalStatus": {
                        "coding": [
                            {
                                "system": "http://terminology.hl7.org/CodeSystem/condition-clinical",
                                "code": "active",
                            }
                        ]
                    },
                    "verificationStatus": {
                        "coding": [
                            {
                                "system": "http://terminology.hl7.org/CodeSystem/condition-ver-status",
                                "code": "confirmed",
                            }
                        ]
                    },
                    "code": {
                        "coding": [
                            {
                                "system": "http://snomed.info/sct",
                                "code": "44054006",
                                "display": "Type 2 diabetes mellitus",
                            }
                        ]
                    },
                    "subject": {"reference": patient_ref},
                    "encounter": {"reference": encounter_ref},
                    "onsetDateTime": effective_date,
                },
            )
        )

    ckd_stage = row["ckd_stage"]
    out.append(
        (
            urn_for(patient_id, "condition-ckd"),
            {
                "resourceType": "Condition",
                "clinicalStatus": {
                    "coding": [
                        {
                            "system": "http://terminology.hl7.org/CodeSystem/condition-clinical",
                            "code": "active",
                        }
                    ]
                },
                "verificationStatus": {
                    "coding": [
                        {
                            "system": "http://terminology.hl7.org/CodeSystem/condition-ver-status",
                            "code": "confirmed",
                        }
                    ]
                },
                "code": {
                    "coding": [
                        {
                            "system": "http://snomed.info/sct",
                            "code": "709044004",
                            "display": "Chronic kidney disease",
                        }
                    ],
                    "text": f"Chronic kidney disease, stage {ckd_stage}",
                },
                "subject": {"reference": patient_ref},
                "encounter": {"reference": encounter_ref},
                "onsetDateTime": effective_date,
            },
        )
    )

    return out


def observation_resource(
    patient_id: str,
    key: str,
    patient_ref: str,
    encounter_ref: str,
    effective_date: str,
    code: str,
    display: str,
    value_quantity: Dict[str, object],
    category_code: str = "laboratory",
    category_display: str = "Laboratory",
) -> Tuple[str, Dict[str, object]]:
    return (
        urn_for(patient_id, f"obs-{key}"),
        {
            "resourceType": "Observation",
            "status": "final",
            "category": [
                {
                    "coding": [
                        {
                            "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                            "code": category_code,
                            "display": category_display,
                        }
                    ]
                }
            ],
            "code": {
                "coding": [
                    {
                        "system": "http://loinc.org",
                        "code": code,
                        "display": display,
                    }
                ]
            },
            "subject": {"reference": patient_ref},
            "encounter": {"reference": encounter_ref},
            "effectiveDateTime": effective_date,
            "valueQuantity": value_quantity,
        },
    )


def blood_pressure_resource(
    patient_id: str,
    patient_ref: str,
    encounter_ref: str,
    effective_date: str,
    systolic: int,
    diastolic: int,
) -> Tuple[str, Dict[str, object]]:
    return (
        urn_for(patient_id, "obs-blood-pressure"),
        {
            "resourceType": "Observation",
            "status": "final",
            "category": [
                {
                    "coding": [
                        {
                            "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                            "code": "vital-signs",
                            "display": "Vital Signs",
                        }
                    ]
                }
            ],
            "code": {
                "coding": [
                    {
                        "system": "http://loinc.org",
                        "code": "85354-9",
                        "display": "Blood pressure panel with all children optional",
                    }
                ]
            },
            "subject": {"reference": patient_ref},
            "encounter": {"reference": encounter_ref},
            "effectiveDateTime": effective_date,
            "component": [
                {
                    "code": {
                        "coding": [
                            {
                                "system": "http://loinc.org",
                                "code": "8480-6",
                                "display": "Systolic blood pressure",
                            }
                        ]
                    },
                    "valueQuantity": quantity(systolic, "mm[Hg]", "mm[Hg]"),
                },
                {
                    "code": {
                        "coding": [
                            {
                                "system": "http://loinc.org",
                                "code": "8462-4",
                                "display": "Diastolic blood pressure",
                            }
                        ]
                    },
                    "valueQuantity": quantity(diastolic, "mm[Hg]", "mm[Hg]"),
                },
            ],
        },
    )


def medication_request(
    patient_id: str,
    key: str,
    medication_text: str,
    patient_ref: str,
    encounter_ref: str,
    authored_on: str,
) -> Tuple[str, Dict[str, object]]:
    return (
        urn_for(patient_id, f"med-{key}"),
        {
            "resourceType": "MedicationRequest",
            "status": "active",
            "intent": "order",
            "subject": {"reference": patient_ref},
            "encounter": {"reference": encounter_ref},
            "authoredOn": authored_on,
            "medicationCodeableConcept": {"text": medication_text},
        },
    )


def resources_for_row(row: Dict[str, str], index: int, effective_date: str) -> List[Dict[str, object]]:
    entries: List[Dict[str, object]] = []
    patient_id = row["patient_id"]

    patient_full_url, patient = patient_resource(row, index, effective_date)
    encounter_full_url, encounter = encounter_resource(patient_full_url, row, effective_date)
    entries.append(mk_entry(patient_full_url, patient, "Patient"))
    entries.append(mk_entry(encounter_full_url, encounter, "Encounter"))

    for cond_url, cond in condition_resources(patient_full_url, encounter_full_url, row, effective_date):
        entries.append(mk_entry(cond_url, cond, "Condition"))

    bp = blood_pressure_resource(
        patient_id,
        patient_full_url,
        encounter_full_url,
        effective_date,
        to_int(row, "systolic_bp_mmhg"),
        to_int(row, "diastolic_bp_mmhg"),
    )
    entries.append(mk_entry(bp[0], bp[1], "Observation"))

    observations = [
        (
            "bmi",
            "39156-5",
            "Body mass index (BMI) [Ratio]",
            quantity(to_float(row, "bmi_kg_m2"), "kg/m2", "kg/m2"),
            "vital-signs",
            "Vital Signs",
        ),
        (
            "heart-rate",
            "8867-4",
            "Heart rate",
            quantity(to_int(row, "heart_rate_bpm"), "beats/minute", "/min"),
            "vital-signs",
            "Vital Signs",
        ),
        (
            "hba1c",
            "4548-4",
            "Hemoglobin A1c/Hemoglobin.total in Blood",
            quantity(to_float(row, "hba1c_percent"), "%", "%"),
            "laboratory",
            "Laboratory",
        ),
        (
            "fasting-glucose",
            "1558-6",
            "Glucose [Mass/volume] in Serum or Plasma --Fasting",
            quantity(to_int(row, "fasting_glucose_mg_dl"), "mg/dL", "mg/dL"),
            "laboratory",
            "Laboratory",
        ),
        (
            "random-glucose",
            "2339-0",
            "Glucose [Mass/volume] in Blood",
            quantity(to_int(row, "random_glucose_mg_dl"), "mg/dL", "mg/dL"),
            "laboratory",
            "Laboratory",
        ),
        (
            "c-peptide",
            "1986-9",
            "C peptide [Mass/volume] in Serum or Plasma",
            quantity(to_float(row, "c_peptide_ng_ml"), "ng/mL", "ng/mL"),
            "laboratory",
            "Laboratory",
        ),
        (
            "creatinine",
            "2160-0",
            "Creatinine [Mass/volume] in Serum or Plasma",
            quantity(to_float(row, "creatinine_mg_dl"), "mg/dL", "mg/dL"),
            "laboratory",
            "Laboratory",
        ),
        (
            "egfr",
            "33914-3",
            "Glomerular filtration rate/1.73 sq M.predicted",
            quantity(to_float(row, "egfr_ml_min_1_73m2"), "mL/min/{1.73_m2}", "mL/min/{1.73_m2}"),
            "laboratory",
            "Laboratory",
        ),
        (
            "bun",
            "3094-0",
            "Urea nitrogen [Mass/volume] in Serum or Plasma",
            quantity(to_int(row, "bun_mg_dl"), "mg/dL", "mg/dL"),
            "laboratory",
            "Laboratory",
        ),
        (
            "uacr",
            "14959-1",
            "Albumin/Creatinine [Mass Ratio] in Urine",
            quantity(to_int(row, "uacr_mg_g"), "mg/g", "mg/g"),
            "laboratory",
            "Laboratory",
        ),
        (
            "ldl",
            "13457-7",
            "Cholesterol in LDL [Mass/volume] in Serum or Plasma by calculation",
            quantity(to_int(row, "ldl_mg_dl"), "mg/dL", "mg/dL"),
            "laboratory",
            "Laboratory",
        ),
        (
            "hdl",
            "2085-9",
            "Cholesterol in HDL [Mass/volume] in Serum or Plasma",
            quantity(to_int(row, "hdl_mg_dl"), "mg/dL", "mg/dL"),
            "laboratory",
            "Laboratory",
        ),
        (
            "triglycerides",
            "2571-8",
            "Triglyceride [Mass/volume] in Serum or Plasma",
            quantity(to_int(row, "triglycerides_mg_dl"), "mg/dL", "mg/dL"),
            "laboratory",
            "Laboratory",
        ),
    ]

    for obs_key, code, display, value_quantity, category_code, category_display in observations:
        obs_url, obs = observation_resource(
            patient_id,
            obs_key,
            patient_full_url,
            encounter_full_url,
            effective_date,
            code,
            display,
            value_quantity,
            category_code,
            category_display,
        )
        entries.append(mk_entry(obs_url, obs, "Observation"))

    med_requests = []
    if row["insulin_use"] != "none":
        med_requests.append(
            (
                "insulin",
                f"Insulin therapy ({row['insulin_use'].replace('_', ' ')})",
            )
        )
    if to_bool_flag(row, "metformin_use"):
        med_requests.append(("metformin", "Metformin"))
    if to_bool_flag(row, "sglt2_inhibitor_use"):
        med_requests.append(("sglt2", "SGLT2 inhibitor"))
    if to_bool_flag(row, "glp1_ra_use"):
        med_requests.append(("glp1ra", "GLP-1 receptor agonist"))

    for key, medication_text in med_requests:
        med_url, med = medication_request(
            patient_id,
            key,
            medication_text,
            patient_full_url,
            encounter_full_url,
            effective_date,
        )
        entries.append(mk_entry(med_url, med, "MedicationRequest"))

    return entries


def load_rows(input_csv: str) -> List[Dict[str, str]]:
    with open(input_csv, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return list(reader)


def main() -> None:
    parser = argparse.ArgumentParser(description="Export synthetic cohort CSV to a FHIR R4 transaction Bundle")
    parser.add_argument("--input-csv", required=True, help="Path to synthetic cohort CSV")
    parser.add_argument("--output-json", required=True, help="Path to write FHIR Bundle JSON")
    parser.add_argument(
        "--effective-date",
        default="2026-02-01",
        help="Clinical date to stamp observations/encounters (YYYY-MM-DD)",
    )
    args = parser.parse_args()

    _ = date.fromisoformat(args.effective_date)
    rows = load_rows(args.input_csv)
    entries: List[Dict[str, object]] = []

    for idx, row in enumerate(rows):
        entries.extend(resources_for_row(row, idx, args.effective_date))

    bundle = {
        "resourceType": "Bundle",
        "type": "transaction",
        "entry": entries,
    }

    with open(args.output_json, "w", encoding="utf-8") as f:
        json.dump(bundle, f, indent=2)
        f.write("\n")

    print(f"Wrote {len(entries)} transaction entries for {len(rows)} patients to {args.output_json}")


if __name__ == "__main__":
    main()
