# Project Brief: FHIR + AI Hackathon (BMI 512)

All domain-specific context for the FHIR hackathon project lives here. The
agent identity files (AGENT.md) are domain-independent; this file makes them
work for THIS project.

---

## Course and Audience

**Course:** BMI 512 — Clinical Informatics and AI, Stony Brook University

**Who the students are:**
- Biomedical informatics and clinical informatics trainees (masters and PhD)
- Many are clinicians (MDs, nurses, pharmacists) or clinically oriented researchers
- Comfortable with computers and AI as users — they use EHRs, read about LLMs,
  understand what AI tools do at a high level
- Most are novice programmers — they may have taken an intro Python course but
  cannot write or debug non-trivial code independently
- They reason fluently about diagnoses, lab values, medications, clinical
  plausibility, and healthcare workflows

**What they should leave the hackathon with:**
- Conceptual understanding of FHIR as a data standard (resources, queries,
  what you can and cannot ask for)
- Intuition for how AI agents work (observe, decide, act, repeat) — built
  through doing the agent's job themselves
- Awareness of agent failure modes (incomplete evidence, reasoning errors,
  over-reliance on single data points)
- Ability to evaluate whether an AI agent's clinical reasoning is sound
- Enough confidence to prompt and direct an AI agent, even without coding skills

**What they should NOT need to do:**
- Write Python code from scratch
- Debug API calls or parse JSON
- Understand HTTP, REST, or authentication mechanisms
- Read implementation code to follow what is happening

---

## Pedagogy: "You Are the Agent"

### Three-Layer Model

**Layer 1 — Human Mode (Act as the Agent):**
The student manually performs the agent's job. Choose which FHIR queries to
run (from a menu), read the returned clinical data, reason about what the
evidence means, decide on a classification, and receive immediate feedback.
This builds intuition for the agent loop before the student ever sees an
AI agent run.

Design requirements: student choices must affect outcomes, multiple queries
should be needed (one-query solutions defeat the purpose), feedback must be
immediate and specific (not just correct/incorrect), the clinical domain must
provide genuine complexity.

**Layer 2 — Hybrid Mode (Agent with Guidance):**
The student can ask the LLM for help ("What query should I run next?" or
"What does this lab value mean?") but still makes decisions and executes
queries. Bridges manual investigation and full delegation.

Design requirements: hints guide reasoning without giving answers, student
still executes queries and makes the final classification.

**Layer 3 — LLM Mode (Prompt Engineer):**
The student writes a natural-language prompt and the AI agent runs
autonomously. The student compares the agent's reasoning chain with their
own experience from Layer 1 and can iterate on the prompt.

Design requirements: agent reasoning must be visible (queries chosen, data
received, how it decided), student can run the agent multiple times with
different prompts, scoring is transparent.

### The "Bored or Baffled" Framework

Every cell and activity is evaluated against three states:

- **Bored:** Student has nothing meaningful to do. Signs: "run this cell and
  observe," all dropdown options lead to the same outcome, task is trivially
  solvable, student watches AI work without a role.
- **Baffled:** Student faces something they cannot engage with. Signs: code
  they must read to understand, too many options without guidance, error
  messages with no explanation.
- **Engaged:** Student makes real decisions with real consequences. Signs:
  query choices reveal different information, classification gets immediate
  specific feedback, prompts change agent behavior, ambiguous cases require
  genuine reasoning.

### Real vs. Fake Agency

Real: student's choice changes the outcome, feedback is specific and evidence-
based, repeatable with different results, genuine difficulty where one data
point is not enough.

Fake: dropdown with no consequences, one-query solutions, predetermined
conclusions, submit button with no feedback.

### Design Principles

1. **Clinical reasoning over code reading** — cognitive challenge is in
   interpreting labs and weighing evidence, not understanding Python.
2. **Agent behavior should be visible** — show queries chosen, data received,
   reasoning process, classification and confidence.
3. **Designed clinical world** — synthetic patients create meaningful
   classification challenges requiring multi-query investigation.
4. **Clear learning objectives** — every activity has a "what am I learning
   about agents?" answer. If the answer is "nothing, this is setup," hide it.
5. **Active not passive** — students make decisions. "Read this output" is not
   a decision. "Choose which query to run next" is.

