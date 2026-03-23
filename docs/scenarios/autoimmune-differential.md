# Autoimmune Differentiation Scenario Design

## Clinical Scenario: "The Undifferentiated Autoimmune Patient"

**Version:** 1.0 (Design Document)
**Date:** 2026-03-23
**Status:** Proposed — requires new synthetic dataset

---

## 1. Clinical Framing

### The Question Students Must Answer

> A patient presents to rheumatology clinic with positive ANA and nonspecific
> autoimmune symptoms (fatigue, joint pain, Raynaud phenomenon). Based on the
> available clinical data, which autoimmune diagnosis best fits this patient's
> presentation? Classify each patient into one of:
>
> 1. **Systemic Lupus Erythematosus (SLE)**
> 2. **Rheumatoid Arthritis (RA)**
> 3. **Primary Sjogren Syndrome (pSS)**
> 4. **Mixed Connective Tissue Disease (MCTD)**
> 5. **Overlap Syndrome / Undifferentiated Connective Tissue Disease (UCTD)**

### Why This Scenario Works for Teaching

The autoimmune differential is genuinely difficult in clinical practice. These
diseases share overlapping features — joint pain, fatigue, positive ANA, elevated
inflammatory markers — yet differ in organ targets, autoantibody profiles, and
treatment implications. No single lab test resolves the differential. A clinician
must integrate serology, organ involvement patterns, hematologic data, and
medication history to reach a working diagnosis.

