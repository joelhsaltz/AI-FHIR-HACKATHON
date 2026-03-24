#!/usr/bin/env python3
"""
FHIR Server Data Discovery Script

Queries the live FHIR server to discover what clinical data exists
for each of the 6 synthetic phenotypes. Produces a structured report
of condition counts, lab availability, value ranges, and phenotype
identification rules.
"""

import requests
import json
import warnings
import statistics
from collections import defaultdict

warnings.filterwarnings("ignore", message="Unverified HTTPS request")

BASE_URL = "https://lfh-fhir.eastus2.cloudapp.azure.com:9443/fhir-server/api/v4"
AUTH = ("fhiruser", "BmI512@ccess")

SNOMED = {
    "T1D": "46635009",
    "T2D": "44054006",
    "CKD": "709044004",
}

LOINC = {
    "HbA1c": "4548-4",
    "C-peptide": "1986-9",
    "BMI": "39156-5",
    "Creatinine": "2160-0",
    "eGFR": "33914-3",
    "UACR": "14959-1",
}


def fhir_get(path, params=None):
    p = {**(params or {}), "_format": "json"}
    resp = requests.get(f"{BASE_URL}/{path}", params=p, auth=AUTH, verify=False, timeout=30)
    resp.raise_for_status()
    return resp.json()


def fhir_get_all(path, params=None, max_pages=20):
    """Page through all results."""
    p = {**(params or {}), "_format": "json"}
    if "_count" not in p:
        p["_count"] = "200"
    all_entries = []
    url = f"{BASE_URL}/{path}"
    page = 0
    while url and page < max_pages:
        resp = requests.get(url, params=p if page == 0 else None, auth=AUTH, verify=False, timeout=30)
        resp.raise_for_status()
        bundle = resp.json()
        entries = bundle.get("entry", [])
        all_entries.extend(entries)
        # Find next link
        url = None
        for link in bundle.get("link", []):
            if link.get("relation") == "next":
                url = link["url"]
                break
        page += 1
    return all_entries


def get_patient_ids_by_condition(snomed_code):
    """Get all unique patient IDs for a given condition SNOMED code."""
    entries = fhir_get_all("Condition", {"code": f"http://snomed.info/sct|{snomed_code}"})
    patient_ids = set()
    for entry in entries:
        resource = entry.get("resource", {})
        subj = resource.get("subject", {}).get("reference", "")
        if subj.startswith("Patient/"):
            patient_ids.add(subj.replace("Patient/", ""))
    return patient_ids


def get_latest_obs_value(patient_id, loinc_code):
    """Get the most recent observation value for a patient+LOINC."""
    try:
        bundle = fhir_get("Observation", {
            "subject": f"Patient/{patient_id}",
            "code": f"http://loinc.org|{loinc_code}",
            "_count": "1",
            "_sort": "-date",
        })
    except Exception:
        return None
    entries = bundle.get("entry", [])
    if not entries:
        return None
    resource = entries[0].get("resource", {})
    vq = resource.get("valueQuantity", {})
    return vq.get("value")


def get_medications(patient_id):
    """Get all medication requests for a patient."""
    try:
        entries = fhir_get_all("MedicationRequest", {
            "subject": f"Patient/{patient_id}",
            "_count": "50",
        }, max_pages=3)
    except Exception:
        return []
    meds = []
    for entry in entries:
        resource = entry.get("resource", {})
        med_ref = resource.get("medicationCodeableConcept", {})
        text = med_ref.get("text", "")
        codings = med_ref.get("coding", [])
        display = codings[0].get("display", "") if codings else ""
        meds.append(text or display or "unknown")
    return list(set(meds))


def summarize_values(values):
    """Compute min, median, max, count for a list of values."""
    clean = [v for v in values if v is not None]
    if not clean:
        return {"count": 0}
    return {
        "count": len(clean),
        "min": round(min(clean), 2),
        "median": round(statistics.median(clean), 2),
        "max": round(max(clean), 2),
    }


# ============================================================
# STEP 1: Count patients per condition
# ============================================================
print("=" * 70)
print("STEP 1: CONDITION COUNTS")
print("=" * 70)

condition_patients = {}
for name, code in SNOMED.items():
    ids = get_patient_ids_by_condition(code)
    condition_patients[name] = ids
    print(f"  {name} ({code}): {len(ids)} patients")

# Check overlaps
t1d = condition_patients["T1D"]
t2d = condition_patients["T2D"]
ckd = condition_patients["CKD"]

