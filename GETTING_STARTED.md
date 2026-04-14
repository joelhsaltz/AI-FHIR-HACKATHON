# Getting Started: Faculty Setup Guide

A focused walkthrough for setting up the FHIR Clinical Education Notebook
Framework. By the end, you'll have generated a working notebook, tried it in
Google Colab, and used AI agents to design your own clinical scenario.

---

## Try It First

Before cloning anything, see what the framework produces:

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/joelhsaltz/AI-FHIR-HACKATHON/blob/main/prototypes/you_are_the_agent_demo.ipynb)

This is the demo notebook you'll learn to generate in Phase 2. Running it
first gives you context for what the framework produces. You'll need an API
key (Anthropic or OpenAI) in Colab Secrets for Activity 2, but Activity 1
works without one.

---

## Prerequisites

You need these before starting:

| Requirement | How to get it |
|-------------|---------------|
| **Python 3.10+** | `python3 --version` to check. Install from [python.org](https://www.python.org/downloads/) if needed. |
| **git** | `git --version` to check. |
| **LLM API key** | An Anthropic or OpenAI API key. See [Which API key?](#which-api-key) below. |
| **Google account** | For Google Colab (free tier is sufficient). |
| **Claude Code** (for Phase 4) | Anthropic's CLI for AI-assisted development. See [Claude Code setup](#claude-code-setup) below. |

### Which API key?

You need **one** of these for the AI agent activities (Activity 2 in the
notebook). Activity 1 works without any API key.

- **Anthropic API key** — Best clinical reasoning accuracy in our testing.
  Get one at [console.anthropic.com](https://console.anthropic.com/).
- **OpenAI API key** — Works well. Get one at
  [platform.openai.com](https://platform.openai.com/).

**Azure AI Foundry note:** If your institution provides OpenAI access through
Azure AI Foundry, those keys use the `AzureOpenAI` client class with an
endpoint URL — they won't work with this framework's current `OpenAI` client.
Use a direct OpenAI key (from platform.openai.com) or an Anthropic key instead.
Azure support is planned for a future update.

### Claude Code setup

Claude Code is required for Phase 4 (creating your own scenarios with the
agent pipeline). You can skip it for Phases 1-3.

```bash
# Install Claude Code
npm install -g @anthropic-ai/claude-code

# Verify
claude --version
```

Claude Code requires a Claude subscription (Max, Teams, or API). See
[claude.ai/code](https://claude.ai/code) for details.

---

## Phase 1: Clone and Configure

```bash
# Clone the repository
git clone https://github.com/joelhsaltz/AI-FHIR-HACKATHON.git
cd AI-FHIR-HACKATHON

# Set up credentials
cp .env.example .env
```

Edit `.env` and add your API key:

```bash
# For Anthropic:
ANTHROPIC_API_KEY=sk-ant-your-key-here

# OR for OpenAI:
OPENAI_API_KEY=sk-your-key-here
```

The FHIR server credentials are pre-configured — no changes needed for
`FHIR_BASE`, `FHIR_USERNAME`, or `FHIR_PASSWORD`.

### Checkpoint: Verify FHIR connectivity

```bash
python instructor_materials/validate_fhir_server.py
```

You should see **9/10 checks pass**:

```
[PASS] Server reachable: FHIR version 4.0.1
[PASS] Type 2 Diabetes conditions found: 20 entries, 20 unique patients
[PASS] Patient resources fetchable: 10/10 succeeded
...
[FAIL] Hypertension conditions found: 0 conditions, 0 patients
```

The Hypertension check fails by design — diabetes-specific condition codes are
scrambled in the data to prevent students from shortcutting the classification
task. This is expected.

---

## Phase 2: Generate and Run the Demo Notebook

### Generate the notebook

```bash
python create_prototype_demo.py
# Output: prototypes/you_are_the_agent_demo.ipynb
```

### Run the local smoke test

```bash
python test_demo_notebook.py
```

You should see all cells pass against the live FHIR server. This tests the
notebook's FHIR queries and logic without calling any LLM API.

### Try it in Google Colab

**Quickest way:** Click this badge to open the notebook directly:

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/joelhsaltz/AI-FHIR-HACKATHON/blob/main/prototypes/you_are_the_agent_demo.ipynb)

Or manually: go to [colab.research.google.com](https://colab.research.google.com/), click **GitHub** in the Open Notebook dialog, search for `joelhsaltz`, select the `AI-FHIR-HACKATHON` repo, and choose `prototypes/you_are_the_agent_demo.ipynb`.

Then:
1. Add your API key to Colab Secrets:
   - Click the **key icon** in the left sidebar
   - Add a secret named `ANTHROPIC_API_KEY` or `OPENAI_API_KEY` with your key
   - Toggle **Notebook access** on
4. In **Step 1**, select your AI provider from the dropdown (Anthropic or OpenAI)
5. Run cells top-to-bottom

### What you'll experience

**Activity 1 — You are the agent:** You manually choose FHIR queries from
dropdown menus to investigate patients, then classify their diabetes management
complexity. You get immediate feedback after each classification.

**Activity 2 — You are the prompt engineer:** You write a natural-language
prompt telling an AI agent how to approach the same cases. The agent runs
autonomously using your instructions, making its own FHIR queries. You can
iterate on your prompt and compare results.

### Checkpoint

After completing both activities, you should see a **Summary** table comparing
your accuracy and query count against the AI agent's. The AI agent should
classify 6 patients and display its reasoning for each.

---

## Phase 3: Create Your Own Scenario with the Agent Pipeline

This is where it gets interesting. The repo includes four AI agents (built as
Claude Code skills) that help you design, build, and review clinical education
scenarios. You need [Claude Code](#claude-code-setup) installed for this phase.

### Start Claude Code in the project

```bash
cd AI-FHIR-HACKATHON
claude
```

Claude Code reads the project's `CLAUDE.md` file and understands the framework
automatically. The four agents are:

| Agent | What it does | How to invoke |
|-------|-------------|---------------|
| **Clinical Scenario Designer** | Designs a clinical scenario: question, evidence requirements, classification categories, difficulty calibration | Type `/scenario-design` |
| **Synthetic Data Architect** | Generates synthetic patient data matching your scenario's clinical requirements | Type `/synth-data` |
| **Notebook Implementation Reviewer** | Pre-flight technical check: Colab form syntax, cell dependencies, clinical coherence | Type `/nb-preflight` |
| **Clinical Education Reviewer** | Evaluates pedagogy: is the activity engaging? Too easy? Too hard? | Type `/edu-review` |

### Workflow

1. **Design a scenario.** Type `/scenario-design` in Claude Code. The agent
   will ask you about the clinical question, what FHIR resources are relevant,
   what classification categories to use, and where the ambiguity lives. It
   produces a design document at `docs/scenarios/<name>.md`.

2. **Generate synthetic data** (if needed). If the existing FHIR server data
   doesn't cover your scenario, type `/synth-data`. The agent reads your
   scenario design and produces phenotype configs for the synthetic data
   pipeline.

3. **Build a generator script.** Copy `create_prototype_demo.py` and modify it
   for your scenario. Claude Code can help — it understands the generator
   pattern and can write the cells for you.

4. **Review.** Run `/nb-preflight` for technical correctness, then `/edu-review`
   for pedagogical quality. Both agents read your scenario design document and
   check the notebook against it.

### Existing scenario designs

Four scenarios are already designed (only the first is implemented as a
notebook):

| Scenario | Design doc | Status |
|----------|-----------|--------|
| Diabetes management complexity | `docs/scenarios/diabetes-type-classification.md` | Implemented |
| Autoimmune differential | `docs/scenarios/autoimmune-differential.md` | Designed |
| CKD progression risk | `docs/scenarios/ckd-progression-risk.md` | Designed |
| CLL follow-up therapy | `docs/scenarios/cll-follow-up-therapy-selection.md` | Designed |

You can implement one of these or design your own from scratch.

### Checkpoint

After `/scenario-design`, you should have a design document in `docs/scenarios/`
that specifies the clinical question, classification categories, required FHIR
queries, and where the ambiguity lives. After `/edu-review`, you should have a
severity-rated review of your activity's pedagogical quality.

---

## Phase 4: Optional — Vertex AI Verification Pipeline

For production use, notebooks should be verified running against the live FHIR
server in a Jupyter environment. The framework uses Google Vertex AI Workbench
for this — an SSH tunnel to a managed Jupyter instance with programmatic cell
execution.

**You don't need this to get started.** Manual verification in Colab (Phase 2)
is sufficient for trying the framework. Set up Vertex AI when you're ready to
build a production verification pipeline.

### What's needed

- A Google Cloud project with Vertex AI Workbench enabled
- A Workbench instance (e2-standard-4 is sufficient)
- The `gcloud` CLI authenticated
- SSH tunnel scripts (`setup_vertex.sh`, `stop_vertex.sh` in the repo)

See the full setup guide in `TECHNICAL.md` under "Verification Infrastructure"
and the Vertex AI skill documentation referenced in `CLAUDE.md`.

---

## Key Documentation

| Document | What it covers |
|----------|---------------|
| [README.md](README.md) | Project overview, architecture, all scenarios |
| [TECHNICAL.md](TECHNICAL.md) | Generator pattern, agent pipeline, FHIR tools, provider adapter |
| [SPEC.md](SPEC.md) | Requirements, scenario template, design decisions |
| [docs/LESSONS_LEARNED.md](docs/LESSONS_LEARNED.md) | What went wrong and what we learned building this |

---

## Troubleshooting

**"AI Agent: Not configured" in the notebook's connection status**
Your API key isn't being found. In Colab, check that you added it to Secrets
(key icon, left sidebar) with the correct name (`ANTHROPIC_API_KEY` or
`OPENAI_API_KEY`) and toggled "Notebook access" on.

**FHIR validation shows 0/10 or connection errors**
The SBU teaching server may be temporarily down. The server uses a self-signed
certificate, so you may see SSL warnings — that's normal.

**Smoke test fails on agent cells**
Agent cells (Steps 8-9) are skipped in the smoke test because they require an
LLM API call. If non-agent cells fail, check your FHIR connectivity.

**Claude Code agents don't respond to `/scenario-design`**
Make sure you're running `claude` from the repo root directory. Claude Code
reads `.claude/agents/` and `.claude/skills/` from the project directory.

**Azure AI Foundry keys don't work**
See the [Azure note](#which-api-key) above. Azure-hosted keys require a
different client class. Use a direct OpenAI key or Anthropic key instead.
