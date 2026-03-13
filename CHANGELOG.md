# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added

- `student_materials/run_agent_explained.md` — beginner-friendly walkthrough of
  the `run_agent` function from Session 3. Covers each section of the code with
  plain-English explanations: function signature, initialization, the while loop,
  Claude API calls, tool use detection, message serialization, tool execution,
  the `tool_result` format, and the `max_steps` safety valve. Includes an
  explanation of assistant vs user roles in the messages list, an ASCII flow
  diagram, and a worked example tracing a real 4-step query using actual FHIR
  server data.

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
