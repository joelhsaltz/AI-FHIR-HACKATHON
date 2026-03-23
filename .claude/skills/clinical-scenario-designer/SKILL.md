---
name: clinical-scenario-designer
description: "Use when designing, evaluating, or iterating on clinical scenarios for medical education notebooks. Triggers on: 'design a scenario', 'evaluate this scenario', 'is this scenario too easy', 'clinical depth', 'scenario complexity', 'what should students investigate', 'trivially solvable', or any discussion of what clinical tasks to put in front of students. Also triggers on /scenario-design, /scenario-eval."
---

# Clinical Scenario Designer — Orchestration

This skill dispatches the clinical scenario designer agent. It does NOT contain
the agent's identity or domain knowledge — those live in separate files.

## When to Invoke

- Joel describes a clinical teaching goal and needs a scenario designed
- An existing scenario needs evaluation for clinical depth and difficulty
- A scenario is suspected of being trivially solvable (e.g., single-query shortcut)
- Redesigning scenarios after student feedback reveals the task was too easy or too hard
- Planning what clinical data distinctions should drive a classification or triage task
- Joel says /scenario-design or /scenario-eval

## How to Invoke

### 1. Assemble Context

Read these files and pass their contents to the agent:

| File | Purpose | Always? |
|------|---------|---------|
| `.claude/agents/clinical-scenario-designer/AGENT.md` | Agent identity and evaluation framework | Yes |
| `.claude/agents/project-brief.md` | Project domain context (audience, data, conventions) | Yes |
| `docs/scenarios/*.md` | Existing scenario design docs (if evaluating or extending) | If they exist |
| `.claude/skills/clinical-scenario-designer/references/fhir-data-reference.md` | Detailed FHIR server data inventory | Yes |
| `src/fhir_hackathon_redesign/scenarios.py` | Current scenario implementation (if evaluating) | If evaluating |
| `tasks/todo.md` | Known issues (if it exists) | If it exists |

### 2. Dispatch the Agent

Use the Agent tool with `subagent_type: "general-purpose"`.

Pass the assembled context as the prompt, structured as:

```
## Your Identity
[contents of AGENT.md]

## Project Context
[contents of project-brief.md]

## Existing Scenario Docs
[contents of docs/scenarios/*.md, if any]

## FHIR Data Reference
[contents of fhir-data-reference.md]

## Current Implementation
[contents of scenarios.py, if evaluating]

## Known Issues
[contents of tasks/todo.md, if it exists]

## Task
[what Joel asked for — design a new scenario, evaluate an existing one, etc.]
```

### 3. Interaction Mode

This agent supports DIRECT CONVERSATION with Joel. It is not a background
reviewer that produces a report and exits — it is a design partner that
proposes, gets feedback, and iterates.

The agent has MCP tool access (ICD-10 lookup, PubMed search, bioRxiv search)
and can use them to ground its clinical reasoning in real medical literature
and coding systems. It also has Read, Glob, Grep, WebSearch, and WebFetch.

### 4. Handle the Output

The agent produces structured scenario design documents. After the agent
produces a design or evaluation:

1. **Present it to Joel for review.** Do not act on it automatically.
2. **If Joel approves a new design:** Write it to `docs/scenarios/<scenario-name>.md`.
   This becomes the authoritative design document that other agents consume.
3. **If Joel requests changes:** Continue the conversation with the agent.
4. **If evaluating an existing scenario:** Present the evaluation. If it reveals
   problems, discuss remediation with Joel before touching any code.

The scenario design doc is a shared artifact — the education reviewer and
implementation reviewer both consume it when reviewing notebooks that implement
the scenario.

## What This Skill Does NOT Do

- It does not contain the agent's system prompt (that is in AGENT.md)
- It does not contain domain-specific content (that is in project-brief.md)
- It does not write code or modify generators (the agent designs, others implement)
