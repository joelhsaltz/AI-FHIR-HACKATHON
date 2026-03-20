# CLAUDE.md — Project Context for Claude Code

## Project

FHIR + AI Hackathon for BMI 512 (Clinical Informatics and AI) at Stony Brook
University. Three-session educational hackathon teaching FHIR data querying and
AI agent patterns with Claude. The redesign shifts from code-explanation to
"You Are the Agent" pedagogy: students act as the agent via menus, then compare
to how the LLM does it (Human → Hybrid → LLM progression).

## Repository Layout

```
fhir-hackathon/
├── archive/                    # Old v1/v2/v3 materials (preserved for reference)
│   ├── student_materials/notebooks/
│   ├── instructor_materials/notebooks/
│   └── generators/
├── src/fhir_hackathon_redesign/   # Core Python modules
│   ├── __init__.py
│   ├── fhir.py                 # FHIR client + Claude tool schemas
│   ├── scenarios.py            # Scenario configs, state management, candidate builders
│   ├── config.py               # Settings (Anthropic API key, FHIR creds)
│   ├── claude_agent.py         # Claude agent loop (being built)
│   └── capstone.py             # Population ranking helpers (being built)
├── prototypes/                 # Phase 0 prototype notebooks
│   └── you_are_the_agent_prototype.ipynb
├── docs/                       # Design documents
│   ├── REDESIGN_SPIKE.md
│   ├── SCENARIO_BRIEFS.md
│   ├── SESSION2_YOU_ARE_THE_AGENT_SPIKE.md
│   ├── TEACHING_APPLICATION_PLAN.md
│   ├── fhir_hackathon_claude_code_spec.md  # historical
│   └── SIMPLIFICATION_SUMMARY.md
├── student_materials/          # Final student-facing materials
│   ├── orientation_pdfs/
│   ├── run_agent_explained.md
│   └── README_FOR_STUDENTS.md
├── instructor_materials/       # Instructor materials
│   ├── validate_fhir_server.py
│   ├── tests/
│   └── README_FOR_INSTRUCTORS.md
├── .claude/skills/colab-notebook-tools/  # Colab notebook lifecycle skill
│   ├── SKILL.md                         # Main skill definition
│   └── references/                      # Verification + creation pattern docs
├── scripts/colab-tools/                 # Supporting scripts for notebook tools
│   ├── auth_setup.py                    # One-time Google auth → storageState
│   ├── colab_screenshot.py              # Playwright Colab screenshotter
│   ├── nb_validate.py                   # Structure + syntax validation
│   ├── nb_exec_harness.py              # Generic exec() harness
│   └── requirements.txt
├── create_prototype_demo.py             # Generates demo prototype (FHIR-grounded, form cells)
├── create_prototype_v2.py              # Earlier iteration (form cells, less FHIR grounding)
├── create_main_teaching_notebook.py    # Generates main teaching notebook (being built)
├── create_capstone_notebook.py         # Generates capstone notebook (being built)
├── create_session2_you_are_the_agent_prototype.py  # Original prototype generator
├── test_demo_notebook.py               # Smoke test for demo prototype
├── run_main_teaching_smoke_test.py     # Smoke test (being built)
├── run_capstone_smoke_test.py          # Smoke test (being built)
├── .env.example
├── README.md, CHANGELOG.md, SPEC.md, TECHNICAL.md
└── CLAUDE.md
```

## Key Commands

```bash
# Generate demo prototype notebook (current)
python create_prototype_demo.py

# Smoke test the demo prototype (runs against live FHIR server)
python test_demo_notebook.py

# Generate original prototype notebook (superseded)
python create_session2_you_are_the_agent_prototype.py

# Validate FHIR server connectivity and data availability
python instructor_materials/validate_fhir_server.py

# Generate main teaching notebook (when ready)
python create_main_teaching_notebook.py

# Generate capstone notebook (when ready)
python create_capstone_notebook.py

# Run smoke tests (when ready)
python run_main_teaching_smoke_test.py
python run_capstone_smoke_test.py

# Colab notebook tools — the primary notebook verification workflow
python scripts/colab-tools/auth_setup.py                              # One-time Google sign-in (persistent context + anti-detection)
python scripts/colab-tools/colab_screenshot.py <file_id> --sections   # Run all cells + 5-position screenshots
python scripts/colab-tools/colab_screenshot.py <file_id> --no-run --sections  # Screenshots only (no execution)
python scripts/colab-tools/nb_validate.py <path.ipynb>                # Structure + syntax validation
python scripts/colab-tools/nb_exec_harness.py <path.ipynb> --skip-pattern "LLM|agent"  # Local exec test

# Old screenshot tool (SUPERSEDED — use scripts/colab-tools/ instead)
# python screenshot_colab.py <file_id>
```

