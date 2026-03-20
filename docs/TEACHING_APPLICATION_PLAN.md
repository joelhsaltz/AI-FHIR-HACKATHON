# Teaching Application Plan

## Summary

Build a single notebook-first teaching application in the redesign workspace
that teaches how agents work in clinical informatics workflows. The app is for
remote, individual use on student laptops and is explicitly not a
medicine-teaching tool. The clinical scenarios are vehicles for teaching:

- how agents gather evidence
- how agents operationalize a natural-language request
- how agents automate work that would otherwise require human review
- why agent flexibility differs from brittle rules-based logic
- why a recommendation still needs evidence inspection and critique

The application will use two scenarios in this order:

1. Inpatient endocrine follow-up prioritization
2. Type 1 vs Type 2 clarification in younger patients

The learning progression is fixed:

1. Human mode: student plays the agent
2. Hybrid mode: student asks the LLM for next-step help
3. LLM mode: notebook runs the full autonomous agent and shows replay

## Product Framing

The app should open with a short explicit framing section:

- In health care quality and operational informatics, the default solution is
  often a rules-based workflow.
- Rules are stable but rigid.
- Agents are valuable because they can operationalize natural-language
  variations of a task without rebuilding brittle logic each time.
- The question is not "does the agent know medicine?"
- The question is "how does the agent turn a workflow request into
  evidence-gathering actions and a justified recommendation?"

This framing should appear before Scenario 1 and should be written for
informatics trainees, not for general consumers or lay patients.

## Delivery Surface

Use a main canonical notebook as the student-facing application, plus a
separate capstone notebook for population-scale ranking and audit.

Distribution model:

- the source of truth for students is the public GitHub repository
- students should open notebooks from GitHub in Google Colab
- students should save copies into their own Google Drive folder before working
- Google Drive sharing and MCP/connector-based distribution are not the default
  student workflow

The notebook should contain:

- short intro and framing
- scenario selector or sequential scenario sections
- one shared runtime and state model
- minimal visible infrastructure code
- readable tables and state panels
- a replay section for autonomous LLM runs

Do not expose raw orchestration code in the main learning flow. Keep helper
logic in shared runtime code under the redesign workspace and surface only
simple notebook entry cells.

For Colab distribution, the generated notebooks should be self-contained at
runtime rather than depending on a local checkout of `src/`.

## Shared Application Behavior

Use one shared interaction model across both scenarios in the main notebook.

Student-visible panels each turn:

- current scenario and task
- current evidence state
- evidence still missing
- step history
- next-action menu

Shared action menu:

- `Find patients by diagnosis`
- `Review one candidate patient`
- `Get demographics`
- `Get full problem list`
- `Get labs`
- `Get medications`
- `Get encounters`
- `Add patient to follow-up list`
- `Mark patient as not priority`
- `Mark patient as uncertain`
- `Ask the LLM what to do next`
- `Finish and answer`

Before each action, prompt the student for a short rationale or expected
evidence note.

After each action, render:

- compact result table
- short evidence summary
- updated missing-evidence list

Shared student modes:

- Human mode
  Student chooses every step.
- Hybrid mode
  Student can ask the LLM for exactly one recommended next action.
- LLM mode
  The full autonomous agent runs and the notebook shows the replay trace.

The replay trace should be shown as:

- step number
- tool selected
- arguments
- key result
- final answer

The notebook should also make explicit how interaction options map to FHIR
queries. In particular:

- `Find patients by diagnosis` corresponds to the Notebook 3 tool
  `search_conditions`, which issues a query of the form
  `GET /Condition?code={snomed_code}&_count={max_results}&_format=json`
- `Get full problem list` corresponds to the Notebook 3 tool
  `search_all_conditions`, which issues a query of the form
  `GET /Condition?subject=Patient/{patient_id}&_count={max_results}&_format=json`

That distinction is a core teaching point. The first query builds a candidate
population. The second query reviews the complete diagnosis context for one
already selected patient.

## Colab Distribution and Validation

The notebooks should be prepared specifically for public GitHub -> Colab use.

### Student Credential Model

Student friction should be minimized.

Follow the pattern used in the older `AI-FHIR-HACKATHON` student notebooks:

- hardcode the teaching FHIR server configuration in the notebook
- hardcode the synthetic-data authentication for the teaching server
- treat only the LLM API key as a student secret

For the current redesign notebooks, the intended student-facing setup is:

- hardcoded:
  - `FHIR_BASE = "https://lfh-fhir.eastus2.cloudapp.azure.com:9443/fhir-server/api/v4"`
  - `FHIR_SESSION.auth = ("fhiruser", "BmI512@ccess")`
  - `FHIR_SESSION.verify = False`
- student secret:
  - `OPENAI_API_KEY`

Students should not need to create secrets for FHIR base URL, FHIR username,
or FHIR password.

### Colab Notebook Structure

The generated notebooks should follow the same structure that already worked in
the older public repo:

1. package install cell
2. setup and connection-check cell
3. helper / tool definitions
4. quick validation cell
5. main teaching flow

This should apply to both the main notebook and the capstone notebook.

### Testing Gate Before Distribution

