#!/usr/bin/env python3
"""
Quick smoke test: extract code cells from the demo notebook and run them
in order, mocking interactive #@param values and skipping LLM-dependent cells.

Two-activity notebook structure (10 steps):
  Steps 1-3: Setup (FHIR connection, tools, candidates)
  Step 4: Choose number of cases
  Step 5: Activity 1 — investigate (query-only cell, repeatable)
  Step 6: Activity 1 — classify (classification cell with confirmation)
  Step 7: Activity 1 results
  Steps 8-9: Activity 2 (prompt editor, AI agent — skipped, needs LLM)
  Step 10: Summary (skipped, needs agent_runs populated)
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


# New query-only dropdown
QUERY_PARAM = (
    'query = "Get HbA1c" #@param '
    '["Get demographics", "Get problem list", "Get HbA1c", '
    '"Get eGFR", "Get UACR", "Get treatment regimen", '
    '"Get C-peptide", "Get encounters"]'
)

# Classification dropdown
CLASSIFY_PARAM = (
    'classification = "Routine" #@param '
    '["Routine", "Moderate complexity", "High complexity", "No diabetes"]'
)

CONFIRM_PARAM = (
    'confirm = "No, let me query more" #@param '
    '["No, let me query more", "Yes, submit my answer"]'
)


def strip_params(src, **overrides):
    """Replace #@param annotations with concrete values."""
    processed = src
    processed = re.sub(r"#@title .+\n?", "", processed)

    # Query dropdown (Step 5)
    if "query" in overrides:
        processed = processed.replace(QUERY_PARAM, f'query = "{overrides["query"]}"')

    # Classification dropdown (Step 6)
    if "classification" in overrides:
        processed = processed.replace(CLASSIFY_PARAM, f'classification = "{overrides["classification"]}"')

    # Confirm dropdown (Step 6)
    if "confirm" in overrides:
        processed = processed.replace(CONFIRM_PARAM, f'confirm = "{overrides["confirm"]}"')

    # Num cases (Step 4)
    processed = processed.replace(
        'num_cases = 6 #@param {type:"integer"}',
        'num_cases = 3',
    )

    # AI provider dropdown (Step 1)
    processed = re.sub(
        r'AI_PROVIDER = ".*?" #@param \["Anthropic", "OpenAI"\]',
        'AI_PROVIDER = "Anthropic"',
        processed,
    )

    # Agent prompt editor (Step 8)
    processed = re.sub(
        r'agent_prompt = ".*?" #@param \{type:"string"\}',
        'agent_prompt = "Test agent prompt"',
        processed,
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
        # Skip LLM-dependent cells
        if any(skip in title.lower() for skip in ["run the ai agent", "summary"]):
            print(f"  SKIP (needs LLM): {title}")
            results.append(("SKIP", title))
            continue

        # Step 5: Query cell — run multiple queries for case 1
        if "query the fhir server" in title.lower():
            queries = ["Get HbA1c", "Get eGFR", "Get UACR", "Get treatment regimen",
                        "Get problem list", "Get C-peptide", "Get encounters"]
            for q in queries:
                processed = strip_params(src, query=q)
                ok = run_cell(processed, ns, f"Query: {q}", timeout_sec=60)
                results.append(("PASS" if ok else "FAIL", f"Query: {q}"))
            continue

        # Step 6: Classify cell — classify all cases
        if "classify this patient" in title.lower():
            num_cases = ns.get("_state", {}).get("num_cases", 3)
            for case_i in range(num_cases):
                pid = ns["_state"]["patient_id"]
                if pid:
                    gt = ns["_get_ground_truth"](pid)
                    processed = strip_params(src, classification=gt, confirm="Yes, submit my answer")
                    label = f"Classify case {case_i+1} (answer={gt})"
                    ok = run_cell(processed, ns, label, timeout_sec=60)
                    results.append(("PASS" if ok else "FAIL", label))
            continue

        processed = strip_params(src)
        ok = run_cell(processed, ns, title, timeout_sec=180)
        results.append(("PASS" if ok else "FAIL", title))

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
