# Vertex AI Workbench Capability Testing Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Determine whether the Jupyter MCP connection to Vertex AI Workbench can replace Playwright-based Colab verification for our notebook pipeline.

**Architecture:** We have a live Jupyter MCP connection to a Vertex AI Workbench instance tunneled at `http://localhost:8888`. Instead of building new tools first, we run a series of capability tests using the existing `mcp__jupyter__*` tools to map what works, what partially works, and what's a hard gap. Each test produces a concrete pass/fail result.

**Tech Stack:** Jupyter MCP (`mcp__jupyter__setup_notebook`, `modify_notebook_cells`, `execute_notebook_code`, `query_notebook`), Vertex AI Workbench (Python 3, pandas 3.0.1), FHIR server (SBU LinuxForHealth)

---

## Context: What We Need to Replace

The current Playwright-based pipeline does 6 things:
1. **Execute cells** — Run All via Cmd+F9, monitor completion
2. **Capture output** — Screenshots at 5 scroll positions
3. **Handle dialogs** — Grant Colab Secrets, manage sessions
4. **Interact with forms** — Set `@param` dropdowns, text inputs
5. **Review pedagogy** — Claude evaluates screenshots against checklist
6. **Fix loop** — Generate → execute → review → fix → repeat

The Jupyter MCP can potentially replace #1 (execute), #2 (output capture as text), and #6 (fix loop). Items #3 and #4 are Colab-specific. Item #5 needs testing — can text output replace screenshots for review?

## Key Question

**Can we shift from visual verification (screenshots) to programmatic verification (cell output inspection)?** If yes, the Jupyter MCP on Vertex AI gives us everything. If no, we need to identify exactly which verification items require visual rendering.

---

### Task 1: FHIR Server Connectivity

Test whether the Vertex AI Workbench instance can reach the SBU FHIR server (external HTTPS with self-signed cert, Basic Auth).

**Files:**
- Uses: existing notebook `fhir_hackathon_init.ipynb` on the Jupyter server

- [ ] **Step 1: Add FHIR connectivity test cell**

Use `mcp__jupyter__modify_notebook_cells` to add and execute:

```python
import requests, urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

FHIR_BASE = "https://lfh-fhir.eastus2.cloudapp.azure.com:9443/fhir-server/api/v4"
session = requests.Session()
session.auth = ("fhiruser", "BmI512@ccess")
session.verify = False

resp = session.get(f"{FHIR_BASE}/metadata", timeout=30)
print(f"Status: {resp.status_code}")
print(f"FHIR version: {resp.json().get('fhirVersion', 'unknown')}")
```

Expected: Status 200, FHIR version `4.0.1`

- [ ] **Step 2: Test patient query**

```python
resp = session.get(f"{FHIR_BASE}/Patient?_count=5", timeout=30)
bundle = resp.json()
print(f"Total patients: {bundle.get('total', 'unknown')}")
for entry in bundle.get('entry', [])[:3]:
    r = entry['resource']
    name = r.get('name', [{}])[0]
    print(f"  {name.get('given', ['?'])[0]} {name.get('family', '?')}")
```

Expected: Total patients ~1027, three patient names printed

- [ ] **Step 3: Record results**

Document: Does Vertex AI Workbench have network access to the FHIR server? Any SSL/firewall issues?

**Pass criteria:** Both cells execute with status `ok`, patient data returned.
**Fail action:** If FHIR server unreachable, STOP and ask Joel — this is a hard blocker.

---

### Task 2: Package Installation

Test whether we can install packages (`anthropic`, `requests`, `pandas`) in the Vertex AI kernel, since notebooks pip-install at runtime.

**Files:**
- Uses: `fhir_hackathon_init.ipynb`

- [ ] **Step 1: Test pip install via execute**

```python
import subprocess, sys
result = subprocess.run(
    [sys.executable, "-m", "pip", "install", "-q", "anthropic", "requests"],
    capture_output=True, text=True, timeout=120
)
print(f"Return code: {result.returncode}")
if result.stdout.strip():
    print(f"Stdout: {result.stdout.strip()}")
if result.stderr.strip():
    # Filter out "already satisfied" noise
    lines = [l for l in result.stderr.strip().split('\n') if 'already satisfied' not in l.lower()]
    if lines:
        print(f"Stderr: {chr(10).join(lines)}")
print("pip install OK")
```

Expected: Return code 0, "pip install OK"

- [ ] **Step 2: Test Jupyter MCP's install_packages**

Use `mcp__jupyter__execute_notebook_code` with `execution_type: "install_packages"` and `package_names: "anthropic requests"`.

