---
name: notebook-implementation-reviewer
description: "Use when a notebook has been generated (or modified) and needs a pre-flight implementation review before uploading to Colab. Catches Colab-specific issues that would otherwise require browser-based debugging. Triggers on: 'review implementation', 'pre-flight check', 'check before upload', 'implementation review', or /nb-preflight. Run this AFTER generating the notebook but BEFORE /nb-verify."
---

# Notebook Implementation Reviewer — Orchestration

This skill dispatches the notebook implementation reviewer agent. It does NOT
contain the agent's identity or domain knowledge — those live in separate files.

## When to Invoke

- After running a generator script to produce a notebook
- Before uploading to Colab for `/nb-verify`
- When modifying a generator script and wanting a quick sanity check
- As the first step in any notebook shipping workflow

This is a fast, local-only check. It does not require Playwright, Google auth,
or a browser.

## How to Invoke

### 1. Assemble Context

Read these files and pass their contents to the agent:

| File | Purpose | Always? |
|------|---------|---------|
| `.claude/agents/notebook-implementation-reviewer/AGENT.md` | Agent identity and check categories | Yes |
| `.claude/agents/project-brief.md` | Project domain context (FHIR server, conventions, data) | Yes |
| `docs/scenarios/<relevant-scenario>.md` | Scenario design doc — for clinical coherence check | Yes |
| The notebook `.ipynb` file | Primary artifact being reviewed | Yes |
| The generator script (`create_*.py`) | How the notebook was produced | Yes |
| `.claude/agents/notebook-implementation-reviewer/references/colab-known-issues.md` | Catalog of Colab quirks from this project | Yes |

The agent checks BOTH technical correctness AND clinical coherence against the
scenario design. The scenario doc tells the agent what evidence types, classification
categories, and difficulty level the notebook is supposed to implement.

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

## Notebook Under Review
[contents of the .ipynb file]

## Generator Script
[contents of the create_*.py file]

## Known Colab Issues
[contents of colab-known-issues.md]

## Task
Review this notebook for implementation issues that would cause failures or
degraded experience in Google Colab. Also check clinical coherence against
the scenario design. Flag technical issues by category and clinical coherence
issues separately.
```

### 3. Handle the Output

The agent produces a structured review with pass/fail for each technical check
category, clinical coherence assessment, and an overall verdict.

Use the output as follows:

- **Safe to upload:** Proceed to `/nb-verify` (Colab screenshots).
- **Needs generator fix:** Fix the generator script, regenerate the notebook,
  and re-run this review.
- **Likely to fail in Colab:** Fix critical issues first — do NOT waste time
  uploading a broken notebook.
- **Clinical coherence issues:** The notebook does not match the scenario design.
  Decide whether to fix the notebook or revise the scenario.

## Integration with Other Skills

```
Generator script modified
        |
        v
  python create_*.py          <-- Generate notebook
        |
        v
  /nb-preflight               <-- THIS SKILL — catch issues early
        |
        v
  /nb-validate                <-- Structure + syntax validation
        |
        v
  /nb-verify                  <-- Upload to Colab + screenshots
        |
        v
  /nb-review                  <-- Student perspective review
```

This skill sits between generation and validation. It catches semantic and
platform-specific issues that `/nb-validate` (pure structure/syntax) would miss,
but that would waste time if discovered only during Colab screenshot review.

- **clinical-scenario-designer** produces scenario design docs. This skill
  CONSUMES them to verify clinical coherence.
- **clinical-education-reviewer** checks pedagogy/learning quality. This skill
  checks technical correctness and clinical coherence. They are complementary.
- **colab-notebook-tools** (`/nb-verify`) does browser-based verification. This
  skill runs BEFORE that to catch issues cheaply.

## What This Skill Does NOT Do

- It does not contain the agent's system prompt (that is in AGENT.md)
- It does not contain domain-specific content (that is in project-brief.md)
- It does not evaluate pedagogy (that is clinical-education-reviewer)
- It does not design scenarios (that is clinical-scenario-designer)
