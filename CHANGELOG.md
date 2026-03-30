# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Fixed

- **Classify cell showstopper — invisible confirm dropdown.** Colab's form view
  didn't render the second `#@param` field in Step 6. Replaced two-dropdown
  pattern (classification + confirm) with a single dropdown using "← Keep
  investigating" as the safe default. Selecting a classification = submission.

### Added

- **Explanatory feedback on classification.** When students classify incorrectly,
  the feedback now shows key evidence (HbA1c, eGFR, UACR, medications) that
  supports the correct answer. Previously only showed "correct/incorrect."

- **Open in Colab badges.** README.md and GETTING_STARTED.md now have one-click
  "Open in Colab" badges. Notebook discoverability codified as a hard rule in
  CLAUDE.md.

- **Pre-distribution verification hook.** Blocks notebook uploads to Drive unless
  a `.last_verified_<notebook>` timestamp exists and is newer than the notebook.
  Prevents distributing unverified notebooks.

- **Workbench gcloud guard hook.** Blocks `gcloud compute instances start/stop`
  on Workbench instances (must use `gcloud workbench instances` or the skill).

### Changed

- **Weaker default AI prompt.** Step 8's default prompt is now deliberately
  incomplete ("Classify each patient's diabetes management complexity. Use the
  available FHIR query tools.") to force students to actually write prompts.

- **Step number fix.** API key setup text corrected from "Steps 7-9" to
  "Steps 8-9" for Activity 2.

- **API-agnostic provider support (Anthropic + OpenAI).** Students select their
  AI provider via a dropdown in Step 1. A thin 3-function adapter normalizes
  tool calling differences between Anthropic (`claude-sonnet-4-20250514`) and
  OpenAI (`gpt-4.1-mini`). Only the selected provider's SDK is installed.
  Tool schemas use provider-neutral `"parameters"` format, converted at call
  time. Both providers verified end-to-end on Vertex AI against live FHIR data.
  This is important because many students have OpenAI keys but not Anthropic keys.

### Changed

- **Major documentation revision — framework framing.** Rewrote README.md,
  SPEC.md, TECHNICAL.md, and CLAUDE.md to describe a reusable framework for
  generating clinical education notebooks, not a single-course hackathon
  prototype. FHIR is the constant; educational activities vary by use case.
  - README.md: new title ("FHIR Clinical Education Notebook Framework"), two
    quick starts (run existing / create new scenario), architecture overview
  - SPEC.md: scenario template specification, generator script specification,
    pedagogy framework, four agents with decision boundaries
  - TECHNICAL.md: generator pattern documentation, inter-agent communication
    protocol, state management, synthetic EHR pipeline, "connecting a different
    FHIR server" guide
  - CLAUDE.md: "How to Add a New Scenario" workflow, generator pattern,
    clinical agent pipeline, consolidated verification sections, lessons
    learned reference

### Added

- **docs/LESSONS_LEARNED.md** — institutional knowledge from trial and error:
  infrastructure pivots (Local Jupyter → Playwright → Chrome DevTools → Vertex
  AI), scenario design pitfalls, Colab-specific gotchas, verification standards,
  hard rules established through failure
- **Diabetes complexity assessment notebook** — split combined dropdown into
  separate investigate (Step 5) and classify (Step 6) cells with confirmation
  guard. Updated categories to Routine/Moderate/High/No diabetes. Added UACR
  query, Clinical Context Card, neutral evidence indicator. New ground truth
  logic uses multi-factor scoring (HbA1c, eGFR, UACR, medications, CKD).
- **Vertex AI Workbench verification pipeline** — replaces Playwright-based
  Colab automation for notebook testing. SSH tunnel connects localhost:8888
  to a Jupyter server on an e2-standard-4 VM in us-east4. The `mcp-jupyter`
  MCP server provides programmatic cell execution with structured output
  capture (text/HTML/Markdown instead of pixel screenshots).
  - `setup_vertex.sh` — instance lifecycle management: fast-path check, zone
    discovery, instance creation/start, SSH tunnel, health check
  - `stop_vertex.sh` — instance stop + tunnel cleanup for session end
  - Claude Code hooks: PreToolUse auto-starts instance before any
    `mcp__jupyter__*` call; Stop hook shuts it down on exit
  - `REQUEST_TIMEOUT=180` in MCP config for long-running cells
  - 8 capability tests documented in `docs/vertex-ai-test-results.md`:
    FHIR connectivity, package install, sequential execution, rich output,
    error handling, long-running cells, kernel restart, Anthropic API,
    real prototype execution, Colab form cell behavior
  - 7/10 verification checklist items evaluable via MCP; 3/10 require
    manual Colab review (ui_clarity, dashboard_readability, code_hidden)

### Fixed

- **Candidate pool stratification** — all cases were the same phenotype (T1D)
  because shuffle + sequential scan was fragile. Replaced with deterministic
  round-robin: group by `_group`, shuffle within groups, pick T1D -> T2D ->
  no_diabetes -> repeat. Verified on Vertex AI: pool has 89 candidates
  (46 T1D, 32 T2D, 11 no_diabetes), selection produces 4/3/3 mix.

### Changed

- **Documentation overhaul** — README.md, TECHNICAL.md, SPEC.md, CHANGELOG.md
  updated to reflect current state: "You Are the Agent" redesign, Vertex AI
  verification pipeline, Phase 0 prototype status, open design issues.

### Added

- **Clinical agent pipeline** — four domain-independent agents for scenario
  design, education review, implementation review, and synthetic data generation.
  - `.claude/agents/*/AGENT.md` — domain-independent agent identities (no
    hardcoded clinical codes or course names). Work across any clinical domain.
  - `.claude/agents/project-brief.md` — per-project context auto-loaded from
    working directory (BMI 512 learner profile, FHIR data, pedagogy model)
  - `.claude/skills/*/SKILL.md` — thin orchestration layers that assemble
    context and dispatch agents
  - `docs/scenarios/` — shared scenario design artifacts consumed by all agents.
    Four scenarios designed: diabetes type classification, CKD progression risk,
    autoimmune differential, CLL follow-up therapy
  - Agent test results documented in `docs/agent-test-results-2026-03-23.md`

- **Synthetic EHR data generator** integrated from standalone Codex project into
  `synthetic-ehr/`. Phenotype-driven patient generation with clinical coupling
  constraints (eGFR→CKD stage, HbA1c→glucose via ADAG).
  - 6 scripts: generate_patients.py, generate_cohort.py, validate_patients.py,
    validate_phenotypes.py, add_phenotype.py, export_fhir_r4_bundle.py
  - 6 diabetes/CKD phenotypes with anchors, spread, categorical probabilities
  - Seed recording added to summary JSON for reproducibility
  - Generated data gitignored at `synthetic-ehr/generated/`
  - CKD progression phenotypes: 3 new phenotypes for scenario-specific candidate pools

- **Unified notebook quality pipeline** — expanded `colab-notebook-tools` skill
  with student perspective review, interactive walkthrough, and autonomous fix loop.
  - `scripts/colab-tools/colab_common.py` — shared Playwright utilities extracted
    from `colab_screenshot.py` (auth, dialog handling, scroll, DOM traversal)
  - `scripts/colab-tools/colab_interact.py` — individual cell interaction: run
    single cells, set dropdown values, cell-level screenshots, playbook-driven
    scripted interactions
  - `scripts/colab-tools/student_review.py` — sends Colab screenshots + notebook
    to Claude API for systematic pedagogical evaluation against a 10-item checklist
    (task_complexity, case_variety, ui_clarity, etc.)
  - `scripts/colab-tools/student_walkthrough.py` — autonomous agent that plays
    through the notebook as a student: runs setup, selects dropdown options using
    Claude-powered decision-making, captures screenshots at each step
  - `scripts/colab-tools/fix_loop.py` — autonomous iteration loop: generate →
    validate → upload → walkthrough → review → auto-fix → repeat (up to 5 iterations)
  - `.claude/skills/colab-notebook-tools/references/student-review-checklist.md` —
    10-item pedagogy checklist with pass/fail criteria and auto-fixability metadata
  - `.claude/skills/colab-notebook-tools/references/playwright-interaction.md` —
    cell interaction patterns documentation
  - New skill commands: `/nb-review` (student perspective review), `/nb-ship`
    (full autonomous pipeline)

### Changed

- **Refactored `colab_screenshot.py`** to import shared utilities from
  `colab_common.py` instead of duplicating code. Same behavior, cleaner structure.
- **Updated SKILL.md** with 6-layer architecture (authoring → validation →
  interaction → verification → review → autonomous iteration) and all new commands.

- **`colab-notebook-tools` skill** (`.claude/skills/colab-notebook-tools/`) —
  Claude Code skill for the full Jupyter notebook lifecycle: create, edit,
  validate locally, upload to Drive, execute in Colab, and visually verify via
  Playwright screenshots.
  - `scripts/colab-tools/auth_setup.py` — one-time Google sign-in using
    `launch_persistent_context` + anti-detection args (Google blocks plain
    Chromium automation)
  - `scripts/colab-tools/colab_screenshot.py` — Colab screenshotter that scrolls
    via `colab-scroller#notebook-main` element (5-position viewport capture)
  - `scripts/colab-tools/nb_validate.py` — notebook structure + syntax validation
  - `scripts/colab-tools/nb_exec_harness.py` — generic exec() harness for local testing
  - Skill commands: `/nb-auth`, `/nb-validate`, `/nb-verify`
  - Symlinked to `~/.claude/skills/` for global availability across projects
  - Config at `~/.colab-notebook-tools/` (auth.json + browser_data/)

### Fixed

- **Google sign-in blocking** in `auth_setup.py` — Google detects Playwright's
  Chromium as automation and refuses sign-in. Fixed by using
  `launch_persistent_context` with `--disable-blink-features=AutomationControlled`
  and `ignore_default_args=["--enable-automation"]`. Previously tried
  `channel="chrome"`, plain persistent context, and incognito — all blocked.
- **Colab section screenshots all identical** — `colab_screenshot.py` was using
  `window.scrollTo()` which doesn't work in Colab (content is inside a custom
  `<colab-scroller>` web component). Fixed by detecting and scrolling the
  `colab-scroller#notebook-main` element directly.

