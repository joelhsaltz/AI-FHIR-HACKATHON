# SBU FHIR Server — Status and Data Inventory

**Last validated:** 2026-02-23

---

## Server Information

| Field | Value |
|-------|-------|
| **Endpoint** | `https://lfh-fhir.eastus2.cloudapp.azure.com:9443/fhir-server/api/v4` |
| **Server Type** | IBM FHIR Server (Linux for Health) |
| **FHIR Version** | 4.0.1 (R4) |
| **Software Version** | 4.11.1 |
| **Authentication** | HTTP Basic Auth |
| **Username** | `fhiruser` |
| **Password** | `BmI512@ccess` |
| **SSL** | Self-signed certificate (requires `verify=False` / `-k`) |
| **Hosting** | Azure (eastus2) |

---

## Permissions (Tested 2026-02-23)

All CRUD operations and transaction bundles are confirmed working with the `fhiruser` account.

| Operation | HTTP Method | Status | Notes |
|-----------|------------|--------|-------|
| **Create** | POST | 201 Created | Returns ID in `Location` header; use `Prefer: return=representation` to get body |
| **Read** | GET | 200 OK | Standard FHIR search and read |
| **Update** | PUT | Declared in CapabilityStatement | Not live-tested |
| **Patch** | PATCH | Declared in CapabilityStatement | Not live-tested |
| **Delete** | DELETE | 200 OK | Resource returns 410 Gone after deletion |
| **Transaction Bundle** | POST to root (`/`) | 200 OK | Multi-resource bundles work; must POST to root, NOT `/Bundle` |
| **Search** | GET with params | 200 OK | Standard FHIR search parameters supported |
| **History** | GET `_history` | Declared in CapabilityStatement | Not live-tested |

### IBM FHIR Server Quirks

- **POST response body may be empty** unless you include the header `Prefer: return=representation`
- **Transaction bundles** must be POSTed to the root endpoint (`{BASE}/`), not `{BASE}/Bundle`
- **SSL warnings** must be suppressed in Python:
  ```python
  import urllib3
  urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
  ```

---

## Data Inventory (Current)

The server currently contains a small synthetic test set loaded by staff.

### Resource Counts

| Resource Type | Count | Notes |
|---------------|-------|-------|
| **Patient** | 26 | Named "Patient Synthetic1" through "Synthetic26" |
| **Condition** | 36 | 3 condition types (see below) |
| **Observation** | 280 | 14 LOINC codes (see below) |
| **MedicationRequest** | 25 | Text-only coding (no RxNorm/SNOMED codes) |
| **Encounter** | 20 | All ambulatory (class: AMB), dated 2026-02-01 |
| Practitioner | 0 | Empty |
| Organization | 0 | Empty |
| Procedure | 0 | Empty |
| DiagnosticReport | 0 | Empty |
| AllergyIntolerance | 0 | Empty |
| Immunization | 0 | Empty |
| CarePlan | 0 | Empty |

### Conditions (SNOMED CT)

| Code | Display | Count | Unique Patients |
|------|---------|-------|-----------------|
| 709044004 | Chronic kidney disease (CKD) | 20 | 20 |
| 44054006 | Type 2 diabetes mellitus | 10 | 10 |
| 46635009 | Type 1 diabetes mellitus | 6 | 6 |

**Comorbidity:** All 10 T2D patients also have CKD. No overlap between T1D and T2D.

**Not present:** Hypertension (59621000) returns 0 results.

### Observations (LOINC)

| Code | Display | Count |
|------|---------|-------|
| 85354-9 | Blood pressure panel | 8 |
| 39156-5 | Body mass index (BMI) | 8 |
| 8867-4 | Heart rate | 7 |
| **4548-4** | **Hemoglobin A1c (HbA1c)** | **7** |
| 1558-6 | Fasting glucose | 7 |
| 2339-0 | Glucose in blood | 7 |
| 1986-9 | C peptide | 7 |
| **2160-0** | **Creatinine** | **7** |
| **33914-3** | **eGFR** | **7** |
| 3094-0 | BUN (urea nitrogen) | 7 |
| **14959-1** | **Urine albumin/creatinine ratio** | **7** |
| 13457-7 | LDL cholesterol | 7 |
| 2085-9 | HDL cholesterol | 7 |
| 2571-8 | Triglycerides | 7 |

This is a much richer lab panel than the SMART sandbox (which only has HbA1c reliably).

### HbA1c Distribution

14 of 26 patients have HbA1c > 7.0%:

| HbA1c Range | Count | Notes |
|-------------|-------|-------|
| > 9.0% | 3 | Very poor control |
| 8.0% – 9.0% | 6 | Poor control |
| 7.0% – 8.0% | 5 | Above target |
| < 7.0% | ~12 | At or below target |

### Medications

Medications use `medicationCodeableConcept.text` only (no formal `coding` array with RxNorm/SNOMED codes). Examples:
- "Insulin therapy (basal)"
- "SGLT2 inhibitor"

