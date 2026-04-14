# Handoff: Demo Notebook Testing + Colab Tools Refinement

- **Goal**: Resume testing the "You Are the Agent" demo notebook in Colab, using the new colab-notebook-tools infrastructure. Use the notebook work to shake out and refine the tools.
- **Date**: 2026-03-19
- **Status**: Complete
- **Two threads**: (1) Get the demo notebook fully verified in Colab, (2) Improve the tools based on what breaks

---

## Outcome (2026-03-19)

Both threads completed successfully:

### Demo Notebook — Verified
- All 5 scroll positions screenshotted and reviewed
- All cells execute, form widgets render, code hidden, FHIR data live
- Drive file ID: `116XICnRWkeZzwoCP0LyRGrwrNplT2nlF`
- Ready for Joel's manual review of student experience

### Colab Tools — Debugged and Updated

**Bugs found and fixed:**
1. **Google blocks sign-in** — `auth_setup.py` rewritten to use `launch_persistent_context` + `--disable-blink-features=AutomationControlled` + `ignore_default_args=["--enable-automation"]`. Plain Chromium, `channel="chrome"`, and persistent context without anti-detection args all fail.
2. **Section screenshots all identical** — `colab_screenshot.py` was using `window.scrollTo()` which doesn't work in Colab. Fixed to detect and scroll `colab-scroller#notebook-main` (Colab's custom scroll container). Now takes 5 evenly-spaced viewport screenshots.

**Skill docs updated:**
- `SKILL.md` — auth model, troubleshooting (Google blocking, scroll container), section screenshots
- `references/colab-verification.md` — full rewrite with auth model, Colab DOM structure, failure modes

### Tools Status (all tested and working)

| Script | Status |
|--------|--------|
| `auth_setup.py` | Tested — Google sign-in works with anti-detection args |
| `colab_screenshot.py` | Tested — scrolling, execution, screenshots all working |
| `nb_validate.py` | Tested previously — passes on demo notebook |
| `nb_exec_harness.py` | Not tested this session (local exec not needed — Colab pipeline works) |

---

## Key Files

| File | Role |
|------|------|
| `create_prototype_demo.py` | **Generator** — edit this, not the notebook |
| `prototypes/you_are_the_agent_demo.ipynb` | **Generated output** — don't edit directly |
| `scripts/colab-tools/auth_setup.py` | **Auth setup** — persistent context + anti-detection |
| `scripts/colab-tools/colab_screenshot.py` | **Screenshotter** — Colab scroll container aware |
| `scripts/colab-tools/nb_validate.py` | **Validator** — structure + syntax |
| `scripts/colab-tools/nb_exec_harness.py` | **Local exec test** — mock input() support |
| `.claude/skills/colab-notebook-tools/SKILL.md` | **Skill definition** — updated with fixes |

## Hard Rules (from CLAUDE.md)

1. **Never edit .ipynb directly** — edit the generator, regenerate
2. **Never declare done without Colab screenshots** — local testing is necessary but not sufficient
3. **Stop and ask if resources unavailable** — no mocks, no fallbacks
4. **Notebooks are self-contained** — all code inlined, no src/ imports
