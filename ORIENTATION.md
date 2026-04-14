# Orientation

## What is this?

A framework for generating Google Colab notebooks that teach clinical
informatics through FHIR data querying. Built for BMI 512 at Stony Brook
University, but designed to be reusable by any instructor with a FHIR server.

## What's the usable artifact?

One notebook: **`notebooks/you_are_the_agent_demo.ipynb`**

Students open it in Colab, add their API key, and work through two activities:
1. Manually query a FHIR server to assess diabetes management complexity
2. Write a prompt for an AI agent to do the same thing, then compare strategies

It supports both Anthropic (Claude) and OpenAI (GPT) -- students choose via
dropdown.

## How is the notebook made?

`create_prototype_demo.py` generates the notebook. Never edit the `.ipynb`
directly. Run `python create_prototype_demo.py` to regenerate after changes.
Run `python test_demo_notebook.py` to smoke-test against the live FHIR server.

## What's in `archive/`?

Everything that isn't current. Old 3-session notebooks, legacy automation
scripts, orphaned Python modules, old design docs. Kept for reference, not
for use.

## Where are the design docs?

- `docs/scenarios/` -- clinical scenario designs (4 designed, 1 implemented)
- `docs/LESSONS_LEARNED.md` -- what went wrong and what we learned
- `docs/TEACHING_APPLICATION_PLAN.md` -- pedagogical framework
- `SPEC.md` -- requirements and design decisions
- `TECHNICAL.md` -- architecture deep-dive

## How do I add a new scenario?

See [GETTING_STARTED.md](GETTING_STARTED.md) for the full walkthrough, or
the "How to Add a New Scenario" section in [CLAUDE.md](CLAUDE.md).

## Key directories

| Directory | What's in it |
|-----------|-------------|
| `notebooks/` | Distributable notebooks (the product) |
| `docs/` | Design docs and scenario designs |
| `scripts/` | FHIR validator + hook scripts |
| `synthetic-ehr/` | Synthetic patient data generation pipeline |
| `tests/` | Vertex AI test notebooks |
| `archive/` | Everything old |
