# FHIR Hackathon Redesign Spike

## Purpose

This document is a first-pass redesign brief for the FHIR hackathon. It is
intended to be reviewed, marked up, challenged, and revised quickly. It is not
yet an implementation plan.

The main goal is to redesign the hackathon so it is:

- More interesting for clinically oriented students
- More accessible for novice programmers
- More centered on clinical reasoning than Python mechanics
- Still clearly about agentic workflows, tool use, and structured healthcare
  data

## Boundary

The synthetic data generation pipeline is important context, but it is **not**
part of this hackathon's core hands-on workflow.

For this redesign:

- Students work with a **preloaded synthetic cohort** already available in the
  Stony Brook FHIR server
- Students may learn **how the cohort was designed** at a conceptual level
- Students do **not** generate full datasets and load them into the FHIR server
  during the hackathon
- A separate future hackathon or lab can focus on phenotype design, cohort
  generation, FHIR export, and server loading

Short version: in this hackathon, students interrogate a synthetic clinical
world; later, they may learn how to build one.

## Target Learner Profile

The redesign should be optimized for the actual audience, not an imagined
technical audience.

- Students are in biomedical informatics or clinical informatics training
- Many are clinicians or clinically oriented trainees
- They are comfortable with computers and AI in a general sense
- Most are novice programmers
- Many have minimal intuition for Python control flow, data structures, or API
  orchestration
- They can reason about diagnoses, labs, medications, clinical plausibility,
  and workflow
- They should leave the hackathon with a stronger conceptual understanding of
  FHIR, agents, evidence, and failure modes, even if they do not become
  implementers

This means the primary design target is:

**Clinically sophisticated, implementation-light learners**

## Design Principles

### 1. Clinical reasoning over code reading

Students should spend more time answering:

- What question are we asking?
- What evidence would support the answer?
- Which tools or data elements are needed?
- What would count as a trustworthy answer?

They should spend less time parsing Python loops and notebook plumbing.

### 2. Agent behavior should be visible, not opaque

The agentic aspect is central, but it should be presented as:

- plan
- action
- evidence
- conclusion

not primarily as raw orchestration code.

### 3. The dataset should feel like a designed clinical world

The synthetic cohort is a major asset. Students should understand that it was
constructed with clinically meaningful structure:

- Type 1 vs Type 2 diabetes
- kidney disease progression
- C-peptide differences
- medication patterns
- phenotype coupling

This makes the agent's successes and failures more interpretable.

### 4. Every session should contain an interesting task

Notebook 2 and Notebook 3 should not feel like passive demos. Each session
should ask students to predict, investigate, compare, critique, or explain
something nontrivial.

### 5. Scaffolding should be explicit

Students should not need to infer what matters. Each activity should make clear:

- the question
- the evidence needed
- the expected workflow
- what to look for
- what a good answer contains

### 6. Implementation should support teaching, not dominate it

The notebooks should expose as little infrastructure as necessary. The agent
loop, tool functions, and helper code should be hidden behind simple interfaces
where possible, with advanced details available in an appendix or instructor
materials.

### 7. One canonical experience

The teaching repo should present one obvious current path for students. Legacy
versions, deprecated notebooks, and historical architecture details should not
be part of the student-facing surface area.

## Proposed New 3-Session Arc

## Session 1: Read the Clinical World

### Working title

`From FHIR Resources to Clinical Evidence`

### Core goal

Teach students how a clinical question maps onto structured data, without
requiring them to author much code.

### Student experience

Students work through guided clinical questions using a preloaded synthetic
cohort. They learn how FHIR represents:

- who the patient is
- what conditions they have
- what labs and vitals have been recorded
- what medications they are on

The notebook should emphasize evidence tables, resource relationships, and
small, legible parameter changes rather than open-ended coding.

### Example activities

- Inspect one synthetic patient's chart across multiple FHIR resources
- Find evidence for Type 2 diabetes and kidney disease in one patient
- Compare two patients with different phenotypes
- Identify what makes a patient look more like Type 1 vs Type 2 diabetes

### Student output

A short structured clinical interpretation, not code.

### Why this is better

This gives novices an early success condition. They learn the shape of FHIR by
reading and reasoning, not by fighting syntax.

## Session 2: Watch and Critique the Agent

### Working title

`How an Agent Turns Questions into Evidence`

### Core goal

Teach the agentic loop conceptually, using a trace/replay model instead of raw
Python as the primary teaching surface.

### Student experience

Students are given a clinical question and asked to predict:

- what the agent should do first
- which evidence it needs
- where it might fail

They then run an agent and inspect a structured replay view:

`Question -> Plan -> Tool -> Result -> Why next`

The underlying code exists, but it is de-emphasized. The annotated agent-loop
material becomes optional background, appendix, or instructor support.

