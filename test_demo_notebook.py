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

        # Replace #@param annotations with concrete values
        processed = src
        # Remove the #@title line (it's just a comment)
        processed = re.sub(r"#@title .+\n?", "", processed)
        # Set form param values
        processed = processed.replace(
            'action = "Get demographics" #@param ["Get demographics", "Get full problem list", "Get labs", "Get medications", "Get encounters"]',
            'action = "Get demographics"',
        )
        # lab_type dropdown removed — Get labs now fetches all labs at once
        processed = processed.replace(
            'case_number = 1 #@param {type:"integer"}',
            'case_number = 1',
        )
        processed = processed.replace(
            'classification = "Likely Type 1" #@param ["Likely Type 1", "Likely Type 2", "Unclear / needs more review"]',
            'classification = "Likely Type 1"',
        )
        processed = processed.replace(
            'rationale = "" #@param {type:"string"}',
            'rationale = "Test rationale: low C-peptide, insulin-only"',
        )

        ok = run_cell(processed, ns, title, timeout_sec=180)
        results.append(("PASS" if ok else "FAIL", title))

        # After "Gather evidence" step, also test Get labs (all at once) and Get medications
        if "gather evidence" in title.lower():
            lab_src = src
            lab_src = re.sub(r"#@title .+\n?", "", lab_src)
            lab_src = lab_src.replace(
                'action = "Get demographics" #@param ["Get demographics", "Get full problem list", "Get labs", "Get medications", "Get encounters"]',
                'action = "Get labs"',
            )
            ok2 = run_cell(lab_src, ns, "Gather evidence: Get labs (all)", timeout_sec=60)
            results.append(("PASS" if ok2 else "FAIL", "Gather evidence: all labs"))

            # Also test Get medications
            med_src = src
            med_src = re.sub(r"#@title .+\n?", "", med_src)
            med_src = med_src.replace(
                'action = "Get demographics" #@param ["Get demographics", "Get full problem list", "Get labs", "Get medications", "Get encounters"]',
                'action = "Get medications"',
            )
            ok3 = run_cell(med_src, ns, "Gather evidence: Get medications", timeout_sec=60)
            results.append(("PASS" if ok3 else "FAIL", "Gather evidence: medications"))

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
