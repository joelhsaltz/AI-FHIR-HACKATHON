# Colab Known Issues

Catalog of Google Colab quirks and implementation pitfalls accumulated from
debugging sessions in this project. Use this as a checklist when reviewing
generated notebooks before uploading to Colab.

## Form Cell Syntax

- `#@param` must be on the **same line** as the variable assignment.
  Correct: `scenario = "Diabetes" #@param ["Diabetes", "Asthma"] {type:"string"}`
  Wrong: putting `#@param` on the next line or in a comment block.

- `#@title` must be the **first line** of the cell. If anything comes before
  it (imports, comments), Colab ignores the title annotation.

- Dropdown syntax is exact:
  ```python
  variable = "option1" #@param ["option1", "option2", "option3"] {type:"string"}
  ```
  The default value (left of `#@param`) must be one of the options in the list.

- `cellView: "form"` in cell metadata hides the code and shows only the form
  UI. `cellView: "both"` shows the title bar plus the code. No `cellView` key
  means the cell is fully visible (standard code cell).

- If the `#@param` line has a syntax error, Colab **silently degrades** to
  showing a plain text input instead of the expected dropdown. There is no
  error message — the only symptom is a text field where a dropdown should be.

- Colab needs **separate lines** in the source array to detect all form fields.
  If multiple `#@param` assignments are concatenated into a single source string
  without newlines, Colab may only detect the first one.

- A combined dropdown with too many options (e.g., merging query selection and
  classification into one dropdown) can confuse Colab's form parser. Keep
  dropdowns focused on a single purpose.

## String Escaping

- Use `r"""..."""` (raw triple-quoted strings) for strings containing
  backslashes that should be literal (e.g., regex patterns, file paths).

- In f-strings, `\n` is interpreted as a newline character. If you want the
  literal text `\n` to appear in output, you need `\\n` or a different
  approach (concatenation, `.join()`).

- JSON strings inside Python strings need careful quote escaping. Common
  pattern: use single quotes for the Python string and double quotes for JSON,
  or use `json.dumps()` to generate the JSON string programmatically.

- Triple-quoted strings (`"""..."""`) that contain `#@param` annotations
  inside them can break Colab's form field detection. The `#@param` must be
  in the top-level cell source, not inside a string literal.

## Run All Behavior

- **`input()` calls block Run All.** The notebook hangs waiting for stdin
  with no visible prompt. This is the most common cause of "Run All seems
  stuck." Use `#@param` form cells instead of `input()` for user interaction.

- Colab form cells use their **default values** during Run All. The value
  to the left of `#@param` is what gets used. Make sure defaults produce
  valid, meaningful execution.

- Cell execution is sequential under Run All, but **Colab does not stop on
  error by default.** If cell N throws an exception, cells N+1, N+2, etc.
  still execute. This can cause confusing cascading errors where the root
  cause is in an early cell but the visible error is in a later one.

- Long-running cells (>60s) may trigger "Session crashed" or "Runtime
  disconnected" warnings. For agent loops or heavy FHIR queries, add
  progress indicators and keep execution under 60s per cell when possible.

- Agent loops (Claude tool_use/tool_result cycling) **must** have a
  `max_steps` cap to prevent runaway execution. A value of 10-15 is
  reasonable for educational notebooks; 5 is enough for smoke testing.

## Secrets and API Keys

- Access pattern:
  ```python
  from google.colab import userdata
  api_key = userdata.get("ANTHROPIC_API_KEY")
  ```

- Secrets must be **pre-configured** in the student's Colab account (sidebar,
  key icon, "Secrets"). The notebook cannot create secrets — it can only read
  them.

- On first run, Colab shows a **"Notebook does not have secret access"**
  dialog. The student must click "Grant access." Our screenshot automation
  (`colab_screenshot.py`) auto-clicks this button.

- Recommended fallback pattern for code that runs both in Colab and locally:
  ```python
  try:
      from google.colab import userdata
      api_key = userdata.get("ANTHROPIC_API_KEY")
  except (ImportError, ModuleNotFoundError):
      import os
      api_key = os.environ.get("ANTHROPIC_API_KEY")
  ```

## Display and Output

- Rich output requires explicit imports:
  ```python
  from IPython.display import Markdown, display, HTML
  ```

- `display(Markdown("# Heading\n\nBody text"))` renders markdown in cell
  output. `print("# Heading")` produces plain text — no rendering.

- For tables, `pd.DataFrame(...).to_html()` wrapped in `display(HTML(...))`
  produces styled HTML tables. `print(df)` produces plain-text alignment
  that looks poor in Colab.

