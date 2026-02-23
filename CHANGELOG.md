# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added

- Annotated instructor notebooks (`session1_instructor_annotated.ipynb`, `session2_instructor_annotated.ipynb`, `session3_instructor_annotated.ipynb`) with explanatory markdown cells (8 each for Sessions 1-2, 9 for Session 3) bridging clinical and technical concepts for the mixed-background audience.
- `create_annotated_notebooks.py` script to generate annotated notebooks from the originals. Reads each source notebook, inserts annotation cells at specified positions, and writes the annotated copy without modifying originals.
- Detailed agent loop annotation (C4b) in Session 3 — "Inside the Agent Loop: How `run_agent()` Works" — providing a phase-by-phase code-level walkthrough of the Reason-Act-Observe cycle. Complements Session 2's high-level overview with implementation specifics (message list as memory, `client.messages.create` decision point, `available_functions` dispatch, tool result feedback, `max_steps` termination).

### Fixed

- Session 1 COMBINED ANALYSIS cell no longer fails with `NameError: name 'df_patients' is not defined` when the PATIENT DEMOGRAPHICS TABLE cell is skipped. The cell now rebuilds `df_patients` from the `patients` list directly, making it self-contained. Applied to all four Session 1 notebooks: `session1_student.ipynb`, `session1_instructor.ipynb`, `session1_backup.ipynb`, `session1_backup_instructor.ipynb`.
- Session 3 ADD SESSION 3 TOOLS cell no longer fails with `NameError: name 'tools' is not defined` when the TOOL SCHEMAS cell is skipped. The cell now initializes the base 3 tool schemas and `available_functions` dict before extending with the 3 Session 3 tools, making it self-contained. Applied to `session3_student.ipynb` and `session3_instructor.ipynb`.
