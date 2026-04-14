#!/usr/bin/env python3
"""
FHIR Server Validation Script
Validates that the SBU IBM FHIR Server has all required data
for the FHIR + AI Hackathon.
"""

import os
import requests
import urllib3
import json
from datetime import datetime
from typing import Dict, List, Any

# Suppress InsecureRequestWarning for self-signed SSL cert
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

FHIR_BASE = "https://lfh-fhir.eastus2.cloudapp.azure.com:9443/fhir-server/api/v4"

# ---- FHIR Auth (SBU IBM FHIR Server — self-signed cert, Basic Auth) ----
FHIR_USERNAME = os.environ.get("FHIR_USERNAME", "fhiruser")
FHIR_PASSWORD = os.environ.get("FHIR_PASSWORD", "BmI512@ccess")

FHIR_SESSION = requests.Session()
FHIR_SESSION.auth = (FHIR_USERNAME, FHIR_PASSWORD)
FHIR_SESSION.verify = False

class ValidationResult:
    def __init__(self):
        self.results = []
        self.data = {}

    def add_check(self, name: str, passed: bool, details: str = ""):
        self.results.append({
            "check": name,
            "passed": passed,
            "details": details
        })
        if not passed:
            print(f"[FAIL] {name}: {details}")
        else:
            print(f"[PASS] {name}: {details}")

    def store_data(self, key: str, value: Any):
        self.data[key] = value

def check_server_reachable(result: ValidationResult) -> bool:
    """Check if FHIR server is reachable and returns metadata."""
    try:
        resp = FHIR_SESSION.get(f"{FHIR_BASE}/metadata", params={"_format": "json"}, timeout=10)
        if resp.status_code == 200:
            metadata = resp.json()
            fhir_version = metadata.get("fhirVersion", "unknown")
            result.add_check(
                "Server reachable",
                True,
                f"FHIR version {fhir_version}"
            )
            result.store_data("fhir_version", fhir_version)
            return True
        else:
            result.add_check("Server reachable", False, f"Status code {resp.status_code}")
            return False
    except Exception as e:
        result.add_check("Server reachable", False, str(e))
        return False

def check_diabetes_conditions(result: ValidationResult) -> List[str]:
    """Check for Type 2 Diabetes conditions (SNOMED CT: 44054006)."""
    try:
        resp = FHIR_SESSION.get(
            f"{FHIR_BASE}/Condition",
            params={"code": "44054006", "_count": 20, "_format": "json"},
            timeout=15
        )

        if resp.status_code != 200:
            result.add_check("Type 2 Diabetes conditions", False, f"HTTP {resp.status_code}")
            return []

        bundle = resp.json()
        total = bundle.get("total", 0)
        entries = bundle.get("entry", [])

        # Extract unique patient IDs
        patient_ids = set()
        for entry in entries:
            resource = entry.get("resource", {})
            subject_ref = resource.get("subject", {}).get("reference", "")
            if subject_ref.startswith("Patient/"):
                patient_id = subject_ref.split("/")[-1]
                patient_ids.add(patient_id)

        passed = len(entries) >= 5 and len(patient_ids) >= 3
        result.add_check(
            "Type 2 Diabetes conditions found",
            passed,
            f"{len(entries)} entries, {len(patient_ids)} unique patients"
        )

        result.store_data("diabetes_patient_ids", list(patient_ids))
        return list(patient_ids)

    except Exception as e:
        result.add_check("Type 2 Diabetes conditions", False, str(e))
        return []

def check_patients_fetchable(result: ValidationResult, patient_ids: List[str]) -> List[str]:
    """Check if patient resources can be fetched."""
    if not patient_ids:
        result.add_check("Patient resources fetchable", False, "No patient IDs to test")
        return []

    successful_ids = []
    failed = 0

    for patient_id in patient_ids[:10]:  # Test up to 10 patients
        try:
            resp = FHIR_SESSION.get(
                f"{FHIR_BASE}/Patient/{patient_id}",
                params={"_format": "json"},
                timeout=10
            )

            if resp.status_code == 200:
                patient = resp.json()
                has_name = bool(patient.get("name"))
                has_birthdate = bool(patient.get("birthDate"))
                has_gender = bool(patient.get("gender"))

                if has_name and has_birthdate and has_gender:
                    successful_ids.append(patient_id)
                else:
                    failed += 1
            else:
                failed += 1
        except:
            failed += 1

    passed = len(successful_ids) >= min(3, len(patient_ids))
    result.add_check(
        "Patient resources fetchable",
        passed,
        f"{len(successful_ids)}/{len(patient_ids[:10])} succeeded"
    )

    return successful_ids