- Colab has **output size limits**. Very long HTML output (large tables,
  verbose agent logs) may be truncated with a "Show more" link. For large
  outputs, consider pagination or summarization.

- `print()` output and `display()` output appear in the order they are
  called, but they use different rendering pipelines. Mixing them can
  occasionally produce unexpected ordering.

## Scroll Container

- Colab uses `<colab-scroller id="notebook-main">` as its scroll container,
  not the browser window. `window.scrollTo()` has no effect on notebook
  scrolling.

- This is primarily relevant for screenshot automation, not notebook code.
  But it means any JavaScript injected into cells that tries to scroll the
  page needs to target this element.

## Package Installation

- Reliable pattern for Run All compatibility:
  ```python
  import subprocess, sys
  subprocess.check_call(
      [sys.executable, "-m", "pip", "install", "anthropic", "requests"],
      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
  )
  ```

- `!pip install` in code cells works interactively but is **less reliable**
  under Run All (shell escaping issues, no guaranteed Python environment
  match).

- Always install packages in the **first code cell(s)** of the notebook.
  If a later cell imports a package that was installed in an earlier cell,
  the import works because pip installs into the running kernel's
  `site-packages`.

- Suppress pip output with `stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL`
  to keep cell output clean. Students do not need to see pip resolution logs.

- Colab pre-installs many packages (numpy, pandas, requests, matplotlib).
  Check before adding redundant installs. The `anthropic` package is NOT
  pre-installed and must be explicitly installed.

## Cell Dependencies

- All setup — imports, credentials, FHIR client initialization, helper
  function definitions — must be in early cells. Later cells that use these
  will fail under Run All if the setup cell comes after them.

- Functions and classes defined in one cell are available in all subsequent
  cells within the same runtime session. They are stored in the module-level
  namespace.

- Under Run All, execution is strictly top-to-bottom. There is no way to
  specify "run cell A before cell B" other than ordering them correctly in
  the notebook.

- If a cell defines a variable conditionally (e.g., inside an `if` block
  that may not execute), later cells that reference that variable will get
  a `NameError`. Always provide a default value or guard with
  `if 'var' in dir():`.

- Global state persists across cells. A cell that modifies a global variable
  (e.g., appending to a list, updating a dict) affects all subsequent cells.
  This is expected behavior but can cause subtle bugs if cells are run out
  of order during manual exploration.

## Common Pitfalls from This Project

- **Duplicate cell IDs** cause silent failures. The generator must produce
  unique IDs for every cell. Use `uuid.uuid4().hex[:8]` or a counter.

- **Markdown cells with complex HTML** may not render correctly in Colab.
  Colab's markdown renderer handles standard markdown well but can choke
  on nested HTML tags, inline CSS, or JavaScript.

- **`_format=json`** parameter is needed for FHIR queries against the SBU
  LinuxForHealth server. Some FHIR servers default to XML if this parameter
  is omitted, causing `json.JSONDecodeError` when parsing the response.

- **Self-signed SSL certificates** on the FHIR server require:
  ```python
  import urllib3
  urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
  # Then in every request:
  response = requests.get(url, headers=headers, verify=False)
  ```
  Omitting `verify=False` causes `SSLError`. Omitting the warning
  suppression floods output with `InsecureRequestWarning` on every request.

- **The `anthropic` package** must be pip-installed before `import anthropic`.
  This seems obvious but is easy to miss when the install cell and the
  import cell are far apart in the notebook. Under Run All, if the install
  cell is cell 1 and the import is cell 5, it works. But if someone restarts
  the runtime and runs only cell 5, it fails.

- **FHIR auth credentials** — the SBU server uses Basic Auth with
  `fhiruser`/`BmI512@ccess`. These are embedded in the notebook code
  (acceptable for educational use with a sandboxed server). The `@` in the
  password does not need URL encoding when passed via `requests` `auth`
  parameter, but does need encoding if embedded in a URL string.

- **Combined dropdowns** — merging too many concerns into a single dropdown
  (e.g., "Select query AND classification") confuses both the Colab form
  parser and the student. Keep each dropdown focused on one decision.

- **Cached outputs** — after `colab_screenshot.py` runs a notebook, Colab
  auto-saves outputs to the Drive file. If the notebook is later opened and
  run cell-by-cell, stale cached outputs appear alongside fresh execution.
  Always upload a fresh notebook (with `"outputs": []`) before sharing.