Expected: Installation success message

- [ ] **Step 3: Verify import**

```python
import anthropic
print(f"anthropic version: {anthropic.__version__}")
```

Expected: Version string printed, no ImportError

**Pass criteria:** All three steps succeed. Note which install method is faster/cleaner.

---

### Task 3: Multi-Cell Sequential Execution

Test whether we can execute a sequence of cells where later cells depend on earlier ones (shared kernel state). This is how our notebooks work — setup cell defines variables, later cells use them.

**Files:**
- Create: new notebook `vertex_test_sequential.ipynb`

- [ ] **Step 1: Create test notebook**

```
mcp__jupyter__setup_notebook("vertex_test_sequential.ipynb", server_url="http://localhost:8888")
```

- [ ] **Step 2: Add and execute setup cell (cell 0)**

```python
# Simulates our setup cell
FHIR_BASE = "https://lfh-fhir.eastus2.cloudapp.azure.com:9443/fhir-server/api/v4"
patients = ["Alice", "Bob", "Carol"]
shared_state = {"step": 0, "results": []}
print(f"Setup complete. {len(patients)} patients loaded.")
```

Expected: "Setup complete. 3 patients loaded."

- [ ] **Step 3: Add and execute dependent cell (cell 1)**

```python
# This cell depends on setup cell's variables
shared_state["step"] = 1
for p in patients:
    shared_state["results"].append(f"Queried {p}")
print(f"Step {shared_state['step']}: {len(shared_state['results'])} queries done")
print(f"FHIR_BASE = {FHIR_BASE[:30]}...")
```

Expected: "Step 1: 3 queries done" + FHIR_BASE prefix. This proves kernel state persists across cell executions.

- [ ] **Step 4: Add and execute a cell that reads earlier state (cell 2)**

```python
import json
print(json.dumps(shared_state, indent=2))
```

Expected: JSON showing `{"step": 1, "results": ["Queried Alice", ...]}`.

**Pass criteria:** All three cells execute successfully with shared state. This is the foundation — if state doesn't persist, nothing else works.

---

### Task 4: Rich Output Capture

Test whether Jupyter MCP returns rich output (HTML tables, formatted text) from cell execution, not just plain stdout. Our notebooks use `pandas` DataFrames, `IPython.display.HTML`, and `IPython.display.Markdown`.

**Files:**
- Uses: `vertex_test_sequential.ipynb`

- [ ] **Step 1: Test pandas DataFrame display**

```python
import pandas as pd
df = pd.DataFrame({
    "Patient": ["Alice", "Bob", "Carol"],
    "HbA1c": [6.2, 8.1, 7.8],
    "Classification": ["Normal", "Poor Control", "Poor Control"]
})
display(df)
print("---")
print(f"DataFrame shape: {df.shape}")
```

Expected: Output contains both the DataFrame representation AND the print statement. Check: does the MCP return the HTML table, a text table, or just the print output?

- [ ] **Step 2: Test IPython HTML display**

```python
from IPython.display import HTML, display
display(HTML("<h3>FHIR Query Result</h3><p>Found <b>3</b> patients with HbA1c > 7.5%</p>"))
```

Expected: Output contains the HTML string. Check: is it returned as `text/html` mime type or stripped to plain text?

- [ ] **Step 3: Test IPython Markdown display**

```python
from IPython.display import Markdown, display
display(Markdown("## Patient Summary\n- **Alice**: Normal\n- **Bob**: Poor Control\n- **Carol**: Poor Control"))
```

Expected: Markdown content in output.

- [ ] **Step 4: Document output format**

For each cell, record:
- What output types are in the response (stream, display_data, execute_result)
- What mime types are present (text/plain, text/html, text/markdown, application/json)
- Whether the content is sufficient for Claude to evaluate correctness

**Pass criteria:** Rich outputs are captured with enough detail for programmatic review. Even if we don't get rendered HTML, we need the content.

---

### Task 5: Error Handling and Cell Failure Detection

Test whether we can reliably detect cell execution failures — errors, exceptions, timeouts. This replaces the Playwright screenshot inspection for "red error cells."

**Files:**
- Uses: `vertex_test_sequential.ipynb`

- [ ] **Step 1: Test Python exception**

```python
# Intentional error
x = 1 / 0
```

Expected: Output contains `ZeroDivisionError` traceback. Check: does MCP return `status: "error"` or similar?

- [ ] **Step 2: Test import error**

```python
import nonexistent_package_xyz
```

Expected: `ModuleNotFoundError` in output. Check status field.

