# Lessons Learned

Institutional knowledge from building the FHIR Clinical Education Notebook
Framework. This document is for anyone forking the repo to create new clinical
education notebooks. It records what was tried, what failed, and what rules were
established through repeated trial and error.

---

## Infrastructure Pivots

### Verification: Local Jupyter to Playwright/Colab to Chrome DevTools to Vertex AI

The project went through four verification environments before landing on one
that works reliably. Each pivot was forced by a concrete failure, not a
preference change.

**Stage 1: Local Jupyter / nbconvert.** The first approach was `nbconvert
--execute` against a local Jupyter kernel. This catches Python errors but misses
everything that matters for student-facing notebooks: Colab form widgets
(`@param`) do not render, `cellView: "form"` code hiding does not apply, the
`google.colab.userdata` secrets API does not exist, and markdown rendering
differs. Multiple times, notebooks passed local execution but broke in Colab.
Local testing is still useful as a fast pre-check, but it is never sufficient.

**Stage 2: Playwright + Colab.** To test in the real student environment, we
built a Playwright automation pipeline (`scripts/colab-tools/`) that opens a
notebook in Google Colab, runs all cells, and takes screenshots at multiple
scroll positions. This worked but had two persistent problems:

1. **Google blocks automated sign-in.** Plain Chromium, `channel="chrome"`,
   manual profile copy, and `launch()` with `new_context()` all get blocked.
   The only combination that works is `launch_persistent_context` with both
   `--disable-blink-features=AutomationControlled` and
   `ignore_default_args=["--enable-automation"]`. Even then, auth expires and
   re-auth (`auth_setup.py`) is fragile.

2. **Screenshot-based verification is slow and lossy.** You get viewport-sized
   snapshots at fixed scroll positions. Content between positions is invisible.
   You cannot inspect cell output programmatically. The fix-regenerate-upload-
   screenshot cycle took 5-10 minutes per iteration.

**Stage 3: Chrome DevTools MCP.** The idea was to reuse Joel's existing Chrome
session via Chrome DevTools Protocol, eliminating the auth problem entirely.
`--autoConnect` mode (Chrome 144+) was supposed to find the running Chrome
automatically. In practice: `autoConnect` could not reliably find Chrome's
DevToolsActivePort, required relaunching Chrome with special flags, and was
fundamentally fragile. This approach was abandoned after partial implementation.
Do not revisit it.

**Stage 4: Vertex AI Workbench (current).** An SSH tunnel connects
`localhost:8888` to a Jupyter server on a GCP VM (`e2-standard-4` in
`us-east4-a`). The `mcp-jupyter` MCP server provides programmatic cell execution
with structured output capture (text, HTML, markdown, errors with tracebacks).
No browser automation. No screenshots. No auth expiry.

The key insight across all four stages: **execute via kernel, do not render via
browser.** Browser-based verification conflates two concerns (does the code work?
does it render correctly?) and makes both harder to debug. Kernel-based execution
answers the first question cleanly. Visual rendering review is a separate,
less-frequent manual step.

### LLM Provider: Dual Abstraction to Anthropic Only

The original notebooks supported both Anthropic and Azure OpenAI via a provider
toggle (`LLM_PROVIDER` variable). This added 52 lines to the setup cell and 130
lines to the agent loop for an `openai_tools_to_anthropic()` converter, dual-path
message formatting, and abstract `llm_client` variable naming.

The abstraction was removed because there was only one concrete implementation
anyone used (Anthropic). The simplification cut ~100 lines per notebook, replaced
the abstract `llm_client` with a direct `client = Anthropic(api_key=api_key)`,
and switched tool schemas from the OpenAI `function`/`parameters` format to
Anthropic's native `name`/`input_schema` format.

**Rule:** No abstraction without multiple concrete implementations. If you only
have one LLM provider, write to that provider's API directly. Students benefit
from seeing the real API, not a wrapper.

---

## Scenario Design

### The Single-Query Shortcut Problem

The original scenario was "Type 1 vs Type 2 Diabetes Clarification." It failed
because C-peptide alone solved the classification with one query. There were no
genuinely ambiguous cases in the data, the task did not require iterative evidence
gathering, and it failed the single-query shortcut test.

The replacement scenario (Diabetes Management Complexity Assessment) requires
3-4 queries per patient. No single query resolves any category:
- HbA1c alone tells control status but not kidney involvement
- eGFR alone tells kidney function but not glycemic control
- Medications alone tells regimen complexity but not outcomes
- Conditions alone tells diagnoses but not severity

**Six self-tests every scenario must pass:**

