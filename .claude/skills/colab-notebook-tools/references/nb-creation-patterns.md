# Notebook Creation Patterns — Reference

## Core principle: notebooks are generated, not hand-edited

Always create a Python generator script that produces the .ipynb file. Benefits:
- Version-controllable Python code (not opaque JSON)
- Reproducible output
- Easy to iterate (change generator, re-run)
- Code constants as Python strings with proper escaping

## Generator script structure

```python
#!/usr/bin/env python3
"""Generate <notebook name>."""
import json
import os
import uuid

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_PATH = os.path.join(SCRIPT_DIR, "output", "notebook.ipynb")

def _id():
    return uuid.uuid4().hex[:8]

def md_cell(source):
    """Create a markdown cell."""
    s = source if isinstance(source, list) else [source]
    return {"cell_type": "markdown", "id": _id(), "metadata": {}, "source": s}

def code_cell(source):
    """Create a visible code cell."""
    lines = source if isinstance(source, list) else [source]
    return {
        "cell_type": "code", "id": _id(),
        "metadata": {},
        "source": lines, "execution_count": None, "outputs": [],
    }

def form_cell(source):
    """Create a code cell hidden behind Colab's form view."""
    lines = source if isinstance(source, list) else [source]
    return {
        "cell_type": "code", "id": _id(),
        "metadata": {"cellView": "form"},
        "source": lines, "execution_count": None, "outputs": [],
    }

def build_notebook(cells):
    """Assemble cells into a complete notebook."""
    return {
        "nbformat": 4, "nbformat_minor": 5,
        "metadata": {
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3",
            },
            "language_info": {"name": "python", "version": "3.10.0"},
            "colab": {"provenance": [], "collapsed_sections": []},
        },
        "cells": cells,
    }

# Define cell code as string constants
SETUP_CODE = r"""
#@title Setup
import subprocess, sys
subprocess.check_call(
    [sys.executable, "-m", "pip", "install", "-q", "requests"],
    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
)
import requests
print("Ready!")
""".strip()

# Assemble
cells = [
    md_cell("# My Notebook"),
    form_cell(SETUP_CODE),
]

notebook = build_notebook(cells)
os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
    json.dump(notebook, f, indent=1)
    f.write("\n")
print(f"Wrote {OUTPUT_PATH}")
```

## Colab-specific metadata

### cellView: "form"
Hides the code cell and shows only the title and form widgets:
```python
"metadata": {"cellView": "form"}
```

### #@title annotation
First line of a form cell. Shown as the cell title in Colab:
```python
#@title Step 1: Connect to server
```

### #@param annotations
Create Colab form widgets. Must be on the same line as the variable assignment:

```python
# Dropdown
action = "Option A" #@param ["Option A", "Option B", "Option C"]

# Text input
name = "" #@param {type:"string"}

# Integer
count = 5 #@param {type:"integer"}

# Slider
value = 50 #@param {type:"slider", min:0, max:100, step:5}

# Boolean
verbose = True #@param {type:"boolean"}
```

### Colab notebook metadata
```python
"colab": {
    "provenance": [],
    "collapsed_sections": [],  # IDs of sections to collapse by default
    "toc_visible": true,       # Show table of contents
}
```

## Code as string constants

When embedding code in a generator, use raw strings (`r"""..."""`) to avoid escaping issues:

```python
CELL_CODE = r"""
#@title My Cell
import json
data = {"key": "value with \n newlines"}
print(json.dumps(data))
""".strip()
```

The `r"""` prefix means `\n` in the string is literally `\n` (two characters), which is correct — Python will interpret it as a newline when the cell runs in the notebook.

## Pip installs

Always install dependencies in the first code cell. Use subprocess to suppress output:

```python
import subprocess, sys
subprocess.check_call(
    [sys.executable, "-m", "pip", "install", "-q", "anthropic", "requests", "pandas"],
    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
)
```

Do NOT use `%pip install` in form cells — the magic command output can leak through even with cellView: "form".

## Self-contained notebooks

Notebooks for Colab must be self-contained:
- All code inlined as string constants in cells (no imports from project `src/`)
- All dependencies pip-installed in the notebook
- Configuration via Colab Secrets (`google.colab.userdata`) or hardcoded defaults
- No relative file path dependencies

## Testing generated notebooks

After generating, always validate:
1. `python nb_validate.py notebook.ipynb` — structure + syntax
2. `python nb_exec_harness.py notebook.ipynb --skip-pattern "LLM|agent"` — runtime check
3. Upload to Colab and run with `colab_screenshot.py` — visual verification
