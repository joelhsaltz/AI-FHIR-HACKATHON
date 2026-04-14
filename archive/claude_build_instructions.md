# claude_build_instructions.md — Build Specs Given to Claude Code

## Version History

### v1 — Initial Build (Feb 7-10, 2026)

**Original spec:** `docs/fhir_hackathon_claude_code_spec.md`

Built three-session hackathon notebooks for BMI 512. Key decisions made during
build:

1. **Simplified to Anthropic-only** — Original spec called for dual-provider
   (Anthropic + Azure OpenAI). Removed Azure OpenAI after it proved confusing
   and introduced unnecessary complexity. See `docs/SIMPLIFICATION_SUMMARY.md`.

2. **Migrated from ICD-10 to SNOMED CT** — FHIR server uses SNOMED CT codes for
   conditions, not ICD-10. Updated all condition searches.

3. **Fixed Pydantic SDK serialization** — Anthropic SDK's Pydantic content blocks
   cause errors when passed directly to the messages list. Added manual
   serialization to dict.

4. **Lowered HbA1c threshold to >7.0%** — Synthea data skews low; original 9%
   threshold returned no patients.

5. **Created backup notebook** — `session1_backup.ipynb` with embedded Flask FHIR
   server for when the SMART server is down.

**Status at end of v1:** Three student notebooks tested and working. Instructor
notebooks with example answers created. Validation and test scripts passing.

### v2 — NameError Fixes (Feb 2026)

**Instructions:** Fix `NameError` crashes when students skip cells out of order.

1. **Session 1 `df_patients`** — COMBINED ANALYSIS cell now rebuilds `df_patients`
   from the `patients` list directly, making it self-contained. Applied to all
   four Session 1 notebooks.

2. **Session 3 `tools`** — ADD SESSION 3 TOOLS cell now initializes the base 3
   tool schemas and `available_functions` dict before extending with Session 3
   tools, making it self-contained.

### v3 — Annotated Instructor Notebooks (Feb 2026)

**Instructions:** Create annotated versions of instructor notebooks with
explanatory markdown cells bridging clinical and technical concepts for the
mixed-background audience.

1. Created `create_annotated_notebooks.py` — Script reads each instructor
   notebook, inserts annotation cells at specified positions, writes annotated
   copy. Original notebooks not modified.

2. **Session 1:** 8 annotations (19 → 27 cells) covering FHIR basics, clinical
   terminologies, REST APIs, Bundles, references, pandas operations, and
   clinical narrative generation.

3. **Session 2:** 8 annotations (16 → 24 cells) covering Session 1 recap, API
   keys, function wrapping, tool schemas, system prompts, agent loop anatomy,
   trace reading, and failure modes.

4. **Session 3:** 9 annotations (21 → 30 cells) covering exploration goals, new
   resources, 6-tool capabilities, system prompt reuse, agent loop deep-dive,
   question formulation, failure modes, deliverable explanation, and MCP.

### v4 — Remove Verification Hash (Feb 23, 2026)

**Instructions:** Remove SHA-256 verification hash from Session 3 deliverable.
Unnecessary for informal hackathon, would confuse students.

Changes:
- Removed `import hashlib`, hash computation, and hash print line from
  deliverable cell in both `session3_student.ipynb` and
  `session3_instructor.ipynb`.
- Updated C7 annotation in `create_annotated_notebooks.py` to remove hash
  explanation paragraph.
- Regenerated all annotated notebooks (counts unchanged: 27, 24, 30).

## Outstanding Work

From the original spec, these tasks remain incomplete:

- **Batch grading script** (`grade_session3.py`) — not yet created.
- **Example completed notebooks** — instructor notebooks have example answers but
  do not have captured output from live runs.
- **Orientation PDFs** — Session 1 PDF exists; Sessions 2-3 PDFs exist but may
  need updates.