## Key Files

| File | Purpose |
|------|---------|
| `src/fhir_hackathon_redesign/fhir.py` | FHIR client + Claude tool schemas (Anthropic `input_schema` format) |
| `src/fhir_hackathon_redesign/scenarios.py` | Scenario configs, session state, candidate builders |
| `src/fhir_hackathon_redesign/claude_agent.py` | Claude agent loop (tool_use/tool_result cycling) |
| `src/fhir_hackathon_redesign/config.py` | Settings: `ANTHROPIC_API_KEY`, FHIR creds |
| `prototypes/you_are_the_agent_demo.ipynb` | Demo prototype — FHIR-grounded, Colab form cells |
| `create_prototype_demo.py` | Generator for the demo prototype |
| `test_demo_notebook.py` | Smoke test harness for the demo prototype |
| `prototypes/colab_preview_v2.html` | HTML mockup of Colab student experience |
| `prototypes/you_are_the_agent_prototype.ipynb` | Original Phase 0 prototype (superseded) |
| `create_session2_you_are_the_agent_prototype.py` | Generator for original prototype |
| `screenshot_colab.py` | Old Colab screenshot tool (SUPERSEDED by `scripts/colab-tools/colab_screenshot.py`) |
| `scripts/colab-tools/auth_setup.py` | Google auth for Colab tools (persistent context + anti-detection args) |
| `scripts/colab-tools/colab_screenshot.py` | Colab screenshotter — scrolls `colab-scroller` element, 5-position capture |
| `create_main_teaching_notebook.py` | Generator for the main teaching notebook |
| `docs/TEACHING_APPLICATION_PLAN.md` | Full pedagogy and session design |
| `docs/REDESIGN_SPIKE.md` | Architecture and technical decisions |
| `student_materials/run_agent_explained.md` | Beginner-friendly walkthrough of the agent loop |
| `CHANGELOG.md` | All changes documented here |

## Conventions

- **Notebooks are generated, not hand-edited.** Always edit the generator script
  and re-run. Never edit `.ipynb` files directly.
- **Self-contained Colab notebooks** — Generated notebooks inline all code as
  string constants. No `src/` imports in generated notebooks.
- **FHIR server** — SBU LinuxForHealth at
  `https://lfh-fhir.eastus2.cloudapp.azure.com:9443/fhir-server/api/v4`,
  Basic Auth (`fhiruser`/`BmI512@ccess`), self-signed cert. 1,027 synthetic
  patients across 6 phenotypes.
- **LLM** — Anthropic Claude only (`claude-sonnet-4-20250514`). No dual-provider
  abstraction.
- **HbA1c threshold** — >7.5% for "poor control".
- **"You Are the Agent" pedagogy** — Human → Hybrid → LLM progression. Menu-driven
  interaction in human mode (no code writing by students).
- **End-to-end testing in the student environment** — Every notebook must be
  tested in the actual environment students will use (Google Colab). Local
  Jupyter testing, nbconvert HTML exports, and smoke test harnesses are useful
  for catching code errors, but they are NOT sufficient for verifying the
  student experience. Before declaring any notebook done:
  1. Upload to Google Drive
  2. Open in Colab
  3. Run all cells against the live FHIR server
  4. Take screenshots and visually verify: markdown renders, code is hidden,
     form widgets appear, tables display, FHIR query banners show
  Do not substitute local testing for this. Do not mock the student environment.
  Use `scripts/colab-tools/colab_screenshot.py` for automated Playwright-based
  Colab screenshots (requires one-time auth via `scripts/colab-tools/auth_setup.py`).

## Notebook Debugging Strategy

When debugging notebooks end-to-end, do NOT use `nbconvert --execute` (too slow,
no incremental feedback, hangs on `input()` calls). Instead:

1. Create a temporary harness script (e.g., `debug_session.py`) that:
   - Extracts code cells from the notebook in order
   - Runs each cell in a shared namespace via `exec()`
   - Reports PASS/FAIL with timing after each cell
   - Caps agent `max_steps` at 5 (enough to verify the loop works)
   - Mocks `input()` calls with test values
   - Uses per-cell timeouts (180s for agent cells, 60s for others)
   - Fails fast if setup/connectivity cells fail
2. Run the harness and report results per cell group
3. Fix errors in the generator script (not the notebook directly), regenerate, re-run
4. Clean up the harness script when done

## Verification Standard — Hard Rule

**Notebooks must be verified running in Google Colab with live FHIR data.** No
mocks, no "it should work." This project produces educational materials where the
UI and user experience are the product.