- [ ] **Step 3: Test partial output before error**

```python
print("Line 1: OK")
print("Line 2: OK")
raise ValueError("Intentional failure at line 3")
```

Expected: Output contains "Line 1: OK", "Line 2: OK", AND the ValueError traceback. Check: do we get partial stdout before the error?

- [ ] **Step 4: Document error detection pattern**

Record:
- How errors appear in MCP response (status field? output type?)
- Whether partial output is preserved
- Whether we can distinguish "cell failed" from "cell succeeded with warnings"

**Pass criteria:** We can programmatically detect cell failures from the MCP response without visual inspection.

---

### Task 5b: Long-Running Cell Execution

Test how the Jupyter MCP handles cells that take a long time. The agent loop cell in our real notebook can take 30-60+ seconds. If the MCP has a default timeout or blocks during execution, this is a critical gap.

**Files:**
- Uses: `vertex_test_sequential.ipynb`

- [ ] **Step 1: Test 45-second cell**

```python
import time
start = time.time()
time.sleep(45)
elapsed = time.time() - start
print(f"Completed after {elapsed:.1f} seconds")
```

Expected: Output returned after ~45 seconds with "Completed after 45.0 seconds". Check: does the MCP connection stay alive? Does it timeout?

- [ ] **Step 2: Test 2-minute cell (worst-case agent loop)**

```python
import time
start = time.time()
for i in range(12):
    time.sleep(10)
    print(f"Heartbeat {i+1}/12 at {time.time() - start:.0f}s")
print(f"Completed after {time.time() - start:.1f} seconds")
```

Expected: 12 heartbeats over ~120 seconds. Check: does MCP return all partial output or only final? Does it timeout?

- [ ] **Step 3: Document timeout behavior**

Record: MCP timeout limit (if any), whether partial output is returned for long cells, whether we need to adjust MCP configuration for agent loop cells.

**Pass criteria:** 45-second cells execute reliably. 2-minute cells either work or we know the timeout limit.
**Fail action:** If timeout < 60s, this blocks agent loop execution — document and flag.

---

### Task 5c: Kernel Restart and State Isolation

Test whether we can restart the kernel and get clean state. The fix loop requires regenerating a notebook and running from scratch — stale state from a previous run could produce false positives.

**Files:**
- Uses: `vertex_test_sequential.ipynb`

- [ ] **Step 1: Confirm state exists from prior tasks**

```python
# This should work if kernel still has state from Task 3
print(f"shared_state = {shared_state}")
```

Expected: Prints the state from Task 3.

- [ ] **Step 2: Attempt kernel restart**

Check whether the Jupyter MCP supports kernel restart. Try:
```
mcp__jupyter__query_notebook("vertex_test_sequential.ipynb", "list_sessions")
```
Look for kernel restart options. If MCP doesn't support it, try via cell:

```python
import IPython
IPython.Application.instance().kernel.do_shutdown(restart=True)
```

- [ ] **Step 3: Verify state is cleared after restart**

```python
try:
    print(shared_state)
except NameError:
    print("STATE CLEARED - kernel restart successful")
```

Expected: "STATE CLEARED" — proving no stale state.

- [ ] **Step 4: Document restart capability**

Record: Can we restart kernels via MCP? Via code? What's the workaround if neither works (create a new notebook for each run)?

**Pass criteria:** We have a reliable way to get clean kernel state between runs.

---

### Task 6: Anthropic API Integration

Test whether the Vertex AI Workbench kernel can call the Anthropic API (Claude). This is critical for Activity 2 (AI agent mode) in our notebooks.

**Files:**
- Uses: `vertex_test_sequential.ipynb`

- [ ] **Step 1: Check for API key availability**

```python
import os
api_key = os.environ.get("ANTHROPIC_API_KEY", "")
if api_key:
    print(f"API key found: {api_key[:8]}...{api_key[-4:]}")
else:
    print("NO API KEY FOUND in environment")
    print("Available env vars with 'API' or 'KEY':")
    for k in sorted(os.environ):
        if 'API' in k.upper() or 'KEY' in k.upper():
            print(f"  {k}")
```

Expected: Either the key is in the environment, or we need to find another way to provide it (Colab uses Secrets; Vertex AI may use Secret Manager or env vars).

- [ ] **Step 2: Test Anthropic API call (if key available)**

```python
import anthropic
client = anthropic.Anthropic()  # uses ANTHROPIC_API_KEY env var
response = client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=100,
    messages=[{"role": "user", "content": "Say 'Hello from Vertex AI' in exactly 5 words."}]
)
print(f"Response: {response.content[0].text}")
print(f"Model: {response.model}")
print(f"Usage: {response.usage.input_tokens} in, {response.usage.output_tokens} out")
```