1. **Single-Query Shortcut:** No single query resolves any category
2. **Evidence Type Diversity:** Requires multiple FHIR resource types
3. **Ambiguity and Uncertainty:** At least two cases have genuinely defensible
   boundary answers
4. **Clinical Plausibility:** The classification task maps to a real clinical
   workflow
5. **Data Availability:** All required data types exist in the FHIR server
6. **Difficulty Calibration:** Appropriate for the target audience with any
   provided reference materials

Run these tests on paper before building anything. The diabetes scenario passed
all six after redesign; the original passed only three.

### Candidate Pool Stratification

The first implementation shuffled all patients and picked sequentially. Because
the FHIR server stores patients by phenotype group, this produced candidate pools
where all patients had the same phenotype. Students saw six identical cases and
learned nothing about differentiation.

**Fix:** Group patients by phenotype, shuffle within each group, then round-robin
pick across groups. This guarantees phenotype diversity in every candidate pool.
The candidate pool should include patients from at least 4 of 6 phenotypes, at
least 1 non-diabetes control, and a mix of clear and ambiguous cases (2 clear,
2-3 ambiguous, 1 control, 1-2 additional).

### Condition Scrambling

The FHIR Condition resource (problem list) gives away the diabetes diagnosis
before students can investigate. If a student sees "Type 2 diabetes mellitus"
in the conditions list, the classification exercise is pointless.

**Fix:** Deterministic per-patient replacement of condition displays with
clinically plausible alternatives. The scrambling is seeded by patient ID so it
is reproducible but not obvious. The underlying FHIR data is unchanged; only the
display in the candidate table is affected. Students must use lab values,
medications, and other evidence to determine the actual diagnosis.

---

## Colab-Specific Gotchas

### Form Cells Are Not Unbreakable

Colab form cells (`#@title` + `cellView: "form"`) hide the code behind a
rendered title bar. Students see a clean form interface. However, double-clicking
the title bar reveals the code and clears the execution state. There is no way
to prevent this in Colab.

**Design decision:** This is acceptable. Form cells are a UX convenience, not a
security boundary. Students who show the code will see string constants and
`display()` calls, which is harmless. The "Show code" link in the collapsed cell
is one-way (code is revealed but cannot be re-hidden without re-running). A
future improvement would be a JS-based toggle button injected into cell output,
but this is not yet implemented.

### Colab DOM Structure

Colab uses a custom web component `<colab-scroller id="notebook-main">` as its
main scroll container. Standard `window.scrollTo()` calls have no effect. All
scroll operations must target this element directly:

```javascript
document.querySelector('colab-scroller#notebook-main').scrollTo(0, targetY);
```