### Example activities

- Predict the tool sequence before running the agent
- Compare human workflow vs agent workflow
- Identify whether the agent gathered enough evidence
- Decide whether the final answer is justified by the trace

### Student output

A short critique of the agent's reasoning and evidence sufficiency.

### Why this is better

Students engage with agent behavior directly, without needing to mentally
execute a Python loop.

## Session 3: Red-Team the Agent

### Working title

`Can the Agent Be Trusted?`

### Core goal

Move from observation to evaluation. Students should investigate where the
agent succeeds, fails, overreaches, or stops early.

### Student experience

Students ask clinically interesting questions against the synthetic cohort and
judge the agent's performance using evidence and known cohort structure.

The key shift is that the questions should be genuinely worth asking, such as:

- How do Type 1 and Type 2 patients differ in C-peptide?
- Which patients have patterns consistent with diabetic kidney disease?
- Are there cases where the agent gives a correct-looking answer with weak
  evidence?
- Does the agent compare cohorts fairly, or inspect too few patients?

### Example activities

- Run two or three predefined high-value evaluation tasks
- Optionally add one student-authored question
- Label errors as evidence gap, reasoning gap, tool-choice problem, or data
  limitation
- Propose one change that would improve trustworthiness

### Student output

A structured evaluation memo or lightweight report with:

- question
- expected evidence
- agent answer
- verdict
- failure mode or surprise
- proposed fix

### Why this is better

This makes Session 3 an actual investigation rather than an open-ended prompt
to "find something interesting."

## What To Keep

- The synthetic phenotype-based cohort on the Stony Brook FHIR server
- The emphasis on structured clinical codes and resource linking
- The core agentic idea: question -> tool use -> evidence -> answer
- The contrast between human workflow and agent workflow
- The notion that trustworthy AI requires evaluation, not just impressive
  output
- The useful existing explainer on the agent loop as supporting material

## What To Cut

- Expecting students to read substantial orchestration code in the main flow
- Large empty code cells that assume students can prompt an LLM to write the
  right Python
- Too much notebook real estate devoted to SDK details, message formatting, and
  serialization issues
- Legacy-version clutter in the student-facing experience
- Passive "run this and watch" activities with no concrete analytical task

## What To De-Emphasize

- MCP as a major learning goal in the main 3-session arc
- Provider-specific implementation details
- Low-level Python control flow
- Full tool schema internals as a required student competency
- Historical discussion of old public SMART vs newer SBU infrastructure in the
  student path

These may remain in instructor notes, appendices, or advanced optional
materials.

## Candidate Structural Changes

### Notebook surface

- Fewer raw implementation cells
- More guided markdown framing
- More prebuilt evidence tables and visual summaries
- More "predict before run" and "judge after run" prompts

### Code organization

- Move the agent loop and tool code into helper modules where possible
- Keep notebook cells focused on interaction, evidence review, and reflection
- Preserve an appendix or separate explainer for students who want to go deeper

### Repository organization

- Prefer a new fork or clean repo for the redesigned teaching path
- Keep the existing repo as archival/reference material
- Expose one canonical student path and one instructor path

## Open Decisions Needing Input

### 1. Repo strategy

- Do we want a clean fork for the redesign?
- If yes, should the current repo become archive/reference only?

### 2. Session count and duration

- Do we want to preserve the current 3 x 1-hour structure?
- Or should one session become longer or split into lecture plus lab?

### 3. Session 1 coding level

- Should Session 1 include any student-authored Python at all?
- Or should it be almost entirely guided exploration with small parameter edits?

### 4. Agent transparency format

- Do we want a custom replay/trace display in notebooks?
- Or is a text trace plus structured summary sufficient?

### 5. Deliverable format

- Should Session 3 still produce JSON?
- Or should the student-facing deliverable be a short narrative memo with JSON
  captured behind the scenes?

### 6. Clinical focus

- Should the hackathon stay primarily centered on diabetes plus CKD?
- Or should we broaden to a few distinct clinical stories inside the same
  cohort?

### 7. Use of synthetic-data-generation context

- How much do we want students to see about phenotype design?
- Should they read brief phenotype summaries only, or compare alternate cohort
  designs conceptually?

## Suggested Next Iteration Artifacts

To iterate efficiently, the next spike outputs should probably be:

1. A one-page session map for the redesigned Sessions 1-3
2. A detailed prototype for the new Session 2
3. A mockup of how agent replay/evidence review should look in a notebook
4. A proposed repo structure for a clean fork

## Current Working Thesis

The redesign should treat the hackathon as an exercise in:

- understanding a structured synthetic clinical world
- using FHIR to inspect that world
- watching an agent reason over that world
- evaluating whether the agent's answer is actually supported

It should not primarily be an exercise in reading Python implementation code.