print(f"\n  Overlaps:")
print(f"    T1D + T2D: {len(t1d & t2d)} patients")
print(f"    T1D + CKD: {len(t1d & ckd)} patients")
print(f"    T2D + CKD: {len(t2d & ckd)} patients")
print(f"    T1D + T2D + CKD: {len(t1d & t2d & ckd)} patients")
print(f"    Any diabetes (T1D | T2D): {len(t1d | t2d)} patients")

# Total patients on server
print(f"\n  Checking total patient count...")
total_bundle = fhir_get("Patient", {"_summary": "count"})
total_patients = total_bundle.get("total", "unknown")
print(f"  Total patients on server: {total_patients}")

all_with_conditions = t1d | t2d | ckd
print(f"  Patients with at least one condition: {len(all_with_conditions)}")
# Patients with no relevant condition = total - those with conditions
# (We'll check a sample later)

# ============================================================
# STEP 2: Lab availability and value ranges per condition group
# ============================================================
print("\n" + "=" * 70)
print("STEP 2: LAB AVAILABILITY AND VALUE RANGES")
print("=" * 70)

SAMPLE_SIZE = 20  # sample per group

lab_data = {}  # group -> lab -> [values]

for group_name, patient_ids in [("T1D", t1d), ("T2D", t2d), ("CKD", ckd)]:
    sample = sorted(patient_ids)[:SAMPLE_SIZE]
    print(f"\n  --- {group_name} (sampling {len(sample)} of {len(patient_ids)} patients) ---")
    lab_data[group_name] = {}

    for lab_name, loinc in LOINC.items():
        values = []
        for pid in sample:
            v = get_latest_obs_value(pid, loinc)
            if v is not None:
                values.append(v)
        lab_data[group_name][lab_name] = values
        summary = summarize_values(values)
        if summary["count"] > 0:
            print(f"    {lab_name}: {summary['count']}/{len(sample)} patients, "
                  f"range [{summary['min']} - {summary['max']}], median={summary['median']}")
        else:
            print(f"    {lab_name}: 0/{len(sample)} patients -- NOT FOUND")

# ============================================================
# STEP 3: Medication patterns per condition group
# ============================================================
print("\n" + "=" * 70)
print("STEP 3: MEDICATION PATTERNS")
print("=" * 70)

med_data = {}

for group_name, patient_ids in [("T1D", t1d), ("T2D", t2d), ("CKD", ckd)]:
    sample = sorted(patient_ids)[:10]
    print(f"\n  --- {group_name} (sampling {len(sample)} patients) ---")
    all_meds = defaultdict(int)
    patients_with_meds = 0
    for pid in sample:
        meds = get_medications(pid)
        if meds:
            patients_with_meds += 1
        for m in meds:
            all_meds[m] += 1
    med_data[group_name] = dict(all_meds)
    print(f"    Patients with any meds: {patients_with_meds}/{len(sample)}")
    for med, count in sorted(all_meds.items(), key=lambda x: -x[1]):
        print(f"      {med}: {count}/{len(sample)}")

# ============================================================
# STEP 4: Deep-dive — T2D without CKD to distinguish subtypes
# ============================================================
print("\n" + "=" * 70)
print("STEP 4: T2D SUBTYPES (with vs without insulin)")
print("=" * 70)

t2d_only = t2d - ckd  # T2D without CKD
t2d_ckd = t2d & ckd   # T2D with CKD

print(f"  T2D only (no CKD): {len(t2d_only)}")
print(f"  T2D + CKD: {len(t2d_ckd)}")

# Check insulin use in T2D patients
sample_t2d = sorted(t2d_only)[:20]
insulin_users = []
non_insulin_users = []

for pid in sample_t2d:
    meds = get_medications(pid)
    med_lower = [m.lower() for m in meds]
    has_insulin = any("insulin" in m for m in med_lower)
    if has_insulin:
        insulin_users.append(pid)
    else:
        non_insulin_users.append(pid)

print(f"\n  In T2D-only sample ({len(sample_t2d)}):")
print(f"    With insulin: {len(insulin_users)}")
print(f"    Without insulin: {len(non_insulin_users)}")

# Compare labs between insulin/non-insulin T2D
for subgroup_name, subgroup_pids in [("T2D+insulin", insulin_users), ("T2D no insulin", non_insulin_users)]:
    if not subgroup_pids:
        print(f"\n  --- {subgroup_name}: NO PATIENTS ---")
        continue
    print(f"\n  --- {subgroup_name} ({len(subgroup_pids)} patients) ---")
    for lab_name, loinc in LOINC.items():
        values = []
        for pid in subgroup_pids:
            v = get_latest_obs_value(pid, loinc)
            if v is not None:
                values.append(v)
        summary = summarize_values(values)
        if summary["count"] > 0:
            print(f"    {lab_name}: {summary['count']} patients, "
                  f"range [{summary['min']} - {summary['max']}], median={summary['median']}")

