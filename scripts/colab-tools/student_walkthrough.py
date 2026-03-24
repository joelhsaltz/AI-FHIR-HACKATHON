#!/usr/bin/env python3
"""
Autonomous student walkthrough agent for Colab notebooks.

"Plays" through a notebook as a student would: runs setup cells, selects
dropdown options, makes classification decisions using Claude, and captures
screenshots at each step. Then sends all screenshots to student_review.py
for pedagogical evaluation.

Usage:
    python student_walkthrough.py <file_id> --notebook path.ipynb
    python student_walkthrough.py <file_id> --notebook path.ipynb --output-dir ./walkthrough
    python student_walkthrough.py <file_id> --notebook path.ipynb --num-cases 2 --review
"""

import argparse
import base64
import json
import sys
import time
from pathlib import Path

try:
    import anthropic
except ImportError:
    print("ERROR: anthropic is not installed. Run: pip install anthropic", file=sys.stderr)
    sys.exit(1)

from colab_common import (
    DEFAULT_AUTH_PATH,
    PlaywrightTimeout,
    check_auth,
    create_browser_context,
    expand_all_sections,
    handle_colab_dialogs,
    open_colab_notebook,
    sync_playwright,
    wait_for_runtime,
)
from colab_interact import (
    execute_playbook,
    get_cell_info,
    get_cell_output_text,
    run_cell,
    screenshot_cell,
    set_dropdown,
    set_text_input,
)


# ── Notebook structure analysis ──────────────────────────────────────────

def analyze_notebook(notebook_path: Path) -> dict:
    """Analyze notebook JSON to find cell indices, dropdowns, and structure.

    Returns a dict describing the notebook's interactive elements so the
    walkthrough can adapt to any notebook layout.
    """
    with open(notebook_path) as f:
        nb = json.load(f)

    cells = []
    for i, cell in enumerate(nb.get("cells", [])):
        source = "".join(cell.get("source", []))
        cell_type = cell.get("cell_type", "unknown")
        metadata = cell.get("metadata", {})
        is_form = metadata.get("cellView") == "form"

        # Extract title
        title = ""
        for line in source.split("\n"):
            if "#@title" in line:
                title = line.split("#@title", 1)[1].strip()
                break

        # Find @param annotations
        params = []
        for line in source.split("\n"):
            if "#@param" in line:
                params.append(line.strip())

        # Detect dropdown options from @param
        dropdown_options = []
        for param in params:
            if "#@param [" in param or '#@param ["' in param:
                # Extract list of options
                try:
                    start = param.index("[")
                    end = param.rindex("]") + 1
                    opts = json.loads(param[start:end])
                    dropdown_options.append(opts)
                except (ValueError, json.JSONDecodeError):
                    pass

        # Detect text inputs
        text_inputs = []
        for param in params:
            if '{type:"string"}' in param or "{type:'string'}" in param:
                text_inputs.append(param)

        # Detect key cell roles from content
        roles = []
        source_lower = source.lower()
        if "pip install" in source_lower or "import " in source_lower and i < 3:
            roles.append("setup")
        if "num_cases" in source or "number of cases" in source_lower:
            roles.append("case_config")
        if "fhir" in source_lower and ("query" in source_lower or "request" in source_lower):
            roles.append("fhir_query")
        if "classify" in source_lower or "classification" in source_lower:
            roles.append("classification")
        if "agent" in source_lower and ("prompt" in source_lower or "run" in source_lower):
            roles.append("agent")
        if "summary" in source_lower or "comparison" in source_lower:
            roles.append("summary")
        if dropdown_options:
            roles.append("interactive")

        cells.append({
            "index": i,
            "type": cell_type,
            "is_form": is_form,
            "title": title,
            "params": params,
            "dropdown_options": dropdown_options,
            "text_inputs": text_inputs,
            "roles": roles,
            "source_preview": source[:300],
        })

    # Identify key cell groups
    setup_cells = [c for c in cells if "setup" in c["roles"]]
    interactive_cells = [c for c in cells if "interactive" in c["roles"]]
    agent_cells = [c for c in cells if "agent" in c["roles"]]
    summary_cells = [c for c in cells if "summary" in c["roles"]]

    return {
        "cells": cells,
        "total_cells": len(cells),
        "setup_cells": [c["index"] for c in setup_cells],
        "interactive_cells": [c["index"] for c in interactive_cells],
        "agent_cells": [c["index"] for c in agent_cells],
        "summary_cells": [c["index"] for c in summary_cells],
    }


# ── Student decision-making via Claude ───────────────────────────────────

