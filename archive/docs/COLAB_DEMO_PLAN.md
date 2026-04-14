# Plan: Colab-Tested "You Are the Agent" Demo Notebook

## Background and Reasoning

### The Problem

Joel needs a working "You Are the Agent" prototype notebook for a demo. Three attempts have failed:

1. **Attempt 1 (original prototype)**: Used `input()` calls and exposed Python code (`def run_menu():`, if/else chains). Students would see a coding tutorial, not a clinical exercise.

2. **Attempt 2 (Colab form cells)**: Used `cellView: "form"` metadata and `#@param` annotations to hide code and provide dropdown menus. This is the correct approach for Colab — but I tested it in local Jupyter where these features don't work. Result: all code visible, form widgets missing.

3. **Attempt 3 (FHIR-grounded v2)**: Added FHIR query surfacing (showing `GET /Patient/{id}` etc. in output). Good content direction per Joel's feedback, but same Colab-vs-Jupyter testing problem.

### Root Cause

The core issue is **I can't visually verify what the notebook looks like**. I generate the `.ipynb`, run a smoke test that executes code cells in Python, and check that the JSON structure is correct — but I never see the actual rendered notebook. This means:
- Literal `\n` in markdown cells goes undetected
- Broken table formatting goes undetected
- Whether code cells are actually hidden goes undetected
- Whether form widgets actually render goes undetected

### Why Colab (Not Local Jupyter)

The notebook uses Colab-specific features (`cellView: "form"`, `#@param` form widgets) that **only work in Google Colab**. These are the right design choice because:
- Joel's students will use Colab (no local setup required)
- Colab form cells hide code natively — no CSS hacks needed
- `#@param` provides real form widgets (dropdowns, text fields, integers)
- The FHIR server is accessible from Colab (public endpoint with basic auth)

Trying to make the notebook work in both Colab and local Jupyter adds complexity for no benefit. **Target Colab exclusively.**

### The Solution: End-to-End Colab Testing

Set up a pipeline where I can:
1. Generate the notebook
2. Upload it to Google Drive
3. Open it in Colab via Playwright (headless browser)
4. Run cells and take screenshots
5. Read the screenshots to check rendering
6. Fix issues and repeat

This requires two infrastructure pieces that are already installed but not connected:
- **Google Drive access** via the `google-personal` MCP server (configured in `~/.claude.json`, has OAuth tokens, but not loading in current session)
- **Playwright** for browser automation (installed: Python 1.48.0, npm 1.58.2)

---

## Infrastructure Setup

### A. Fix google-personal MCP Server

**Status**: Configured in `~/.claude.json` under `mcpServers.google-personal`. Uses `uvx workspace-mcp` (114 tools including `create_drive_file`). OAuth token exists at `~/.google-mcp/personal/joelhsaltz@gmail.com.json` with a valid refresh_token. CLI test confirmed tools work. But tools aren't loading in this Claude Code session.

**Fix**: Restart Claude Code. The MCP server initializes at session start. After restart, verify `create_drive_file` tool is available.

**Config reference**:
```
~/.claude.json → mcpServers.google-personal
  command: uvx workspace-mcp
  env:
    GOOGLE_CLIENT_SECRET_PATH: ~/.google-mcp/credentials.json
    WORKSPACE_MCP_CREDENTIALS_DIR: ~/.google-mcp/personal
    MCP_SINGLE_USER_MODE: 1
```

### B. Playwright Colab Automation Script

Create `screenshot_colab.py` that:
1. Launches Chrome with Joel's existing profile (reuses Google login — no auth needed)
2. Navigates to `https://colab.research.google.com/drive/{file_id}`
3. Waits for notebook to load
4. Triggers "Run All" (Runtime menu or Ctrl+F9)
5. Waits for execution (~60-90s for FHIR queries + optional Claude API calls)
6. Takes sectioned screenshots (top, middle, bottom of notebook)
7. Saves to `prototypes/colab_screenshots/`

Chrome user data: `/Users/joelsaltz/Library/Application Support/Google/Chrome`

### C. Also Configure jupyter-mcp-server (Optional, for Future)

Joel pointed to `datalayer/jupyter-mcp-server` (932 stars) — a full-featured MCP server for executing cells, reading outputs (including images), and multi-notebook support. This would be valuable for ongoing notebook development but is **not required for the immediate demo**. Can be set up after the demo ships.

