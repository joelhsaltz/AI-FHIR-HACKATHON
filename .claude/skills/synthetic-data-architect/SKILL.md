---
name: synthetic-data-architect
description: "Use when designing phenotype configurations for synthetic patient data, creating cohort plans, or evaluating whether generated data is clinically plausible. Triggers on: 'design phenotypes', 'generate test data', 'phenotype config', 'synthetic data', 'cohort plan', or any discussion of translating clinical scenarios into generator configs. Also triggers on /synth-data, /phenotype-design."
---

# Synthetic Data Architect

Dispatches an agent that collaborates on phenotype design for the synthetic
EHR data generator. The agent translates clinical phenotype descriptions
(from scenario design docs) into generator-consumable JSON configs, runs
test batches, and evaluates plausibility.

## When to Invoke

- After a scenario design doc is produced and approved by Joel
- When Joel wants to create or modify phenotype configs for the generator
- When exploring what variables a new clinical domain would need
- When evaluating whether existing phenotype configs produce plausible patients
- When creating a cohort plan for a new scenario

## How to Invoke

Dispatch a subagent via the Agent tool. This agent supports **direct
conversation** — Joel collaborates interactively on phenotype parameter
tuning, like the Clinical Scenario Designer.

### Context to pass

Read ALL of the following before dispatching:

1. `.claude/agents/synthetic-data-architect/AGENT.md` — agent identity
2. `.claude/agents/project-brief.md` — project context
3. The relevant scenario doc from `docs/scenarios/` (if one exists)
4. `synthetic-ehr/references/phenotype_schema.md` — generator schema
5. `synthetic-ehr/assets/phenotype_template.json` — existing phenotypes

### What to expect

The agent will:
- Propose phenotype configs with specific anchor values, spreads, and
  categorical probabilities
- Run `validate_phenotypes.py` to check schema validity
- Generate small test batches (10-20 patients) and run `validate_patients.py`
- Show sample patient data and flag implausible values
- For new domains: produce a variable extension spec documenting what
  generator changes are needed

### After the agent completes

1. Review the phenotype configs with Joel
2. If approved: the configs are ready for full cohort generation
3. If variable extensions are needed: hand off the extension spec as
   a generator implementation task
4. Store final configs in `synthetic-ehr/assets/`

## Integration with Other Skills

```
/scenario-design (Scenario Designer)
        │
        ▼ produces scenario doc
  docs/scenarios/<name>.md
        │
        ▼
/synth-data (THIS SKILL)
        │
        ▼ produces phenotype JSON + cohort plan
  synthetic-ehr/assets/
        │
        ▼ generates data
  synthetic-ehr/generated/*.csv
```

This skill sits between scenario design and data generation. It requires
a scenario design (or at minimum a clinical domain description) as input,
and produces generator-ready configs as output.

## Relationship to Other Skills

- **clinical-scenario-designer** produces the clinical phenotype descriptions
  this agent translates into configs. Run scenario design FIRST.
- **clinical-education-reviewer** and **notebook-implementation-reviewer**
  operate on notebooks, not data generation. They are downstream consumers.
- **colab-notebook-tools** handles notebook verification. Independent of
  this skill.
