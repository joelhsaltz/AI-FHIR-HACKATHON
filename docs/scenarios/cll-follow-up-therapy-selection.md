# Scenario: CLL Follow-Up Therapy Selection After Treatment Failure

**Status:** New domain proposal — requires synthetic data creation

**Clinical question:** Given a CLL patient who has progressed or relapsed after
initial therapy, which follow-up treatment strategy is most appropriate based on
the available clinical evidence?

**Classification categories:**
- **BTK inhibitor (continuous)** — e.g., ibrutinib, acalabrutinib, zanubrutinib
- **Venetoclax-based regimen (fixed duration)** — venetoclax + anti-CD20
- **Clinical trial / specialist referral** — high-risk features or multiply relapsed
- **Uncertain — needs more data** — insufficient evidence to recommend

---

## Clinical Grounding

### Domain Summary

Chronic lymphocytic leukemia (CLL) is the most common adult leukemia in Western
countries. Treatment has shifted from chemoimmunotherapy to targeted agents:
Bruton tyrosine kinase (BTK) inhibitors and BCL2 inhibitors (venetoclax). After
first-line treatment failure, therapy selection depends on what the patient
received initially, why they failed (progression vs. intolerance), their
molecular risk profile, comorbidities, and organ function.

Based on articles retrieved from PubMed:

- The **NCCN CLL/SLL Guidelines v2.2024** (Wierda et al., JNCCN 2024;
  [DOI](https://doi.org/10.6004/jnccn.2024.0018)) state that treatment
  selection is based on disease stage, del(17p)/TP53 mutation status, IGHV
  mutation status, patient age, performance status, comorbidities, and the
  prior agent's toxicity profile.

- A **Lancet review** (Jain et al., Lancet 2024;
  [DOI](https://doi.org/10.1016/S0140-6736(24)00595-6)) confirms that BTK
  inhibitors, BCL2 inhibitors, and CD20 monoclonal antibodies are established
  therapy options in both frontline and relapsed/refractory CLL, with
  non-covalent BTK inhibitors and CAR-T emerging for multiply relapsed disease.

- **Prognostication in CLL** (Moia & Gaidano, Semin Hematol 2024;
  [DOI](https://doi.org/10.1053/j.seminhematol.2024.02.002)) establishes that
  TP53 disruptions identify high-risk patients who benefit most from continuous
  BTKi therapy, while IGHV-mutated patients without TP53 disruption benefit
  most from fixed-duration venetoclax-obinutuzumab.

- **Approaches for relapsed CLL** (Roeker & Mato, ASH Education Program 2020;
  [DOI](https://doi.org/10.1182/hematology.2020000168)) provides the
  sequencing logic: after BTKi progression, venetoclax-based regimens are
  preferred; after venetoclax progression, BTKi is preferred; after BTKi
  intolerance, either venetoclax or alternative BTKi is reasonable.

- **Precision diagnostics in CLL** (Mollstedt et al., Front Oncol 2023;
  [DOI](https://doi.org/10.3389/fonc.2023.1146486)) describes the FISH-based
  cytogenetic panel (del(11q), del(13q), del(17p), trisomy 12) and IGHV/TP53
  mutational status as the foundation for risk stratification.

### Why This Scenario Works for Teaching

The CLL follow-up therapy decision is a genuine multi-factor clinical reasoning
problem. No single data point determines the answer:

1. **Prior therapy matters** — the sequencing logic is "switch mechanism of
   action." But you need to know WHAT the patient already received.
2. **Molecular risk matters** — del(17p)/TP53 mutation changes the
   recommendation regardless of prior therapy.
3. **Reason for failure matters** — progression (disease resistant) vs.
   intolerance (side effects) leads to different strategies.
4. **Comorbidities matter** — cardiac history (atrial fibrillation) is a
   relative contraindication to ibrutinib; renal impairment affects venetoclax
   tumor lysis syndrome risk.
5. **Lab values matter** — absolute lymphocyte count trends, beta-2
   microglobulin, LDH indicate disease burden and tempo.

A student cannot solve this with one query. They must gather prior therapy,
molecular markers, comorbidities, lab trends, and reason across all of them.

---

## Required Evidence Types

| # | Data Type | FHIR Resource | Why It Is Needed |
|---|-----------|---------------|------------------|
| 1 | **CLL diagnosis and status** | Condition | Confirm CLL diagnosis, check if in relapse vs. remission vs. not in remission. Needed to establish the clinical question applies. |
| 2 | **Prior therapy history** | MedicationRequest / MedicationAdministration | What drug class the patient received first-line (BTKi, venetoclax, chemoimmunotherapy). Critical for sequencing logic. |
| 3 | **Reason for treatment discontinuation** | Condition / AdverseEvent / Observation (clinical notes proxy) | Did the patient progress on therapy (resistance) or stop due to intolerance (side effects)? Changes the recommendation. |
| 4 | **Molecular markers: TP53/del(17p)** | DiagnosticReport / Observation | TP53 mutation or del(17p) by FISH. High-risk marker that steers toward continuous BTKi or clinical trial. |
| 5 | **Molecular markers: IGHV mutation status** | DiagnosticReport / Observation | Mutated vs. unmutated IGHV. Unmutated = worse prognosis, may influence duration of therapy. |
| 6 | **FISH cytogenetics panel** | DiagnosticReport / Observation | del(11q), del(13q), trisomy 12 — additional risk stratification beyond TP53. |
| 7 | **Comorbidities** | Condition | Atrial fibrillation (relative contraindication to ibrutinib), renal impairment (venetoclax TLS risk), bleeding history. |
| 8 | **Lab values: disease burden** | Observation | Absolute lymphocyte count (ALC), beta-2 microglobulin (B2M), LDH — indicate disease tempo and tumor lysis risk. |
| 9 | **Lab values: organ function** | Observation | Creatinine/eGFR (renal function for venetoclax dosing/TLS), liver function tests. |
| 10 | **Demographics** | Patient | Age, performance status proxy. Older/frailer patients may not tolerate certain regimens. |

---

## Minimum Queries to Classify Correctly

**4-6 queries per patient**, depending on complexity:

1. **Condition query** — Confirm CLL diagnosis and status (relapse/remission/active)
2. **MedicationRequest query** — Identify prior therapy (BTKi? venetoclax? chemo?)
3. **Molecular markers query** — TP53/del(17p) and IGHV status
4. **Comorbidity query** — Cardiac history, renal disease, bleeding disorders
5. **Lab values query** — ALC, B2M, creatinine/eGFR (disease burden + organ function)
6. **Demographics query** — Age, for context on tolerability

No single query is sufficient. The key reasoning chain is:

> Prior therapy class + reason for failure --> candidate switch strategy
> --> modified by TP53/IGHV risk --> modified by comorbidity contraindications
> --> modified by organ function/TLS risk --> final recommendation

---

## Where Ambiguity Lives

### Clear cases (build confidence, ~40% of cohort)

- **Patient on first-line ibrutinib who progressed, no TP53 mutation, no cardiac
  history, good renal function** --> Venetoclax-based regimen (textbook switch)
- **Patient on first-line venetoclax-obinutuzumab who relapsed 2 years after
  completing fixed-duration therapy, IGHV unmutated, no contraindications** -->
  BTK inhibitor (textbook switch)

### Ambiguous cases (teach reasoning, ~40% of cohort)

- **Patient on ibrutinib who stopped due to atrial fibrillation (intolerance),
  now with rising ALC** — Do they get venetoclax, or a different BTKi
  (acalabrutinib has less cardiac toxicity)? Requires weighing intolerance type
  against alternative BTKi data.
- **Patient with del(17p) who progressed on first-line venetoclax** — High-risk
  molecular profile plus prior venetoclax failure. BTKi is reasonable but
  prognosis is poor. Clinical trial referral may be appropriate.
- **Elderly patient (age 82) with CKD stage 3 who relapsed after
  chemoimmunotherapy** — BTKi is preferred over chemoimmunotherapy rechallenge,
  but which BTKi? Venetoclax is an option but TLS risk is elevated with renal
  impairment. Multiple reasonable answers.
- **Patient who progressed on ibrutinib with borderline cardiac history
  (occasional palpitations, no documented AF)** — Venetoclax is the default
  switch, but is the cardiac history significant enough to also avoid other
  BTKi? Requires judgment.

### Hard cases (stretch, ~20% of cohort)

- **Multiply relapsed patient (failed both BTKi and venetoclax)** — Limited
  standard options. Clinical trial, pirtobrutinib (non-covalent BTKi), or
  CAR-T consideration. Students should recognize the limits of standard
  algorithms.
- **Patient with possible Richter transformation (rapidly rising LDH, growing
  lymph nodes, worsening symptoms on BTKi)** — This is NOT just CLL relapse.
  Needs biopsy, different management. Students should recognize the red flags
  and classify as "specialist referral."

---

## ICD-10 Codes for the Scenario

### CLL Diagnosis Codes (ICD-10-CM)

| Code | Description | Use |
|------|-------------|-----|
| C91.10 | CLL of B-cell type, not having achieved remission | Active CLL, not yet responded |
| C91.11 | CLL of B-cell type, in remission | Post-treatment remission |
| C91.12 | CLL of B-cell type, in relapse | Relapsed after prior response |

### Comorbidity Codes

| Code | Description | Clinical Relevance |
|------|-------------|-------------------|
| I48.0 | Paroxysmal atrial fibrillation | Relative contraindication to ibrutinib |
| I48.19 | Other persistent atrial fibrillation | Stronger contraindication to ibrutinib |
| I48.21 | Permanent atrial fibrillation | Strong contraindication to ibrutinib |
| N18.3 | Chronic kidney disease, stage 3 | Elevated TLS risk with venetoclax |
| N18.4 | Chronic kidney disease, stage 4 | Higher TLS risk, dose adjustments needed |
| E88.3 | Tumor lysis syndrome | History of prior TLS episode |
| D69.6 | Thrombocytopenia, unspecified | Bleeding risk consideration |

### History / Status Codes

| Code | Description | Use |
|------|-------------|-----|
| Z85.6 | Personal history of leukemia | Prior treatment context |
| Z92.21 | Personal history of antineoplastic chemotherapy | Prior chemoimmunotherapy |

---

## FHIR Resource Mapping

### FHIR Query Menu (What Students Would Choose From)

| Menu Label | FHIR Query | Returns |
|------------|-----------|---------|
| Look up CLL diagnosis | `GET /Condition?subject=Patient/{id}&code=C91.10,C91.11,C91.12` | CLL status: active/remission/relapse |
| Check other diagnoses | `GET /Condition?subject=Patient/{id}&_count=20` | Comorbidities (AF, CKD, etc.) |
| Review prior medications | `GET /MedicationRequest?subject=Patient/{id}&_count=20&_sort=-date` | Treatment history: drug names, dates, status |
| Get molecular markers | `GET /Observation?subject=Patient/{id}&code={TP53_LOINC,IGHV_LOINC,FISH_LOINC}` | Risk stratification results |
| Check recent labs | `GET /Observation?subject=Patient/{id}&code={ALC,B2M,LDH,creatinine}&_sort=-date` | Disease burden + organ function |
| View demographics | `GET /Patient/{id}` | Age, gender |
| Check encounter history | `GET /Encounter?subject=Patient/{id}&_count=10&_sort=-date` | Care frequency, recent visits |

### LOINC Codes Needed

| LOINC Code | Description | Clinical Use |
|------------|-------------|-------------|
| 26474-7 | Lymphocytes [#/volume] in Blood | Absolute lymphocyte count (disease burden) |
| 1952-1 | Beta-2 microglobulin (serum) | Prognostic marker, disease burden |
| 2532-0 | LDH (serum) | Disease tempo, Richter transformation signal |
| 2160-0 | Creatinine (serum) | Renal function (TLS risk) |
| 33914-3 | eGFR | Renal function staging |
| 21440-3 | TP53 gene mutation analysis | High-risk molecular marker |
| 62210-8 | IGHV mutation status | Prognostic/predictive molecular marker |

Note: FISH cytogenetics (del(17p), del(11q), del(13q), trisomy 12) would
typically be represented as DiagnosticReport resources with coded results.
LOINC codes exist for individual FISH probes but may need custom mapping.

---

## Potential Shortcuts to Block

| Shortcut | Why It Trivializes | How to Block |
|----------|-------------------|-------------|
| TP53 alone determines everything | TP53+ is high-risk but still needs prior therapy and comorbidity context | Include TP53-negative patients where the decision is still complex (intolerance vs. progression, comorbidity contraindications) |
| Prior drug class alone | Knowing "was on ibrutinib" narrows to venetoclax, but comorbidities and molecular markers still matter | Include cases where the obvious switch is contraindicated (e.g., venetoclax switch but severe CKD) |
| One lab value (e.g., ALC) | ALC shows disease burden but does not determine therapy class | ALC is supplementary context, never the sole discriminator |
| Age alone | Older patients may be frailer but age does not determine drug class | Include fit elderly patients and younger patients with comorbidities |

---

## Difficulty Assessment

**Medium-Hard** for the target audience (BMI 512 clinical informatics trainees).

- **Clinical reasoning:** Most students are clinicians or clinically trained and
  will recognize the names of drug classes, understand what "relapsed" means,
  and appreciate why cardiac history matters for drug selection. The CLL-specific
  molecular markers (TP53, IGHV) will be less familiar but are explained in the
  scenario context.
- **Query strategy:** Requires 4-6 queries per patient across multiple resource
  types. No single query solves the problem.
- **Ambiguity:** ~40% of cases have genuinely debatable answers, teaching
  evidence synthesis rather than lookup.
- **New domain challenge:** Students have not worked with oncology data in prior
  sessions (which focus on diabetes). This tests whether the "You Are the Agent"
  pedagogy transfers to an unfamiliar clinical domain.

This is appropriate for a **Session 3 / capstone activity** where students have
already built agent intuition in the diabetes domain and are ready to apply those
skills to a new problem.

---

## Six-Test Self-Evaluation

### 1. Single-Query Shortcut Test: PASS

No single query resolves the classification. Prior therapy narrows the options
but does not determine the answer without molecular risk, comorbidities, and
reason for failure. TP53 is important but insufficient alone (still need prior
therapy and comorbidity context). This is a genuine multi-query problem.

### 2. Evidence Type Diversity: PASS

Requires at minimum: Conditions (diagnosis + comorbidities), MedicationRequests
(prior therapy), Observations (molecular markers + labs), and Patient
(demographics). Four distinct FHIR resource types, each revealing different
aspects of the decision.

### 3. Ambiguity and Uncertainty: PASS

~40% of cases are designed to be genuinely ambiguous: intolerance cases where
alternative BTKi vs. mechanism switch is debatable; high-risk patients where
clinical trial vs. standard therapy is judgment-dependent; patients with
comorbidity contraindications that complicate the default sequencing logic.
Clear cases (~40%) build confidence first.

### 4. Clinical Plausibility: PASS

This mirrors real-world tumor board and hematology clinic workflow. A
hematologist evaluating a relapsed CLL patient would look at exactly these data
types in exactly this order: confirm diagnosis and relapse status, review prior
therapy, check molecular risk, assess comorbidities, review labs for disease
burden and organ function. The NCCN guidelines explicitly describe this
decision framework (Wierda et al., JNCCN 2024;
[DOI](https://doi.org/10.6004/jnccn.2024.0018)).

### 5. Data Availability: CONDITIONAL PASS — Requires Synthetic Data Creation

This domain does NOT exist in the current FHIR dataset (which contains only
diabetes and CKD patients). All CLL patient data would need to be synthetically
generated and loaded into the FHIR server. See Data Requirements Specification
below.

### 6. Difficulty Calibration: PASS

The clinical concepts (drug class switching, molecular risk, comorbidity
contraindications) are accessible to clinically trained informatics students.
The oncology-specific details (TP53, IGHV, FISH panel) are less familiar but
are the "clinical content to learn," not prerequisites. The menu-driven
interface means students never need to construct queries — they choose from a
list and interpret results. The difficulty is in the reasoning, not the
mechanics.

---

## Data Requirements Specification

### Overview

A synthetic CLL cohort must be created and loaded into the FHIR server. The
cohort must support the six-phenotype structure below, with enough patients to
provide 8-12 candidates per student session (mix of clear and ambiguous cases).

### Target Population: 60-80 Synthetic CLL Patients

### Phenotype Definitions

| # | Phenotype | Count | Prior Therapy | TP53/del(17p) | IGHV | Key Comorbidities | Expected Classification |
|---|-----------|-------|--------------|---------------|------|-------------------|------------------------|
| 1 | Clear BTKi-to-venetoclax switch | 12-15 | Ibrutinib (progressed) | Negative | Either | None significant | Venetoclax-based regimen |
| 2 | Clear venetoclax-to-BTKi switch | 12-15 | Venetoclax-obinutuzumab (relapsed post-completion) | Negative | Unmutated | None significant | BTK inhibitor |
| 3 | BTKi intolerance (cardiac) | 8-10 | Ibrutinib (stopped — AF) | Either | Either | Atrial fibrillation | Ambiguous: venetoclax vs. alternative BTKi |
| 4 | High-risk molecular (TP53+) | 8-10 | Any (progressed) | Positive | Unmutated | Varies | BTKi continuous or clinical trial |
| 5 | Comorbidity-complicated | 8-10 | Any | Either | Either | CKD stage 3-4, bleeding history | Ambiguous: standard switch complicated by organ dysfunction |
| 6 | Multiply relapsed / Richter concern | 5-8 | Failed both BTKi AND venetoclax | Either | Usually unmutated | Varies | Clinical trial / specialist referral |

### Required FHIR Resources Per Patient

#### Patient Resource
```
- name, birthDate, gender, address
- Age range: 55-85 (CLL is a disease of older adults)
- Gender: slight male predominance (realistic)
```

#### Condition Resources (per patient: 2-5)
```
- CLL diagnosis: C91.10, C91.11, or C91.12 (with appropriate clinicalStatus)
- Comorbidities as assigned by phenotype:
  - Atrial fibrillation: I48.0, I48.19, I48.21
  - CKD: N18.3, N18.4
  - History of tumor lysis syndrome: E88.3
  - Thrombocytopenia: D69.6
  - Hypertension: I10 (common background comorbidity)
- onsetDateTime should be clinically plausible (CLL diagnosis 2-10 years ago)
```

#### MedicationRequest Resources (per patient: 2-6)
```
First-line therapy (completed or stopped):
- Ibrutinib 420mg daily (RxNorm: 1599803)
- Acalabrutinib 100mg BID (RxNorm: 2049106)
- Venetoclax (various doses, RxNorm: 1876120)
- Obinutuzumab (RxNorm: 1657989)
- Fludarabine/cyclophosphamide/rituximab (FCR — for chemo-exposed phenotype)

Status values:
- "stopped" — for discontinued therapies
- "completed" — for fixed-duration regimens that ran to completion
- "active" — should NOT appear for first-line (they have all failed/completed)

authoredOn dates should tell a coherent story:
- First-line therapy started 1-5 years ago
- Treatment duration appropriate for the drug (BTKi: months-years continuous;
  venetoclax-obinutuzumab: ~12 months fixed duration; FCR: 6 cycles)
```

#### Observation Resources — Molecular Markers (per patient: 2-4)
```
TP53 mutation analysis:
- LOINC 21440-3
- valueCodeableConcept: "Detected" or "Not detected"
- effectiveDateTime: at or before first treatment

IGHV mutation status:
- LOINC 62210-8
- valueCodeableConcept: "Mutated" (<2% deviation) or "Unmutated" (>=2% deviation)
- effectiveDateTime: at diagnosis

FISH cytogenetics (as individual Observations or one DiagnosticReport):
- del(17p): detected/not detected
- del(11q): detected/not detected
- del(13q): detected/not detected (favorable, most common)
- Trisomy 12: detected/not detected
```

#### Observation Resources — Lab Values (per patient: 3-8 over time)
```
Absolute lymphocyte count (LOINC 26474-7):
- Multiple values over time to show trend (rising = progression)
- Units: 10*3/uL
- Range: 5-300 (wide range in CLL)

Beta-2 microglobulin (LOINC 1952-1):
- Value at relapse assessment
- Units: mg/L
- Elevated (>3.5 mg/L) = worse prognosis

LDH (LOINC 2532-0):
- Value at relapse assessment
- Units: U/L
- Markedly elevated = Richter transformation concern

Creatinine (LOINC 2160-0):
- Recent value
- Units: mg/dL
- Elevated in CKD phenotype patients

eGFR (LOINC 33914-3):
- Recent value
- Units: mL/min/1.73m2
- <60 = CKD stage 3+, affects venetoclax TLS risk
```

#### Encounter Resources (per patient: 3-10)
```
- Ambulatory hematology visits over time
- class: AMB
- Recent encounters show the patient is actively being followed
- Gap in encounters may indicate lost to follow-up (educational discussion point)
```

### Data Quality Requirements

1. **Temporal coherence:** Dates must tell a consistent clinical story.
   Diagnosis before first treatment. First treatment before relapse. Molecular
   markers obtained before or at first treatment. Labs trend appropriately
   (ALC rising before relapse is documented).

2. **Clinical plausibility:** No impossible combinations. TP53+ patients should
   not have IGHV mutated status AND del(13q) only (this would be contradictory
   risk). Ibrutinib-intolerant patients should have AF onset during or after
   ibrutinib start.

3. **Ambiguity by design:** Some patients should have missing data (e.g.,
   IGHV status not performed — forces reasoning without it). Some should have
   borderline values (e.g., B2M at 3.5, the prognostic cutoff). Some should
   have conflicting signals (e.g., favorable cytogenetics but TP53+).

4. **Phenotype balance:** The candidate selection algorithm should present a
   mix of clear and ambiguous cases per student session, not all from one
   phenotype.

### Loading Strategy

Synthetic patients would be created as FHIR Bundle resources (type: transaction)
and POSTed to the FHIR server. A Python generator script (analogous to the
existing synthetic diabetes data loader) would:

1. Define phenotype templates with value ranges
2. Generate N patients per phenotype with randomized values within ranges
3. Create FHIR-compliant JSON bundles
4. POST to the server endpoint with Basic Auth
5. Validate that all resources are retrievable via the expected queries

---

## Implementation Notes

### Adapting the "You Are the Agent" Framework

This scenario maps directly to the three-layer model:

- **Layer 1 (Human Mode):** Student sees a CLL patient who has relapsed. They
  choose queries from the menu (check prior meds, look up molecular markers,
  review comorbidities, check labs). After gathering evidence, they classify
  into one of the four categories. Immediate feedback explains the guideline-
  based reasoning.

- **Layer 2 (Hybrid Mode):** Student can ask the LLM "What should I look at
  next?" or "What does del(17p) mean for treatment?" The LLM guides without
  giving the answer.

- **Layer 3 (LLM Mode):** Student writes a prompt like "Review this CLL
  patient's data and recommend a follow-up therapy strategy." The agent runs
  autonomously, and the student compares its reasoning chain to their own.

### Feedback Design

For each classification, feedback should explain:
- What the guideline-based recommendation is and why
- Which evidence the student gathered that supports or contradicts their choice
- What evidence they did NOT gather that would have been informative
- For ambiguous cases: "Both X and Y are reasonable here because..."

### Scoring Rubric (for Layer 3 / Agent Mode)

Agent scoring should weight:
- Correct classification (40%)
- Evidence gathered — did the agent check all relevant data types? (30%)
- Reasoning quality — did the agent explain WHY, referencing specific data? (20%)
- Appropriate uncertainty — did the agent flag ambiguous cases as uncertain
  rather than forcing a definitive answer? (10%)
