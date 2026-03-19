#!/usr/bin/env python3
"""
Generic exec() harness for running Jupyter notebook code cells in a shared namespace.

Usage:
    python nb_exec_harness.py <path.ipynb> [options]

Options:
    --mock-inputs '{"key": "val"}'   JSON dict of mock values for input() calls
    --timeout 60                     Per-cell timeout in seconds (default: 60)
    --skip-pattern "LLM|agent"       Regex to match against cell #@title to skip
    --max-cells 50                   Maximum number of cells to execute

Runs each code cell via exec() in a shared namespace. Auto-detects #@param
annotations and substitutes default values. Reports PASS/FAIL per cell with
timing to stderr. Prints JSON summary to stdout.

NOTE: Per-cell timeout uses signal.SIGALRM (Unix-only; not available on Windows).
"""

import argparse
import json
import os
import re
import signal
import sys
import time
import traceback


def timeout_handler(signum, frame):
    raise TimeoutError("Cell execution timed out")


def extract_title(source: str) -> str | None:
    """Extract the #@title value from a cell, if present."""
    m = re.search(r"#@title\s+(.+)", source)
    return m.group(1).strip() if m else None


def strip_param_annotations(source: str) -> str:
    """Process #@param annotations: keep the assignment but strip the annotation.

    For lines like:
        var = "value" #@param ["opt1", "opt2"]
        var = 1 #@param {type:"integer"}
        var = "text" #@param {type:"string"}

    Strips the #@param... suffix, leaving just the assignment with its default value.
    Also strips #@title lines.
    """
    lines = []
    for line in source.splitlines():
        # Remove #@title lines entirely
        if re.match(r"\s*#@title\s+", line):
            continue
        # Strip #@param annotations, keeping the assignment
        line = re.sub(r"\s*#@param\s+.*$", "", line)
        lines.append(line)
    return "\n".join(lines)


def make_input_mock(mock_inputs: dict | None):
    """Create a mock input() function that returns values from the dict.

    Keys can be matched against the prompt string. If no match is found,
    returns an empty string.
    """
    call_count = [0]
    prompts_seen = []

    def mock_input(prompt=""):
        prompts_seen.append(prompt)
        call_count[0] += 1

        if mock_inputs:
            # Try exact key match first
            if prompt in mock_inputs:
                val = mock_inputs[prompt]
                print(f"  [mock input] prompt={prompt!r} -> {val!r}", file=sys.stderr)
                return str(val)
            # Try substring match
            for key, val in mock_inputs.items():
                if key in prompt:
                    print(f"  [mock input] prompt={prompt!r} matched key={key!r} -> {val!r}", file=sys.stderr)
                    return str(val)

        print(f"  [mock input] prompt={prompt!r} -> '' (no match)", file=sys.stderr)
        return ""

    return mock_input


def run_cell(code: str, namespace: dict, label: str, timeout_sec: int) -> tuple[bool, float, str | None]:
    """Run a code string in a shared namespace with a timeout.

    Returns (success, elapsed_seconds, error_message_or_None).
    """
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(timeout_sec)
    start = time.time()
    try:
        exec(code, namespace)
        elapsed = time.time() - start
        print(f"  PASS ({elapsed:.1f}s): {label}", file=sys.stderr)
        return True, elapsed, None
    except Exception as e:
        elapsed = time.time() - start
        error_msg = f"{type(e).__name__}: {e}"
        print(f"  FAIL ({elapsed:.1f}s): {label}", file=sys.stderr)
        print(f"    {error_msg}", file=sys.stderr)
        traceback.print_exc(limit=3, file=sys.stderr)
        return False, elapsed, error_msg
    finally:
        signal.alarm(0)