- **"You Are the Agent" demo prototype** (`prototypes/you_are_the_agent_demo.ipynb`)
  — redesigned notebook with Colab form cells (`cellView: "form"` metadata).
  All code is hidden behind titled Run-button bars with `#@param` dropdowns.
  Students interact purely via menus; FHIR queries are surfaced in output
  (showing actual `GET /Resource?params` requests and FHIR resource types)
  so students learn the data layer without seeing Python code.
- `create_prototype_demo.py` — generator for the demo prototype notebook.
  Produces self-contained Colab notebook with 9 steps: connect, load tools,
  build candidate pool, select case, gather evidence (repeatable), AI coach,
  record answer, watch AI agent, compare & reflect.
- `prototypes/colab_preview_v2.html` — styled HTML mockup simulating the
  Colab student experience with FHIR-grounded toolkit reference, query
  banners, and agent dashboard.
- `test_demo_notebook.py` — smoke test harness that extracts code cells,
  mocks `#@param` values, and runs against the live FHIR server.

### Changed

- Prototype notebook UX redesigned per Phase 0 of the migration plan:
  - All code cells use `cellView: "form"` + `#@title` (hidden in Colab)
  - `#@param` annotations replace `input()` calls (Colab form widgets)
  - `display(Markdown(...))` replaces `print()` for rich output
  - FHIR queries shown in output after each action (resource type, endpoint, parameters)
  - Agent Dashboard shows evidence by FHIR resource, missing evidence with query hints
  - Query log tracks actual FHIR requests, not Python function names
  - AI agent comparison shows FHIR endpoints called at each step
  - Discussion questions reference FHIR resource types explicitly