Expected: A 5-word response from Claude.

- [ ] **Step 3: If no API key, load from .env file**

```python
import os
# Load from the project's .env file (same pattern as local development)
env_path = "/home/jupyter/fhir-hackathon/.env"  # adjust path based on tunnel root
if os.path.exists(env_path):
    with open(env_path) as f:
        for line in f:
            if line.strip() and not line.startswith("#") and "=" in line:
                k, v = line.strip().split("=", 1)
                os.environ[k] = v
    print(f"Loaded .env, API key: {os.environ.get('ANTHROPIC_API_KEY', 'MISSING')[:8]}...")
else:
    print(f".env not found at {env_path}")
    print("ASK JOEL: How should the API key be provided in Vertex AI?")
```

If `.env` doesn't exist, STOP and ask Joel for the API key and the preferred injection method (env var, Secret Manager, manual).

**Pass criteria:** We can make Anthropic API calls from the Vertex AI kernel. If the key must be injected manually, document the method.
**Fail action:** If no way to provide the API key, STOP and ask Joel.

---

### Task 7: Notebook Upload and Execution of Real Prototype

The ultimate test: can we take our actual demo prototype notebook, upload it to Vertex AI Workbench via the Jupyter MCP, and execute all cells successfully?

**Files:**
- Read: `prototypes/you_are_the_agent_demo.ipynb`
- Upload via: Jupyter MCP or filesystem copy through tunnel

- [ ] **Step 1: Check if prototype notebook is accessible**

Try to set up the prototype notebook path via Jupyter MCP. The tunnel maps to the fhir-hackathon directory, so:

```
mcp__jupyter__query_notebook("prototypes/you_are_the_agent_demo.ipynb", "check_server")
```

If not found, we may need to copy it via the Jupyter API or create it fresh.

- [ ] **Step 2: List cells in prototype**

```
mcp__jupyter__query_notebook("prototypes/you_are_the_agent_demo.ipynb", "view_source")
```

Count total cells, identify which are code vs markdown.

- [ ] **Step 3: Execute setup cell (cell 0 or first code cell)**

Execute just the first code cell to verify FHIR connectivity + pip installs work in the real notebook context.

- [ ] **Step 4: Test one interactive cell to capture failure mode**

Before skipping all interactive cells, try executing one that uses `input()` to see exactly what happens:

```python
# If a cell calls input(), does MCP hang? Error? Accept programmatic input?
```

Document the failure mode. This determines whether the "modify default value and re-execute" workaround from Task 8 is the only path.

- [ ] **Step 5: Execute remaining cells sequentially through Activity 1**

Execute each code cell one at a time. Skip remaining `input()` cells after documenting the failure mode in Step 4.

Record for each cell:
- Cell index and title (from `#@title` comment)
- Execution status (ok/error)
- Output summary (what data was returned)
- Whether the cell is interactive (needs `input()` or `@param` dropdown)

- [ ] **Step 6: Document results**

Create a cell execution report:
- Total cells: N
- Code cells: N (markdown: N)
- Executed successfully: N
- Failed: N (with error details)
- Skipped (interactive): N
- Key outputs verified: FHIR data present? Patient names? HbA1c values?

**Pass criteria:** Non-interactive code cells execute successfully with FHIR data. Interactive cells are identified and cataloged.

---

### Task 8: Colab Form Cell Behavior

Test what happens with Colab `@param` form annotations in Jupyter (not Colab). This is the known gap — Colab renders dropdowns, Jupyter ignores the annotations. We need to understand exactly what happens.

**Files:**
- Create: new notebook `vertex_test_form_cells.ipynb`

- [ ] **Step 1: Test @param dropdown**

```python
#@title Select a query
action = "Get HbA1c values" #@param ["Get HbA1c values", "Get medications", "Classify patient"]
print(f"Selected action: {action}")
```

Expected: In Jupyter, the `#@param` annotation is ignored. The variable gets its default value. Cell executes with "Selected action: Get HbA1c values".

- [ ] **Step 2: Test @param text input**

```python
#@title Enter your prompt
user_prompt = "Analyze this patient's diabetes risk" #@param {type:"string"}
print(f"Prompt: {user_prompt}")
```

Expected: Default value used, prints the hardcoded string.

- [ ] **Step 3: Test re-execution with modified value**

Use `mcp__jupyter__modify_notebook_cells` to edit the cell, changing the default value:

```python
#@title Select a query
action = "Get medications" #@param ["Get HbA1c values", "Get medications", "Classify patient"]
print(f"Selected action: {action}")
```

Then execute. Expected: "Selected action: Get medications".

- [ ] **Step 4: Test #@title behavior (code hiding)**

```python
#@title This title should hide the code in Colab
result = 42 * 2
print(f"Result: {result}")
```

Expected: In Jupyter, `#@title` is just a comment — code is fully visible. Document: this confirms that `code_hidden` verification is impossible outside Colab.

- [ ] **Step 5: Assess the gap**

Document:
- Can we simulate student dropdown selection by editing the cell's default value and re-executing? (YES/NO)
- Is this "good enough" for automated testing, even though it doesn't test the dropdown UI? (JUDGMENT CALL)
- `#@title` code hiding: definitively cannot be tested outside Colab (expected)
- What verification items from the review checklist CANNOT be tested this way?

**Pass criteria:** We can change `@param` default values and re-execute to simulate different student choices. This is the workaround for missing form widgets.

---

### Task 9: Full Pipeline Feasibility Assessment

Synthesize all test results into a go/no-go decision for migrating from Playwright to Vertex AI Workbench + Jupyter MCP.

**Files:**
- Create: `docs/vertex-ai-test-results.md`

- [ ] **Step 1: Compile test results table**

| Capability | Status | Notes |
|------------|--------|-------|
| FHIR connectivity | ? | Task 1 |
| Package install | ? | Task 2 |
| Sequential execution | ? | Task 3 |
| Rich output capture | ? | Task 4 |
| Error detection | ? | Task 5 |
| Long-running cells | ? | Task 5b |
| Kernel restart | ? | Task 5c |
| Anthropic API | ? | Task 6 |
| Real notebook execution | ? | Task 7 |
| Form cell workaround | ? | Task 8 |

- [ ] **Step 2: Map to current verification checklist**

For each item in the student_review.py checklist, assess whether it can be evaluated from Jupyter MCP output:

| Checklist Item | Can Evaluate via MCP? | How |
|---------------|----------------------|-----|
| task_complexity | ? | Analyze cell outputs for decision complexity |
| case_variety | ? | Check patient data diversity in outputs |
| ui_clarity | **NO** (pre-classified) | Requires visual rendering of Colab form widgets |
| fhir_visibility | ? | Check for FHIR query strings in output |
| feedback_quality | ? | Check classification feedback text |
| dashboard_readability | **NO** (pre-classified) | Requires visual rendering of HTML tables/layout |
| activity_flow | ? | Check cell sequence and progression in outputs |
| code_hidden | **NO** (pre-classified) | Requires Colab `cellView:form` — impossible in Jupyter |
| game_mechanics | ? | Check for scoring/progression in output |
| clinical_plausibility | ? | Check clinical values in output |

Note: 3 of 10 items are definitively visual and cannot be evaluated via MCP output.
The go/no-go question is whether the remaining 7 are sufficient for automated
iteration, with the 3 visual items deferred to Joel's manual review.

- [ ] **Step 3: Write recommendation**

Based on results, recommend one of:
- **A: Full migration** — Jupyter MCP replaces Playwright entirely
- **B: Hybrid** — Jupyter MCP for execution/output testing, manual Colab review for visual items
- **C: Abandon** — Gaps too large, keep Playwright

Include: what needs to change in CLAUDE.md verification standards, which scripts to deprecate, which to keep.

- [ ] **Step 4: Update the migration plan**

Update `~/.claude/plans/colab-auth-vertex-migration.md` with test results and the chosen path forward.

**Pass criteria:** Clear recommendation with evidence from Tasks 1-8.

---

## Execution Notes

- **Tasks 1-3 are independent** — can run in parallel
- **Tasks 4-6 depend on Task 2** — need package install working (anthropic, pandas)
- **Tasks 5b-5c are independent** — can run after Task 3
- **Task 7 depends on Tasks 1-2** — need FHIR connectivity and package install working
- **Task 8 is independent** — can run in parallel with everything
- **Task 9 depends on all others** — synthesis step

## What This Plan Does NOT Cover

- Building replacement tools (that's Phase 2, after we know what works)
- gcloud CLI setup (we already have a working tunnel)
- Colab Enterprise REST API — if Jupyter MCP results in a FAIL or HYBRID recommendation, the Colab Enterprise REST API remains the fallback path documented in `~/.claude/plans/colab-auth-vertex-migration.md`
- Updating skills or CLAUDE.md (premature until we know what works)
