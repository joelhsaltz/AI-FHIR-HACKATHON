# Session Spike: You Are the Agent

## Purpose

This document proposes a replacement for the current Session 2. It assumes
students have already completed the original Session 1 and do not need a repeat
introduction to FHIR basics.

The new core idea is:

**Students learn what an agent does by temporarily acting as the agent.**

Instead of starting with Python code or a hidden LLM loop, students are placed
inside a simplified agent workflow and must decide what tool to use next, what
evidence matters, and when enough evidence has been gathered to answer a
clinical question.

## Core Thesis

Students will understand agentic workflows better if they:

- see the current question
- see the accumulated evidence
- choose the next tool from a menu
- observe the result
- decide whether to continue or stop

This makes the loop concrete before they ever see an LLM perform it.

## Learning Goals

By the end of this session, students should be able to:

- Explain what an agent does in plain language
- Describe an agent loop as repeated cycles of:
  - review current state
  - choose next action
  - gather evidence
  - decide whether to continue
- Recognize that tool choice and stopping decisions are core parts of agent
  behavior
- Distinguish between a well-supported answer and a plausible-sounding but
  weakly supported answer
- Compare their own reasoning to an LLM-driven workflow

## Student-Facing Theme

Suggested headline:

`You Are the Agent`

Suggested subheading:

`For one session, you will play the role of the LLM: choosing tools, reviewing
evidence, and deciding when you know enough to answer.`

This framing should be explicit and repeated. The point of the session is not
that the student learns how to code an agent. The point is that the student
experiences the decision-making structure of an agent.

## Why This Is Better Than the Current Session 2

The current Session 2 asks students to understand the agent by watching it and
then reading code. For this audience, that is too abstract and too dense.

The new session:

- is active rather than observational
- is clinically legible rather than implementation-heavy
- makes state accumulation visible
- makes tool choice explicit
- makes stopping criteria discussable
- naturally sets up later comparison with a real LLM agent

## Assumptions

- Students already had a first exposure to FHIR resources in the prior session
- Students are novice programmers
- Students are more comfortable with clinical reasoning than with Python
- The Stony Brook FHIR server already contains the synthetic cohort
- We want to use the richer current tool set rather than an artificially
  reduced one

## Recommended Tool Set

Use the fuller clinically useful tool set from the current richer notebooks.

Candidate menu:

- `Find patients by diagnosis`
- `Get one patient's demographics`
- `Get labs for a patient`
- `Get medications for a patient`
- `Get encounters for a patient`
- `Get all conditions for a patient`
- `Finish and answer`

Important principle:

Students should not type raw Python function calls. They should choose tools
from a constrained menu and only supply small amounts of structured input.

## Interaction Model

Each turn has the same rhythm.

### Panel 1: Clinical question

Show one focused question at the top of the page.

Examples:

- `Is this patient more consistent with Type 1 or Type 2 diabetes?`
- `Which patients have diabetes plus evidence of kidney disease progression?`
- `Does this patient have enough evidence to support diabetic nephropathy?`

### Panel 2: Current evidence state

Show a compact state summary such as:

- Patients identified so far
- Diagnoses found so far
- Labs found so far
- Medications found so far
- Open questions remaining

This should read like an evidence board, not a raw JSON dump.

### Panel 3: Available actions

Show a menu like:

1. Find patients by diagnosis
2. Get demographics for a patient
3. Get labs for a patient
4. Get medications for a patient
5. Get encounters for a patient
6. Get all conditions for a patient
7. Let the LLM choose the next step
8. Finish and answer

### Panel 4: Prompt to reflect

Before the action runs, ask one short question:

- `Why are you choosing this tool now?`
- `What evidence do you expect to get from this step?`

The answer can be brief and optional, but the prompt matters pedagogically.

### Panel 5: Result

After the tool runs, show the result in a human-readable form:

- small table
- summary bullets
- highlighted key evidence

Then return to the next turn.

## Modes

This session works best if it supports three modes.

### Mode 1: Human Agent

The student chooses every step.

Use case:

- best for learning the loop
- best for first run-through

### Mode 2: Hybrid Agent

At each turn, the student can decide whether to:

- choose the next tool themselves
- ask the LLM what it would do next

Use case:

- best for comparing human and model strategy
- shows the LLM as collaborator rather than magic box

### Mode 3: LLM Agent

The LLM runs the task end-to-end after the student has already experienced the
loop manually.

Use case:

- best for comparison and critique
- should come after Human or Hybrid mode, not before

## Session Flow

## Part A: What an agent actually does

Very short framing:

- An agent is not just "AI that answers questions"
- An agent is a system that repeatedly decides:
  - what to do next
  - what evidence to gather
  - whether it knows enough to stop

No raw code yet.

## Part B: You play the agent

Students work through one or two guided clinical tasks using the menu-based
interface.

The notebook should make this feel like:

- clinical detective work
- evidence gathering
- deciding what is enough

not software engineering.