- `student_materials/run_agent_explained.md` — beginner-friendly walkthrough of
  the `run_agent` function from Session 3. Covers each section of the code with
  plain-English explanations: function signature, initialization, the while loop,
  Claude API calls, tool use detection, message serialization, tool execution,
  the `tool_result` format, and the `max_steps` safety valve. Includes an
  explanation of assistant vs user roles in the messages list, an ASCII flow
  diagram, and a worked example tracing a real 4-step query using actual FHIR
  server data.

### Removed

- Small orientation PDFs (`pre_session{1,2,3}_orientation.pdf`) — no longer
  needed for the course.
- Stale remote branches (`codex/add-reference-materials`,
  `codex/notebook-debug-strategy`, `codex/fhir-auth-v2`,
  `codex/session3-plot-optimization`) that carried ~43 MB of large "Notebook LM
  talks" PDFs in their history. Deleting these branches reduced fresh clone size
  from ~42 MB to ~600 KB and clone time from 2+ minutes to under 10 seconds.

### Changed

- Updated clone URL in README.md to the correct GitHub repository
  (`https://github.com/joelhsaltz/AI-FHIR-HACKATHON.git`).
- Updated repository structure in README.md to reflect current layout (v1/v2/v3
  notebooks, instructor_materials, docs).

- **V3 notebooks** — complete content rewrite targeting SBU LinuxForHealth FHIR
  server with 1,027 phenotype-structured synthetic patients across 6 clinical
  groups. 6 new notebooks: `session{1,2,3}_{student,instructor}_v3.ipynb`.
