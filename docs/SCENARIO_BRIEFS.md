# Hackathon Scenario Briefs

## Purpose

These briefs define two candidate scenarios for the redesigned hackathon. They
are written to be:

- clinically plausible
- understandable to non-programmer trainees
- well matched to a "You Are the Agent" interaction model
- suitable for later comparison against an LLM-driven agent

The two scenarios are intentionally different:

- Scenario 1 is about **operational prioritization**
- Scenario 2 is about **diagnostic classification under uncertainty**

## Scenario 1

## Inpatient Diabetes Follow-Up Prioritization

### Short framing

Your hospital wants to identify inpatients with diabetes who may need nurse
practitioner or endocrine follow-up during the admission, even when diabetes is
not the primary reason they are in the hospital.

### Why this is a good teaching scenario

- It is operationally realistic
- It requires combining several kinds of evidence
- It shows that agents are not just answering questions, they are supporting
  workflow decisions
- It creates room for ambiguity, triage, and "not enough evidence"

### Student-facing prompt

`Your team wants an alert to help prioritize hospitalized patients for diabetes
follow-up. Review the available evidence and decide which patients should be
flagged for NP/endocrine review during the hospitalization.`

Optional sharper version:

`Which hospitalized patients with diabetes appear most likely to need follow-up
for poor control or diabetes-related complexity during this admission?`

### Core learning objective

Students should learn that a useful clinical alert requires:

- gathering the right evidence
- distinguishing stronger from weaker signals
- avoiding over-flagging based on a single lab or diagnosis code
- recognizing when an answer is only partially supported

### Decision task

For each candidate patient, the student-agent should assign:

- `Flag`
- `Do not flag`
- `Uncertain / needs more review`

This is better than a simple yes/no decision because it leaves room for missing
data and borderline cases.

### Likely tools

- `Find patients by diagnosis`
- `Get demographics for a patient`
- `Get labs for a patient`
- `Get medications for a patient`
- `Get encounters for a patient`
- `Get all conditions for a patient`

### High-value evidence

The student-agent should be encouraged to look for combinations such as:

- diabetes diagnosis
- evidence of current or recent hospitalization
- elevated HbA1c
- insulin use or complex diabetes regimen
- chronic kidney disease
- multiple diabetes-related conditions or complications

### Suggested evidence rubric

Strong reasons to flag:

- clearly poor glycemic control
- diabetes plus CKD or another meaningful complication
- complex regimen, especially insulin-based treatment
- evidence that the patient is medically complex rather than having mild,
  incidental diabetes

Moderate reasons to flag:

- diabetes diagnosis plus incomplete but concerning evidence
- elevated HbA1c without clear complication data
- possible complexity but missing confirmation

Reasons not to flag:

- limited evidence of active diabetes-related management need
- mild or stable pattern without complications
- no clear sign that inpatient follow-up would add value

Reasons to mark uncertain:

- conflicting signals
- missing labs
- hospitalization present but diabetes severity not established
- diagnosis present but too little supporting context

### Student-agent reasoning questions

At each turn, students should be pushed to ask:

- Do I know enough about severity?
- Do I know enough about current diabetes management?
- Do I know whether this patient appears clinically complex?
- Am I flagging the patient because of one datapoint or a meaningful pattern?

### Common failure modes to look for

- Flagging based only on the presence of diabetes
- Treating one elevated HbA1c as sufficient without other context
- Ignoring CKD or complication burden
- Ignoring treatment complexity
- Stopping too early once one concerning signal appears
- Giving a confident recommendation despite thin evidence

### Why this scenario works well for the hackathon

This scenario turns the agent into a triage assistant rather than a trivia
machine. It connects tool use to an actual care workflow and naturally raises
questions about evidence sufficiency and trustworthiness.

### Caution

If the available encounter data does not support a robust distinction between
"hospitalized for diabetes" and "hospitalized for other reasons," the scenario
should avoid promising that exact determination. In that case, frame the task
around prioritizing hospitalized diabetic patients rather than identifying the
primary admission cause.

## Scenario 2

## Diabetes Type Clarification in Younger Patients

### Short framing