---

## FHIR Server and Data

- **Endpoint:** `https://lfh-fhir.eastus2.cloudapp.azure.com:9443/fhir-server/api/v4`
- **Auth:** Basic Auth (`fhiruser` / `BmI512@ccess`)
- **TLS:** Self-signed certificate (`verify=False` in Python requests)
- **Population:** 1,027 synthetic patients across 6 phenotypes

### Available FHIR Resource Types

| Resource | Key Fields | Use For |
|----------|-----------|---------|
| Patient | name, birthDate, gender, address | Demographics, age calculation, identifying the person |
| Condition | code (SNOMED), clinicalStatus, onsetDateTime | Finding patients by diagnosis, checking comorbidities |
| Observation | code (LOINC), valueQuantity, effectiveDateTime | Lab results, trending values (sort by `-date`) |
| MedicationRequest | medicationCodeableConcept, status, authoredOn | Insulin use, oral agents, treatment complexity |
| Encounter | class (AMB/IMP/EMER), period, type | Visit frequency, care engagement (ambulatory-heavy) |

---

## Available Clinical Codes

### SNOMED CT Codes (Conditions)

| Code | Description | Notes |
|------|-------------|-------|
| 46635009 | Type 1 diabetes mellitus | Seeded diagnosis |
| 44054006 | Type 2 diabetes mellitus | Seeded diagnosis |
| 709044004 | Chronic kidney disease | Comorbidity, present in a subset of patients |

### LOINC Codes (Observations / Labs)

| Code | Description | Clinical Significance |
|------|-------------|----------------------|
| 4548-4 | HbA1c | Glycemic control. >7.5% = poor control (project threshold) |
| 1986-9 | C-peptide | Endogenous insulin. Low = Type 1, Normal/High = Type 2 |
| 39156-5 | BMI | Metabolic context. Higher BMI more common in Type 2 |
| 2160-0 | Creatinine (serum) | Kidney function. Elevated = impaired function |
| 33914-3 | eGFR | Kidney function. Lower = worse CKD stage |
| 14959-1 | UACR | Early kidney damage. Elevated = albuminuria |

---

## Synthetic Cohort

### Six Phenotypes

1. **Clear Type 1 diabetes** — low C-peptide, insulin-dependent
2. **Clear Type 2 diabetes** — normal C-peptide, oral agents
3. **Type 2 with insulin** — progressed T2D, may superficially resemble Type 1
4. **Diabetes with CKD** — comorbidity adds management complexity
5. **Poor glycemic control** — high HbA1c regardless of diabetes type
6. **Well-controlled diabetes** — HbA1c within target

### Key Clinical Distinctions

**Type 1 vs Type 2:**
C-peptide is the strongest discriminator (low in T1D, normal/high in T2D).
Supporting signals: BMI (higher in T2D), medication pattern (insulin-only vs.
oral agents), age of onset.

**Glycemic control:**
HbA1c >7.5% = poor control. Combine with medication data to assess treatment
adequacy.

**CKD staging:**
eGFR determines CKD stage, UACR indicates albuminuria, creatinine correlates
with eGFR. CKD adds complexity to diabetes management.

**Medication complexity:**
Insulin-only (more typical T1D or advanced T2D), insulin + oral agents
(complex T2D), oral agents only (earlier T2D), no diabetes medications
(diet-controlled, newly diagnosed, or data gap).

### Known Data Issue

C-peptide alone currently makes Type 1 vs. Type 2 classification trivially
solvable — one query is enough. A well-designed scenario must require
corroborating evidence from multiple sources. This is a known open issue
(see `tasks/todo.md`).

---

## FHIR Query Patterns

### Search for patients by diagnosis
```
GET /Condition?code={snomed_code}&_count={max_results}&_format=json
```
Returns Condition resources. Extract `subject.reference` to get Patient IDs.

### Get patient demographics
```
GET /Patient/{patient_id}?_format=json
```

### Get all conditions for a patient
```
GET /Condition?subject=Patient/{patient_id}&_count={max_results}&_format=json
```

### Get specific lab values for a patient
```
GET /Observation?subject=Patient/{patient_id}&code={loinc_code}&_count={max_results}&_sort=-date&_format=json
```