---

## Notebook Fix

### File: `create_prototype_demo.py`

The generator is mostly correct for Colab. Three fixes needed:

#### Fix 1: Markdown Source Format

The `md_cell()` function receives a list of strings. Each string must end with a real `\n` character. Current code does this correctly in the cell assembly section (lines using list syntax). **Verify all md_cell calls use proper list-of-strings format.**

#### Fix 2: display(Markdown(...)) Strings Inside Code Cells

The code cell string constants use `r"""..."""` (raw strings). Inside raw strings, `\n` is a literal backslash-n, NOT a newline. This is the bug Joel saw — markdown output showing `\n` instead of line breaks.

**Fix**: Change from raw strings to regular strings, or replace `\n` with actual newlines in triple-quoted blocks. For the `_render_dashboard()` function and all `display(Markdown(...))` calls inside code cell constants.

Affected constants: `SETUP`, `TOOLS`, `BUILD_CANDIDATES`, `SELECT_CASE`, `GATHER_EVIDENCE`, `LLM_COACH`, `RECORD_ANSWER`, `LLM_AGENT`, `DEBRIEF`

#### Fix 3: Keep Colab Features (No Change)

`cellView: "form"` metadata and `#@param` annotations are correct. Do NOT remove them. They are the right approach for Colab.

---

## Execution Plan

1. **Restart Claude Code** → verify google-personal MCP loads
2. **Fix generator** → `create_prototype_demo.py` (markdown + display string fixes)
3. **Regenerate** → `python create_prototype_demo.py`
4. **Upload to Drive** → `create_drive_file` to Student Notebooks folder (`1KQvcm8J3pPTvXoD9hDjZ0wBSBD_wqg6a`)
5. **Screenshot in Colab** → run `screenshot_colab.py`, read screenshots
6. **Fix issues** → edit generator, regenerate, re-upload, re-screenshot
7. **Deliver** → give Joel the Colab link

---

## Files

| File | Action |
|------|--------|
| `create_prototype_demo.py` | Fix markdown/display strings |
| `prototypes/you_are_the_agent_demo.ipynb` | Regenerate |
| `screenshot_colab.py` | Create (Playwright Colab automation) |
| `prototypes/colab_screenshots/` | Create directory for screenshots |

## Hard Blocks — Stop and Ask Joel

**If any of the following cannot be completed, STOP IMMEDIATELY. Do not mock, simulate, substitute, or work around. Ask Joel how to proceed.**

1. **google-personal MCP server doesn't load after restart** → STOP. Do not mock Drive uploads with local file operations. Do not skip the upload step. Ask Joel to troubleshoot the MCP server together.

2. **create_drive_file fails or returns an error** → STOP. Do not pretend the file was uploaded. Do not switch to a manual upload workflow without asking. Show the error and ask Joel.

3. **Playwright cannot open Colab** (auth fails, page doesn't load, etc.) → STOP. Do not substitute local Jupyter screenshots. Do not use nbconvert HTML as a "good enough" proxy. Show the error and ask Joel.

4. **Colab "Run All" fails or cells error out** → STOP on the first error. Do not skip failing cells. Do not comment out problematic code. Show the error and fix it in the generator, then re-run from the beginning.

5. **Screenshots show rendering issues** (literal `\n`, broken tables, visible code) → STOP. Do not declare the notebook "good enough." Fix the generator and re-verify end-to-end.

6. **Any resource is unavailable** (FHIR server down, Anthropic API unreachable, Google auth expired) → STOP. Do not mock the resource. Ask Joel.

**The principle**: Every verification step must run against the real system. A screenshot of the notebook running in Colab with live FHIR data is the only acceptable proof that the demo works. No proxies, no mocks, no "it should work."

## Verification Checklist

Each item must be verified against real systems, not mocked:

- [ ] google-personal MCP server loads (create_drive_file tool available)
- [ ] Notebook uploads to Google Drive successfully (real file ID returned)
- [ ] Colab opens the notebook (Playwright screenshot of loaded page)
- [ ] Screenshots show: no literal `\n`, code hidden, form widgets visible
- [ ] Candidate table displays with real patient names from live FHIR server
- [ ] FHIR query banners appear after evidence gathering
- [ ] Agent Dashboard renders as formatted markdown
- [ ] Joel can open the Colab link and run the demo