# ============================================================
# STEP 5: HbA1c distribution across all groups for control assessment
# ============================================================
print("\n" + "=" * 70)
print("STEP 5: HbA1c DISTRIBUTION (glycemic control)")
print("=" * 70)

# Sample larger sets for HbA1c to understand the distribution
for group_name, patient_ids in [("T1D", t1d), ("T2D", t2d)]:
    sample = sorted(patient_ids)[:min(40, len(patient_ids))]
    hba1c_vals = []
    for pid in sample:
        v = get_latest_obs_value(pid, LOINC["HbA1c"])
        if v is not None:
            hba1c_vals.append(v)
    hba1c_vals.sort()
    print(f"\n  {group_name} HbA1c values ({len(hba1c_vals)} patients):")
    # Show distribution buckets
    buckets = {"<6.5": 0, "6.5-7.0": 0, "7.0-7.5": 0, "7.5-8.5": 0, "8.5-10": 0, ">10": 0}
    for v in hba1c_vals:
        if v < 6.5:
            buckets["<6.5"] += 1
        elif v < 7.0:
            buckets["6.5-7.0"] += 1
        elif v < 7.5:
            buckets["7.0-7.5"] += 1
        elif v < 8.5:
            buckets["7.5-8.5"] += 1
        elif v < 10:
            buckets["8.5-10"] += 1
        else:
            buckets[">10"] += 1
    for bucket, count in buckets.items():
        bar = "#" * count
        print(f"    {bucket:>8}: {count:3d} {bar}")
    if hba1c_vals:
        print(f"    All values: {[round(v,1) for v in hba1c_vals]}")

# ============================================================
# STEP 6: Check for patients with NO diabetes condition
# ============================================================
print("\n" + "=" * 70)
print("STEP 6: PATIENTS WITHOUT DIABETES CONDITIONS")
print("=" * 70)

# Get a batch of patient IDs from the server
patient_entries = fhir_get_all("Patient", {"_count": "200", "_elements": "id"}, max_pages=10)
all_patient_ids = set()
for entry in patient_entries:
    resource = entry.get("resource", {})
    all_patient_ids.add(resource.get("id"))

print(f"  Total patients found: {len(all_patient_ids)}")
diabetes_patients = t1d | t2d
no_diabetes = all_patient_ids - diabetes_patients
print(f"  Patients with diabetes (T1D or T2D): {len(diabetes_patients)}")
print(f"  Patients with NO diabetes condition: {len(no_diabetes)}")
print(f"  Patients with CKD but no diabetes: {len(ckd - diabetes_patients)}")

# Check a sample of no-diabetes patients for labs
if no_diabetes:
    sample_no_dm = sorted(no_diabetes)[:10]
    print(f"\n  Sampling {len(sample_no_dm)} patients with no diabetes condition:")
    for lab_name, loinc in LOINC.items():
        values = []
        for pid in sample_no_dm:
            v = get_latest_obs_value(pid, loinc)
            if v is not None:
                values.append(v)
        summary = summarize_values(values)
        if summary["count"] > 0:
            print(f"    {lab_name}: {summary['count']} patients, "
                  f"range [{summary['min']} - {summary['max']}], median={summary['median']}")
        else:
            print(f"    {lab_name}: NOT FOUND")

# ============================================================
# STEP 7: Check C-peptide distribution more carefully
# ============================================================
print("\n" + "=" * 70)
print("STEP 7: C-PEPTIDE DEEP DIVE")
print("=" * 70)

for group_name, patient_ids in [("T1D", t1d), ("T2D", t2d)]:
    sample = sorted(patient_ids)[:min(30, len(patient_ids))]
    cpep_vals = []
    for pid in sample:
        v = get_latest_obs_value(pid, LOINC["C-peptide"])
        if v is not None:
            cpep_vals.append(v)
    cpep_vals.sort()
    print(f"\n  {group_name} C-peptide ({len(cpep_vals)} values):")
    if cpep_vals:
        print(f"    Values: {[round(v,2) for v in cpep_vals]}")
        print(f"    Min={round(min(cpep_vals),2)}, Median={round(statistics.median(cpep_vals),2)}, Max={round(max(cpep_vals),2)}")

print("\n" + "=" * 70)
print("DISCOVERY COMPLETE")
print("=" * 70)