def main():
    parser = argparse.ArgumentParser(
        description="Execute notebook code cells in a shared namespace with reporting."
    )
    parser.add_argument("notebook", help="Path to .ipynb file")
    parser.add_argument(
        "--mock-inputs",
        type=str,
        default=None,
        help='JSON dict of mock values for input() calls, e.g. \'{"Enter name": "Alice"}\'',
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=60,
        help="Per-cell timeout in seconds (default: 60)",
    )
    parser.add_argument(
        "--skip-pattern",
        type=str,
        default=None,
        help="Regex pattern to match against cell #@title lines to skip",
    )
    parser.add_argument(
        "--max-cells",
        type=int,
        default=None,
        help="Maximum number of code cells to execute",
    )
    args = parser.parse_args()

    # Parse mock inputs
    mock_inputs = None
    if args.mock_inputs:
        try:
            mock_inputs = json.loads(args.mock_inputs)
        except json.JSONDecodeError as e:
            print(f"Error: --mock-inputs is not valid JSON: {e}", file=sys.stderr)
            sys.exit(2)

    # Compile skip pattern
    skip_re = None
    if args.skip_pattern:
        try:
            skip_re = re.compile(args.skip_pattern, re.IGNORECASE)
        except re.error as e:
            print(f"Error: --skip-pattern is not a valid regex: {e}", file=sys.stderr)
            sys.exit(2)

    # Read notebook
    try:
        with open(args.notebook) as f:
            nb = json.load(f)
    except Exception as e:
        print(f"Error reading notebook: {e}", file=sys.stderr)
        sys.exit(2)

    # Extract code cells
    code_cells = []
    for i, cell in enumerate(nb.get("cells", [])):
        if cell.get("cell_type") != "code":
            continue
        src = cell.get("source", "")
        if isinstance(src, list):
            src = "".join(src)
        title = extract_title(src) or f"Code cell {i}"
        code_cells.append((i, title, src))

    total_cells = len(code_cells)
    max_cells = args.max_cells or total_cells

    # Set up shared namespace with mocked input
    ns = {"__builtins__": __builtins__}
    input_mock = make_input_mock(mock_inputs)
    ns["input"] = input_mock

    # Also inject into builtins so nested calls see it
    import builtins
    original_input = builtins.input
    builtins.input = input_mock

    results = []
    executed = 0
    skipped = 0
    passed = 0
    failed = 0

    print(f"\nRunning {args.notebook} ({total_cells} code cells, max {max_cells})\n", file=sys.stderr)
    print("=" * 60, file=sys.stderr)

    try:
        for idx, (cell_i, title, src) in enumerate(code_cells):
            if executed + skipped >= max_cells:
                # Remaining cells beyond max_cells are not reported
                break

            # Check skip pattern against title
            if skip_re and skip_re.search(title):
                print(f"  SKIP (pattern match): {title}", file=sys.stderr)
                results.append({
                    "index": cell_i,
                    "title": title,
                    "status": "skip",
                    "reason": "matched skip pattern",
                })
                skipped += 1
                continue

            # Process the cell source
            processed = strip_param_annotations(src)

            # Execute
            ok, elapsed, error = run_cell(processed, ns, title, args.timeout)
            executed += 1

            if ok:
                passed += 1
                results.append({
                    "index": cell_i,
                    "title": title,
                    "status": "pass",
                    "time_s": round(elapsed, 3),
                })
            else:
                failed += 1
                results.append({
                    "index": cell_i,
                    "title": title,
                    "status": "fail",
                    "error": error,
                    "time_s": round(elapsed, 3),
                })
    finally:
        # Restore original input
        builtins.input = original_input

    print("=" * 60, file=sys.stderr)
    print(f"\nSummary: {passed} passed, {failed} failed, {skipped} skipped\n", file=sys.stderr)

    # Output JSON summary to stdout
    summary = {
        "notebook": args.notebook,
        "total_cells": total_cells,
        "executed": executed,
        "skipped": skipped,
        "passed": passed,
        "failed": failed,
        "results": results,
    }
    json.dump(summary, sys.stdout, indent=2)
    print()  # trailing newline

    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
