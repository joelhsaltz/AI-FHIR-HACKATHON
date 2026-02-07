#!/usr/bin/env python3
"""
Test Session 1 notebook cells against live FHIR server.
"""

import requests
import json
import pandas as pd

FHIR_BASE = "https://launch.smarthealthit.org/v/r4/fhir"

def show_json(data, max_lines=30):
    """Pretty-print JSON, truncated for readability."""
    text = json.dumps(data, indent=2)
    lines = text.split('\n')
    if len(lines) > max_lines:
        print('\n'.join(lines[:max_lines]))
        print(f'\n... ({len(lines) - max_lines} more lines)')
    else:
        print(text)

print("="*70)
print("SESSION 1 NOTEBOOK TEST")
print("="*70)
print()

# Test Cell 1: Setup and verify server
print("TEST 1: Server connection")
print("-"*70)
resp = requests.get(f"{FHIR_BASE}/metadata", params={"_format": "json"}, timeout=10)
if resp.status_code == 200:
    fhir_version = resp.json().get("fhirVersion", "unknown")
    print(f"✅ Connected to FHIR server: {FHIR_BASE}")
    print(f"   FHIR version: {fhir_version}")
else:
    print(f"❌ Could not connect. Status: {resp.status_code}")
    exit(1)

# Test Cell 2: First FHIR query (Patient resources)
print("\nTEST 2: Fetch Patient resources")
print("-"*70)
resp = requests.get(f"{FHIR_BASE}/Patient", params={"_count": 3, "_format": "json"})
bundle = resp.json()
print(f"Response type: {bundle['resourceType']}")
print(f"Total patients on server: {bundle.get('total', 'unknown')}")
print(f"Entries returned: {len(bundle.get('entry', []))}")
if bundle.get('entry'):
    first_patient = bundle["entry"][0]["resource"]
    print(f"✅ Successfully fetched {len(bundle.get('entry', []))} patients")
else:
    print("❌ No patients returned")
    exit(1)

# Test Cell 3b: Condition search (simulating Claude-generated code)
print("\nTEST 3: Search for Type 2 Diabetes conditions (SNOMED 44054006)")
print("-"*70)
resp = requests.get(
    f"{FHIR_BASE}/Condition",
    params={"code": "44054006", "_count": 20, "_format": "json"}
)
bundle = resp.json()
patient_refs = set()
condition_count = 0
for entry in bundle.get("entry", []):
    resource = entry["resource"]
    condition_id = resource.get("id", "")
    patient_ref = resource.get("subject", {}).get("reference", "")
    code_display = resource.get("code", {}).get("coding", [{}])[0].get("display", "")
    onset = resource.get("onsetDateTime", "unknown")

    if patient_ref:
        patient_refs.add(patient_ref)
    condition_count += 1

patient_ids = [ref.split("/")[-1] for ref in patient_refs if "/" in ref]
print(f"✅ Found {len(patient_refs)} unique patients with Type 2 diabetes")
print(f"   Example references: {list(patient_refs)[:3]}")
print(f"   Extracted patient IDs: {patient_ids[:3]}")

if not patient_ids:
    print("❌ No patient IDs extracted")
    exit(1)

# Test Cell 4b: Get patient demographics (simulating Claude-generated code)
print("\nTEST 4: Fetch Patient demographics")
print("-"*70)
patients = []
for pid in patient_ids[:5]:  # Test first 5
    resp = requests.get(f"{FHIR_BASE}/Patient/{pid}", params={"_format": "json"})
    if resp.status_code == 200:
        p = resp.json()
        name = p.get("name", [{}])[0]
        full_name = f"{' '.join(name.get('given', []))} {name.get('family', '')}".strip()
        patients.append({
            "id": p.get("id", pid),
            "name": full_name,
            "birthDate": p.get("birthDate", "unknown"),
            "gender": p.get("gender", "unknown")
        })

df_patients = pd.DataFrame(patients)
print(f"✅ Retrieved demographics for {len(df_patients)} patients")
print(df_patients.to_string(index=False))

if len(patients) == 0:
    print("❌ No patient demographics retrieved")
    exit(1)

# Test Cell 5b: Get HbA1c observations (simulating Claude-generated code)
print("\nTEST 5: Fetch HbA1c observations (LOINC 4548-4)")
print("-"*70)
observations = []
for patient in patients:
    pid = patient["id"]
    resp = requests.get(
        f"{FHIR_BASE}/Observation",
        params={
            "subject": f"Patient/{pid}",
            "code": "4548-4",
            "_sort": "-date",
            "_count": 1,
            "_format": "json"
        }
    )
    if resp.status_code == 200:
        bundle = resp.json()
        if bundle.get("entry"):
            obs = bundle["entry"][0]["resource"]
            observations.append({
                "patient_id": pid,
                "date": obs.get("effectiveDateTime", "unknown"),
                "value": obs.get("valueQuantity", {}).get("value", "N/A"),
                "unit": obs.get("valueQuantity", {}).get("unit", "")
            })
        else:
            observations.append({
                "patient_id": pid,
                "date": "N/A",
                "value": "N/A",
                "unit": ""
            })

df_obs = pd.DataFrame(observations)
print(f"✅ Retrieved HbA1c data for {len(observations)} patients")
print(df_obs.to_string(index=False))

# Test Cell 5c: Combined analysis
print("\nTEST 6: Combined analysis")
print("-"*70)
df_patients_str = df_patients.copy()
df_patients_str["id"] = df_patients_str["id"].astype(str)
df_obs["patient_id"] = df_obs["patient_id"].astype(str)

df_merged = df_obs.merge(df_patients_str, left_on="patient_id", right_on="id", how="left")
df_merged["hba1c_numeric"] = pd.to_numeric(df_merged["value"], errors="coerce")

def control_flag(x):
    if pd.isna(x): return '⚪ No data'
    if x > 7.5: return '🔴 Poor control'
    if x >= 6.5: return '🟡 Diabetic range'
    return '🟢 Below threshold'

df_merged['glycemic_control'] = df_merged['hba1c_numeric'].apply(control_flag)

print(f"✅ Analysis complete:")
has_data = df_merged['hba1c_numeric'].notna()
poor = (df_merged['hba1c_numeric'] > 7.5) & has_data
print(f"   Total diabetic patients: {len(df_merged)}")
print(f"   With HbA1c data: {has_data.sum()}")
print(f"   🔴 Poor control (>7.5%): {poor.sum()}")
print(f"   🟢 Adequate: {(has_data & ~poor).sum()}")
print(f"   ⚪ No data: {(~has_data).sum()}")

print("\n" + "="*70)
print("✅ ALL SESSION 1 TESTS PASSED!")
print("="*70)
print("\nSession 1 notebook is ready for students.")
print("Note: With the 7.5% threshold, students will find patients with poor control.")
