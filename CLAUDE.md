# CLAUDE.md — Project Context for Claude Code

## Project

FHIR + AI Hackathon for BMI 512 (Clinical Informatics and AI) at Stony Brook
University. Three-session educational hackathon teaching FHIR data querying and
AI agent patterns with Claude.

## Repository Layout

```
fhir-hackathon/
├── student_materials/
│   ├── notebooks/          # Student-facing Jupyter notebooks (Sessions 1-3)
│   │   ├── session1_student.ipynb
│   │   ├── session1_backup.ipynb   # Local Flask FHIR fallback
│   │   ├── session2_student.ipynb
│   │   └── session3_student.ipynb
│   ├── orientation_pdfs/   # Pre-session slide decks
│   └── README_FOR_STUDENTS.md
├── instructor_materials/
│   ├── notebooks/          # Instructor versions + annotated variants
│   │   ├── session{1,2,3}_instructor.ipynb
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
├── README.md
├── CHANGELOG.md
├── SPEC.md
├── TECHNICAL.md
└── claude_build_instructions.md
```

## Key Commands

```bash
# Regenerate annotated instructor notebooks after editing source notebooks
python create_annotated_notebooks.py
# Expected output: Session 1: 27 cells, Session 2: 24 cells, Session 3: 30 cells

# Validate FHIR server connectivity and data availability
python instructor_materials/validate_fhir_server.py

# Run notebook validation tests
cd instructor_materials/tests && python run_tests.py
```

## Key Files

| File | Purpose |
|------|---------|
| `student_materials/notebooks/session3_student.ipynb` | Session 3 student notebook (deliverable cell here) |
| `instructor_materials/notebooks/session3_instructor.ipynb` | Session 3 instructor version |
| `create_annotated_notebooks.py` | Inserts annotation markdown cells into instructor notebooks |
| `CHANGELOG.md` | All changes documented here |

## Conventions

- **Notebooks share cell IDs** — Student and instructor notebooks for the same
  session use identical cell IDs so edits can be applied consistently.
- **Annotated notebooks are generated, not hand-edited.** Always edit
  `create_annotated_notebooks.py` and re-run, never edit the `_annotated.ipynb`
  files directly.
- **FHIR server** — Public sandbox at `https://launch.smarthealthit.org/v/r4/fhir`,
  no auth required. Uses SNOMED CT codes for conditions (not ICD-10).
- **LLM** — Anthropic Claude only (`claude-sonnet-4-20250514`). No dual-provider
  abstraction.
- **HbA1c threshold** — >7.0% for "poor control" (Synthea data skews low).

## Git Workflow

Follow the governance rules in `~/.claude/CLAUDE.md`:
- Never push directly to main — use branches + PRs
- Branch naming: `codex/<topic>`
- One open PR per repo at a time
- Update CHANGELOG.md with every change