The notebooks should not be distributed to students until two testing stages
have happened:

1. I test them first
2. Joel tests them in real Colab second

The first-stage testing should include:

- notebook JSON validation
- cell-order validation
- validation that the notebooks do not depend on local `src/` imports
- automated notebook execution using `nbclient`
- browser-driven smoke tests using Playwright against the public GitHub and
  Colab workflow

The second-stage testing should be an explicit handoff to Joel with:

- direct Colab links
- the single required secret name (`OPENAI_API_KEY`)
- a short checklist for saving a copy to Drive and confirming the notebooks run

Student-facing setup docs should be finalized only after Joel confirms that the
Colab flow works for him end to end.

## Scenario 1: Inpatient Endocrine Follow-Up Prioritization

This scenario is the onboarding scenario and the first required module.

### Core Teaching Purpose

Teach agents as automated workflow support systems for tasks that would
otherwise require manual human review and list construction.

This scenario should not be framed as learning diabetes management. It should
be framed as:

- a familiar informatics problem
- traditionally handled by fixed criteria or dashboard logic
- now explored through a flexible agentic interface

### Student-Facing Framing

Introduce a short base case:

- a hospital or endocrine division wants to identify inpatients with diabetes
  who may warrant endocrine or NP follow-up during admission
- historically, this kind of work is often driven by fixed rules or dashboards
- now the student will act as the agent reviewer

The key task is to assemble a list of patients who should be followed by a
diabetes clinician, not just to review one preselected patient in isolation.

Implementation note:

- the current live synthetic cohort exposes recent encounter metadata, but in
  the records sampled so far those encounters are mostly ambulatory rather than
  robust inpatient admissions
- the first build therefore teaches the list-construction workflow using the
  live cohort as it exists today, while avoiding unsupported claims about
  hospitalization status

### Base Prioritization Request

Use this as the default first request:

Review hospitalized patients with diabetes and identify which patients should
be prioritized for endocrine staff follow-up during the admission based on
evidence of poor control or diabetes-related complexity.

This wording intentionally avoids requiring unsupported inference about the
primary admission diagnosis.

Operationally, the student should:

1. find candidate patients with diabetes
2. review hospitalization and clinical complexity evidence
3. decide who belongs on the follow-up list

### Controlled Natural-Language Variations

After students complete the base request once, offer 2-3 controlled variants to
make the flexibility advantage concrete.

Default variants:

1. Poor-control emphasis

   Prioritize hospitalized diabetic patients whose recent data suggests poor
   glycemic control, even if complication burden is not yet clear.

2. Complexity emphasis

   Prioritize hospitalized diabetic patients whose overall diabetes-related
   complexity suggests they may benefit from endocrine review, especially if
   kidney disease or intensive treatment is present.

3. Conservative-flagging emphasis

   Only prioritize hospitalized diabetic patients when the evidence for poor
   control or diabetes-related complexity is strong enough that endocrine
   review would likely change management.

The point of these variations is not to force different final patient lists.
The point is to show that agents can flexibly operationalize different task
formulations without rewriting hard-coded rule logic.

### Student Verdict Labels

Use fixed per-patient outputs:

- `Flag`
- `Do not flag`
- `Uncertain / needs more review`

The scenario-level output is a constructed follow-up list plus a short
justification for each included patient.

### Evidence Emphasis

Students should be guided to inspect:

- whether the patient entered the candidate pool because of diabetes
- diabetes diagnosis context
- hospitalization or encounter context
- HbA1c / glycemic control
- medication complexity, especially insulin
- CKD or diabetes-related complication burden
- whether the evidence supports a meaningful follow-up recommendation

The first step in the notebook should explicitly mirror the earlier Session 1
FHIR pattern:

- query `Condition` by SNOMED code to find patients with diabetes
- then move from candidate identification to patient-level review

### Scenario 1 Learning Outcome

By the end of Scenario 1, students should understand:

- how a candidate patient list is assembled from FHIR data
- how an agent automates a review workflow
- how natural-language task wording affects evidence-gathering behavior
- why flexible task formulation is a core advantage over rules
- why a recommendation still requires evidence review

## Scenario 2: Type 1 vs Type 2 Clarification in Younger Patients

This scenario is second and builds on the loop learned in Scenario 1.

### Core Teaching Purpose

Teach agents as evidence-gathering systems for classification under uncertainty,
where the main issue is not workflow prioritization but whether the evidence is
sufficient to support a conclusion.

### Student-Facing Framing

Use a short context:

- a younger patient cohort with diabetes may contain incomplete, inconsistent,
  or misleading chart labels
- the student’s job is not to diagnose medicine from scratch
- the student’s job is to gather enough evidence to judge whether the case
  looks more consistent with Type 1, Type 2, or remains unclear

### Base Request

Use this default wording:

Review this younger patient with diabetes and decide whether the case is more
consistent with Type 1 diabetes, Type 2 diabetes, or remains unclear based on
the available evidence.

### Student Verdict Labels

Use fixed outputs:

- `Likely Type 1`
- `Likely Type 2`
- `Unclear / needs more review`

### Evidence Emphasis

Students should be guided to inspect:

