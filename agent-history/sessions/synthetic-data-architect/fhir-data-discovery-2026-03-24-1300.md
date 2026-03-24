# Session: FHIR Server Data Discovery

- **Date:** 2026-03-24
- **Task:** Verify what clinical data exists on the current FHIR server for each phenotype
- **Status:** Complete

## Key Findings

### Condition Counts
- T1D: 249 patients
- T2D: 630 patients
- CKD: 1,015 patients (nearly universal!)
- No diabetes: 148 patients (non-DM controls exist!)
- No T1D+T2D overlap (clean separation)
- T1D+CKD: 249 (100% of T1D have CKD)
- T2D+CKD: 629 (99.8% of T2D have CKD)

### Lab Availability (ALL labs present for ALL groups)

| Lab | T1D Range | T1D Median | T2D Range | T2D Median | No-DM Range |
|-----|-----------|-----------|-----------|-----------|-------------|
| HbA1c | 6.8-9.6 | 7.9 | 6.2-9.0 | 7.1 | 5.46-6.15 |
| C-peptide | 0.03-0.27 | 0.15 | 1.62-5.23 | 2.85 | 3.0-5.39 |
| BMI | 22.3-30.8 | 25.4 | 27.0-38.4 | 31.3 | 27.4-31.6 |
| Creatinine | 0.85-1.95 | 1.16 | 0.64-2.14 | 1.14 | 0.93-1.05 |
| eGFR | 46.6-96.0 | 82.5 | 29.3-99.2 | 80.0 | 89.8-93.8 |
| UACR | 65-395 | 79.5 | 21-441 | 25.0 | 15-18 |

### Medication Patterns
- T1D: 100% on insulin (60% pump, 40% basal-bolus)
- T2D: Mixed — metformin (70%), SGLT2i (60%), insulin basal (40%), GLP-1 RA (10%)
- No-DM: No diabetes medications

### Critical Insight: CKD Is Universal

CKD is coded for 1,015/1,027 patients. This means CKD presence alone is NOT a
useful discriminator for phenotype grouping. Instead, CKD SEVERITY (eGFR level)
is the discriminator:
- eGFR > 60: CKD stage 1-2 (mild/early)
- eGFR 30-60: CKD stage 3 (moderate)
- eGFR < 30: CKD stage 4 (severe)

### Phenotype Identification Rules

Given the actual data, here's how to identify patient complexity from FHIR:

**Rule 1: Diabetes Type**
- Has T1D condition → Type 1
- Has T2D condition → Type 2
- No T1D/T2D condition → No diabetes

**Rule 2: Glycemic Control**
- HbA1c ≤ 7.0 → Well-controlled
- HbA1c 7.0-7.5 → Borderline
- HbA1c > 7.5 → Poor control
- HbA1c > 9.0 → Very poor control

**Rule 3: Kidney Function (from eGFR)**
- eGFR ≥ 60 → Preserved kidney function
- eGFR 45-59 → Mild-moderate CKD (stage 3a)
- eGFR 30-44 → Moderate-severe CKD (stage 3b)
- eGFR < 30 → Severe CKD (stage 4)

**Rule 4: Medication Complexity**
- No diabetes meds → Diet-controlled or no diabetes
- Oral only (metformin ± SGLT2i) → Simple regimen
- Insulin + orals → Complex regimen
- Insulin only (pump or basal-bolus) → T1D-typical regimen

**Composite Complexity Assessment:**
- **Routine:** Well-controlled (A1c ≤ 7.5) + preserved kidney (eGFR ≥ 60) + simple regimen
- **Moderate:** ONE of: poor control (A1c > 7.5), mild CKD (eGFR 45-59), complex regimen
- **High:** TWO OR MORE of: poor control, moderate+ CKD (eGFR < 45), complex regimen + UACR > 300

### Candidate Pool Stratification Strategy

1. Query T1D conditions → get T1D patient IDs
2. Query T2D conditions → get T2D patient IDs
3. From each group, sample and check HbA1c to find:
   - Well-controlled (A1c ≤ 7.0)
   - Poorly controlled (A1c > 7.5)
4. Check eGFR to find:
   - Preserved function (eGFR ≥ 60)
   - Impaired function (eGFR < 60)
5. Include 1-2 non-diabetes patients (from the 148 without DM conditions)
6. Select 6-8 patients ensuring diversity across:
   - At least 1 T1D, 1 T2D
   - At least 1 well-controlled, 1 poorly controlled
   - At least 1 with eGFR < 60 (clear CKD severity)
   - At least 1 non-diabetes control
   - Mix of medication patterns

### Data Surprises

1. UACR data EXISTS and has real variation (15-441 mg/g) — the Phase 2 UACR
   ambiguity mechanism may actually be partially usable with current data
2. T1D UACR is consistently elevated (median 79.5) vs T2D (median 25.0) —
   this could be a useful teaching signal
3. Non-DM controls DO exist (148 patients) — "No diabetes" category is viable
4. eGFR spread in T2D goes down to 29.3 — some T2D patients have severe CKD
5. CKD being universal means the scenario should use eGFR thresholds for
   kidney severity, not CKD presence/absence
