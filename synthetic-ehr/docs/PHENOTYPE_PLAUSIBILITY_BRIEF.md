# Synthetic EHR Phenotype Plausibility Brief
Date: February 11, 2026

This brief explains why each synthetic phenotype is clinically plausible and how major variables are constrained to be internally consistent. The focus is educational realism (not epidemiologic prevalence matching).

## Core grounding used across all phenotypes
- Diabetes diagnostic ranges and interpretation of A1c/FPG/random glucose are aligned to NIDDK summaries of ADA criteria and testing caveats [1,2].
- HbA1c to glucose consistency uses the ADAG relationship: estimated average glucose (mg/dL) ~= 28.7 x HbA1c - 46.7 [3].
- CKD severity and albuminuria staging follow KDIGO 2024 categories (G stages from eGFR, A stages from UACR) [4].
- Creatinine-eGFR coherence is based on the CKD-EPI 2021 framework (creatinine, age, sex linked to kidney function) [5].
- Metabolic syndrome patterning (high TG, low HDL, elevated BP, elevated glucose with adiposity) follows AHA/NHLBI and harmonized criteria concepts [6,7].
- BP category interpretation uses ACC/AHA 2017 ranges [8].
- C-peptide is used to separate endogenous insulin production patterns in type 1 vs type 2 diabetes [9].

---

## 1) Metabolic Syndrome, No Diabetes, No CKD (`metabolic_syndrome_no_dm_ckd`)

### Clinical narrative
This phenotype represents a high-risk cardiometabolic patient with obesity, elevated blood pressure, hypertriglyceridemia, and borderline dysglycemia, but without overt diabetes and without clinically significant kidney disease. It is realistic for patients who cluster metabolic syndrome features yet remain below formal diabetes thresholds.

### Why the variable pattern is plausible
- Glycemia: HbA1c near the prediabetes zone and fasting glucose near impaired fasting glucose are plausible and intentionally constrained not to enter sustained diabetic ranges [1,2].
- Lipids: high triglycerides with low HDL are core metabolic syndrome features [6,7].
- BP: values generally in elevated/stage 1 to low stage 2 hypertensive range are common in this profile [8].
- Renal panel: eGFR is usually preserved; UACR remains mostly A1 (<30 mg/g), compatible with no CKD complications [4].
- C-peptide: relatively preserved/high endogenous insulin secretion is expected with insulin resistance and absent type 1 diabetes physiology [9].

### Internal relationship logic used in generation
- HbA1c is nudged toward glucose-implied values (ADAG consistency) [3].
- Triglycerides increase with adiposity and glycemic burden; HDL decreases as TG rises (metabolic syndrome pattern) [6,7].
- CKD stage and albuminuria stage are not free-text fields; they are derived from eGFR and UACR, respectively [4].
- Diabetes-none constraint forces duration 0 and diabetes medications/insulin off.

### Teaching value
Useful for showing how patients can have substantial cardiometabolic risk before crossing diabetes thresholds, and why risk-factor clustering matters even when overt diabetes is absent.

---

## 2) Early Type 2 Diabetes, Minimal Kidney Involvement (`early_t2d_no_ckd`)

### Clinical narrative
This phenotype models early established type 2 diabetes with mild-moderate hyperglycemia, obesity/insulin resistance features, and little renal damage. It mirrors outpatient patients who are still relatively early in disease course and commonly managed with metformin-centered therapy.

### Why the variable pattern is plausible
- Glycemia: HbA1c typically above diagnostic diabetes threshold, fasting/random glucose in diabetic range [1,2].
- C-peptide: preserved endogenous secretion is expected in early type 2 diabetes [9].
- Lipid/BP pattern: mixed dyslipidemia and mild hypertension commonly co-travel with insulin resistance [6,7,8].
- Kidney findings: eGFR often normal or mildly reduced; UACR may still be A1, consistent with limited nephropathy burden [4].

