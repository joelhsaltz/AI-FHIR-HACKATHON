# CLAUDE.md — Project Context for Claude Code

## Project

FHIR + AI Hackathon for BMI 512 (Clinical Informatics and AI) at Stony Brook
University. Three-session educational hackathon teaching FHIR data querying and
AI agent patterns with Claude.

## Repository Layout

```
fhir-hackathon/
├── student_materials/
│   ├── notebooks/          # Student-facing Jupyter notebooks
│   │   ├── session{1,2,3}_student.ipynb      # v1 (public SMART sandbox)
│   │   ├── session{1,2,3}_student_v2.ipynb   # v2 (SBU server, auth patched)
│   │   ├── session{1,2,3}_student_v3.ipynb   # v3 (SBU server, full rewrite)
│   │   └── session1_backup.ipynb              # Local Flask FHIR fallback
│   ├── orientation_pdfs/   # Pre-session slide decks
│   └── README_FOR_STUDENTS.md
├── instructor_materials/
│   ├── notebooks/          # Instructor versions + annotated variants
│   │   ├── session{1,2,3}_instructor.ipynb
│   │   ├── session{1,2,3}_instructor_v2.ipynb
│   │   ├── session{1,2,3}_instructor_v3.ipynb
│   │   ├── session{1,2,3}_instructor_annotated.ipynb
│   │   └── session1_backup_instructor.ipynb
│   ├── tests/              # Notebook validation tests
│   ├── validate_fhir_server.py
│   ├── TESTING_SUMMARY.md
│   └── README_FOR_INSTRUCTORS.md
├── docs/
│   ├── fhir_hackathon_claude_code_spec.md   # Original build spec (historical)
│   └── SIMPLIFICATION_SUMMARY.md
├── create_annotated_notebooks.py   # Generates annotated instructor notebooks
├── create_v2_notebooks.py          # Generates v2 notebooks (auth patching)
├── create_v3_notebooks.py          # Generates v3 notebooks (full rewrite)
├── README.md
├── CHANGELOG.md
├── SPEC.md
├── TECHNICAL.md
└── claude_build_instructions.md
```

## Key Commands

```bash
# Generate v3 notebooks (SBU server, full rewrite)
python create_v3_notebooks.py
# Expected: S1: 21 cells, S2: 19 cells, S3: 24 cells (x2 student+instructor)

# Regenerate annotated instructor notebooks (v1 only)
python create_annotated_notebooks.py

# Validate FHIR server connectivity and data availability
python instructor_materials/validate_fhir_server.py

# Run notebook validation tests
cd instructor_materials/tests && python run_tests.py
```

## Key Files

| File | Purpose |
|------|---------|
| `student_materials/notebooks/session{1,2,3}_student_v3.ipynb` | V3 student notebooks (current) |
| `instructor_materials/notebooks/session{1,2,3}_instructor_v3.ipynb` | V3 instructor notebooks (current) |
| `create_v3_notebooks.py` | Generates all 6 v3 notebooks from scratch |
| `create_annotated_notebooks.py` | Inserts annotation cells into v1 instructor notebooks |
| `CHANGELOG.md` | All changes documented here |

## Conventions

- **Notebooks share cell IDs** — Student and instructor notebooks for the same
  session use identical cell IDs so edits can be applied consistently.
- **Annotated notebooks are generated, not hand-edited.** Always edit
  `create_annotated_notebooks.py` and re-run, never edit the `_annotated.ipynb`
  files directly.
- **FHIR server (v3)** — SBU LinuxForHealth at
  `https://lfh-fhir.eastus2.cloudapp.azure.com:9443/fhir-server/api/v4`,
  Basic Auth (`fhiruser`/`BmI512@ccess`), self-signed cert. 1,027 synthetic
  patients across 6 phenotypes.
- **FHIR server (v1/v2)** — Public SMART sandbox, no auth required.
- **LLM** — Anthropic Claude only (`claude-sonnet-4-20250514`). No dual-provider
  abstraction.
- **HbA1c threshold (v3)** — >7.5% for "poor control" (richer synthetic data).
- **HbA1c threshold (v1/v2)** — >7.0% for "poor control" (Synthea data skews low).
- **V3 notebooks are generated, not hand-edited.** Always edit
  `create_v3_notebooks.py` and re-run.

## Notebook Debugging Strategy

When debugging notebooks end-to-end, do NOT use `nbconvert --execute` (too slow,
no incremental feedback, hangs on `input()` calls). Instead:

1. Create a temporary harness script (e.g., `debug_sessionN.py`) that:
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

## Git Workflow

Follow the governance rules in `~/.claude/CLAUDE.md`:
- Never push directly to main — use branches + PRs
- Branch naming: `codex/<topic>`
- One open PR per repo at a time
- Update CHANGELOG.md with every change
