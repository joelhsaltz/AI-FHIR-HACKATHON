---
name: clinical-education-reviewer
description: "Use when evaluating whether a notebook or activity design delivers on its educational objectives. Triggers on: 'review pedagogy', 'student perspective review', 'does this teach well', 'education review', 'is this engaging', activity design evaluation, or any request to assess learning quality of a notebook. Also triggers on /edu-review."
---

# Clinical Education Reviewer — Orchestration

This skill dispatches the clinical education reviewer agent. It does NOT
contain the agent's identity or domain knowledge — those live in separate files.

## When to Invoke

- **After notebook generation, before Colab verification:** Catches pedagogy
  issues (trivially solvable tasks, fake agency, passive observation) before
  spending time on Colab screenshots.
- **During design:** Evaluates a proposed activity structure described in a
  design doc or spec before implementation begins.
- **After Joel flags UX/pedagogy issues:** Runs a systematic review to find
  related problems beyond the ones already identified.
- Run this skill BEFORE colab-notebook-tools verification (`/nb-verify`).

## How to Invoke

### 1. Assemble Context

Read these files and pass their contents to the agent:

| File | Purpose | Always? |
|------|---------|---------|
| `.claude/agents/clinical-education-reviewer/AGENT.md` | Agent identity and review framework | Yes |
| `.claude/agents/project-brief.md` | Project domain context (audience, pedagogy, conventions) | Yes |
| `docs/scenarios/<relevant-scenario>.md` | Scenario design doc for what the notebook implements | Yes — the agent CONSUMES scenario designs |
| `.claude/skills/clinical-education-reviewer/references/pedagogy-framework.md` | Detailed pedagogy reference | Yes |
| The notebook `.ipynb` file | Primary artifact being reviewed | Yes |
| The generator script (`create_*.py`) | How the notebook was produced (if generated) | If it exists |
| `docs/TEACHING_APPLICATION_PLAN.md` | Session design and learning objectives | If it exists |
| `tasks/todo.md` | Known pedagogy-related issues | If it exists |

The scenario design doc is critical. The education reviewer needs to know the
INTENDED clinical scenario to evaluate whether the notebook delivers on it.
If no scenario doc exists in `docs/scenarios/`, check `docs/SCENARIO_BRIEFS.md`
as a fallback.

### 2. Dispatch the Agent

Use the Agent tool with `subagent_type: "general-purpose"`.

Pass the assembled context as the prompt, structured as:

```
## Your Identity
[contents of AGENT.md]

## Project Context
[contents of project-brief.md]

## Scenario Design
[contents of the relevant scenario doc from docs/scenarios/]

## Pedagogy Framework
[contents of pedagogy-framework.md]

## Notebook Under Review
[contents of the .ipynb file]

## Generator Script
[contents of the create_*.py file, if applicable]

## Teaching Plan
[contents of TEACHING_APPLICATION_PLAN.md, if it exists]

## Known Issues
[contents of tasks/todo.md, if it exists]

## Task
Review this notebook for educational quality. Evaluate whether it delivers
on the learning objectives described in the scenario design and project brief.
```

### 3. Handle the Output

The agent produces a structured review with per-activity assessments, an issues
summary (with severity: blocks-learning / reduces-engagement / cosmetic), and
an overall verdict.

Use the output as follows:

- **blocks-learning issues:** Must be fixed before the notebook ships. Add to
  `tasks/todo.md` if they require design discussion with Joel.
- **reduces-engagement issues:** Fix straightforward ones immediately. Flag
  subjective ones for Joel's input.
- **cosmetic issues:** Fix during the next edit pass.
- **Overall verdict of "needs redesign":** Stop implementation and discuss with
  Joel. Do not try to fix fundamental design problems by tweaking code.

## Relationship to Other Skills

- **clinical-scenario-designer** produces scenario design docs that this skill
  CONSUMES. The education reviewer checks whether the notebook faithfully
  implements the scenario's learning objectives.
- **notebook-implementation-reviewer** checks technical correctness. This skill
  checks learning quality. They are complementary — run both.
- **colab-notebook-tools** handles Colab-specific verification (does it render?
  do widgets work?). Run this skill BEFORE `/nb-verify` — there is no point
  verifying rendering of an activity that does not teach anything.

## What This Skill Does NOT Do

- It does not contain the agent's system prompt (that is in AGENT.md)
- It does not contain domain-specific content (that is in project-brief.md)
- It does not evaluate technical implementation (that is notebook-implementation-reviewer)