def check_hba1c_observations(result: ValidationResult, patient_ids: List[str]) -> Dict[str, List[str]]:
    """Check for HbA1c observations (LOINC 4548-4)."""
    if not patient_ids:
        result.add_check("HbA1c observations", False, "No patient IDs to test")
        return {"with_hba1c": [], "poor_control": []}

    patients_with_hba1c = []
    patients_poor_control = []

    for patient_id in patient_ids[:10]:  # Test up to 10 patients
        try:
            resp = FHIR_SESSION.get(
                f"{FHIR_BASE}/Observation",
                params={
                    "subject": f"Patient/{patient_id}",
                    "code": "4548-4",
                    "_count": 5,
                    "_sort": "-date",
                    "_format": "json"
                },
                timeout=10
            )

            if resp.status_code == 200:
                bundle = resp.json()
                entries = bundle.get("entry", [])

                if entries:
                    patients_with_hba1c.append(patient_id)

                    # Check for values > 7.0
                    for entry in entries:
                        obs = entry.get("resource", {})
                        value = obs.get("valueQuantity", {}).get("value")
                        if value and float(value) > 7.0:
                            patients_poor_control.append(patient_id)
                            break
        except:
            continue

    passed = len(patients_with_hba1c) >= 1
    result.add_check(
        "HbA1c observations found",
        passed,
        f"{len(patients_with_hba1c)} patients have HbA1c data"
    )

    result.add_check(
        "HbA1c values > 7.0% found",
        len(patients_poor_control) > 0,
        f"{len(patients_poor_control)} patients with poor control"
    )

    result.store_data("patients_with_hba1c", patients_with_hba1c)
    result.store_data("patients_poor_control", patients_poor_control)

    return {
        "with_hba1c": patients_with_hba1c,
        "poor_control": patients_poor_control
    }

def check_medications(result: ValidationResult, patient_ids: List[str]) -> bool:
    """Check for MedicationRequest resources."""
    if not patient_ids:
        result.add_check("MedicationRequest resources", False, "No patient IDs to test")
        return False

    found_count = 0
    for patient_id in patient_ids[:5]:
        try:
            resp = FHIR_SESSION.get(
                f"{FHIR_BASE}/MedicationRequest",
                params={
                    "subject": f"Patient/{patient_id}",
                    "_count": 5,
                    "_format": "json"
                },
                timeout=10
            )

            if resp.status_code == 200:
                bundle = resp.json()
                if bundle.get("entry"):
                    found_count += 1
        except:
            continue

    passed = found_count > 0
    result.add_check(
        "MedicationRequest resources found",
        passed,
        f"{found_count}/{len(patient_ids[:5])} patients have medications"
    )
    return passed

def check_encounters(result: ValidationResult, patient_ids: List[str]) -> bool:
    """Check for Encounter resources."""
    if not patient_ids:
        result.add_check("Encounter resources", False, "No patient IDs to test")
        return False

    found_count = 0
    for patient_id in patient_ids[:5]:
        try:
            resp = FHIR_SESSION.get(
                f"{FHIR_BASE}/Encounter",
                params={
                    "subject": f"Patient/{patient_id}",
                    "_count": 5,
                    "_format": "json"
                },
                timeout=10
            )

            if resp.status_code == 200:
                bundle = resp.json()
                if bundle.get("entry"):
                    found_count += 1
        except:
            continue

    passed = found_count > 0
    result.add_check(
        "Encounter resources found",
        passed,
        f"{found_count}/{len(patient_ids[:5])} patients have encounters"
    )
    return passed

def check_all_conditions(result: ValidationResult, patient_ids: List[str]) -> bool:
    """Check for multiple conditions per patient."""
    if not patient_ids:
        result.add_check("Multiple conditions per patient", False, "No patient IDs to test")
        return False

    patients_with_multiple = 0
    for patient_id in patient_ids[:5]:
        try:
            resp = FHIR_SESSION.get(
                f"{FHIR_BASE}/Condition",
                params={
                    "subject": f"Patient/{patient_id}",
                    "_count": 20,
                    "_format": "json"
                },
                timeout=10
            )

            if resp.status_code == 200:
                bundle = resp.json()
                if len(bundle.get("entry", [])) > 1:
                    patients_with_multiple += 1
        except:
            continue

    passed = patients_with_multiple > 0
    result.add_check(
        "Multiple conditions per patient found",
        passed,
        f"{patients_with_multiple}/{len(patient_ids[:5])} patients have multiple conditions"
    )
    return passed

def check_hypertension(result: ValidationResult) -> List[str]:
    """Check for hypertension conditions (SNOMED CT: 59621000)."""
    try:
        resp = FHIR_SESSION.get(
            f"{FHIR_BASE}/Condition",
            params={"code": "59621000", "_count": 10, "_format": "json"},
            timeout=15
        )

        if resp.status_code == 200:
            bundle = resp.json()
            entries = bundle.get("entry", [])

            patient_ids = set()
            for entry in entries:
                ref = entry.get("resource", {}).get("subject", {}).get("reference", "")
                if ref.startswith("Patient/"):
                    patient_ids.add(ref.split("/")[-1])

            passed = len(entries) > 0
            result.add_check(
                "Hypertension conditions found",
                passed,
                f"{len(entries)} conditions, {len(patient_ids)} patients"
            )

            result.store_data("hypertension_patient_ids", list(patient_ids))
            return list(patient_ids)
        else:
            result.add_check("Hypertension conditions found", False, f"HTTP {resp.status_code}")
            return []
    except Exception as e:
        result.add_check("Hypertension conditions found", False, str(e))
        return []