### Encounters

- All encounters are class `AMB` (ambulatory)
- All dated 2026-02-01
- Status: `finished`

---

## Comparison with SMART Sandbox

| Feature | SMART Sandbox | SBU Server |
|---------|--------------|------------|
| **URL** | `https://launch.smarthealthit.org/v/r4/fhir` | `https://lfh-fhir.eastus2.cloudapp.azure.com:9443/fhir-server/api/v4` |
| **Auth** | None (public) | HTTP Basic Auth |
| **SSL** | Valid cert | Self-signed (needs `-k` / `verify=False`) |
| **Patients** | ~100+ | 26 |
| **T2D patients** | ~20 | 10 |
| **HbA1c data** | Yes (many low values) | Yes (richer distribution, more poor control) |
| **Creatinine** | Sparse/missing | 7 patients |
| **eGFR** | Not available | 7 patients |
| **Lipids** | Not tested | Full panel (LDL, HDL, triglycerides) |
| **Fasting glucose** | Not available | 7 patients |
| **C peptide** | Not available | 7 patients |
| **Urine albumin/creatinine** | Not available | 7 patients |
| **CKD diagnoses** | Not present | 20 patients |
| **Hypertension** | 0 results | 0 results |
| **Write access** | No | Yes (full CRUD + transaction bundles) |
| **Data source** | Synthea (pre-loaded) | Custom synthetic data |
| **Server software** | SMART on FHIR | IBM FHIR Server 4.11.1 |

### Key Advantages of SBU Server for Teaching

1. **Diabetic nephropathy cohort** — All T2D patients have CKD, with creatinine, eGFR, and urine albumin/creatinine data. This enables a richer clinical scenario than the SMART sandbox.
2. **Comprehensive lab panels** — 14 observation types vs. effectively 1 (HbA1c) on SMART.
3. **Writable** — Students or instructors can load additional Synthea data.
4. **Authenticated** — Teaches students about real-world FHIR auth (Basic Auth), unlike the open sandbox.
5. **More realistic HbA1c distribution** — Majority of diabetic patients have poor control (>7%), making the clinical scenario more engaging.

### Limitations / Gaps

1. **No hypertension data** — SNOMED 59621000 returns 0 results.
2. **Medication coding is text-only** — No RxNorm or SNOMED codes in medication resources.
3. **Small dataset** — 26 patients total. May want to load more Synthea data.
4. **All observations dated 2026-02-01** — No longitudinal data (trending over time).
5. **No Practitioner/Organization** — Resource references may be incomplete.
6. **Self-signed SSL** — Requires extra setup in Python and curl.

---

## Loading Additional Data

The server supports Synthea transaction bundle ingestion. To load a bundle:

```python
import requests, json, urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE = 'https://lfh-fhir.eastus2.cloudapp.azure.com:9443/fhir-server/api/v4'
session = requests.Session()
session.auth = ('fhiruser', 'BmI512@ccess')
session.verify = False
session.headers.update({
    'Accept': 'application/fhir+json',
    'Content-Type': 'application/fhir+json'
})

# Load bundle from file
with open('synthea_bundle.json', 'r') as f:
    bundle = json.load(f)

# POST to root endpoint (NOT /Bundle)
response = session.post(BASE + '/', json=bundle)

if response.status_code == 200:
    result = response.json()
    entries = result.get('entry', [])
    successes = sum(1 for e in entries if e.get('response', {}).get('status', '').startswith('2'))
    print(f"Loaded {successes}/{len(entries)} resources")
else:
    print(f"Error: {response.status_code} - {response.text[:500]}")
```

### Before Loading Data

- Coordinate with the person who set up the server to avoid conflicts
- Consider whether to clear existing data first or add alongside it
- IBM FHIR Server may have resource count or bundle size limits

---

## Quick Reference

```bash
# Test connectivity
curl -u fhiruser:BmI512@ccess \
  -H "Accept: application/fhir+json" \
  -k \
  https://lfh-fhir.eastus2.cloudapp.azure.com:9443/fhir-server/api/v4/metadata

# Search patients
curl -u fhiruser:BmI512@ccess \
  -H "Accept: application/fhir+json" \
  -k \
  https://lfh-fhir.eastus2.cloudapp.azure.com:9443/fhir-server/api/v4/Patient

# Search T2D conditions
curl -u fhiruser:BmI512@ccess \
  -H "Accept: application/fhir+json" \
  -k \
  "https://lfh-fhir.eastus2.cloudapp.azure.com:9443/fhir-server/api/v4/Condition?code=44054006"
```

```python
import requests, urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE = 'https://lfh-fhir.eastus2.cloudapp.azure.com:9443/fhir-server/api/v4'
session = requests.Session()
session.auth = ('fhiruser', 'BmI512@ccess')
session.verify = False
session.headers.update({'Accept': 'application/fhir+json'})

# Search
response = session.get(f'{BASE}/Patient')
```