Colab dialogs (e.g., "Notebook does not have secret access", "Too many
sessions") use shadow DOM. Standard DOM queries cannot find dialog buttons. You
need JavaScript that recursively searches shadow roots:

```javascript
// Simplified — actual implementation in colab_common.py
function findInShadow(root, selector) {
  let el = root.querySelector(selector);
  if (el) return el;
  for (const child of root.querySelectorAll('*')) {
    if (child.shadowRoot) {
      el = findInShadow(child.shadowRoot, selector);
      if (el) return el;
    }
  }
  return null;
}
```

If you are building any browser-based Colab automation, these two issues will
block you immediately if you do not know about them.

### Cached Outputs After Run All

After `colab_screenshot.py` (or any automated run) executes a notebook, Colab
auto-saves cell outputs to the Google Drive file. If someone later opens this
notebook in Colab, they see stale cached outputs that look like cells have
already completed. Running cells individually on top of cached outputs produces
confusing state mismatches (e.g., `_state` NameError because the setup cell's
cached output displays "Connected" but the kernel has no state).

**Rule:** Always upload a fresh notebook (regenerated from the generator script,
with `"outputs": []` in every cell) before sharing with students or doing a
manual review. Never share a notebook that has been through an automated run.

### Markdown Rendering with Raw Strings

Python raw strings (`r"..."`) preserve backslash sequences literally. If you use
`r"""..."""` for a string that gets passed to `display(Markdown(...))`, the `\n`
sequences render as literal `\n` in the output instead of newlines. This is not
a bug in your generator; it is Python string semantics.

**Rule:** Use regular strings (not raw strings) for any text that will be
displayed via `display(Markdown(...))`. Reserve raw strings for regex patterns
and file paths.

---

## Verification Standards (Why They Exist)

### "Should Work" Is Not Verification

Across the project's history, Claude declared notebooks "verified" or "working"
at least three times without running them in Colab. Each time, real issues were
only caught when the notebook was actually executed in the student environment:
widget rendering failures, cell dependency problems, Colab-specific import
errors, and state management bugs.

The product is a student-facing UI experience, not a Python script. Code that
executes correctly in a local kernel can still produce a broken student
experience in Colab.

**Rule:** Real Colab (or Vertex AI Workbench), real FHIR data, every time. If
the verification environment is unavailable (auth broken, server down, VM
stopped), stop and ask. Do not substitute local testing and call it done.

### Change-Specific Checklists

On 2026-03-20, after implementing 8 specific UI changes (3-way classification
redesign), Claude took 5 section screenshots, noted that several key items
"cannot be verified from these viewport positions" (candidate table columns,
dropdown options, debrief section), and declared verification complete anyway.
The missing items included the most important changes.

This happened because "take 5 screenshots and eyeball them" is not verification
of specific changes. You can look at 5 clean screenshots and completely miss
that the change you made is not visible in any of them.

**Rule:** After taking Colab screenshots, write a numbered checklist of every
user-visible change from the implementation plan. Check each item against the
screenshots. If any item is not visible:

1. Increase `--num-sections` (e.g., 10, 15, 20) and re-run screenshots. This is
   cheap and fast.
2. Only if a change physically cannot be captured (requires interactive input
   that Run All does not provide), explicitly flag it for manual verification
   with a concrete reason.
3. Never declare verification complete with unchecked items.

### Resource Unavailability

When a required resource is unavailable (FHIR server down, API key missing,
Vertex AI instance stopped, Colab auth expired), never mock it, never fall back
to a substitute, never continue with degraded resources.

**Rule:** Stop and ask the user. Degraded resources produce misleading results,
and a workaround that silently changes the test conditions is worse than
stopping. This applies with extra force during testing and validation, where both
sides of any comparison must be running against real infrastructure.

---

## Playwright Auth (Legacy but Instructive)

This section documents the Playwright-based Colab auth approach. It is no longer
the primary verification path (Vertex AI replaced it), but the lessons apply to
any project that needs to automate Google-authenticated web apps.

### What Google Blocks

Google actively detects and blocks automated browsers during sign-in. These
approaches were all tried and all failed:

- **Plain Chromium** via `playwright.chromium.launch()` — blocked immediately
- **`channel="chrome"`** with `launch()` + `new_context()` — still detected
- **Manual Chrome profile copy** — Keychain dependency on macOS, lock file
  conflicts, 500MB profile directories
- **`launch_persistent_context` without anti-detection args** — still detected
- **`launch()` with anti-detection args but no persistent context** — no profile
  persistence between runs

### What Works

`launch_persistent_context` with two specific anti-detection arguments:

```python
context = playwright.chromium.launch_persistent_context(
    user_data_dir="~/.colab-notebook-tools/browser_data/",
    headless=False,
    args=["--disable-blink-features=AutomationControlled"],
    ignore_default_args=["--enable-automation"],
)
```

After successful sign-in, export cookies via `context.storage_state()` to a JSON
file. Subsequent tools load these cookies with `browser.new_context(
storage_state="path/to/auth.json")` and do not need to sign in again. Google
session cookies last approximately 2 years.

Both flags are required. `--disable-blink-features=AutomationControlled` removes
the `navigator.webdriver=true` property. `ignore_default_args=["--enable-
automation"]` prevents the "Chrome is being controlled by automated test
software" infobar. Either flag alone is insufficient.

---

## Vertex AI Configuration

### GCP Metadata Is the Right Layer

Early attempts used shell script logic for VM configuration: startup scripts in
GCS, zone iteration loops, manual idle-timeout management. The "golden
configuration" moved all of this to GCP instance metadata, which is simpler and
more reliable.

Three metadata keys handle everything:

1. **`startup-script`** — Inline bash that disables XSRF token validation on
   every boot. No GCS bucket needed (the `post-startup-script` metadata key
   requires a GCS path, but `startup-script` accepts inline content).
2. **`idle-timeout-seconds=3600`** — VM auto-stops after 60 minutes of idle.
   No cron job, no shell script, no hook management.
3. **Zone discovery** — `gcloud compute instances list --filter="name=..."` finds
   the instance across all zones in one API call. No zone-by-zone iteration.

The Stop hook only kills the local SSH tunnel. The VM manages its own lifecycle
via the idle timeout.

### SDK Gotchas

These cost hours of debugging because the error messages do not explain the
actual problem:

- **`gcloud workbench instances ssh` does not exist** in Google Cloud SDK 562+.
  Use `gcloud compute ssh` instead. The `workbench` subcommand group has
  different coverage than `compute`.
- **`gcloud workbench instances list` requires `--location`**, making cross-zone
  discovery tedious. Use `gcloud compute instances list` with `--filter` for
  single-call discovery.
- **`idle-shutdown-timeout` is not a top-level flag.** It is a metadata key
  (`idle-timeout-seconds`), set via `--metadata`.
- **`post-startup-script` requires a GCS path.** For inline bash, use the
  `startup-script` metadata key instead.
- **MCP `install_packages` fails on Vertex AI** because the underlying `uv pip`
  command needs `--system` on the Vertex AI environment. Use `subprocess` pip
  calls instead.
- **The Jupyter MCP server has a default 10-second request timeout.** Any cell
  that takes longer silently times out. Set `REQUEST_TIMEOUT=180` in the MCP
  server's environment variables. This requires a Claude Code restart to take
  effect.

---

## Hard Rules (Established Through Failure)

Each of these rules exists because violating it caused a concrete, documented
failure. They are not preferences.

1. **No mocks for required resources.** If the FHIR server, API, or verification
   environment is down, stop and ask. Do not substitute.

2. **Colab/Vertex verification is mandatory and non-deferrable.** Local testing
   is a pre-check, not a substitute. The student environment is the product.

3. **Change-specific screenshot verification checklist.** Enumerate every UI
   change, verify each in a screenshot. Increase screenshot count if items fall
   between positions. Never hand off with unchecked items.

4. **Generator scripts are the source of truth.** Never edit `.ipynb` files
   directly. Edit the generator, regenerate, re-verify. Direct notebook edits
   get overwritten on the next generation and create untraceable divergence.

5. **One open PR per repo at a time.** Multiple open PRs create merge conflicts
   and make it unclear which branch is current.

6. **No dual-provider abstraction.** If you have one LLM provider, write to that
   provider's API directly. Abstraction layers without multiple implementations
   add complexity for students with zero benefit.

7. **Surface FHIR queries to students.** Students are learning FHIR, not just
   doing clinical exercises. After every FHIR query, show the request URL and
   resource type. Label evidence by FHIR resource in dashboards. The toolkit
   reference card (mapping tools to FHIR endpoints) must be visible before the
   exercise starts. Hiding the FHIR layer defeats the learning objective.

---

## Distribution and Verification (2026-03-30)

### Unverified distribution

**What happened:** The demo notebook had a showstopper bug — Colab's form view
didn't render the second dropdown (`confirm`) in Step 6, so students had no way
to submit their classification. The markdown, the error output, and the activity
intro all referenced a `confirm` field that was invisible. The notebook was
distributed to a collaborator without re-running after the change was made.

**Root cause:** A two-dropdown pattern in a single Colab form cell. Colab
sometimes fails to render the second `#@param` field. The change seemed safe
("just added a confirmation step") so it wasn't re-verified.

**Fix:** Replaced with a single dropdown using "← Keep investigating" as the
safe default. Any classification option = submission. No phantom `confirm` field.

**Rule established:** Every notebook must pass end-to-end execution verification
before distribution. "It was working before" is not verification. Any change to
the generator — no matter how minor — invalidates prior verification.

**Enforcement:** PreToolUse hook on `mcp__google-personal__create_drive_file`
blocks `.ipynb` uploads unless a `.last_verified_<notebook>` timestamp file
exists and is newer than the notebook. See `scripts/check_notebook_verified.sh`.

### Wrong gcloud command on Workbench instances

**What happened:** Used `gcloud compute instances start fhir-hackathon-instance`
and got a 403 even with `roles/owner`. Spent 20 minutes debugging permissions,
re-authenticating, checking IAM policies.

**Root cause:** Vertex AI Workbench instances are managed resources. The Notebooks
API places a mutation lock on the underlying Compute Engine VM to prevent
out-of-band changes that could corrupt the Workbench state. `gcloud compute
instances start/stop` bypasses the Workbench control plane and is blocked.
`gcloud workbench instances start/stop` works correctly.

**Existing infrastructure:** `setup_vertex.sh` already used the correct command.
The problem was manually running gcloud instead of using the script.

**Rule established:** Always use `/colab-mcp` skill or `bash setup_vertex.sh`.
Never improvise gcloud commands for Workbench instances.

**Enforcement:** PreToolUse hook on Bash blocks `gcloud compute instances
start/stop` targeting `fhir-hackathon-instance`. See
`scripts/check_gcloud_workbench.sh`.