- C-peptide
- medication pattern
- problem list / diagnosis context
- BMI or insulin-resistance context
- age as supporting context only, not as decisive evidence

### Scenario 2 Learning Outcome

By the end of Scenario 2, students should understand:

- that agents often need several evidence sources before a classification is
  justified
- that ambiguity is an acceptable output
- that a plausible-looking answer can still be weakly supported

## Capstone Notebook: Population-Scale Ranking and Audit

The capstone is a separate notebook, not part of the main teaching notebook.

### Core Purpose

Show what changes when the workflow scales from small teaching cases to the
full 1000+ patient server population.

The capstone teaches:

- how natural-language requests can be operationalized differently
- that some requests can be translated into explicit rule-like logic
- that some requests remain judgment-heavy
- that ranking logic should be visible and auditable

### Capstone Flow

1. Student enters a prioritization request in natural language.
2. System classifies the request as `rule-translatable` or
   `judgment-heavy`.
3. System explains why it made that classification.
4. If `rule-translatable`, the system shows the translated rule explicitly.
5. If `judgment-heavy`, the system shows a simplified qualitative rubric.
6. Student may revise the proposed logic in plain language.
7. The resulting logic is locked for the run.
8. The system ranks patients across the full server population and produces a
   top-25 follow-up list.
9. Student audits the result.

### Transparency

The capstone should show by default:

- request classification
- classification explanation
- translated rule or simplified rubric
- ranked list
- plain-language reasons patients rank high or low

Detailed formula and factor contributions should be available behind an
optional click or reveal step.

## Student Setup Documentation

After Colab validation passes, add student-facing instructions in two places:

- a detailed step-by-step guide in `docs/STUDENT_COLAB_SETUP.md`
- a shorter onboarding section in `README.md`

The student setup instructions should tell students to:

1. create a Google Drive folder such as `AI-on-FHIR Notebooks`
2. open the notebook from the public GitHub repo in Colab
3. save a copy into their Drive folder
4. add `OPENAI_API_KEY` to Colab Secrets
5. run the setup cell first
6. proceed with the notebook

## Shared Runtime and Interfaces

The implementation should use the OpenAI-backed runtime already started in the
redesign workspace.

Stable internal interfaces:

- `ScenarioConfig`
  - `id`
  - `title`
  - `intro_text`
  - `base_prompt`
  - `prompt_variants`
  - `candidate_builder`
  - `verdict_labels`
  - `evidence_checklist`
  - `llm_instructions`
  - `teaching_objective`
- `SessionState`
  - `scenario_id`
  - `candidate_ids`
  - `current_patient_id`
  - `question`
  - `candidate_context`
  - `evidence`
  - `history`
  - `missing_evidence`
  - `follow_up_list`
  - `final_answer`
  - `mode`
- Shared runtime functions
  - load settings
  - load scenario
  - build candidate pool
  - initialize candidate-review state
  - select current candidate patient
  - render state panel
  - execute selected action
  - summarize evidence
  - add patient to follow-up list
  - mark patient not priority / uncertain
  - request one LLM next-step suggestion
  - run full autonomous agent
  - render replay trace
  - reset state

Public student-facing behavior should remain notebook-first and menu-driven.
Code organization can live under shared Python modules in the workspace.

## Test Plan

### Functional Checks

- notebook startup works with valid FHIR configuration
- both scenarios load successfully
- candidate pools are built successfully
- each menu action updates state and history correctly
- human mode works without LLM execution
- hybrid mode returns one useful next-step suggestion
- LLM mode completes a tool-using run and produces a final answer
- replay trace renders readable step-by-step output

### Scenario Checks

Scenario 1:

- candidate list begins with a diabetes-identification step using `search_conditions`
- at least one clearly flaggable case
- at least one non-flaggable or uncertain case
- prompt variants change the review framing without breaking the workflow
- no wording depends on unsupported primary-diagnosis inference unless later
  dataset validation proves that reliable
- final output is a constructed follow-up list, not only one patient verdict

Scenario 2:

- at least one clear Type 1-pattern case
- at least one clear Type 2-pattern case
- at least one borderline or discussion-worthy case if available
- C-peptide is surfaced as a high-value discriminator

### Teaching Checks

- students can complete Scenario 1 without reading raw loop code
- the state panel is understandable after each turn
- the shift from human to hybrid to LLM mode is clear
- the application reads as an informatics workflow exercise, not a medicine
  lecture

## Defaults and Assumptions

- Delivery remains notebook-first.
- The first release is optimized for remote individual students.
- Scenario order is fixed:
  1. inpatient prioritization
  2. Type 1 vs Type 2 clarification
- Mode order is fixed:
  1. Human
  2. Hybrid
  3. LLM
- The application teaches agent behavior and workflow automation, not clinical
  medicine.
- The most important comparison is rules-based rigidity vs agentic flexibility.
- The value of the agent is in flexible task specification and evidence
  gathering, not necessarily in producing a different final patient list from a
  rules system.
- For Scenario 1, students work from a stable diabetes candidate set and
  construct the final follow-up list themselves.
- Synthetic data generation remains out of scope for the main teaching
  application and stays as future separate material.