Your team is reviewing younger patients with diabetes because some charts may
contain incomplete, misleading, or inconsistent information about whether the
patient has Type 1 or Type 2 diabetes.

### Why this is a good teaching scenario

- It is clinically intuitive
- It naturally rewards multi-step evidence gathering
- It strongly fits the synthetic phenotype structure
- It creates realistic ambiguity rather than a trivial binary lookup
- It is ideal for the "You Are the Agent" format

### Student-facing prompt

`Review younger patients with diabetes and decide whether each case is more
consistent with Type 1 diabetes, Type 2 diabetes, or remains unclear based on
the available evidence.`

Optional sharper version:

`Some younger patients with diabetes may be mislabeled or incompletely
characterized. Use the available evidence to judge whether each case is more
consistent with Type 1, Type 2, or uncertain.`

### Core learning objective

Students should learn that clinical classification often requires synthesis
rather than one-step lookup. They should see that:

- diagnosis codes may not be enough
- age alone is not enough
- medication pattern matters
- C-peptide can be highly informative
- agents can overreach when evidence is incomplete

### Decision task

For each candidate patient, the student-agent should assign:

- `Likely Type 1`
- `Likely Type 2`
- `Unclear / needs more review`

This is preferable to forcing a binary answer.

### Likely tools

- `Find patients by diagnosis`
- `Get demographics for a patient`
- `Get labs for a patient`
- `Get medications for a patient`
- `Get all conditions for a patient`
- `Get encounters for a patient`

### High-value evidence

The student-agent should be encouraged to gather:

- age
- diabetes diagnosis codes
- C-peptide
- insulin use
- oral diabetes medications
- BMI or obesity-related pattern if available
- evidence of long-standing diabetes complications

### Suggested evidence rubric

Evidence more consistent with Type 1:

- very low C-peptide
- insulin dependence
- lack of a strong insulin-resistance pattern
- clinical picture coherent with autoimmune or insulin-deficient diabetes

Evidence more consistent with Type 2:

- preserved or higher C-peptide
- oral diabetes medications
- obesity or metabolic-syndrome pattern
- clinical picture coherent with insulin resistance

Reasons to mark uncertain:

- conflicting diagnosis codes
- missing or absent C-peptide
- mixed medication pattern
- age suggests one possibility but other evidence points elsewhere

### Student-agent reasoning questions

At each turn, students should be pushed to ask:

- Am I relying too much on age alone?
- Do I have direct evidence about insulin production?
- Does the medication pattern match my hypothesis?
- Is the chart internally consistent?
- Do I really know enough to classify this patient?

### Common failure modes to look for

- Using age as the main classifier
- Treating a diagnosis code as ground truth without checking supporting
  evidence
- Ignoring C-peptide when available
- Ignoring medication pattern
- Forcing a binary answer when the evidence is ambiguous
- Stopping before checking the most discriminating evidence

### Why this scenario works well for the hackathon

This scenario is easy to explain, clinically meaningful, and well aligned with
the synthetic cohort. It makes the loop visible because students can feel why
they need another step: one diagnosis code is not enough, one medication list
is not enough, and one lab may not be enough.

## How To Use Both Scenarios

A good sequence would be:

1. Start with **Scenario 2**
   It is more intuitive and better for introducing the student-as-agent model.
2. Follow with **Scenario 1**
   It builds from patient-level interpretation to operational prioritization.

This creates a natural progression:

- first classify and interpret
- then triage and prioritize

## Design Recommendation

If only one scenario is used in the first prototype, use:

`Diabetes Type Clarification in Younger Patients`

Reasons:

- easiest for students to grasp quickly
- strongest fit for the phenotype-based synthetic dataset
- best demonstration that an agent needs multiple evidence sources
- easier to review in a short notebook session

If time permits a second task, use:

`Inpatient Diabetes Follow-Up Prioritization`

That second scenario is valuable because it turns evidence gathering into a
workflow decision rather than a classification exercise.

## Suggested Next Artifacts

The next concrete design step should be:

1. one turn-by-turn prototype for Scenario 2
2. one shorter prototype or worksheet for Scenario 1
3. a shared menu/state interface that both scenarios use
