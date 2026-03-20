# TECHNICAL.md — Architecture and Implementation Guide

## Architecture Overview

### Session 1: Manual Orchestration

```
Student → Claude Web UI → Python Code → FHIR Server → Data → LLM Summary
```

Students write FHIR queries (with Claude's help generating code), run them in
Colab, and manually chain results together. No API key needed — only HTTP
requests to the public FHIR server.

### Sessions 2 & 3: Agentic Orchestration

```
Student Question → Agent Loop → Claude API (tool_use) → Local Python → FHIR Server
                      ↑                                        ↓
                      └──────────── tool_result ───────────────┘
```

The agent loop sends the question + tool schemas to Claude. Claude responds with
either a `tool_use` block (requesting a function call) or a `text` block (final
answer). The loop executes requested tool calls locally and feeds results back
until Claude produces a final answer or hits `max_steps`.

## Key Components

### FHIR Tool Functions

Six Python functions wrapping FHIR REST API calls:

| Function | FHIR Endpoint | Purpose |
|----------|---------------|---------|
| `search_conditions(code, max_results)` | `GET /Condition?code=...` | Find patients by diagnosis code |
| `get_patient(patient_id)` | `GET /Patient/{id}` | Retrieve demographics |
| `search_observations(patient_id, loinc_code, max_results)` | `GET /Observation?subject=...&code=...` | Get lab/vital results |
| `search_medications(patient_id, max_results)` | `GET /MedicationRequest?subject=...` | Get prescribed medications |
| `search_encounters(patient_id, max_results)` | `GET /Encounter?subject=...` | Get visit history |
| `search_all_conditions(patient_id, max_results)` | `GET /Condition?subject=...` | Get full problem list |

Sessions 1-2 use the first three. Session 3 adds the remaining three.

### Tool Schemas

Defined in Anthropic's native format:

```python
{
    "name": "search_conditions",
    "description": "Search for patient Condition resources...",
    "input_schema": {
        "type": "object",
        "properties": {
            "code": {"type": "string", "description": "..."},
            "max_results": {"type": "integer", "default": 20}
        },
        "required": ["code"]
    }
}
```

The LLM never sees the Python source code — only the schema descriptions. Tool
description quality directly affects agent performance.

### Agent Loop (`run_agent()`)

Located in the AGENT LOOP cell of Sessions 2 and 3. Key implementation details:

1. **Message list as memory** — `messages` accumulates the full conversation.
   Nothing persists between API calls except this list.

2. **Content block serialization** — Anthropic SDK returns Pydantic objects that
   cause serialization errors. The loop manually converts them to plain dicts:

   ```python
   assistant_content = []
   for block in response.content:
       if block.type == "text":
           assistant_content.append({"type": "text", "text": block.text})
       elif block.type == "tool_use":
           assistant_content.append({
               "type": "tool_use", "id": block.id,
               "name": block.name, "input": block.input
           })
   messages.append({"role": "assistant", "content": assistant_content})
   ```

3. **Tool dispatch** — `available_functions[fn_name](**fn_args)` maps tool names
   to Python callables.

4. **Termination** — Loop exits when Claude responds with text (no `tool_use`
   blocks) or when `step >= max_steps` (default 15).

### Annotated Notebook Generation

`create_annotated_notebooks.py` reads each instructor notebook, inserts
explanatory markdown cells at specified positions, and writes the annotated copy.

- **Session 1:** 8 annotations (19 → 27 cells)
- **Session 2:** 8 annotations (16 → 24 cells)
- **Session 3:** 9 annotations (21 → 30 cells)

Annotations are defined as `(insert_before_index, source_text)` tuples. Inserts
are processed in reverse order so earlier indices remain valid.

**Important:** Never edit `_annotated.ipynb` files directly. Edit the annotation
text in `create_annotated_notebooks.py` and re-run the script.

### Session 3 Deliverable

The deliverable cell generates a JSON report:

```json
{
  "student_id": "...",
  "timestamp": "2026-02-23T...",
  "session": 3,
  "runs": [
    {
      "question": "...",
      "tool_calls": [...],
      "num_tool_calls": 8,
      "tools_used": ["search_conditions", "get_patient", ...],
      "final_answer": "..."
    }
  ]
}
```

The report captures whatever runs are in memory. Students must not restart the
kernel between running questions and generating the deliverable.

## FHIR Server Details

**URL:** `https://launch.smarthealthit.org/v/r4/fhir`

- Public sandbox, no authentication required
- FHIR R4 compliant
- Synthea-generated synthetic data
- Uses SNOMED CT for conditions (not ICD-10)

**Known data gaps:**
- Hypertension (SNOMED 59621000): 0 results
- Creatinine (LOINC 2160-0): sparse/absent
- HbA1c values skew low — >7.0% threshold needed to find poor-control patients

**Backup:** `session1_backup.ipynb` runs a local Flask FHIR server with 30
cached Synthea patients embedded as Python dicts. Same API surface as the real
server.

## Colab Notebook Tools — Technical Details

### Architecture

```
Layer 4: VISUAL VERIFICATION    Playwright + storageState → Colab screenshots
Layer 3: COLAB EXECUTION        Run All via Playwright, wait for completion
Layer 2: LOCAL VALIDATION        nbformat + ast.parse + exec() harness
Layer 1: NOTEBOOK AUTHORING      nbformat programmatic creation/editing
```

### Google Auth (the hard part)

Google blocks sign-in in automation browsers. Three things are required:

1. **`launch_persistent_context`** — creates a real browser profile at
   `~/.colab-notebook-tools/browser_data/` that persists across runs
2. **`--disable-blink-features=AutomationControlled`** — removes `navigator.webdriver=true`
3. **`ignore_default_args=["--enable-automation"]`** — suppresses automation infobar

After sign-in, cookies are exported via `context.storage_state()` to `auth.json`.
The screenshot script loads this into a regular ephemeral context — it doesn't
need the persistent profile.

**What does NOT work:** `channel="chrome"`, plain `launch_persistent_context`
without args, `launch()` + `new_context()`, incognito mode. Google's detection
is server-side and checks for specific browser properties.

### Colab DOM Structure

Colab uses a custom web component for scrolling:

```
<colab-scroller id="notebook-main" class="notebook-container">
  scrollHeight: ~6000-8000px, clientHeight: ~730px
</colab-scroller>
```

`window.scrollTo()` has no effect. Must scroll this element directly:
```javascript
document.querySelector('colab-scroller#notebook-main').scrollTo(0, y);
```

### Screenshot Pipeline

1. Load `auth.json` into ephemeral browser context
2. Navigate to `colab.research.google.com/drive/{file_id}`
3. Wait for notebook load (cells visible)
4. Expand all collapsed sections
5. Connect to runtime (click Connect button if needed)
6. Trigger Run All via `Meta+F9` (macOS) or `Control+F9`
7. Handle "Run anyway" confirmation dialog
8. Wait for execution (monitor running indicator elements)
9. Take before/after screenshots
10. Scroll `colab-scroller` to 5 evenly-spaced positions, screenshot each

## Debugging Guide

### Common Issues

**"Set ANTHROPIC_API_KEY in Colab Secrets or environment"**
- Student hasn't added their API key to Colab Secrets (key icon in sidebar).
- Key must be named exactly `ANTHROPIC_API_KEY`.

**`NameError: name 'tools' is not defined`**
- Student skipped the TOOL SCHEMAS cell. The ADD SESSION 3 TOOLS cell is
  self-contained and re-initializes the base tools, so this should not occur in
  Session 3. If it does, re-run the ADD SESSION 3 TOOLS cell.

**`NameError: name 'df_patients' is not defined`**
- Student skipped the PATIENT DEMOGRAPHICS TABLE cell in Session 1. The COMBINED
  ANALYSIS cell rebuilds `df_patients` from the `patients` list, so this should
  not occur. If it does, re-run from the patient demographics step.

**`TypeError: argument 'by_alias': 'NoneType' object...`**
- Pydantic serialization error. The agent loop should already serialize content
  blocks manually. If this appears, the serialization code is missing or was
  modified.

**FHIR server returns 500/502 errors**
- The SMART server is intermittently unreliable. Wait and retry, or switch to
  `session1_backup.ipynb` for Session 1.

**Agent hits max_steps without final answer**
- The question may be too broad, causing the agent to make too many tool calls.
  Try a more specific question or increase `max_steps`.

### Modifying Notebooks

When editing notebook cells shared between student and instructor versions:

1. Both notebooks use the same cell IDs for corresponding cells.
2. Edit both `session*_student.ipynb` and `session*_instructor.ipynb`.
3. If the change affects annotated content, also edit
   `create_annotated_notebooks.py` and re-run it.
4. Verify annotation counts match expectations (27, 24, 30).

### Adding Annotations

To add a new annotation to an instructor notebook:

1. Identify the cell index (0-based) where the annotation should appear.
2. Add a `(index, "markdown source text")` tuple to the appropriate
   `SESSION_*_ANNOTATIONS` list in `create_annotated_notebooks.py`.
3. Update the expected cell count in the `configs` list in `main()`.
4. Run `python create_annotated_notebooks.py` and verify.