### Internal relationship logic used in generation
- Random glucose is constrained to be usually >= fasting glucose.
- HbA1c-glucose coherence enforced via ADAG relationship [3].
- C-peptide floor for type 2 diabetes avoids implausible severe insulinopenia in early disease [9].
- CKD and albuminuria categories are derived, preventing contradictory labels (for example, G1 with low eGFR cannot occur) [4].

### Teaching value
Good for demonstrating transition from prediabetes/metabolic syndrome to overt diabetes while renal markers can remain near-normal, and why early intervention focuses on glycemia and cardiometabolic risk.

---

## 3) Type 2 Diabetes with Obesity and Early Diabetic Kidney Disease (`t2d_obesity_ckd2`)

### Clinical narrative
This phenotype captures a common intermediate-risk presentation: longer-duration type 2 diabetes, obesity, worse glycemic control, and measurable albuminuria with mild-moderate eGFR decline. It is intentionally a bridge state between early T2D and advanced CKD phenotypes.

### Why the variable pattern is plausible
- Glycemia: HbA1c and glucose are higher than early T2D, representing progression or more treatment resistance [1,2].
- Renal injury: UACR in A2 (microalbuminuria range) with G2 kidney function is classic early diabetic kidney disease profile [4].
- BP/lipids: higher BP, high TG, low HDL are congruent with metabolic-renal-cardiovascular comorbidity [6,7,8].
- Medications: metformin and SGLT2 use are plausible in non-advanced CKD; insulin use becomes more mixed [clinical heuristic + guideline-consistent directionality].

### Internal relationship logic used in generation
- UACR is internally linked to spot urine albumin and creatinine.
- Albuminuria stage is derived from UACR cutoff logic (A1/A2/A3), not independently sampled [4].
- Creatinine and BUN are coupled to lower eGFR using deterministic adjustments (kidney chemistry coherence) [5].
- BP is influenced by age, BMI, and CKD burden to keep values physiologically coherent.

### Teaching value
This phenotype is useful for teaching how glycemic burden, obesity, blood pressure, and renal microvascular injury begin to reinforce each other before severe CKD appears.

---

## 4) Long-Duration Type 2 Diabetes with CKD 3b and Macroalbuminuria (`advanced_t2d_ckd3b`)

### Clinical narrative
This phenotype represents high-complexity, non-ESRD diabetic kidney disease: long-duration T2D, substantial albuminuria (A3), eGFR in G3b range, and higher cardiovascular-metabolic burden. It is realistic for advanced outpatient nephro-diabetes management but still above ESRD threshold by design.

### Why the variable pattern is plausible
- CKD severity: eGFR in 30-44 mL/min/1.73m2 maps to G3b; UACR >300 mg/g maps to A3 [4].
- Renal chemistry: higher creatinine and BUN are expected with reduced filtration [5].
- Glycemia: persistent diabetes with moderate-high HbA1c is plausible despite treatment intensity [1,2].
- BP: hypertensive burden is common and generally higher in CKD [8].
- Diabetes meds: metformin usually reduced/discontinued in this advanced profile; insulin use more common (heuristic but clinically standard direction).

### Internal relationship logic used in generation
- eGFR constrained >=15 to enforce non-ESRD scope.
- Creatinine strongly weighted to eGFR/age/sex relationship to avoid impossible pairings [5].
- CKD and albuminuria class labels are regenerated from numeric values each time [4].
- Lipids remain dysmetabolic but bounded to physiologic ranges.

### Teaching value
Excellent for discussing multimorbidity and tradeoffs in advanced diabetic kidney disease, while illustrating the distinction between severe CKD and ESRD.

---

## 5) Type 1 Diabetes with Early Nephropathy (`t1d_early_nephropathy`)

### Clinical narrative
This phenotype models long-standing type 1 diabetes with ongoing insulin dependence, low endogenous insulin secretion, and early kidney injury (usually A2 with preserved/mildly reduced eGFR). It reflects patients where nephropathy appears before major eGFR collapse.

