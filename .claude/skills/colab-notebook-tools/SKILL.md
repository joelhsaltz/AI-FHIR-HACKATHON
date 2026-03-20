---
name: colab-notebook-tools
description: "Use when working with Jupyter notebooks destined for Google Colab: creating, editing, validating, uploading, executing in Colab, or taking screenshots. Triggers on: notebook creation/editing requests, 'verify in Colab', 'screenshot notebook', 'upload to Drive', 'run in Colab', nbformat/ipynb work, or any mention of Colab notebooks. Also triggers on /nb-auth, /nb-validate, /nb-verify, /nb-create, /nb-edit, /nb-lifecycle."
---

# Colab Notebook Tools

Tools and workflows for the full Jupyter notebook lifecycle: create, edit, validate locally, upload to Drive, execute in Colab, and visually verify via screenshots.

## Architecture

```
Layer 4: VISUAL VERIFICATION    Playwright + storageState → Colab screenshots
Layer 3: COLAB EXECUTION        Run All via Playwright, wait for completion
Layer 2: LOCAL VALIDATION        nbformat + ast.parse + exec() harness
Layer 1: NOTEBOOK AUTHORING      nbformat programmatic creation/editing
```

Each layer works independently. If Playwright isn't installed, Layers 1-2 still work.

## Scripts Location

All scripts live in `scripts/colab-tools/` relative to the project root:

| Script | Purpose |
|--------|---------|
| `auth_setup.py` | One-time Google auth → saves storageState |
| `colab_screenshot.py` | Playwright-based Colab screenshotter |
| `nb_validate.py` | Structure + syntax validation |
| `nb_exec_harness.py` | Generic exec() harness with mock input() |

Config lives at `~/.colab-notebook-tools/`:
- `auth.json` — Playwright storageState (Google session cookies, exported after sign-in)
- `browser_data/` — Persistent Chromium profile used by `auth_setup.py` (survives across runs)

## User-Invoked Commands

### /nb-auth — One-time Google sign-in

Run this once to set up Google auth for Colab screenshots.

**How it works:** Uses `launch_persistent_context` with a `user_data_dir` at
`~/.colab-notebook-tools/browser_data/`. This creates a real browser profile that
Google trusts for sign-in. Two anti-detection flags are critical:
- `--disable-blink-features=AutomationControlled` — hides `navigator.webdriver`
- `ignore_default_args=["--enable-automation"]` — suppresses automation banner

After sign-in, the script exports cookies via `context.storage_state()` to `auth.json`
for use by `colab_screenshot.py` (which uses a regular ephemeral context with the saved state).

**Steps:**
1. Run `python scripts/colab-tools/auth_setup.py`
2. Sign in to Google in the browser window that opens
3. Script saves storageState to `~/.colab-notebook-tools/auth.json`
4. Session persists for months (Google cookies last ~2 years)
5. The persistent browser profile at `browser_data/` is also kept — re-running detects an existing session

**When auth expires:** The screenshot script will exit with a clear error telling you to re-run `/nb-auth`.

**If Google blocks sign-in ("This browser or app may not be secure"):**
1. Delete `~/.colab-notebook-tools/browser_data/` (stale profile can be flagged)
2. Re-run `auth_setup.py` — a fresh profile with the anti-detection args should work
3. If still blocked: check that `auth_setup.py` uses `launch_persistent_context` (not `launch` + `new_context`) with both anti-detection args

### /nb-validate — Local notebook validation

Validate a notebook's structure and code without running in Colab.

**Steps:**
1. Run `python scripts/colab-tools/nb_validate.py <path.ipynb>`
2. Checks: valid nbformat, kernel metadata, code cell syntax (ast.parse), common Colab issues
3. For deeper validation: `python scripts/colab-tools/nb_exec_harness.py <path.ipynb> --skip-pattern "LLM|agent" --timeout 60`
4. Review the JSON output — fix any errors in the generator script, not the notebook

**Flags:**
- `--strict` — treat warnings as errors
- The exec harness accepts `--mock-inputs`, `--skip-pattern`, `--timeout`, `--max-cells`

### /nb-verify — Full Colab verification pipeline

The main event: validate locally, upload to Drive, run in Colab, take screenshots.

**Prerequisites:**
- Auth set up via `/nb-auth`
- Playwright installed: `pip install playwright && playwright install chromium`
- Notebook uploaded to Google Drive (or use Drive integration below)

