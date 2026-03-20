#!/usr/bin/env python3
"""
Quick smoke test: extract code cells from the demo notebook and run them
in order, mocking interactive #@param values and skipping LLM-dependent cells.
"""

import json
import os
import re
import signal
import sys
import time
import traceback


def timeout_handler(signum, frame):
    raise TimeoutError("Cell execution timed out")


def run_cell(code, namespace, label, timeout_sec=120):
    """Run a code string in a shared namespace with a timeout."""
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(timeout_sec)
    start = time.time()
    try:
        exec(code, namespace)
        elapsed = time.time() - start
        print(f"  PASS ({elapsed:.1f}s): {label}")
        return True
    except Exception as e:
        elapsed = time.time() - start
        print(f"  FAIL ({elapsed:.1f}s): {label}")
        print(f"    {type(e).__name__}: {e}")
        traceback.print_exc(limit=3)
        return False
    finally:
        signal.alarm(0)


# New dropdown value for the 8-option action param
ACTION_PARAM_OLD = (
    'action = "Get demographics" #@param '
    '["Get demographics", "Get problem list", "Get C-peptide", '
    '"Get HbA1c", "Get BMI", "Get eGFR", "Get treatment regimen", "Get encounters"]'
)
ASSESSMENT_PARAM_OLD = (
    'assessment = "No opinion yet" #@param '
    '["No opinion yet", "Slight lean toward Type 1", "Slight lean toward Type 2", '
    '"Strongly leaning Type 1", "Strongly leaning Type 2", '
    '"Confident Type 1", "Confident Type 2", "Unclear — conflicting evidence"]'
)
READY_PARAM_OLD = 'ready_to_answer = False #@param {type:"boolean"}'


def strip_params(src, action_value="Get demographics"):
    """Replace #@param annotations with concrete values."""
    processed = src
    processed = re.sub(r"#@title .+\n?", "", processed)
    # Action dropdown
    processed = processed.replace(ACTION_PARAM_OLD, f'action = "{action_value}"')
    # Assessment dropdown
    processed = processed.replace(ASSESSMENT_PARAM_OLD, 'assessment = "No opinion yet"')
    # Ready checkbox
    processed = processed.replace(READY_PARAM_OLD, 'ready_to_answer = False')
    # Case number
    processed = processed.replace(
        'case_number = 1 #@param {type:"integer"}',
        'case_number = 1',
    )
    # Classification
    processed = processed.replace(
        'classification = "Likely Type 1" #@param ["Likely Type 1", "Likely Type 2", "Unclear / needs more review"]',
        'classification = "Likely Type 1"',
    )
    # Rationale
    processed = processed.replace(
        'rationale = "" #@param {type:"string"}',
        'rationale = "Test rationale: low C-peptide, insulin-only"',
    )
    return processed


def main():
    with open("prototypes/you_are_the_agent_demo.ipynb") as f:
        nb = json.load(f)

    code_cells = []
    for i, cell in enumerate(nb["cells"]):
        if cell["cell_type"] != "code":
            continue
        src = "".join(cell["source"]) if isinstance(cell["source"], list) else cell["source"]
        title_match = re.search(r"#@title\s+(.+)", src)
        title = title_match.group(1).strip() if title_match else f"Code cell {i}"
        code_cells.append((i, title, src))

    # Shared namespace
    ns = {"__builtins__": __builtins__}

    results = []
    for idx, (cell_i, title, src) in enumerate(code_cells):
        # Skip LLM-dependent cells (coach, agent, debrief with comparison)
        if any(skip in title.lower() for skip in ["ai coach", "ai agent", "watch the ai"]):
            print(f"  SKIP (needs LLM): {title}")
            results.append(("SKIP", title))
            continue

        processed = strip_params(src)
        ok = run_cell(processed, ns, title, timeout_sec=180)
        results.append(("PASS" if ok else "FAIL", title))

        # After "Gather evidence" step, test individual tools
        if "gather evidence" in title.lower():
            # Test Get C-peptide (individual lab)
            cp_src = strip_params(src, action_value="Get C-peptide")
            ok_cp = run_cell(cp_src, ns, "Gather evidence: Get C-peptide", timeout_sec=60)
            results.append(("PASS" if ok_cp else "FAIL", "Gather evidence: C-peptide"))

            # Test Get HbA1c
            hba1c_src = strip_params(src, action_value="Get HbA1c")
            ok_hba1c = run_cell(hba1c_src, ns, "Gather evidence: Get HbA1c", timeout_sec=60)
            results.append(("PASS" if ok_hba1c else "FAIL", "Gather evidence: HbA1c"))

            # Test Get BMI
            bmi_src = strip_params(src, action_value="Get BMI")
            ok_bmi = run_cell(bmi_src, ns, "Gather evidence: Get BMI", timeout_sec=60)
            results.append(("PASS" if ok_bmi else "FAIL", "Gather evidence: BMI"))

            # Test Get eGFR
            egfr_src = strip_params(src, action_value="Get eGFR")
            ok_egfr = run_cell(egfr_src, ns, "Gather evidence: Get eGFR", timeout_sec=60)
            results.append(("PASS" if ok_egfr else "FAIL", "Gather evidence: eGFR"))

            # Test Get treatment regimen
            med_src = strip_params(src, action_value="Get treatment regimen")
            ok_med = run_cell(med_src, ns, "Gather evidence: Get treatment regimen", timeout_sec=60)
            results.append(("PASS" if ok_med else "FAIL", "Gather evidence: treatment regimen"))

            # Test Get encounters
            enc_src = strip_params(src, action_value="Get encounters")
            ok_enc = run_cell(enc_src, ns, "Gather evidence: Get encounters", timeout_sec=60)
            results.append(("PASS" if ok_enc else "FAIL", "Gather evidence: encounters"))

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    pass_count = sum(1 for s, _ in results if s == "PASS")
    fail_count = sum(1 for s, _ in results if s == "FAIL")
    skip_count = sum(1 for s, _ in results if s == "SKIP")
    for status, title in results:
        print(f"  [{status}] {title}")
    print(f"\n{pass_count} passed, {fail_count} failed, {skip_count} skipped")
    return 0 if fail_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
