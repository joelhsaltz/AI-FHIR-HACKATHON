# Colab Verification Pipeline — Reference

## Why Colab verification matters

Local Jupyter and `nbconvert --execute` do NOT replicate the Colab environment:
- Colab has its own Python runtime with pre-installed packages
- `@param` form widgets only render in Colab
- `cellView: "form"` hides code only in Colab
- `google.colab.userdata` for secrets is Colab-specific
- Markdown rendering differs slightly
- Network access (e.g., to FHIR servers) works differently

**If the notebook is meant for students in Colab, it must be verified in Colab.**

## Two-stage verification

### Stage 1: Automated (Claude's job)

1. **Local validation** — `nb_validate.py` catches syntax errors and structural issues
2. **Local exec harness** — `nb_exec_harness.py` runs cells in a shared namespace, catching import errors, API failures, logic bugs. Skip LLM-dependent cells with `--skip-pattern`.
3. **Colab screenshots** — `colab_screenshot.py` opens the notebook in Colab, runs all cells, captures screenshots at multiple scroll positions. Claude reads the screenshots and identifies issues.

This loop (fix → regenerate → re-verify) runs without human intervention.

### Stage 2: Manual (human's job)

Once automated testing shows the notebook is technically working, the human reviews the student experience: pedagogy flow, clarity, visual polish. This is the sign-off.

## Auth model: persistent context + storageState export

Google blocks sign-in in automation browsers. The solution has two layers:

### Layer 1: Persistent browser profile (for sign-in)

`auth_setup.py` uses `launch_persistent_context` to create a real Chromium profile
at `~/.colab-notebook-tools/browser_data/`. Two anti-detection flags are required:

```python
context = p.chromium.launch_persistent_context(
    user_data_dir=str(browser_data_path),
    headless=False,
    args=["--disable-blink-features=AutomationControlled"],
    ignore_default_args=["--enable-automation"],
)
```

**Why both flags:**
- `--disable-blink-features=AutomationControlled` removes the `navigator.webdriver=true`
  property that Google checks
- `ignore_default_args=["--enable-automation"]` prevents Chromium from showing the
  "Chrome is being controlled by automated test software" infobar, which also signals
  to Google that this is an automation session

**What does NOT work for Google sign-in:**
- `channel="chrome"` with `launch()` + `new_context()` — still detected
- Plain `launch_persistent_context` without anti-detection args — still detected
- `launch()` with `new_context()` and anti-detection args — still detected (no profile persistence)

### Layer 2: storageState export (for subsequent tools)

After successful sign-in, `auth_setup.py` exports cookies via `context.storage_state()`
to `~/.colab-notebook-tools/auth.json`. This JSON file is then loaded by
`colab_screenshot.py` via `browser.new_context(storage_state="path/to/auth.json")`.

**Why two layers?** The screenshot script doesn't need to sign in — it just needs
valid cookies. Using `storage_state` with an ephemeral context is simpler and
avoids lock-file conflicts with the persistent profile.

**Advantages over Chrome profile copying:**
- Works on macOS (no Keychain dependency)
- No temp directory management
- No lock file conflicts with running Chrome
- Portable between Playwright versions
- Smaller file (~50KB vs ~500MB Chrome profile)
- Google session cookies last ~2 years → one sign-in persists for months

## Colab DOM structure (as of March 2026)

### Scroll container

Colab uses a custom web component as its main scroll container:

```
<colab-scroller id="notebook-main" class="notebook-container">
  <div class="notebook-scrolling-horizontal-container">
    ... cells ...
  </div>
</colab-scroller>
```

- **Tag:** `COLAB-SCROLLER` (custom element)
- **ID:** `notebook-main`
- **Class:** `notebook-container`
- **Overflow:** `auto scroll`
- **Typical dimensions:** scrollHeight ~6000-8000px, clientHeight ~730px

`window.scrollTo()` has NO effect — you must scroll the `colab-scroller` element directly:

```javascript
document.querySelector('colab-scroller#notebook-main').scrollTo(0, targetY);
```

The screenshot script's `find_scroll_container()` function detects this dynamically,
falling back to window scroll if the Colab-specific elements aren't found.

### Section headers

Colab collapses cells under markdown headers. The script expands all sections before
Run All by clicking collapsed section headers.

## Screenshot script details

### OS detection
- macOS: `Meta+F9` for Run All
- Linux/Windows: `Control+F9` for Run All

### Execution detection
The script watches for running indicators:
- `div.cell-execution-indicator[class*='running']`
- `svg.circular-progress`
- `div.executing`, `div[class*='pending']`

It waits until no running indicators remain, with a double-check after 5s of idle.

### Section screenshots

The `--sections` flag takes 5 evenly-spaced viewport screenshots by scrolling
the Colab scroll container:

1. Detect the scroll container (`colab-scroller#notebook-main` or fallback)
2. Measure `scrollHeight` and `clientHeight`
3. Calculate 5 positions at 0%, 25%, 50%, 75%, 100% of max scroll
4. Scroll + wait 1s + screenshot at each position

This covers the full notebook length. For longer notebooks, the scroll positions
may miss content between viewports — increase `num_sections` in the code if needed.

## Common failure modes

| Symptom | Cause | Fix |
|---------|-------|-----|
| Google blocks sign-in ("browser not secure") | Automation detected | Use `launch_persistent_context` + both anti-detection args (see auth model above) |
| Screenshots show Google login page | Auth expired | Re-run `auth_setup.py` |
| All section screenshots identical | Scroll container not found | Check that `find_scroll_container` returns `colab-scroller#notebook-main` |
| Cells show errors but local harness passed | Colab environment differs | Check for Colab-specific imports, missing pip installs |
| Form widgets don't appear | Missing cellView metadata | Add `"cellView": "form"` to cell metadata |
| Run All doesn't trigger | Keyboard shortcut not recognized | Check OS detection, try headed mode |
| Timeout waiting for execution | Complex notebook, slow server | Increase `--timeout` |
| "Notebook container not found" warning | Colab DOM changed | Update selector in `wait_for_colab_load()` — usually harmless |