**Steps:**
1. Run `/nb-validate` first (fail fast on code errors)
2. Upload notebook to Drive if not already there:
   - If `google-personal` MCP is available: use `create_drive_file` with `fileUrl=file:///path/to/notebook`
   - If neither is available: ask user to upload manually and provide the Drive file ID
3. Run the screenshot script:
   ```bash
   python scripts/colab-tools/colab_screenshot.py <drive_file_id> \
     --sections --output-dir ./colab_screenshots
   ```
4. Read the screenshots (Claude can view PNG files) and report:
   - Cell execution errors
   - Rendering issues
   - Missing output
   - Broken widgets or form cells
5. Return the Drive file ID + screenshot paths

**Flags for colab_screenshot.py:**
- `--no-run` — screenshot without executing cells
- `--sections` — take 5 evenly-spaced viewport screenshots scrolling through the notebook
- `--headless` — run headless (uses Chrome's new headless mode with full renderer)
- `--timeout N` — max seconds to wait for execution (default: 300)
- `--output-dir PATH` — where to save screenshots
- `--keep-open` — keep browser open for manual inspection
- `--storage-state PATH` — custom auth file path
- `--no-grant-secrets` — don't auto-grant Colab Secrets access (click Cancel instead of Grant access)

**Output:** JSON on stdout with `{"success": bool, "drive_file_id": "...", "screenshots": [...]}`

**Automatic dialog handling:** The script automatically handles two Colab dialogs
that would otherwise block execution:

1. **"Notebook does not have secret access"** — When a notebook tries to read a
   Colab Secret (e.g., `ANTHROPIC_API_KEY` via `google.colab.userdata.get()`),
   Colab shows a permission dialog. The script auto-clicks "Grant access" (or
   "Cancel" if `--no-grant-secrets` is set). This requires the secret to already
   exist in the user's Colab Secrets — the script grants the *notebook* access
   to it, it doesn't create the secret.

2. **"Too many sessions"** — When Colab's free tier session limit is reached,
   the script clicks "Manage sessions", terminates old sessions, and retries
   the connection. This commonly happens after repeated automated test runs.

Both handlers use JavaScript that pierces Colab's shadow DOM to find and click
buttons, since standard Playwright selectors can't reach elements inside web
component shadow roots.

## Model-Invoked Behaviors

### When creating a notebook (nb-create)

Triggered when the user asks to create a new notebook for Colab.

**Rules:**
1. **Never hand-write .ipynb JSON.** Always create a Python generator script that uses `nbformat` or raw dict construction (like `create_prototype_demo.py`).
2. Include Colab metadata in cells: `"cellView": "form"` for code-hidden cells, provenance, collapsed_sections.
3. Add `%pip install` or `subprocess.check_call([sys.executable, "-m", "pip", "install", ...])` cells for dependencies.
4. Use `#@title` annotations for cell labels in Colab.
5. Use `#@param` annotations for Colab form widgets (dropdowns, text inputs, integers).
6. After generating the notebook, run `/nb-validate` to check it.
7. If there's an existing generator script pattern in the project, follow it.

**Generator script pattern:**
```python
def md_cell(source):
    s = source if isinstance(source, list) else [source]
    return {"cell_type": "markdown", "id": _id(), "metadata": {}, "source": s}

def form_cell(source):
    lines = source if isinstance(source, list) else [source]
    return {
        "cell_type": "code", "id": _id(),
        "metadata": {"cellView": "form"},
        "source": lines, "execution_count": None, "outputs": [],
    }

def build_notebook(cells):
    return {
        "nbformat": 4, "nbformat_minor": 5,
        "metadata": {
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python", "version": "3.10.0"},
            "colab": {"provenance": [], "collapsed_sections": []},
        },
        "cells": cells,
    }
```

### When editing a notebook (nb-edit)

Triggered when the user asks to modify an existing notebook.

**Rules:**
1. **If a generator script exists** → edit the generator, then re-run it. Never edit the .ipynb directly.
2. **If no generator exists** → parse the notebook with `nbformat.read()`, modify programmatically, write back with `nbformat.write()`. Do NOT hand-edit the JSON.
3. After editing, run `/nb-validate`.
4. To find the generator: look for `create_*.py` files in the project root, or check if CLAUDE.md mentions a generator.

### When shipping a notebook (nb-lifecycle)

Triggered when the user says "ship this notebook", "make it ready", "verify end-to-end", "is this notebook done?".

**Orchestration:**
1. `/nb-validate` — catch code errors locally
2. Upload to Drive (detect available method)
3. `/nb-verify` — Colab screenshots
4. Report findings
5. If issues found: fix in generator, regenerate, re-verify

## Troubleshooting

### Google blocks sign-in ("This browser or app may not be secure")
Google detects Playwright automation and refuses login. The fix requires ALL of:
1. `launch_persistent_context` (not `launch` + `new_context`)
2. `args=["--disable-blink-features=AutomationControlled"]`
3. `ignore_default_args=["--enable-automation"]`

If still blocked after code is correct, delete `~/.colab-notebook-tools/browser_data/`
and retry — a previously-flagged profile stays flagged.

**Do NOT try:** `channel="chrome"` (still blocked), incognito mode (still blocked),
plain `launch_persistent_context` without anti-detection args (still blocked).

### Auth expired
Symptom: colab_screenshot.py exits with "Not signed in" error.
Fix: Run `/nb-auth` to re-authenticate.

### Playwright not installed
```bash
pip install playwright
playwright install chromium
```

### Headless mode issues
Colab's `@param` form widgets require a full renderer. The `--headless` flag uses Chrome's new headless mode (`headless="new"`) which includes the full renderer. If widgets still don't render, run without `--headless`.

### Screenshots show login page
Auth file may be corrupted or expired. Delete `~/.colab-notebook-tools/auth.json` and re-run `/nb-auth`.

### "Notebook does not have secret access" dialog not dismissed
The script uses JavaScript to pierce Colab's shadow DOM and click "Grant access".
If this fails:
1. Colab may have changed its dialog component — check browser DevTools for the
   button element type and update `dismiss_dialog()` in `colab_screenshot.py`
2. The secret must already exist in the user's Colab Secrets (key icon → left
   sidebar). The script grants notebook access, it doesn't create secrets.