### Why the variable pattern is plausible
- Type 1 physiology: very low C-peptide and obligatory insulin treatment are key discriminators [9].
- Glycemia: HbA1c often moderately elevated in long-duration type 1 diabetes.
- Renal profile: albuminuria may appear with still-preserved eGFR, especially in early nephropathy states [4].
- Lipids/BP: can be less dysmetabolic than severe T2D obesity phenotypes, while still showing cardiometabolic risk.

### Internal relationship logic used in generation
- Type 1 rule forces insulin use not to be none.
- C-peptide upper cap decreases with diabetes duration to reflect progressive beta-cell failure [9].
- UACR and stage mapping remain deterministic from urine values and KDIGO thresholds [4].
- HbA1c remains coupled to glucose and bounded within clinically plausible limits [3].

### Teaching value
Useful for teaching phenotype differentiation between T1D and T2D: insulin dependence and C-peptide behavior, plus how renal injury can begin even when filtration remains relatively preserved.

---

## 6) Type 1 Diabetes, Poor Control, CKD 3a (`t1d_poor_control_ckd3a`)

### Clinical narrative
This phenotype represents advanced but non-ESRD type 1 diabetes kidney disease: very long diabetes duration, poor glycemic control, low C-peptide, and clinically relevant kidney impairment (often G3a, with frequent A3 but variable albuminuria class).

### Why the variable pattern is plausible
- Glycemia: high HbA1c and elevated fasting/random glucose indicate chronic poor control [1,2,3].
- Type 1 physiology: near-absent C-peptide with insulin dependence is consistent with long disease duration [9].
- CKD pattern: eGFR in G3a range (45-59) plus elevated UACR is plausible pre-ESRD diabetic kidney disease [4].
- BP often higher, reflecting combined diabetes-kidney cardiovascular risk [8].

### Internal relationship logic used in generation
- Type 1 constraints on insulin and C-peptide are hard-enforced.
- Creatinine/BUN are tied to reduced eGFR so kidney chemistries match stage [5].
- Albuminuria category derived from UACR can vary between A2 and A3 depending on sampled urine values, which is clinically realistic [4].
- Non-ESRD guardrail keeps eGFR >=15 across all generated records.

### Teaching value
Strong case for discussing progressive complications in long-duration T1D and why patients with similar eGFR can have heterogeneous albuminuria severity.

---

## References
1. NIDDK. Diabetes & Prediabetes Tests (diagnostic thresholds and test characteristics). https://www.niddk.nih.gov/health-information/professionals/clinical-tools-patient-management/diabetes/diabetes-prediabetes
2. NIDDK. The A1C Test & Diabetes. https://www.niddk.nih.gov/health-information/diagnostic-tests/a1c-test
3. Nathan DM, et al. Translating the A1C assay into estimated average glucose values. Diabetes Care. 2008;31(8):1473-1478. PMID: 18540046. https://pubmed.ncbi.nlm.nih.gov/18540046/
4. KDIGO 2024 Clinical Practice Guideline for CKD Evaluation and Management. https://kdigo.org/wp-content/uploads/2024/03/KDIGO-2024-CKD-Guideline.pdf
5. National Kidney Foundation. CKD-EPI Creatinine Equation (2021). https://www.kidney.org/ckd-epi-creatinine-equation-2021
6. Grundy SM, et al. Diagnosis and management of the metabolic syndrome: AHA/NHLBI Scientific Statement. Circulation. 2005;112(17):2735-2752. PMID: 16157765. https://pubmed.ncbi.nlm.nih.gov/16157765/
7. Alberti KGMM, et al. Harmonizing the Metabolic Syndrome. Circulation. 2009;120(16):1640-1645. PMID: 19805654. https://pubmed.ncbi.nlm.nih.gov/19805654/
8. ACC/AHA guideline summary (BP categories and thresholds), 2017. https://www.acc.org/latest-in-cardiology/ten-points-to-remember/2017/11/09/11/41/2017-guideline-for-high-blood-pressure-in-adults
9. Jones AG, Hattersley AT. The clinical utility of C-peptide measurement in the care of patients with diabetes. Diabet Med. 2013;30(7):803-817. PMID: 23413806. https://pubmed.ncbi.nlm.nih.gov/23413806/