def check_blood_pressure(result: ValidationResult, patient_ids: List[str]) -> bool:
    """Check for blood pressure observations (LOINC 85354-9)."""
    if not patient_ids:
        result.add_check("Blood pressure observations", False, "No patient IDs to test")
        return False

    found_count = 0
    for patient_id in patient_ids[:5]:
        try:
            resp = FHIR_SESSION.get(
                f"{FHIR_BASE}/Observation",
                params={
                    "subject": f"Patient/{patient_id}",
                    "code": "85354-9",
                    "_count": 5,
                    "_format": "json"
                },
                timeout=10
            )

            if resp.status_code == 200:
                bundle = resp.json()
                if bundle.get("entry"):
                    found_count += 1
        except:
            continue

    passed = found_count > 0
    result.add_check(
        "Blood pressure observations found",
        passed,
        f"{found_count}/{len(patient_ids[:5])} patients have BP data"
    )
    return passed

def check_creatinine(result: ValidationResult, patient_ids: List[str]) -> bool:
    """Check for creatinine observations (LOINC 2160-0)."""
    if not patient_ids:
        result.add_check("Creatinine observations", False, "No patient IDs to test")
        return False

    found_count = 0
    for patient_id in patient_ids[:5]:
        try:
            resp = FHIR_SESSION.get(
                f"{FHIR_BASE}/Observation",
                params={
                    "subject": f"Patient/{patient_id}",
                    "code": "2160-0",
                    "_count": 5,
                    "_format": "json"
                },
                timeout=10
            )

            if resp.status_code == 200:
                bundle = resp.json()
                if bundle.get("entry"):
                    found_count += 1
        except:
            continue

    passed = found_count > 0
    result.add_check(
        "Creatinine observations found",
        passed,
        f"{found_count}/{len(patient_ids[:5])} patients have creatinine data"
    )
    return passed

def main():
    print("=" * 70)
    print("FHIR SERVER VALIDATION")
    print("=" * 70)
    print(f"Server: {FHIR_BASE}")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print("=" * 70)
    print()

    result = ValidationResult()

    # Core checks (must pass)
    print("CORE CHECKS:")
    print("-" * 70)
    if not check_server_reachable(result):
        print("\n❌ CRITICAL: Server not reachable. Stopping validation.")
        return

    diabetes_patients = check_diabetes_conditions(result)
    if not diabetes_patients:
        print("\n❌ CRITICAL: No diabetes patients found. Stopping validation.")
        return

    fetchable_patients = check_patients_fetchable(result, diabetes_patients)
    if not fetchable_patients:
        print("\n❌ CRITICAL: Cannot fetch patient resources. Stopping validation.")
        return

    hba1c_data = check_hba1c_observations(result, fetchable_patients)

    print()
    print("SESSION 3 RESOURCES:")
    print("-" * 70)
    check_medications(result, fetchable_patients)
    check_encounters(result, fetchable_patients)
    check_all_conditions(result, fetchable_patients)

    print()
    print("ADDITIONAL CLINICAL SCENARIOS:")
    print("-" * 70)
    hypertension_patients = check_hypertension(result)
    if hypertension_patients:
        check_blood_pressure(result, hypertension_patients)

    if fetchable_patients:
        check_creatinine(result, fetchable_patients)

    # Summary
    print()
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    passed = sum(1 for r in result.results if r["passed"])
    total = len(result.results)
    print(f"Checks passed: {passed}/{total}")
    print()

    if hba1c_data["with_hba1c"]:
        print(f"Sample patient IDs with diabetes + HbA1c:")
        for pid in hba1c_data["with_hba1c"][:5]:
            print(f"  - {pid}")

    if hba1c_data["poor_control"]:
        print(f"\nPatient IDs with HbA1c > 7.0% (poor control):")
        for pid in hba1c_data["poor_control"][:5]:
            print(f"  - {pid}")

    # Save results
    output = {
        "timestamp": datetime.now().isoformat(),
        "server": FHIR_BASE,
        "fhir_version": result.data.get("fhir_version"),
        "checks": result.results,
        "sample_data": {
            "diabetes_patients": result.data.get("diabetes_patient_ids", [])[:10],
            "patients_with_hba1c": result.data.get("patients_with_hba1c", [])[:10],
            "patients_poor_control": result.data.get("patients_poor_control", [])[:10],
            "hypertension_patients": result.data.get("hypertension_patient_ids", [])[:10]
        },
        "summary": {
            "total_checks": total,
            "passed_checks": passed,
            "all_passed": passed == total
        }
    }

    with open("validation_results.json", "w") as f:
        json.dump(output, f, indent=2)

    print(f"\n✅ Results saved to validation_results.json")

    if passed < total:
        print(f"\n⚠️  WARNING: {total - passed} checks failed")
        return 1
    else:
        print("\n✅ All checks passed!")
        return 0

if __name__ == "__main__":
    exit(main())