def student_choose_action(evidence_so_far: list[str], available_actions: list[str],
                          case_context: str, model: str = "claude-sonnet-4-20250514") -> str:
    """Use Claude to decide what a student would do next.

    Given the evidence gathered so far and available actions, returns the
    action the student would most likely choose.
    """
    client = anthropic.Anthropic()

    prompt = f"""You are a BMI 512 graduate student investigating a clinical case in a FHIR hackathon.

Case context: {case_context}

Evidence gathered so far:
{chr(10).join(f"- {e}" for e in evidence_so_far) if evidence_so_far else "- No evidence gathered yet"}

Available actions (choose exactly one):
{chr(10).join(f"- {a}" for a in available_actions)}

As a student learning about FHIR and clinical data, which action would you choose next?
Think about what information would help differentiate between diabetes types or confirm
a diagnosis. Choose a query that gathers NEW information (don't repeat what you already know).

If you have enough evidence to classify, choose a classification action.
If you're still investigating, choose a query action.

Reply with ONLY the exact action text, nothing else."""

    response = client.messages.create(
        model=model,
        max_tokens=100,
        messages=[{"role": "user", "content": prompt}],
    )
    chosen = response.content[0].text.strip()

    # Match to available actions (handle slight text differences)
    for action in available_actions:
        if action.lower() == chosen.lower():
            return action
    # Fuzzy match — find closest
    for action in available_actions:
        if chosen.lower() in action.lower() or action.lower() in chosen.lower():
            return action

    # Fallback to first non-classification action, or first action
    query_actions = [a for a in available_actions if "classify" not in a.lower()]
    return query_actions[0] if query_actions else available_actions[0]


def student_classify(evidence: list[str], classification_options: list[str],
                     model: str = "claude-sonnet-4-20250514") -> str:
    """Use Claude to make a classification decision based on gathered evidence."""
    client = anthropic.Anthropic()

    prompt = f"""You are a BMI 512 graduate student classifying a patient based on clinical evidence.

Evidence gathered:
{chr(10).join(f"- {e}" for e in evidence)}

Classification options:
{chr(10).join(f"- {c}" for c in classification_options)}

Based on the evidence, which classification is most appropriate?
Reply with ONLY the exact classification text, nothing else."""

    response = client.messages.create(
        model=model,
        max_tokens=100,
        messages=[{"role": "user", "content": prompt}],
    )
    chosen = response.content[0].text.strip()

    for option in classification_options:
        if option.lower() == chosen.lower():
            return option
    for option in classification_options:
        if chosen.lower() in option.lower() or option.lower() in chosen.lower():
            return option
    return classification_options[0]


# ── Walkthrough engine ───────────────────────────────────────────────────

