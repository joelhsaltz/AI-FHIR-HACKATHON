# Playwright Cell Interaction Patterns — Reference

## Overview

`colab_interact.py` extends the Playwright automation to interact with
individual cells rather than just running all cells and taking screenshots.
This enables interactive walkthroughs that simulate a student's experience.

## Cell Identification

Colab renders cells as `div.cell` or `colab-cell` elements in the DOM.
Cells are indexed 0-based in document order. Use `get_cell_info()` to
discover cell indices, types, titles, and available form widgets.

```bash
# List all cells and their properties
python colab_interact.py <file_id> --list-cells
```

## Interaction Primitives

### Run a single cell

Focuses the cell and clicks its run button (or uses Ctrl/Cmd+Enter as fallback).
Waits for the cell's execution indicator to clear.

```python
from colab_interact import run_cell
success = run_cell(page, cell_index=3, timeout_s=180)
```

**How it works:**
1. Scroll cell into view via `scrollIntoView()`
2. Click cell to focus
3. Find and click the cell's `colab-run-button` (piercing shadow DOM)
4. Fallback: send Ctrl+Enter / Cmd+Enter keyboard shortcut
5. Poll for cell execution indicators (running spinner, pending state)
6. Return True when no running indicators remain

### Set a dropdown value

Colab `@param` dropdowns render as `<select>` elements inside the cell.

```python
from colab_interact import set_dropdown
result = set_dropdown(page, cell_index=5, value="Get C-peptide")
```

**How it works:**
1. Find `<select>` elements inside the cell
2. Match the target value against option values and text content
3. Set `select.value` and dispatch `change` + `input` events
4. Returns `{success: True}` or `{success: False, error: ..., available: [...]}`

**Important:** Colab may have multiple dropdowns in a cell. Use `dropdown_index`
to target a specific one (0-indexed).

### Set a text input

For `@param {type:"string"}` inputs:

```python
from colab_interact import set_text_input
result = set_text_input(page, cell_index=7, value="Classify this patient")
```

### Cell-level screenshot

Screenshots the viewport with the cell scrolled into view. If the cell fits
within 2000px height, clips to the cell's bounding box.

```python
from colab_interact import screenshot_cell
path = screenshot_cell(page, cell_index=5, output_path=Path("cell5.png"))
```

### Get cell output text

Extracts the text content of a cell's output area (first 2000 chars).

```python
from colab_interact import get_cell_output_text
output = get_cell_output_text(page, cell_index=5)
```

## Playbook-Driven Interaction

For scripted multi-step interactions, use a playbook JSON file:

```json
[
    {"action": "run_cell", "cell": 0},
    {"action": "run_cell", "cell": 1},
    {"action": "run_cell", "cell": 2},
    {"action": "wait", "seconds": 3},
    {"action": "set_dropdown", "cell": 5, "value": "Get HbA1c"},
    {"action": "run_cell", "cell": 5},
    {"action": "screenshot_cell", "cell": 5, "label": "after_hba1c"},
    {"action": "set_dropdown", "cell": 5, "value": "Classify: Type 2 Diabetes"},
    {"action": "run_cell", "cell": 5},
    {"action": "screenshot", "label": "classification_feedback"},
    {"action": "get_output", "cell": 5}
]
```

```bash
python colab_interact.py <file_id> --playbook interactions.json --output-dir ./walkthrough
```

### Available actions

| Action | Required fields | Optional fields | Description |
|--------|----------------|-----------------|-------------|
| `run_cell` | `cell` | `timeout` (default 180) | Run a cell and wait |
| `wait` | | `seconds` (default 2) | Sleep |
| `set_dropdown` | `cell`, `value` | `dropdown_index` (default 0) | Set dropdown |
| `set_text` | `cell`, `value` | `input_index` (default 0) | Set text input |
| `screenshot` | | `label` | Full viewport screenshot |
| `screenshot_cell` | `cell` | `label` | Cell-focused screenshot |
| `get_output` | `cell` | | Extract cell output text |

## Dynamic Playbook Generation

The `student_walkthrough.py` script generates playbooks dynamically by:
1. Reading the notebook JSON to find cell indices and dropdown options
2. Using Claude to decide which queries to make (simulating student reasoning)
3. Building the playbook actions based on notebook structure

This means playbooks adapt when the notebook structure changes — no hardcoded
cell positions.

## Common Pitfalls

### Form cells may not have visible run buttons
Colab form cells (`cellView: "form"`) show a play button on hover. The
`run_cell` function searches for `colab-run-button` in the cell's DOM tree
(including shadow DOM) and falls back to keyboard shortcuts.

### Dropdown change events
Setting `select.value` alone is not sufficient — Colab's JavaScript needs
the `change` and `input` events to update the underlying Python variable.
Always dispatch both events after setting the value.

### Cell execution timing
After `run_cell`, the cell's output may take a moment to render even after
the execution indicator clears. Add a `wait` action if you need to capture
the output immediately after.

### Shadow DOM barriers
Colab wraps many UI elements in shadow DOM. The interaction functions use
recursive shadow root traversal to find buttons and elements. If Colab
changes its component structure, these traversals may need updating.
