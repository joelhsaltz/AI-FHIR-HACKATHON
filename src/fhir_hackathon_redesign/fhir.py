"""FHIR client and tool definitions for the redesign workspace."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Callable

import requests
import urllib3


urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


SNOMED = {
    "t1d": "46635009",
    "t2d": "44054006",
    "ckd": "709044004",
}

LOINC = {
    "hba1c": "4548-4",
    "c_peptide": "1986-9",
    "bmi": "39156-5",
    "creatinine": "2160-0",
    "egfr": "33914-3",
    "uacr": "14959-1",
}


def compute_age(birth_date: str) -> int | None:
    if not birth_date:
        return None
    born = datetime.strptime(birth_date, "%Y-%m-%d").date()
    today = date.today()
    return today.year - born.year - ((today.month, today.day) < (born.month, born.day))


class FHIRClient:
    """Small FHIR wrapper exposing the tool surface we want the model to use."""

    def __init__(
        self,
        base_url: str,
        username: str,
        password: str,
        *,
        verify_ssl: bool = False,
        timeout: int = 30,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()
        self.session.auth = (username, password)
        self.session.verify = verify_ssl
        self.available_functions: dict[str, Callable[..., dict[str, Any]]] = {
            "search_conditions": self.search_conditions,
            "get_patient": self.get_patient,
            "search_observations": self.search_observations,
            "search_medications": self.search_medications,
            "search_all_conditions": self.search_all_conditions,
            "search_encounters": self.search_encounters,
            "search_patients": self.search_patients,
        }

    def verify_connection(self) -> dict[str, Any]:
        metadata = self.session.get(
            f"{self.base_url}/metadata",
            params={"_format": "json"},
            timeout=self.timeout,
        )
        metadata.raise_for_status()
        count_resp = self.session.get(
            f"{self.base_url}/Patient",
            params={"_summary": "count", "_format": "json"},
            timeout=self.timeout,
        )
        count_resp.raise_for_status()
        return {
            "fhir_version": metadata.json().get("fhirVersion", "unknown"),
            "patient_count": count_resp.json().get("total", "unknown"),
        }

    def search_conditions(self, code: str, max_results: int = 50) -> dict[str, Any]:
        resp = self.session.get(
            f"{self.base_url}/Condition",
            params={"code": code, "_count": max_results, "_format": "json"},
            timeout=self.timeout,
        )
        resp.raise_for_status()
        bundle = resp.json()
        rows = []
        for entry in bundle.get("entry", []):
            resource = entry["resource"]
            coding = resource.get("code", {}).get("coding", [{}])[0]
            rows.append(
                {
                    "condition_id": resource.get("id"),
                    "code": coding.get("code", ""),
                    "display": coding.get("display", ""),
                    "patient_reference": resource.get("subject", {}).get("reference", ""),
                    "clinical_status": resource.get("clinicalStatus", {})
                    .get("coding", [{}])[0]
                    .get("code", ""),
                }
            )
        return {"total": bundle.get("total", 0), "results": rows}

    def get_patient(self, patient_id: str) -> dict[str, Any]:
        resp = self.session.get(
            f"{self.base_url}/Patient/{patient_id}",
            params={"_format": "json"},
            timeout=self.timeout,
        )
        resp.raise_for_status()
        patient = resp.json()
        name = patient.get("name", [{}])[0]
        return {
            "id": patient.get("id"),
            "name": f"{' '.join(name.get('given', []))} {name.get('family', '')}".strip(),
            "gender": patient.get("gender", ""),
            "birthDate": patient.get("birthDate", ""),
            "age": compute_age(patient.get("birthDate", "")),
        }

    def search_observations(
        self,
        patient_id: str,
        loinc_code: str,
        max_results: int = 5,
    ) -> dict[str, Any]:
        resp = self.session.get(
            f"{self.base_url}/Observation",
            params={
                "subject": f"Patient/{patient_id}",
                "code": loinc_code,
                "_count": max_results,
                "_sort": "-date",
                "_format": "json",
            },
            timeout=self.timeout,
        )
        resp.raise_for_status()
        bundle = resp.json()
        rows = []
        for entry in bundle.get("entry", []):
            resource = entry["resource"]
            coding = resource.get("code", {}).get("coding", [{}])[0]
            value_qty = resource.get("valueQuantity", {})
            row = {
                "display": coding.get("display", ""),
                "code": coding.get("code", ""),
                "value": value_qty.get("value"),
                "unit": value_qty.get("unit", ""),
                "date": resource.get("effectiveDateTime", ""),
            }
            if row["value"] is None and resource.get("component"):
                row["components"] = [
                    {
                        "component": comp.get("code", {}).get("coding", [{}])[0].get("display", ""),
                        "value": comp.get("valueQuantity", {}).get("value"),
                        "unit": comp.get("valueQuantity", {}).get("unit", ""),
                    }
                    for comp in resource.get("component", [])
                ]
            rows.append(row)
        return {"total": bundle.get("total", 0), "results": rows}

    def search_medications(self, patient_id: str, max_results: int = 10) -> dict[str, Any]:
        resp = self.session.get(
            f"{self.base_url}/MedicationRequest",
            params={
                "subject": f"Patient/{patient_id}",
                "_count": max_results,
                "_format": "json",
            },
            timeout=self.timeout,
        )
        resp.raise_for_status()
        bundle = resp.json()
        rows = []
        for entry in bundle.get("entry", []):
            resource = entry["resource"]
            med_concept = resource.get("medicationCodeableConcept", {})
            coding = med_concept.get("coding", [{}])[0] if med_concept.get("coding") else {}
            rows.append(
                {
                    "medication": coding.get("display") or med_concept.get("text", "unknown"),
                    "code": coding.get("code", ""),
                    "status": resource.get("status", ""),
                    "authoredOn": resource.get("authoredOn", ""),
                }
            )
        return {"total": bundle.get("total", 0), "results": rows}

    def search_all_conditions(self, patient_id: str, max_results: int = 20) -> dict[str, Any]:
        resp = self.session.get(
            f"{self.base_url}/Condition",
            params={
                "subject": f"Patient/{patient_id}",
                "_count": max_results,
                "_format": "json",
            },
            timeout=self.timeout,
        )
        resp.raise_for_status()
        bundle = resp.json()
        rows = []
        for entry in bundle.get("entry", []):
            resource = entry["resource"]
            coding = resource.get("code", {}).get("coding", [{}])[0]
            rows.append(
                {
                    "condition": coding.get("display", ""),
                    "code": coding.get("code", ""),
                    "clinical_status": resource.get("clinicalStatus", {})
                    .get("coding", [{}])[0]
                    .get("code", ""),
                }
            )
        return {"total": bundle.get("total", 0), "results": rows}

    def search_encounters(self, patient_id: str, max_results: int = 10) -> dict[str, Any]:
        resp = self.session.get(
            f"{self.base_url}/Encounter",
            params={
                "subject": f"Patient/{patient_id}",
                "_count": max_results,
                "_sort": "-date",
                "_format": "json",
            },
            timeout=self.timeout,
        )
        resp.raise_for_status()
        bundle = resp.json()
        rows = []
        for entry in bundle.get("entry", []):
            resource = entry["resource"]
            enc_type = resource.get("type", [{}])[0].get("text", "") if resource.get("type") else ""
            rows.append(
                {
                    "status": resource.get("status", ""),
                    "class": resource.get("class", {}).get("code", ""),
                    "type": enc_type,
                    "period_start": resource.get("period", {}).get("start", ""),
                }
            )
        return {"total": bundle.get("total", 0), "results": rows}

    def search_patients(self, max_results: int = 50) -> dict[str, Any]:
        resp = self.session.get(
            f"{self.base_url}/Patient",
            params={"_count": max_results, "_format": "json"},
            timeout=self.timeout,
        )
        resp.raise_for_status()
        bundle = resp.json()
        rows = []
        for entry in bundle.get("entry", []):
            patient = entry["resource"]
            name = patient.get("name", [{}])[0]
            rows.append(
                {
                    "id": patient.get("id"),
                    "name": f"{' '.join(name.get('given', []))} {name.get('family', '')}".strip(),
                    "gender": patient.get("gender", ""),
                    "birthDate": patient.get("birthDate", ""),
                    "age": compute_age(patient.get("birthDate", "")),
                }
            )
        return {"total": bundle.get("total", 0), "results": rows}

    def call_tool(self, name: str, args: dict[str, Any]) -> dict[str, Any]:
        fn = self.available_functions.get(name)
        if fn is None:
            raise KeyError(f"Unknown tool: {name}")
        return fn(**args)

    def build_claude_tools(self) -> list[dict[str, Any]]:
        return [
            {
                "name": "search_conditions",
                "description": (
                    "Search for conditions by SNOMED CT code. "
                    "Common codes: 46635009 for Type 1 diabetes, "
                    "44054006 for Type 2 diabetes, 709044004 for chronic kidney disease."
                ),
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "code": {"type": "string"},
                        "max_results": {"type": "integer", "default": 50},
                    },
                    "required": ["code"],
                },
            },
            {
                "name": "get_patient",
                "description": "Get demographics for a single patient by patient ID.",
                "input_schema": {
                    "type": "object",
                    "properties": {"patient_id": {"type": "string"}},
                    "required": ["patient_id"],
                },
            },
            {
                "name": "search_observations",
                "description": (
                    "Search observations for a patient by LOINC code. "
                    "Useful codes: 4548-4 HbA1c, 1986-9 C-peptide, 39156-5 BMI, "
                    "2160-0 creatinine, 33914-3 eGFR, 14959-1 urine albumin/creatinine ratio."
                ),
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "patient_id": {"type": "string"},
                        "loinc_code": {"type": "string"},
                        "max_results": {"type": "integer", "default": 5},
                    },
                    "required": ["patient_id", "loinc_code"],
                },
            },
            {
                "name": "search_medications",
                "description": "Get medication requests for a patient.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "patient_id": {"type": "string"},
                        "max_results": {"type": "integer", "default": 10},
                    },
                    "required": ["patient_id"],
                },
            },
            {
                "name": "search_all_conditions",
                "description": "Get the full problem list for a patient.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "patient_id": {"type": "string"},
                        "max_results": {"type": "integer", "default": 20},
                    },
                    "required": ["patient_id"],
                },
            },
            {
                "name": "search_encounters",
                "description": "Get recent encounters for a patient.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "patient_id": {"type": "string"},
                        "max_results": {"type": "integer", "default": 10},
                    },
                    "required": ["patient_id"],
                },
            },
            {
                "name": "search_patients",
                "description": "Get a batch of patient demographics.",
                "input_schema": {
                    "type": "object",
                    "properties": {"max_results": {"type": "integer", "default": 50}},
                },
            },
        ]