def run_walkthrough(page, notebook_analysis: dict, output_dir: Path,
                    num_cases: int = 2, max_queries_per_case: int = 4,
                    model: str = "claude-sonnet-4-20250514",
                    grant_secrets: bool = True) -> dict:
    """Play through the notebook as a student would.

    Returns a walkthrough report with all screenshots and decisions made.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    report = {
        "screenshots": [],
        "decisions": [],
        "cell_outputs": [],
        "errors": [],
    }

    def capture(label: str, cell_idx: int = None):
        """Take a screenshot and add to report."""
        path = output_dir / f"walkthrough_{label}.png"
        if cell_idx is not None:
            screenshot_cell(page, cell_idx, path)
        else:
            page.screenshot(path=str(path))
            print(f"  Screenshot: {path.name}", file=sys.stderr)
        report["screenshots"].append({"label": label, "path": str(path)})

    cells = notebook_analysis["cells"]

    # Phase 1: Run setup cells
    print("Phase 1: Running setup cells...", file=sys.stderr)
    setup_indices = notebook_analysis["setup_cells"]
    if not setup_indices:
        # Fallback: run first 3 code cells as setup
        setup_indices = [c["index"] for c in cells if c["type"] == "code"][:3]

    for idx in setup_indices:
        success = run_cell(page, idx, timeout_s=120, grant_secrets=grant_secrets)
        capture(f"setup_cell_{idx}", idx)
        if not success:
            report["errors"].append(f"Setup cell {idx} may have failed")

    # Phase 2: Find and configure case count
    print("Phase 2: Configuring case count...", file=sys.stderr)
    case_config_cells = [c for c in cells if "case_config" in c["roles"]]
    if case_config_cells:
        config_cell = case_config_cells[0]
        # Look for num_cases dropdown or input
        if config_cell["dropdown_options"]:
            # Try to set dropdown to num_cases
            for opts in config_cell["dropdown_options"]:
                if str(num_cases) in [str(o) for o in opts]:
                    set_dropdown(page, config_cell["index"], str(num_cases))
                    break
        run_cell(page, config_cell["index"], grant_secrets=grant_secrets)
        capture(f"case_config", config_cell["index"])

    # Phase 3: Walk through Activity 1 (interactive investigation)
    print("Phase 3: Walking through Activity 1...", file=sys.stderr)
    interactive = notebook_analysis["interactive_cells"]

    if interactive:
        main_interactive_cell = interactive[0]
        cell_idx = main_interactive_cell["index"]
        cell_info = cells[cell_idx]

        # Separate query actions from classification actions
        all_options = []
        for opt_list in cell_info.get("dropdown_options", []):
            all_options.extend(opt_list)

        query_actions = [a for a in all_options if "classify" not in a.lower()
                         and a.lower() not in ("", "---", "select an action")]
        classify_actions = [a for a in all_options if "classify" in a.lower()]

        # Run investigation loop for each case
        for case_num in range(num_cases):
            print(f"  Case {case_num + 1}/{num_cases}...", file=sys.stderr)
            evidence = []

            # Make queries
            for q in range(max_queries_per_case):
                if not query_actions:
                    break

                # Let Claude-as-student choose the next action
                action = student_choose_action(
                    evidence_so_far=evidence,
                    available_actions=query_actions,
                    case_context=f"Case {case_num + 1} of {num_cases}",
                    model=model,
                )
                report["decisions"].append({
                    "case": case_num + 1,
                    "query": q + 1,
                    "action": action,
                    "type": "query",
                })

                # Execute the action
                set_dropdown(page, cell_idx, action)
                run_cell(page, cell_idx, timeout_s=180, grant_secrets=grant_secrets)

                # Capture output
                output_text = get_cell_output_text(page, cell_idx)
                evidence.append(f"Query '{action}': {output_text[:300]}")
                report["cell_outputs"].append({
                    "case": case_num + 1,
                    "action": action,
                    "output": output_text[:500],
                })
                capture(f"case{case_num+1}_query{q+1}_{action.replace(' ', '_')[:20]}", cell_idx)

                # Handle any dialogs
                handle_colab_dialogs(page, grant_secrets=grant_secrets)

            # Make classification
            if classify_actions:
                classification = student_classify(
                    evidence=evidence,
                    classification_options=classify_actions,
                    model=model,
                )
                report["decisions"].append({
                    "case": case_num + 1,
                    "action": classification,
                    "type": "classification",
                })

                set_dropdown(page, cell_idx, classification)
                run_cell(page, cell_idx, timeout_s=60, grant_secrets=grant_secrets)
                capture(f"case{case_num+1}_classification", cell_idx)

                output_text = get_cell_output_text(page, cell_idx)
                report["cell_outputs"].append({
                    "case": case_num + 1,
                    "action": classification,
                    "output": output_text[:500],
                    "type": "classification_feedback",
                })

    # Phase 4: Walk through Activity 2 (prompt engineering) if present
    print("Phase 4: Checking for Activity 2 (agent)...", file=sys.stderr)
    agent_cells_list = [c for c in cells if "agent" in c["roles"]]

    for agent_cell in agent_cells_list:
        cell_idx = agent_cell["index"]

        # If there's a text input (prompt field), set a test prompt
        if agent_cell.get("text_inputs"):
            set_text_input(page, cell_idx,
                           "Classify this patient by querying their lab values and conditions")

        run_cell(page, cell_idx, timeout_s=300, grant_secrets=grant_secrets)
        capture(f"agent_cell_{cell_idx}", cell_idx)

        output_text = get_cell_output_text(page, cell_idx)
        report["cell_outputs"].append({
            "cell": cell_idx,
            "type": "agent_output",
            "output": output_text[:1000],
        })

    # Phase 5: Run summary cells
    print("Phase 5: Running summary...", file=sys.stderr)
    for idx in notebook_analysis["summary_cells"]:
        run_cell(page, idx, timeout_s=60, grant_secrets=grant_secrets)
        capture(f"summary_cell_{idx}", idx)

    # Final full-notebook screenshots at multiple positions
    print("Phase 6: Final overview screenshots...", file=sys.stderr)
    from colab_common import find_scroll_container, get_scroll_dimensions, scroll_to

    container_sel = find_scroll_container(page)
    dims = get_scroll_dimensions(page, container_sel)
    max_scroll = max(0, dims["scrollHeight"] - dims["clientHeight"])

    for i in range(5):
        frac = i / 4
        y = int(frac * max_scroll)
        scroll_to(page, container_sel, y)
        time.sleep(1)
        path = output_dir / f"walkthrough_overview_{i+1}_of_5.png"
        page.screenshot(path=str(path))
        report["screenshots"].append({"label": f"overview_{i+1}_of_5", "path": str(path)})

    return report


# ── Main ─────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Walk through a Colab notebook as a student"
    )
    parser.add_argument("file_id", help="Google Drive file ID of the notebook")
    parser.add_argument("--notebook", type=Path, required=True,
                        help="Path to the notebook .ipynb file (for structure analysis)")
    parser.add_argument("--num-cases", type=int, default=2,
                        help="Number of cases to walk through (default: 2)")
    parser.add_argument("--max-queries", type=int, default=4,
                        help="Max queries per case (default: 4)")
    parser.add_argument("--output-dir", type=Path, default=Path("./walkthrough_screenshots"),
                        help="Directory for screenshots")
    parser.add_argument("--model", default="claude-sonnet-4-20250514",
                        help="Claude model for student decisions")
    parser.add_argument("--review", action="store_true",
                        help="Run student_review.py on collected screenshots after walkthrough")
    parser.add_argument("--review-output", type=Path, default=None,
                        help="Save review JSON to file")
    parser.add_argument("--headless", action="store_true",
                        help="Run in headless mode")
    parser.add_argument("--storage-state", type=Path, default=DEFAULT_AUTH_PATH,
                        help=f"Auth file path (default: {DEFAULT_AUTH_PATH})")
    parser.add_argument("--no-grant-secrets", action="store_true",
                        help="Don't auto-grant secret access")
    parser.add_argument("--keep-open", action="store_true",
                        help="Keep browser open after walkthrough")
    args = parser.parse_args()

    if not check_auth(args.storage_state):
        print(json.dumps({"success": False,
                          "error": f"Auth not found. Run: python auth_setup.py"}))
        sys.exit(1)

    if not args.notebook.exists():
        print(f"ERROR: Notebook not found: {args.notebook}", file=sys.stderr)
        sys.exit(1)

    # Analyze notebook structure
    print("Analyzing notebook structure...", file=sys.stderr)
    analysis = analyze_notebook(args.notebook)
    print(f"  {analysis['total_cells']} cells: "
          f"{len(analysis['setup_cells'])} setup, "
          f"{len(analysis['interactive_cells'])} interactive, "
          f"{len(analysis['agent_cells'])} agent, "
          f"{len(analysis['summary_cells'])} summary",
          file=sys.stderr)

    _grant = not args.no_grant_secrets

    with sync_playwright() as p:
        browser, context = create_browser_context(
            p, auth_path=args.storage_state, headless=args.headless,
        )
        page = context.new_page()

        if not open_colab_notebook(page, args.file_id, grant_secrets=_grant,
                                   playwright=p, auth_path=args.storage_state,
                                   browser=browser):
            print(json.dumps({"success": False, "error": "Not signed in"}))
            browser.close()
            sys.exit(1)

        expand_all_sections(page)
        wait_for_runtime(page, timeout_s=90)

        report = run_walkthrough(
            page=page,
            notebook_analysis=analysis,
            output_dir=args.output_dir,
            num_cases=args.num_cases,
            max_queries_per_case=args.max_queries,
            model=args.model,
            grant_secrets=_grant,
        )

        if args.keep_open:
            print("Browser open for inspection. Close or Ctrl+C to exit.",
                  file=sys.stderr)
            try:
                page.wait_for_event("close", timeout=300000)
            except (PlaywrightTimeout, KeyboardInterrupt):
                pass

        browser.close()

    report["success"] = len(report["errors"]) == 0
    print(json.dumps(report, indent=2))

    # Optional: run student review on collected screenshots
    if args.review:
        print("\nRunning student perspective review...", file=sys.stderr)
        from student_review import load_screenshots, load_notebook_cells, load_checklist, run_review, format_report

        screenshots = load_screenshots(args.output_dir)
        cells = load_notebook_cells(args.notebook)
        checklist = load_checklist()

        review = run_review(
            screenshots=screenshots,
            cells=cells,
            checklist_md=checklist,
            model=args.model,
        )

        print(format_report(review), file=sys.stderr)

        if args.review_output:
            args.review_output.write_text(json.dumps(review, indent=2))
            print(f"\nReview saved to {args.review_output}", file=sys.stderr)


if __name__ == "__main__":
    main()