This directly addresses the weakness in the current diabetes scenario (noted in
`tasks/todo.md` item #3): "C-peptide alone differentiates Type 1 vs Type 2 —
only one tool use needed." In the autoimmune scenario, students MUST query
multiple data types in sequence because:

- ANA is positive in all five categories (it is the entry criterion, not the answer)
- Specific autoantibodies (anti-dsDNA, anti-Smith, anti-CCP, anti-SSA, anti-U1-RNP) narrow the differential but don't resolve it alone
- Organ involvement patterns (nephritis vs. sicca vs. erosive arthritis vs. pulmonary hypertension) provide crucial discriminating information
- Hematologic abnormalities and complement levels add further evidence
- Medication history reveals treatment patterns that confirm clinical reasoning

---

## 2. Diagnostic Criteria References (from PubMed)

The synthetic dataset and classification logic are grounded in current
evidence-based criteria:

### SLE: 2019 EULAR/ACR Classification Criteria
Aringer M, et al. Ann Rheum Dis. 2019;78(9):1151-1159.
[DOI: 10.1136/annrheumdis-2018-214819](https://doi.org/10.1136/annrheumdis-2018-214819) (PMID: 31383717)

Also published in: Arthritis Rheumatol. 2019;71(9):1400-1412.
[DOI: 10.1002/art.40930](https://doi.org/10.1002/art.40930) (PMID: 31385462, PMC: PMC6827566)

**Key features:** Positive ANA (entry criterion) + weighted scoring across 7
clinical domains (constitutional, hematologic, neuropsychiatric, mucocutaneous,
serosal, musculoskeletal, renal) and 3 immunologic domains (antiphospholipid
antibodies, complement, SLE-specific antibodies). Score >= 10 classifies as SLE.
Sensitivity 96.1%, specificity 93.4%.

### RA: 2010 ACR/EULAR Classification Criteria
Kay J, Upchurch KS. Rheumatology (Oxford). 2012;51 Suppl 6:vi5-9.
[DOI: 10.1093/rheumatology/kes279](https://doi.org/10.1093/rheumatology/kes279) (PMID: 23221588)

**Key features:** Four domains — joint involvement (number and size of affected
joints), serology (RF and/or ACPA/anti-CCP), symptom duration (<6 weeks vs >6
weeks), and acute-phase reactants (CRP and/or ESR). Score >= 6 classifies as RA.

### Primary Sjogren Syndrome: 2016 ACR/EULAR Classification Criteria
Shiboski CH, et al. Arthritis Rheumatol. 2017;69(1):35-45.
[DOI: 10.1002/art.39859](https://doi.org/10.1002/art.39859) (PMID: 27785888, PMC: PMC5650478)

Also published in: Ann Rheum Dis. 2017;76(1):9-16.
[DOI: 10.1136/annrheumdis-2016-210571](https://doi.org/10.1136/annrheumdis-2016-210571) (PMID: 27789466)

**Key features:** Five weighted items — anti-SSA/Ro positivity (weight 3), focal
lymphocytic sialadenitis with focus score >= 1 (weight 3), abnormal ocular
staining score >= 5 (weight 1), Schirmer's test <= 5mm/5min (weight 1),
unstimulated salivary flow <= 0.1 mL/min (weight 1). Score >= 4 classifies.
Sensitivity 96%, specificity 95%.

### MCTD: Anti-U1-RNP and Diagnostic Differentiation
Dima A, Jurcut C, Baicus C. Rheumatol Int. 2018;38(7):1169-1178.
[DOI: 10.1007/s00296-018-4059-4](https://doi.org/10.1007/s00296-018-4059-4) (PMID: 29796907)

**Key features:** Anti-U1-RNP mandatory for MCTD diagnosis. However, anti-U1-RNP
is also present in 25-30% of SLE patients (Johns Hopkins, LUMINA cohorts).
Distinguishing features of MCTD: Raynaud phenomenon (near-universal),
sclerodactyly, myositis, pulmonary hypertension, swollen "sausage" fingers.
SLE patients with anti-U1-RNP may show Raynaud and lung involvement but
typically also have anti-dsDNA, complement consumption, and nephritis — features
rare in MCTD.

---

## 3. ICD-10 Diagnosis Codes for the Synthetic Dataset

### Primary Diagnoses (one per patient)

| Code | Description | Use |
|------|-------------|-----|
| **M32.9** | Systemic lupus erythematosus, unspecified | SLE phenotypes |
| **M32.10** | SLE, organ involvement unspecified | Mild/early SLE |
| **M32.14** | Glomerular disease in SLE | SLE with nephritis |
| **M32.12** | Pericarditis in SLE | SLE with serositis |
| **M05.9** | Rheumatoid arthritis with rheumatoid factor, unspecified | Seropositive RA |
| **M06.9** | Rheumatoid arthritis, unspecified | Seronegative RA (used for M06.00 series) |
| **M35.00** | Sjogren syndrome, unspecified | Primary Sjogren |
| **M35.01** | Sjogren syndrome with keratoconjunctivitis | Sjogren with sicca |
| **M35.09** | Sjogren syndrome with other organ involvement | Sjogren extraglandular |
| **M35.1** | Other overlap syndromes | MCTD |
| **M35.9** | Systemic involvement of connective tissue, unspecified | UCTD |

### Secondary / Comorbid Diagnoses

| Code | Description | Conditions |
|------|-------------|------------|
| **I73.00** | Raynaud syndrome without gangrene | SLE, MCTD, SSc overlap |
| **I27.0** | Primary pulmonary hypertension | MCTD, SSc overlap |
| **I27.20** | Pulmonary hypertension, unspecified | MCTD, SLE |
| **J84.9** | Interstitial pulmonary disease, unspecified | MCTD, RA-ILD, SSc |
| **R80.9** | Proteinuria, unspecified | SLE nephritis |
| **D59.10** | Autoimmune hemolytic anemia, unspecified | SLE |
| **D69.6** | Thrombocytopenia, unspecified | SLE |
| **D72.810** | Lymphocytopenia | SLE |
| **L93.0** | Discoid lupus erythematosus | SLE (cutaneous) |
| **L93.1** | Subacute cutaneous lupus erythematosus | SLE (cutaneous) |
| **R21** | Rash and other nonspecific skin eruption | SLE malar rash |
| **K12.30** | Oral mucositis (ulcerative), unspecified | SLE oral ulcers |
| **R68.2** | Dry mouth, unspecified | Sjogren |
| **H04.129** | Dry eye syndrome, unspecified lacrimal gland | Sjogren |
| **H16.229** | Keratoconjunctivitis sicca, not Sjogren's, unspecified | Sicca symptoms (non-SS) |
| **M34.9** | Systemic sclerosis, unspecified | SSc overlap in MCTD |
| **M33.90** | Dermatopolymyositis, unspecified | Myositis in MCTD |
| **I30.9** | Acute pericarditis, unspecified | Serositis (SLE) |
| **L63.8** | Other alopecia areata | SLE alopecia |

---

## 4. Laboratory Panel Specifications (LOINC Codes)

### Autoantibody Panel

| LOINC | Test | Key For | Interpretation |
|-------|------|---------|----------------|
| **5048-4** | ANA by IFA | All (entry criterion) | Positive in all phenotypes; titer and pattern vary |
| **35362-2** | ANA titer | All | >= 1:80 positive; >= 1:320 highly positive |
| **14238-4** | Anti-dsDNA antibody | SLE | Highly specific for SLE; correlates with nephritis activity |
| **30163-9** | Anti-Smith (Sm) antibody | SLE | Very specific for SLE (~30% sensitivity, ~99% specificity) |
| **49175-6** | Anti-U1-RNP antibody | MCTD, SLE overlap | Required for MCTD; present in 25-30% SLE |
| **56718-4** | Anti-SSA/Ro antibody | Sjogren, SLE | Weight 3 in SS criteria; also in ~50% SLE |
| **56719-2** | Anti-SSB/La antibody | Sjogren | More specific for SS than SSA |
| **53027-3** | Anti-CCP (ACPA) antibody | RA | Highly specific for RA (~95% specificity) |
| **11572-5** | Rheumatoid Factor (RF) | RA, Sjogren | Present in RA (~70-80%) and ~60% Sjogren |
| **32131-4** | Anti-centromere antibody | Limited SSc/CREST | Overlap phenotype marker |
| **16122-7** | Anti-Scl-70 (topoisomerase I) | Diffuse SSc | MCTD-SSc overlap |

### Complement Panel

| LOINC | Test | Key For | Interpretation |
|-------|------|---------|----------------|
| **4485-9** | C3 complement | SLE | Low in active SLE; normal in RA, SS, MCTD |
| **4498-2** | C4 complement | SLE | Low in active SLE, especially nephritis |
| **7622-3** | CH50 total complement | SLE | Low in active SLE |

### Hematologic Panel

| LOINC | Test | Key For | Interpretation |
|-------|------|---------|----------------|
| **6690-2** | WBC count | SLE | Leukopenia (<4000) in SLE |
| **731-0** | Lymphocyte count | SLE | Lymphopenia (<1000) in SLE |
| **777-3** | Platelet count | SLE | Thrombocytopenia (<100,000) in SLE |
| **718-7** | Hemoglobin | SLE | Anemia (hemolytic or chronic disease) |
| **4537-7** | Direct antiglobulin test (DAT/Coombs) | SLE | Positive in autoimmune hemolytic anemia |

### Inflammatory Markers

| LOINC | Test | Key For | Interpretation |
|-------|------|---------|----------------|
| **1988-5** | CRP | RA, SLE | Elevated in RA (usually higher); variably elevated in SLE |
| **30341-2** | ESR | RA, SLE | Elevated in active disease |

### Renal Panel

| LOINC | Test | Key For | Interpretation |
|-------|------|---------|----------------|
| **2160-0** | Creatinine, serum | SLE nephritis | Elevated with renal involvement |
| **33914-3** | eGFR | SLE nephritis | Reduced with renal involvement |
| **5804-0** | Protein in urine (qualitative) | SLE nephritis | Proteinuria in lupus nephritis |
| **2889-4** | Protein/creatinine ratio, urine | SLE nephritis | > 0.5 g/day significant |

### Muscle Enzymes

| LOINC | Test | Key For | Interpretation |
|-------|------|---------|----------------|
| **2157-6** | CK (creatine kinase) | MCTD, myositis | Elevated in myositis component of MCTD |
| **14804-3** | LDH | SLE, MCTD | Elevated in hemolysis or myositis |
| **1920-8** | AST | MCTD | Can be elevated with myositis |
| **1742-6** | ALT | MCTD | Helps distinguish hepatic vs. muscle source |

### Sjogren-Specific Functional Tests

| LOINC | Test | Key For | Interpretation |
|-------|------|---------|----------------|
| *Custom* | Schirmer test result (mm/5min) | Sjogren | <= 5 mm scores 1 point in 2016 criteria |
| *Custom* | Unstimulated salivary flow (mL/min) | Sjogren | <= 0.1 mL/min scores 1 point |
| *Custom* | Ocular staining score | Sjogren | >= 5 scores 1 point |
| *Custom* | Lip biopsy focus score | Sjogren | >= 1 focus/4mm^2 scores 3 points |

*Note: Schirmer test, salivary flow, ocular staining, and lip biopsy results
would be represented as FHIR `Observation` resources with custom coding or
SNOMED codes, since standard LOINC panels for these are limited. For the
educational context, using descriptive `code.text` values is acceptable.*

---

## 5. Medication Profiles (RxNorm / FHIR MedicationRequest)

### By Condition

| Condition | Medications | Rationale |
|-----------|-------------|-----------|
| **SLE** | Hydroxychloroquine (HCQ), prednisone, mycophenolate mofetil, belimumab, azathioprine | HCQ is near-universal; mycophenolate/azathioprine for nephritis; belimumab for refractory |
| **RA** | Methotrexate (MTX), hydroxychloroquine, sulfasalazine, leflunomide, adalimumab, etanercept, tofacitinib, rituximab | MTX is first-line DMARD; biologics for inadequate response |
| **Sjogren** | Hydroxychloroquine, pilocarpine, cevimeline, artificial tears, rituximab | HCQ for systemic; secretagogues for sicca; rituximab for severe extraglandular |
| **MCTD** | Hydroxychloroquine, prednisone, methotrexate, nifedipine, bosentan, iloprost | HCQ + steroids for inflammation; calcium channel blockers/endothelin antagonists for Raynaud/PAH |
| **UCTD** | Hydroxychloroquine, NSAIDs, low-dose prednisone | Conservative treatment; HCQ as disease-modifying |

### Key Discriminating Medication Patterns

| Medication | Strong Signal For | Weak/Absent In |
|------------|-------------------|----------------|
| Methotrexate as primary DMARD | RA | SLE (usually not first-line) |
| Mycophenolate mofetil | SLE (nephritis) | RA, SS |
| Anti-TNF biologics (adalimumab, etanercept) | RA | SLE (contraindicated), SS (not standard) |
| Pilocarpine / cevimeline | Sjogren | RA, SLE |
| Bosentan / endothelin receptor antagonists | MCTD with PAH | RA, SS |
| Belimumab | SLE | RA, SS, MCTD |

---

## 6. FHIR Resource Types Required

| Resource | Content | Query Patterns |
|----------|---------|----------------|
| **Patient** | Demographics (age, sex, race/ethnicity) | Entry point; SLE demographics skew female 9:1, onset 15-45 |
| **Condition** | Active diagnoses with ICD-10 codes | Query by condition code to find cohort; query by patient for full problem list |
| **Observation** | Lab results (autoantibodies, CBC, complement, CRP/ESR, renal, CK) | Query by code (LOINC) + patient; most critical resource type |
| **MedicationRequest** | Active and historical medications | Query by patient; medication patterns are discriminating evidence |
| **DiagnosticReport** | Lab report bundles (ANA panel, CBC, CMP) | Groups observations; useful for panel-level queries |
| **Encounter** | Clinic visits with reason codes | Chronology of care; establishes symptom duration |
| **Procedure** | Lip biopsy (Sjogren), joint imaging | Limited use; biopsy results more important as Observations |
| **AllergyIntolerance** | Drug allergies/intolerances | Minor role; methotrexate intolerance could explain alternative DMARD choice |

### Minimum Query Sequence for Accurate Classification

A student acting as the agent would need to:

1. **Get patient demographics** (Patient) — age/sex distribution provides prior probability
2. **Check autoantibody panel** (Observation: ANA, anti-dsDNA, anti-Sm, anti-CCP, anti-SSA, anti-U1-RNP) — narrows from 5 to 2-3 possibilities
3. **Check organ involvement** (Condition: problem list for nephritis, sicca, ILD, PAH, erosive arthritis) — further narrows differential
4. **Check complement and hematology** (Observation: C3, C4, CBC) — SLE signature (low complement, cytopenias) vs. others
5. **Check medications** (MedicationRequest) — confirms diagnosis and reveals treatment response

Steps 2-5 can be done in different orders, but **no single step resolves the
classification**. This is the core pedagogical requirement.

---

## 7. Patient Phenotypes and Distribution

### Target Dataset Size: 200 patients

(Enough for repeated sampling of 5-patient case sets with variety; large enough
for population-level queries in Activity 2.)

### Phenotype Definitions

#### Phenotype A: Classic SLE (n=40, 20%)
- **Demographics:** Female 90%, age 20-45, higher prevalence in Black/Hispanic patients
- **Autoantibodies:** ANA+ (high titer >= 1:320), anti-dsDNA+, anti-Smith+ (40%), anti-SSA+ (50%), RF+ (20%)
- **Complement:** Low C3 and C4
- **Hematology:** Lymphopenia, mild thrombocytopenia, possible hemolytic anemia (DAT+)
- **Organ involvement:** Nephritis (proteinuria, elevated creatinine), oral ulcers, malar rash, arthritis (non-erosive)
- **Medications:** HCQ + mycophenolate + prednisone; some on belimumab
- **Distinguishing features:** Low complement + anti-dsDNA + nephritis is the SLE triad

#### Phenotype B: SLE Without Nephritis (n=20, 10%)
- **Demographics:** Female 85%, age 25-50
- **Autoantibodies:** ANA+, anti-dsDNA+ (lower titer), anti-Smith- or weakly+, anti-SSA+ (40%)
- **Complement:** Mildly low or normal C3/C4
- **Hematology:** Mild lymphopenia, normal platelets
- **Organ involvement:** Arthritis, serositis (pleurisy/pericarditis), alopecia, photosensitive rash; NO nephritis
- **Medications:** HCQ + low-dose prednisone; azathioprine for serositis
- **Why ambiguous:** Without nephritis and with milder serology, could be mistaken for UCTD. But anti-dsDNA and low complement distinguish from other conditions.

#### Phenotype C: Seropositive RA (n=35, 17.5%)
- **Demographics:** Female 70%, age 35-65
- **Autoantibodies:** ANA+ (low titer 1:80-1:160), RF+, anti-CCP+ (high specificity), anti-dsDNA-, anti-SSA-
- **Complement:** Normal C3, C4
- **Hematology:** Normal or mild anemia of chronic disease; elevated platelets (reactive thrombocytosis)
- **Inflammatory markers:** Elevated CRP and ESR (typically higher CRP than SLE)
- **Organ involvement:** Symmetric polyarthritis (small joints), morning stiffness > 60 min, possible rheumatoid nodules, joint erosions on imaging
- **Medications:** MTX (first-line) + HCQ; biologics (adalimumab, etanercept) for inadequate response
- **Distinguishing features:** Anti-CCP + elevated CRP + erosive arthritis + normal complement

#### Phenotype D: Seronegative RA (n=15, 7.5%)
- **Demographics:** Female 65%, age 40-70
- **Autoantibodies:** ANA+ (low titer), RF-, anti-CCP-, anti-dsDNA-, anti-SSA-
- **Complement:** Normal
- **Hematology:** Normal or mild anemia of chronic disease
- **Inflammatory markers:** Elevated CRP and ESR
- **Organ involvement:** Symmetric polyarthritis, joint erosions
- **Medications:** MTX + sulfasalazine; leflunomide; biologics
- **Why ambiguous:** Without RF or anti-CCP, serology is uninformative. Diagnosis rests on clinical pattern (symmetric erosive polyarthritis) + elevated acute phase reactants + medication pattern. Students must recognize that negative autoantibodies plus RA-pattern treatment = seronegative RA.

#### Phenotype E: Primary Sjogren Syndrome (n=30, 15%)
- **Demographics:** Female 90%, age 40-60
- **Autoantibodies:** ANA+ (moderate titer), anti-SSA/Ro+ (defining feature), anti-SSB/La+ (60%), RF+ (60%), anti-dsDNA-, anti-CCP-
- **Complement:** Normal or mildly low (hypergammaglobulinemia may be present)
- **Hematology:** Normal or mild leukopenia
- **Organ involvement:** Keratoconjunctivitis sicca (dry eyes), xerostomia (dry mouth), parotid gland enlargement, Schirmer test <= 5mm, salivary flow <= 0.1 mL/min, positive lip biopsy (focus score >= 1)
- **Medications:** HCQ, pilocarpine or cevimeline, artificial tears
- **Distinguishing features:** anti-SSA+ with sicca syndrome + secretagogue medications

#### Phenotype F: Sjogren with Extraglandular Features (n=10, 5%)
- **Demographics:** Female 85%, age 35-55
- **Autoantibodies:** ANA+, anti-SSA+, anti-SSB+, RF+ (high titer)
- **Complement:** Low C4 (associated with cryoglobulinemia risk)
- **Hematology:** Leukopenia, mild anemia
- **Organ involvement:** Sicca syndrome PLUS: interstitial nephritis (tubular, not glomerular), peripheral neuropathy, purpura/vasculitis, ILD
- **Medications:** HCQ + rituximab + low-dose prednisone
- **Why ambiguous:** Extraglandular Sjogren can mimic SLE (cytopenias, renal involvement, low complement). Key distinctions: tubulo-interstitial (not glomerular) nephropathy, anti-SSA dominant (not anti-dsDNA), no malar rash or serositis.

#### Phenotype G: MCTD Classic (n=20, 10%)
- **Demographics:** Female 80%, age 25-50
- **Autoantibodies:** ANA+ (high titer, speckled pattern), anti-U1-RNP+ (high titer, MANDATORY), anti-dsDNA- or very low, anti-CCP-, anti-Sm-
- **Complement:** Normal
- **Hematology:** Normal or mild leukopenia
- **Organ involvement:** Raynaud phenomenon (>90%), swollen hands/sclerodactyly, inflammatory myositis (elevated CK), esophageal dysmotility, ILD, possible pulmonary hypertension
- **Medications:** HCQ + prednisone + nifedipine (Raynaud); bosentan if PAH
- **Distinguishing features:** High-titer anti-U1-RNP + Raynaud + myositis + swollen hands, WITHOUT anti-dsDNA, WITHOUT nephritis, WITH normal complement

#### Phenotype H: SLE/MCTD Overlap (n=10, 5%)
- **Demographics:** Female 85%, age 25-45
- **Autoantibodies:** ANA+, anti-U1-RNP+, anti-dsDNA+ (low titer), anti-SSA+ (30%)
- **Complement:** Mildly low C3/C4
- **Hematology:** Mild cytopenias
- **Organ involvement:** Raynaud + arthritis + mild proteinuria + photosensitive rash
- **Medications:** HCQ + prednisone + mycophenolate
- **Why ambiguous:** Has features of BOTH SLE (anti-dsDNA, low complement, proteinuria) and MCTD (anti-U1-RNP, Raynaud). These patients genuinely exist in clinical practice. The "correct" answer is Overlap Syndrome, and students should learn that not every patient fits a single box.

#### Phenotype I: UCTD (n=20, 10%)
- **Demographics:** Female 80%, age 20-50
- **Autoantibodies:** ANA+ (moderate titer), single weak autoantibody (e.g., low-titer anti-SSA or borderline anti-dsDNA), no strongly positive specific antibody
- **Complement:** Normal
- **Hematology:** Normal
- **Organ involvement:** Arthralgia (not true arthritis), fatigue, Raynaud (30%), mild photosensitivity
- **Medications:** HCQ alone or NSAIDs + HCQ
- **Why ambiguous:** These patients have nonspecific autoimmune features without enough criteria to classify into any specific disease. Students must recognize when the evidence is INSUFFICIENT for a specific diagnosis — this is a critical clinical skill.

### Distribution Summary

| Phenotype | n | % | Difficulty |
|-----------|---|---|-----------|
| A: Classic SLE | 40 | 20% | Moderate — requires integrating serology + organ damage + complement |
| B: SLE without nephritis | 20 | 10% | Hard — milder presentation, could be UCTD |
| C: Seropositive RA | 35 | 17.5% | Moderate — anti-CCP is specific but students must look for it |
| D: Seronegative RA | 15 | 7.5% | Hard — no serologic shortcut; must reason from clinical pattern |
| E: Primary Sjogren | 30 | 15% | Moderate — anti-SSA + sicca is characteristic |
| F: Sjogren extraglandular | 10 | 5% | Hard — mimics SLE |
| G: MCTD classic | 20 | 10% | Moderate — anti-U1-RNP is necessary but not sufficient |
| H: SLE/MCTD overlap | 10 | 5% | Very hard — genuinely ambiguous |
| I: UCTD | 20 | 10% | Hard — correct answer is "insufficient evidence" |
| **Total** | **200** | **100%** | |

---

## 8. What Makes Cases Ambiguous

### Overlapping Autoantibody Profiles

The core challenge: autoantibodies are shared across conditions in clinically
realistic patterns.

| Antibody | SLE | RA | Sjogren | MCTD | UCTD |
|----------|-----|-----|---------|------|------|
| ANA | 95-100% | 30-40% | 80-90% | 100% | 100% |
| Anti-dsDNA | 60-70% | <5% | <5% | 5-10% | 5-10% |
| Anti-Smith | 25-30% | <1% | <1% | <5% | <1% |
| Anti-CCP | <5% | 60-80% | <5% | <5% | <5% |
| RF | 20-30% | 70-80% | 50-70% | 20-30% | 10% |
| Anti-SSA | 40-60% | <5% | 60-80% | 10-20% | 15-25% |
| Anti-SSB | 15-25% | <1% | 40-60% | <5% | 5-10% |
| Anti-U1-RNP | 25-30% | <5% | <5% | 100% | 5-15% |

### Specific Ambiguity Scenarios Built Into the Dataset

1. **SLE patient with positive anti-SSA (Phenotype A/B):** Could this be Sjogren? Student must check for sicca symptoms, lip biopsy, and look for SLE-specific features (nephritis, anti-dsDNA, low complement) that Sjogren lacks.

2. **SLE patient with positive anti-U1-RNP (Phenotype H):** MCTD or SLE? Student must check for Raynaud/sclerodactyly (MCTD) vs. nephritis/anti-dsDNA (SLE) vs. both (overlap).

3. **Sjogren with extraglandular disease (Phenotype F):** Renal involvement + cytopenias + low complement looks like SLE. But the nephropathy is tubulo-interstitial (not glomerular), anti-SSA dominates over anti-dsDNA, and sicca symptoms are prominent.

4. **Seronegative RA (Phenotype D):** ANA+ with symmetric polyarthritis and no specific autoantibodies. Without anti-CCP and RF, the serology looks like UCTD. Students must rely on clinical pattern + inflammatory markers + medication history.

5. **UCTD (Phenotype I):** The hardest category. Students who are biased toward "finding a diagnosis" will force-classify these into SLE or Sjogren. The correct answer requires recognizing that the cumulative evidence does not meet classification criteria for any specific condition.

### Built-In "Traps" for Single-Query Shortcuts

| If a student queries only... | They will misclassify... |
|------------------------------|--------------------------|
| ANA | Everyone looks the same (all positive) |
| Anti-dsDNA | Miss MCTD, SS, RA, seroneg RA, UCTD |
| Anti-SSA | Confuse SLE (40-60% positive) with Sjogren |
| Anti-U1-RNP | Confuse SLE overlap (25-30% positive) with MCTD |
| RF | Confuse Sjogren (50-70% positive) with RA |
| Medications alone | HCQ is used in SLE, RA, Sjogren, MCTD, and UCTD |
| Conditions/problem list | If it already says "SLE" the task is trivial |

**Critical design decision:** The FHIR Condition resources should code the
*presenting symptoms* (joint pain, rash, dry eyes, Raynaud), NOT the final
autoimmune diagnosis. The final diagnosis is what the student must determine.
An alternative: include the diagnosis as a Condition but require students to
explain the evidence supporting it (simulating a chart review / second opinion
exercise).

---

## 9. Self-Evaluation: Six Design Tests

### Test 1: Single-Query Shortcut Test
**PASS.** No single FHIR query resolves the differential. ANA is universally
positive. Anti-dsDNA is 60-70% sensitive for SLE but leaves 30-40% undetected and
is occasionally positive in MCTD overlap. Anti-CCP is specific for RA but
misses seronegative RA. Anti-SSA is present in both SLE and Sjogren. Anti-U1-RNP
is present in both MCTD and SLE. Students must query at least 3-4 different data
types (autoantibodies, complement, organ involvement, medications) to
reliably classify.

### Test 2: Evidence Type Diversity
**PASS.** The scenario requires:
- Autoantibody panel (Observation — serology)
- Complement levels (Observation — immunology)
- Hematologic values (Observation — CBC)
- Organ involvement / problem list (Condition)
- Medication history (MedicationRequest)
- Demographics (Patient — age/sex for prior probability)

That is 5-6 distinct FHIR resource types / clinical evidence categories.

### Test 3: Ambiguity and Uncertainty
**PASS.** At least 4 of the 9 phenotypes (B, D, F, H, I) are designed to be
genuinely ambiguous. Phenotype H (SLE/MCTD overlap) and Phenotype I (UCTD)
have no single correct answer in real clinical practice. This teaches students
that diagnostic uncertainty is a feature of medicine, not a failure of data
collection.

### Test 4: Clinical Plausibility
**PASS.** The diagnostic criteria are derived directly from published ACR/EULAR
classification criteria (2019 SLE, 2010 RA, 2016 Sjogren). The phenotype
distributions roughly reflect real-world referral patterns to a rheumatology
clinic. The autoantibody overlap frequencies match published prevalence data.
The medication patterns follow current treatment guidelines.

### Test 5: Data Availability
**PASS (with caveats).** All required data can be represented in standard FHIR
resources. The autoantibody results, complement levels, and hematologic data map
to standard LOINC codes. Sjogren-specific functional tests (Schirmer, salivary
flow, lip biopsy) will require custom observation codes, which is acceptable for
a synthetic educational dataset. The key question for implementation is whether
200 patients with well-structured phenotype data can be generated efficiently
using Synthea or a custom generator.

### Test 6: Difficulty Calibration
**PASS.** The difficulty range spans:
- **Moderate:** Classic SLE (40 patients), seropositive RA (35 patients), classic
  Sjogren (30 patients) — these reward systematic evidence gathering but have
  clear distinguishing features.
- **Hard:** SLE without nephritis (20), seronegative RA (15), extraglandular
  Sjogren (10), UCTD (20) — these require more nuanced reasoning and
  multiple evidence types.
- **Very hard:** SLE/MCTD overlap (10) — genuinely ambiguous, teaches diagnostic
  humility.

For BMI 512 students (informatics trainees, many with clinical backgrounds),
this range is appropriate. The moderate cases teach the systematic approach; the
hard cases reward it; the very hard cases teach that medicine has genuine
uncertainty.

---

## 10. Implementation Considerations

### Dataset Generation Options

1. **Custom Python generator** (recommended): Build a generator script similar to
   the existing diabetes dataset generator. Define phenotype templates with
   randomized variation within clinically realistic ranges. Populate FHIR Bundle
   resources and load to the FHIR server.

2. **Synthea with custom modules**: Synthea supports custom disease modules in
   JSON. An autoimmune module could be written, but the autoantibody and
   complement logic is complex enough that a custom generator may be simpler.

3. **Manual curation + augmentation**: Create 20-30 representative cases manually,
   then programmatically vary lab values and demographics to reach 200.

### FHIR Server Considerations

- The current server has only diabetes patients. Options:
  - **Separate tenant/endpoint** for the autoimmune dataset
  - **Add to existing server** with a distinguishing tag/identifier
  - **New server instance** dedicated to this scenario
- Recommend a separate endpoint or tag to avoid mixing populations

### Notebook Adaptation

The "You Are the Agent" notebook structure carries over directly:
- **Activity 1:** Student manually queries FHIR data to classify patients
  - Available tools: search by condition, get labs, get medications, get demographics
  - 5 patients sampled from the 200, stratified across difficulty levels
- **Activity 2:** Student writes prompts for an AI agent that classifies patients
  - Agent has same FHIR tools
  - Scored on classification accuracy across a larger sample

### Classification Scoring

For the "correct answer" in Activity 2 (AI agent scoring):

| Classification | Acceptable Answers |
|----------------|-------------------|
| Phenotypes A, B | SLE |
| Phenotype C | RA (seropositive) |
| Phenotype D | RA (seronegative) |
| Phenotypes E, F | Sjogren Syndrome |
| Phenotype G | MCTD |
| Phenotype H | Overlap Syndrome OR SLE OR MCTD (all acceptable) |
| Phenotype I | UCTD or "Insufficient evidence for specific diagnosis" |

---

## 11. Comparison to Current Diabetes Scenario

| Dimension | Diabetes (Current) | Autoimmune (Proposed) |
|-----------|-------------------|----------------------|
| Queries to classify | 1 (C-peptide) | 3-5 minimum |
| Evidence types needed | 1 (lab) | 5-6 (serology, complement, CBC, conditions, meds, demographics) |
| Number of categories | 3 (T1D, T2D, No DM) | 5 (SLE, RA, SS, MCTD, UCTD) |
| Ambiguous cases | None (C-peptide is deterministic) | 35% of cases have genuine ambiguity |
| Clinical reasoning depth | Shallow | Deep — requires integrating conflicting evidence |
| Pedagogical fit | Too easy for agent loop | Ideal for iterative observe-decide-act |

---

## 12. Open Questions for Joel

1. **Final diagnosis in Condition list?** Should the FHIR Condition resource
   include the definitive autoimmune diagnosis (making it a chart review exercise)
   or only presenting symptoms (making it a true diagnostic exercise)? The latter
   is harder but more pedagogically valuable.

2. **Dataset generation approach?** Custom Python generator vs. Synthea custom
   module vs. hybrid?

3. **Server deployment?** Separate FHIR endpoint, new tenant on existing server,
   or tagged resources on the current server?

4. **Phenotype mix for Activity 1?** Should each 5-patient case set include one
   from each of the 5 diagnostic categories, or should it be randomized
   (possibly giving a student 2 SLE patients and 0 RA)?

5. **Scoring for ambiguous cases?** How should Activity 2 scoring handle
   Phenotype H (overlap) and Phenotype I (UCTD)? Accept multiple answers?
   Award partial credit?

6. **Sjogren functional tests?** The Schirmer test, salivary flow rate, and lip
   biopsy results are nonstandard in FHIR. Should we include them (more realistic)
   or simplify to just anti-SSA + sicca symptom documentation (easier to generate)?

---

## References

All diagnostic criteria referenced in this document were retrieved from PubMed:

1. Aringer M, et al. 2019 EULAR/ACR classification criteria for SLE. Ann Rheum
   Dis. 2019;78(9):1151-1159. [DOI: 10.1136/annrheumdis-2018-214819](https://doi.org/10.1136/annrheumdis-2018-214819)

2. Aringer M, et al. 2019 EULAR/ACR Classification Criteria for SLE. Arthritis
   Rheumatol. 2019;71(9):1400-1412. [DOI: 10.1002/art.40930](https://doi.org/10.1002/art.40930)

3. Kay J, Upchurch KS. ACR/EULAR 2010 rheumatoid arthritis classification
   criteria. Rheumatology (Oxford). 2012;51 Suppl 6:vi5-9.
   [DOI: 10.1093/rheumatology/kes279](https://doi.org/10.1093/rheumatology/kes279)

4. Shiboski CH, et al. 2016 ACR/EULAR Classification Criteria for Primary
   Sjogren's Syndrome. Arthritis Rheumatol. 2017;69(1):35-45.
   [DOI: 10.1002/art.39859](https://doi.org/10.1002/art.39859)

5. Shiboski CH, et al. 2016 ACR/EULAR classification criteria for primary
   Sjogren's syndrome. Ann Rheum Dis. 2017;76(1):9-16.
   [DOI: 10.1136/annrheumdis-2016-210571](https://doi.org/10.1136/annrheumdis-2016-210571)

6. Dima A, Jurcut C, Baicus C. The impact of anti-U1-RNP positivity: SLE versus
   MCTD. Rheumatol Int. 2018;38(7):1169-1178.
   [DOI: 10.1007/s00296-018-4059-4](https://doi.org/10.1007/s00296-018-4059-4)