- `create_v3_notebooks.py` — generates all 6 v3 notebooks from scratch (unlike
  v2 which patched v1 cells, v3 constructs entirely new content).
- **Session 1 v3:** Expanded to HbA1c + creatinine + eGFR (from HbA1c only).
  Adds scatter plot visualization of glycemic control vs kidney function.
- **Session 2 v3:** 5 tools (from 3), adds `search_medications` and
  `search_all_conditions`. Hardcoded agent question investigating Type 2
  diabetes control, medications, and renal function. Post-agent visualization
  with scatter plot and medication frequency bar chart. `max_steps=25`.
- **Session 3 v3:** 7 tools (adds `search_encounters`, `search_patients`).
  Focus on Type 1 vs Type 2 diabetes comparisons. Pre-built C-peptide vs
  HbA1c comparison plot. Structured question suggestions by difficulty.
- All v3 notebooks: phenotype population description, expanded clinical code
  reference with 14 LOINC codes and interpretation thresholds, matplotlib
  visualizations, hardcoded FHIR credentials (synthetic teaching data),
  HbA1c poor control threshold at >7.5%.
- Type 1 vs Type 2 diabetes comparison guide in Session 3 explaining
  C-peptide as the key differentiating lab.

### Fixed

- HbA1c threshold mismatch: changed 7.5% → 7.0% in student-facing materials to match instructor notebooks and project convention. Affected files: `session2_student.ipynb` (3 cells: reference table, prediction question, agent question), `session3_student.ipynb` (1 cell: reference table), `session1_backup.ipynb` (1 cell: clinical scenario). Also added threshold note explaining the Synthea data rationale to student reference tables (matching instructor versions).
- `validate_fhir_server.py`: updated HbA1c poor control threshold from 7.5% to 7.0% in 4 locations (comment, comparison, check label, summary output) to match project convention.

### Added

- `CLAUDE.md` — Project context for Claude Code: key files, commands, conventions.
- `SPEC.md` — Requirements, scope, and design decisions for the hackathon.
- `TECHNICAL.md` — Architecture, implementation deep-dive, and debugging guide.
- `claude_build_instructions.md` — Build specs given to Claude Code per version.

### Removed

- Verification hash (SHA-256 digest) from Session 3 deliverable cell — unnecessary for an informal hackathon and would confuse students. Removed `import hashlib`, hash computation, and hash print line from both `session3_student.ipynb` and `session3_instructor.ipynb`. Updated C7 annotation in `create_annotated_notebooks.py` to remove hash explanation.

### Added

- Annotated instructor notebooks (`session1_instructor_annotated.ipynb`, `session2_instructor_annotated.ipynb`, `session3_instructor_annotated.ipynb`) with explanatory markdown cells (8 each for Sessions 1-2, 9 for Session 3) bridging clinical and technical concepts for the mixed-background audience.
- `create_annotated_notebooks.py` script to generate annotated notebooks from the originals. Reads each source notebook, inserts annotation cells at specified positions, and writes the annotated copy without modifying originals.
- Detailed agent loop annotation (C4b) in Session 3 — "Inside the Agent Loop: How `run_agent()` Works" — providing a phase-by-phase code-level walkthrough of the Reason-Act-Observe cycle. Complements Session 2's high-level overview with implementation specifics (message list as memory, `client.messages.create` decision point, `available_functions` dispatch, tool result feedback, `max_steps` termination).

### Fixed

- Session 1 COMBINED ANALYSIS cell no longer fails with `NameError: name 'df_patients' is not defined` when the PATIENT DEMOGRAPHICS TABLE cell is skipped. The cell now rebuilds `df_patients` from the `patients` list directly, making it self-contained. Applied to all four Session 1 notebooks: `session1_student.ipynb`, `session1_instructor.ipynb`, `session1_backup.ipynb`, `session1_backup_instructor.ipynb`.
- Session 3 ADD SESSION 3 TOOLS cell no longer fails with `NameError: name 'tools' is not defined` when the TOOL SCHEMAS cell is skipped. The cell now initializes the base 3 tool schemas and `available_functions` dict before extending with the 3 Session 3 tools, making it self-contained. Applied to `session3_student.ipynb` and `session3_instructor.ipynb`.