### Two-stage verification

1. **Automated Colab testing (Claude's job):** Use the colab-notebook-tools
   skill (`/nb-verify`) to run all cells in Colab against the live FHIR server
   and capture screenshots at 5 scroll positions. Claude reviews the screenshots
   for: code errors, cell execution failures, rendering issues, broken widgets,
   missing output. This is the iteration loop — fix issues in the generator,
   regenerate, re-upload, re-screenshot until clean. Requires one-time Google
   sign-in via `scripts/colab-tools/auth_setup.py`, then runs autonomously.

2. **Manual review (Joel's job):** Once automated testing shows the notebook is
   technically working, Joel does a final review in Colab to verify the student
   experience — pedagogy flow, clarity, visual polish. This is the sign-off, not
   the debugging loop.

### What counts as verified

1. **Local harness passes** (see Notebook Debugging Strategy above) — necessary
   but NOT sufficient.
2. **Automated Colab screenshots** show all cells executed successfully with
   live FHIR data, correct rendering, and no errors. Claude reviews these.
3. **Joel's manual review** confirms the student experience is correct. This is
   the final deliverable.

### What does NOT count

- `nbconvert --execute` passing locally
- "The code looks correct" or "this should work"
- Running cells in a local Jupyter instance (Colab has different behavior)
- Testing against a mock or local FHIR server
- Verifying only the generator script without running the generated notebook

### Why this exists

This project has two failure modes: (1) Claude declaring success without running
in Colab at all (caught by requiring Colab screenshots), and (2) requiring Joel
to manually screenshot every iteration (too slow, blocks the fix-regenerate-test
loop). Automated Colab testing solves both — Claude can iterate independently on
technical issues, and Joel reviews only when things are working.

### When to stop and ask

If you cannot verify in Colab (e.g., browser automation broken, auth issues,
server down), **stop and tell the user**. Do not substitute a lesser form of
verification and call it done. The user will decide how to proceed.

## Notebook Change Rule — Hard Rule

**Any time a notebook is created or modified, it MUST be tested in Google Colab
with live FHIR data before the change is considered complete.** This is not
optional and not deferrable. The test sequence is:

1. Regenerate the notebook from the generator script
2. Run local validation (`nb_validate.py` + smoke test)
3. Upload to Google Drive
4. Run all cells in Colab via `colab_screenshot.py --sections`
5. Review screenshots for errors, rendering issues, and correct behavior
6. Fix → regenerate → re-upload → re-screenshot until clean

Skipping Colab testing because "the code looks correct" or "it passed locally"
is never acceptable.

## TO-DO: Future Improvements

- **Reversible code toggle:** Build a proper JS-based button injected into cell
  output that lets students show/hide code without entering edit mode.
  Double-clicking the title bar currently clears execution state, and the
  "Show code" link is one-way. A future iteration should add a toggle button
  that manipulates the DOM safely. (Added 2026-03-20)

## Git Workflow

Follow the governance rules in `~/.claude/CLAUDE.md`:
- Never push directly to main — use branches + PRs
- Branch naming: `codex/<topic>`
- One open PR per repo at a time
- Update CHANGELOG.md with every change

## Colab Notebook Tools Skill

A local Claude Code skill at `.claude/skills/colab-notebook-tools/` covers the
full notebook lifecycle: create, edit, validate, execute in Colab, visually verify.

**Skills available:** `/nb-auth`, `/nb-validate`, `/nb-verify`
**Scripts:** `scripts/colab-tools/` (auth_setup.py, colab_screenshot.py, nb_validate.py, nb_exec_harness.py)
**Config at `~/.colab-notebook-tools/`:**
- `auth.json` — Playwright storageState (Google session cookies)
- `browser_data/` — Persistent Chromium profile for `auth_setup.py`

**Auth approach:** `auth_setup.py` uses `launch_persistent_context` with anti-detection
args (`--disable-blink-features=AutomationControlled` + `ignore_default_args=["--enable-automation"]`)
to bypass Google's automation blocking. After sign-in, cookies are exported via
`storageState` for use by `colab_screenshot.py`.

**Scroll handling:** Colab uses `<colab-scroller id="notebook-main">` as its scroll
container. The screenshot script detects this and scrolls it directly (not `window.scrollTo`).

The skill is symlinked to `~/.claude/skills/colab-notebook-tools` for global
availability. **Future plan:** extract into a standalone distributable plugin.

## Active Plans

| Plan file | Description | Status |
|-----------|-------------|--------|
| `~/.claude/plans/rosy-roaming-hartmanis.md` | Full redesign migration: Phase 0 prototype → Phase 6 smoke tests + docs | In Progress — Phase 0 prototype built |