3. Try running without `--no-grant-secrets` (default grants access)

### "Too many sessions" blocking runtime connection
Colab free tier limits concurrent runtime sessions. After repeated automated
test runs, old sessions accumulate. The script handles this at two stages:

**During runtime connection (`wait_for_runtime`):**
1. Detects the "Manage sessions" button
2. Clicks "Terminate" on old sessions, closes dialog
3. Resets the connection timeout and retries Connect
4. If no Connect button is found after cleanup, reloads the page and retries

**During execution (`run_all_cells`):**
The "too many sessions" dialog can also appear *after* Run All is triggered,
blocking execution. The script detects this, handles the dialog, reconnects
the runtime, and **re-triggers Run All** automatically. The execution timer
resets so the full timeout applies to the actual run. This retry loop handles
multiple consecutive session dialogs (tested with 3+ retries).

**Connect button detection:** Colab's connect button text varies ("Connect",
"Reconnect", "Connect to a new runtime"). The script uses shadow-DOM-piercing
JavaScript to find any button containing "connect" (excluding "disconnect").

**Runtime connection verification:** The script checks for RAM/Disk usage
indicators (visible in the top-right of connected Colab runtimes) as the
definitive signal that a runtime is connected. Simple text-based checks
("Connected") are unreliable due to Colab's shadow DOM.

If this still fails: go to https://colab.research.google.com/ manually, click
Runtime → Manage sessions, and terminate all sessions. Then re-run the script.

### Cached outputs from previous runs confuse cell-by-cell execution
When `colab_screenshot.py` runs a notebook via Run All, Colab auto-saves the
outputs back to the Drive file. If someone later opens this notebook, restarts
the runtime, and runs cells individually, they'll see stale cached outputs from
the previous automated run alongside fresh execution. This can be confusing —
especially if a slow cell (like FHIR queries) is still running but the cached
output makes it look done.

**Prevention:** Upload a fresh notebook (regenerated from the generator script,
with no saved outputs) before sharing with users. Generated notebooks have
`"outputs": []` on all cells by default.

### Section screenshots all show the same content
Colab uses a custom `<colab-scroller id="notebook-main">` element as its scroll
container — `window.scrollTo()` has no effect. The screenshot script must detect
and scroll this element. If sections look identical, the scroll container selector
needs updating (Colab may change its DOM structure).

## References

- [Notebook creation patterns](references/nb-creation-patterns.md) — best practices for Colab-ready notebooks
- [Colab verification details](references/colab-verification.md) — verification pipeline internals