## Part C: Compare yourself to the LLM

After the student has acted as the agent, they can replay the same question
with the LLM.

Comparison prompts:

- Did the LLM gather the same evidence you did?
- Did it miss anything important?
- Did it take unnecessary steps?
- Did it stop too early?
- Which answer would you trust more, and why?

## Part D: Reflection

End with a short reflection:

- What was hardest about being the agent?
- What makes an agent trustworthy or untrustworthy?
- Where can an agent fail even if the tools are correct?

## Clinical Task Design

The questions need to be understandable and worth asking. They should not be
too broad.

Recommended characteristics:

- clinically interpretable
- answerable with a few tool calls
- evidence-based
- well-suited to the synthetic cohort
- capable of revealing bad stopping decisions

## Candidate Intro Tasks

### Task 1: Type 1 or Type 2?

`A patient has diabetes. Is this patient more consistent with Type 1 or Type 2
diabetes, and what evidence supports that conclusion?`

Why this works:

- students understand the distinction clinically
- C-peptide, medications, BMI, and diagnosis history all matter
- there is more than one plausible path through the tools

### Task 2: Is kidney disease part of the story?

`For this patient with diabetes, is there evidence of kidney disease
progression?`

Why this works:

- eGFR, creatinine, UACR, and conditions all matter
- students can see why one lab alone is not enough

### Task 3: Which patient is higher risk?

`Compare two diabetic patients. Which one appears clinically higher risk, and
why?`

Why this works:

- forces synthesis
- encourages comparison rather than isolated lookup
- naturally raises evidence sufficiency questions

## Dataset Presentation Strategy

The session should not start by dumping the whole cohort on students.

Instead, introduce the dataset as a small set of clinically legible stories:

- early Type 2 diabetes
- advanced Type 2 diabetes with CKD
- Type 1 diabetes with low C-peptide
- a borderline or confusing case

This makes the synthetic cohort feel understandable and purposeful.

## What State Should Be Visible

This is one of the most important design decisions.

Students need a persistent state panel showing things like:

- current question
- patients under consideration
- evidence collected
- evidence still missing
- previous steps taken
- whether the answer is ready

This state view is the conceptual replacement for reading the agent loop code.

## What Should Be Hidden

To keep the session accessible, hide or strongly de-emphasize:

- raw message serialization
- SDK object structure
- content-block formatting details
- most of the Python orchestration code
- low-level control flow details

These can live in:

- appendix cells
- instructor materials
- the existing annotated explainer

## Proposed Deliverable

A short structured worksheet or notebook section, not a code artifact.

For each task, students should record:

- the question
- the steps they chose
- the key evidence they found
- their final answer
- whether they think the answer is well supported

Optional extension:

- compare with LLM mode and write one paragraph on differences

## Design Risks

### Risk 1: Too many tools still feels overwhelming

Mitigation:

- present tools as plain-language menu options
- use one focused question at a time
- show tool suggestions or examples

### Risk 2: Students may click randomly

Mitigation:

- require a brief rationale prompt before each step
- use tasks where evidence quality clearly matters

### Risk 3: The interface becomes clunky in notebooks

Mitigation:

- keep interaction simple
- prefer menu-based cells and clean state display
- do not overengineer UI in the first prototype

### Risk 4: Hybrid mode may confuse students

Mitigation:

- sequence the modes clearly
- Human mode first
- Hybrid second
- LLM mode last

## Implications For Session 3

If this session works, Session 3 becomes easier to redesign.

Students will already understand:

- how the loop works
- why tool choice matters
- why stopping too early is dangerous
- why evidence review is necessary

Then Session 3 can focus on:

- evaluating LLM-agent behavior
- red-teaming answers
- spotting unsupported conclusions

instead of trying to teach the loop from scratch.

## Implementation Sketch

At a high level, the notebook implementation could expose a small number of
helper functions such as:

- `show_state()`
- `run_human_turn()`
- `run_llm_turn()`
- `show_trace_summary()`
- `reset_case()`

The notebook should feel like an interactive teaching script, not an agent
framework notebook.

## Open Decisions

### 1. Scope of cases

- Should the session focus on one deep case or two to three shorter cases?

### 2. Student inputs

- Should students choose patient IDs directly?
- Or should the notebook preselect patients for them in the first prototype?

### 3. Tool granularity

- Should `Get labs for a patient` be one tool with selectable lab types?
- Or should there be separate lab-focused menu items?

### 4. Mode progression

- Should all students do Human -> Hybrid -> LLM?
- Or should Hybrid be optional depending on time?

### 5. Interface ambition

- For the spike, do we want a simple notebook text/menu interface?
- Or do we want to explore richer widgets later?

## Recommended Next Step

The next artifact should be a concrete prototype of one case in this format.

Best candidate:

`Type 1 or Type 2?`

That case is clinically intuitive, uses the synthetic phenotype structure well,
and naturally demonstrates why agents need multiple evidence sources rather than
one-step answers.