### Get medications for a patient
```
GET /MedicationRequest?subject=Patient/{patient_id}&_count={max_results}&_format=json
```

### Get encounters for a patient
```
GET /Encounter?subject=Patient/{patient_id}&_count={max_results}&_sort=-date&_format=json
```

---

## Data Limitations

- **Ambulatory-heavy encounters:** Inpatient metadata is sparse and unreliable.
  Do not design scenarios that depend on admission/discharge patterns.
- **No clinical notes:** Only structured data (codes, values, dates). No
  free-text reasoning available.
- **Static dataset:** 1,027 patients, not growing. Query results are
  deterministic for a given query.
- **Synthetic quirks:** Some patients may have clinically implausible
  combinations (e.g., very high C-peptide with Type 1 diagnosis). These can be
  pedagogically useful (teaching students to handle messy data) or confusing.
- **Limited condition vocabulary:** Only diabetes and CKD conditions are
  reliably seeded. Other conditions may be synthetic generator artifacts.

---

## Technical Conventions

- **Code hidden from students:** All code cells use `cellView: "form"` in Colab
- **Generated, not hand-edited:** Notebooks are produced by Python generator
  scripts. Edit the generator, never the `.ipynb` directly.
- **Self-contained:** Generated notebooks inline all code as string constants.
  No `src/` imports in notebooks.
- **Colab deployment:** Notebooks run in Google Colab against the live FHIR
  server. Local Jupyter testing is not sufficient for verification.
- **LLM:** Anthropic Claude only (`claude-sonnet-4-20250514`). No dual-provider
  abstraction.
- **FHIR query banners:** Every query result displays a banner showing the
  FHIR URL that was called, making the data retrieval process visible to
  students.

---

## Decision Boundaries — All Agents

When you encounter a decision where you lack domain expertise, do not default
to the convenient answer. Write the decision to `agent-history/comms/queries/`
and flag it to the orchestrator. Specifically:

- Never assume existing data is adequate without verification
- Never choose clinical thresholds unless you are the Scenario Designer or
  Synthetic Data Architect
- Never assess pedagogical impact unless you are the Education Reviewer
- Never simplify or skip work to save time if the simplification could have
  clinical or pedagogical consequences

If in doubt: flag it. The cost of a false alarm is one query file. The cost
of a wrong assumption is a broken teaching experience.

### How to Flag a Decision

Write a query file to `agent-history/comms/queries/` using the format
described in the agent communication protocol. Include:
- What decision you're facing
- Why it's outside your domain
- Which agent should be consulted
- What specific questions you need answered

Then report the query in your output to the orchestrator.

---

## Existing Scenarios

### Scenario 1: Endocrine Follow-Up List Construction
- **Task:** Review diabetic patients and decide who should be prioritized for
  endocrine follow-up based on poor control or diabetes-related complexity.
- **Verdict labels:** Flag, Do not flag, Uncertain / needs more review
- **Evidence checklist:** diabetes diagnosis, recent encounter context, HbA1c,
  medication complexity, CKD or other complexity
- **Prompt variants:** base request, poor-control emphasis, complexity emphasis,
  conservative flagging
- **Candidate pool:** built from T2D and T1D condition searches, scored by
  HbA1c level, CKD presence, insulin use, and encounter recency

### Scenario 2: Type 1 vs Type 2 Clarification
- **Task:** Review younger patients with diabetes and determine whether the
  case is more consistent with Type 1, Type 2, or unclear.
- **Verdict labels:** Likely Type 1, Likely Type 2, Unclear / needs more review
- **Evidence checklist:** C-peptide, medication pattern, problem list /
  diagnosis context, BMI / insulin-resistance context
- **Candidate pool:** younger patients (age <= 35) from both T1D and T2D
  condition searches, 3 per group

### Known Issues Across Scenarios (from tasks/todo.md)
- **No case variety:** All cases returned are the same phenotype due to FHIR
  server returning cases in insertion order. Need to shuffle or stratify.
- **Combined dropdown is confusing:** Query actions and classification options
  in the same dropdown — students cannot tell them apart.
- **Task is too simple:** C-peptide alone solves classification. Defeats the
  purpose of teaching the multi-step agent loop.
