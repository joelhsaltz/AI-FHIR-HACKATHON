#!/usr/bin/env python3
"""
Autonomous fix loop orchestrator for Colab notebook quality.

Runs the full pipeline: validate → generate → upload → walkthrough → review →
fix → iterate. Automatically fixes issues marked as auto-fixable, flags
others for human review.

Usage:
    python fix_loop.py --generator create_prototype_demo.py --notebook prototypes/you_are_the_agent_demo.ipynb --file-id <drive_id>
    python fix_loop.py --generator create_prototype_demo.py --notebook prototypes/you_are_the_agent_demo.ipynb --file-id <drive_id> --max-iterations 3
"""

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

try:
    import anthropic
except ImportError:
    print("ERROR: anthropic is not installed. Run: pip install anthropic", file=sys.stderr)
    sys.exit(1)

SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent


def run_command(cmd: list[str], cwd: str = None, timeout: int = 300) -> tuple[int, str, str]:
    """Run a command and return (returncode, stdout, stderr)."""
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout,
            cwd=cwd or str(PROJECT_ROOT),
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "Command timed out"


# ── Pipeline stages ──────────────────────────────────────────────────────

def stage_validate(notebook_path: Path) -> dict:
    """Run local validation on the notebook."""
    print("\n=== Stage: Local Validation ===", file=sys.stderr)
    validator = SCRIPT_DIR / "nb_validate.py"
    rc, stdout, stderr = run_command(
        [sys.executable, str(validator), str(notebook_path)]
    )
    success = rc == 0
    if not success:
        print(f"  Validation failed:\n{stderr}", file=sys.stderr)
    else:
        print("  Validation passed", file=sys.stderr)
    return {"stage": "validate", "success": success, "output": stdout, "errors": stderr}


def stage_generate(generator_path: Path) -> dict:
    """Run the generator script to produce/update the notebook."""
    print("\n=== Stage: Generate Notebook ===", file=sys.stderr)
    rc, stdout, stderr = run_command(
        [sys.executable, str(generator_path)]
    )
    success = rc == 0
    if not success:
        print(f"  Generator failed:\n{stderr}", file=sys.stderr)
    else:
        print(f"  Generator succeeded: {stdout.strip()}", file=sys.stderr)
    return {"stage": "generate", "success": success, "output": stdout, "errors": stderr}


def stage_upload(notebook_path: Path, file_id: str) -> dict:
    """Upload notebook to Google Drive (replace existing file).

    Uses the google-personal MCP if available, otherwise returns instructions.
    This stage is handled by the caller (Claude Code skill) since MCP access
    requires the Claude Code context. The fix loop returns a flag indicating
    upload is needed.
    """
    print("\n=== Stage: Upload to Drive ===", file=sys.stderr)
    # The actual upload is handled by the nb-ship skill via MCP
    # This stage just validates the notebook exists and is ready
    if not notebook_path.exists():
        return {"stage": "upload", "success": False,
                "error": f"Notebook not found: {notebook_path}"}

    size = notebook_path.stat().st_size
    print(f"  Notebook ready for upload: {notebook_path} ({size} bytes)", file=sys.stderr)
    return {
        "stage": "upload",
        "success": True,
        "notebook_path": str(notebook_path),
        "file_id": file_id,
        "needs_upload": True,
    }


def stage_walkthrough(file_id: str, notebook_path: Path, output_dir: Path,
                      num_cases: int = 2, model: str = "claude-sonnet-4-20250514",
                      headless: bool = False) -> dict:
    """Run the student walkthrough."""
    print("\n=== Stage: Student Walkthrough ===", file=sys.stderr)
    walkthrough_script = SCRIPT_DIR / "student_walkthrough.py"

    cmd = [
        sys.executable, str(walkthrough_script),
        file_id,
        "--notebook", str(notebook_path),
        "--num-cases", str(num_cases),
        "--output-dir", str(output_dir),
        "--model", model,
    ]
    if headless:
        cmd.append("--headless")

    rc, stdout, stderr = run_command(cmd, timeout=600)

    if rc != 0:
        print(f"  Walkthrough failed:\n{stderr}", file=sys.stderr)
        return {"stage": "walkthrough", "success": False, "errors": stderr}

    try:
        result = json.loads(stdout)
    except json.JSONDecodeError:
        return {"stage": "walkthrough", "success": False,
                "errors": f"Could not parse walkthrough output: {stdout[:500]}"}

    print(f"  Walkthrough completed: {len(result.get('screenshots', []))} screenshots",
          file=sys.stderr)
    return {"stage": "walkthrough", "success": True, "result": result}


def stage_review(screenshot_dir: Path, notebook_path: Path,
                 model: str = "claude-sonnet-4-20250514") -> dict:
    """Run the student perspective review."""
    print("\n=== Stage: Student Review ===", file=sys.stderr)
    review_script = SCRIPT_DIR / "student_review.py"

    cmd = [
        sys.executable, str(review_script),
        "--screenshots", str(screenshot_dir),
        "--notebook", str(notebook_path),
        "--model", model,
        "--human-readable",
    ]

    rc, stdout, stderr = run_command(cmd, timeout=120)

    if rc != 0:
        print(f"  Review failed:\n{stderr}", file=sys.stderr)
        return {"stage": "review", "success": False, "errors": stderr}

    try:
        result = json.loads(stdout)
    except json.JSONDecodeError:
        return {"stage": "review", "success": False,
                "errors": f"Could not parse review output: {stdout[:500]}"}

    print(f"  Review: {result['pass_count']} pass, {result['fail_count']} fail, "
          f"{result['unclear_count']} unclear", file=sys.stderr)
    return {"stage": "review", "success": True, "result": result}


# ── Auto-fix engine ──────────────────────────────────────────────────────

def generate_fix(generator_path: Path, issue: dict,
                 model: str = "claude-sonnet-4-20250514") -> dict:
    """Use Claude to generate a fix for the generator script.

    Returns {success: bool, edit: {old_string, new_string}} or {success: False, reason: ...}
    """
    client = anthropic.Anthropic()

    generator_source = generator_path.read_text()

    prompt = f"""You are fixing a Python generator script that produces a Colab notebook.

## The Issue

ID: {issue['id']}
Severity: {issue.get('severity', 'unknown')}
Description: {issue['description']}
Evidence: {issue.get('evidence', 'N/A')}
Suggested fix: {issue.get('suggested_fix', 'N/A')}

## Generator Script

```python
{generator_source}
```

## Instructions

Generate a MINIMAL fix for this issue. Output JSON with:
- "old_string": the exact string in the generator to replace (must be unique and present in the file)
- "new_string": the replacement string
- "explanation": one sentence explaining the change

The fix should be as small as possible — change only what's needed to address
the specific issue. Do not refactor, reorganize, or "improve" unrelated code.

Output ONLY valid JSON, no markdown code fences."""

    response = client.messages.create(
        model=model,
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}],
    )

    response_text = response.content[0].text.strip()
    if response_text.startswith("```"):
        lines = response_text.split("\n")
        lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        response_text = "\n".join(lines)

    try:
        fix = json.loads(response_text)
    except json.JSONDecodeError:
        return {"success": False, "reason": f"Could not parse fix response: {response_text[:300]}"}

    # Validate the fix
    old = fix.get("old_string", "")
    new = fix.get("new_string", "")
    if not old or not new:
        return {"success": False, "reason": "Fix missing old_string or new_string"}
    if old == new:
        return {"success": False, "reason": "old_string equals new_string"}
    if old not in generator_source:
        return {"success": False, "reason": f"old_string not found in generator: {old[:100]}"}
    if generator_source.count(old) > 1:
        return {"success": False, "reason": f"old_string is not unique ({generator_source.count(old)} occurrences)"}

    return {"success": True, "edit": fix}


def apply_fix(generator_path: Path, fix: dict) -> bool:
    """Apply a fix to the generator script."""
    source = generator_path.read_text()
    old = fix["old_string"]
    new = fix["new_string"]

    if old not in source:
        print(f"  ERROR: old_string not found in {generator_path}", file=sys.stderr)
        return False

    new_source = source.replace(old, new, 1)
    generator_path.write_text(new_source)
    print(f"  Applied fix: {fix.get('explanation', 'no explanation')}", file=sys.stderr)
    return True


# ── Main loop ────────────────────────────────────────────────────────────

def run_fix_loop(generator_path: Path, notebook_path: Path, file_id: str,
                 max_iterations: int = 5, num_cases: int = 2,
                 model: str = "claude-sonnet-4-20250514",
                 headless: bool = False) -> dict:
    """Run the full autonomous fix loop."""
    history = []
    flagged_for_human = []
    fixes_applied = []
    persistent_issues = {}  # issue_id -> consecutive count

    for iteration in range(1, max_iterations + 1):
        print(f"\n{'='*60}", file=sys.stderr)
        print(f"ITERATION {iteration}/{max_iterations}", file=sys.stderr)
        print(f"{'='*60}", file=sys.stderr)

        iter_result = {"iteration": iteration, "stages": []}

        # 1. Generate notebook
        gen_result = stage_generate(generator_path)
        iter_result["stages"].append(gen_result)
        if not gen_result["success"]:
            iter_result["outcome"] = "generator_failed"
            history.append(iter_result)
            break

        # 2. Validate locally
        val_result = stage_validate(notebook_path)
        iter_result["stages"].append(val_result)
        if not val_result["success"]:
            iter_result["outcome"] = "validation_failed"
            history.append(iter_result)
            # Try to fix validation errors in next iteration
            continue

        # 3. Upload (returns flag — actual upload handled by caller)
        upload_result = stage_upload(notebook_path, file_id)
        iter_result["stages"].append(upload_result)
        if upload_result.get("needs_upload"):
            print("  NOTE: Upload needed — in standalone mode, this must be done externally",
                  file=sys.stderr)

        # 4. Run walkthrough
        walkthrough_dir = Path(f"./walkthrough_iter_{iteration}")
        wt_result = stage_walkthrough(
            file_id, notebook_path, walkthrough_dir,
            num_cases=num_cases, model=model, headless=headless,
        )
        iter_result["stages"].append(wt_result)

        if not wt_result["success"]:
            iter_result["outcome"] = "walkthrough_failed"
            history.append(iter_result)
            continue

        # 5. Run review
        review_result = stage_review(walkthrough_dir, notebook_path, model=model)
        iter_result["stages"].append(review_result)

        if not review_result["success"]:
            iter_result["outcome"] = "review_failed"
            history.append(iter_result)
            continue

        review = review_result["result"]
        failures = [i for i in review.get("items", []) if i["status"] == "fail"]

        if not failures:
            iter_result["outcome"] = "all_passed"
            history.append(iter_result)
            print("\n*** ALL CHECKLIST ITEMS PASSED ***", file=sys.stderr)
            break

        # 6. Process failures
        auto_fixable = [i for i in failures if i.get("auto_fixable")]
        not_fixable = [i for i in failures if not i.get("auto_fixable")]

        # Flag non-auto-fixable issues
        for issue in not_fixable:
            if issue["id"] not in [f["id"] for f in flagged_for_human]:
                flagged_for_human.append(issue)
                print(f"  Flagged for human: {issue['id']} — {issue['description'][:80]}",
                      file=sys.stderr)

        # Check for persistent issues (same issue 2+ consecutive iterations)
        current_issue_ids = {i["id"] for i in failures}
        for issue_id in current_issue_ids:
            persistent_issues[issue_id] = persistent_issues.get(issue_id, 0) + 1
        # Clear issues that resolved
        for issue_id in list(persistent_issues.keys()):
            if issue_id not in current_issue_ids:
                del persistent_issues[issue_id]

        # Demote persistent auto-fixable issues to flagged
        demoted = []
        for issue in auto_fixable:
            if persistent_issues.get(issue["id"], 0) >= 2:
                print(f"  Demoting persistent issue: {issue['id']}", file=sys.stderr)
                flagged_for_human.append(issue)
                demoted.append(issue["id"])

        auto_fixable = [i for i in auto_fixable if i["id"] not in demoted]

        if not auto_fixable:
            iter_result["outcome"] = "no_auto_fixable_issues_remain"
            history.append(iter_result)
            print("\n*** No auto-fixable issues remain ***", file=sys.stderr)
            break

        # 7. Apply fixes
        print(f"\n  Attempting {len(auto_fixable)} auto-fix(es)...", file=sys.stderr)
        for issue in auto_fixable:
            fix_result = generate_fix(generator_path, issue, model=model)
            if fix_result["success"]:
                if apply_fix(generator_path, fix_result["edit"]):
                    fixes_applied.append({
                        "iteration": iteration,
                        "issue_id": issue["id"],
                        "fix": fix_result["edit"],
                    })
            else:
                print(f"  Could not generate fix for {issue['id']}: {fix_result['reason']}",
                      file=sys.stderr)
                flagged_for_human.append(issue)

        iter_result["outcome"] = "fixes_applied"
        iter_result["fixes_applied"] = len([f for f in fixes_applied if f["iteration"] == iteration])
        history.append(iter_result)

    # Build final report
    final_report = {
        "iterations_run": len(history),
        "max_iterations": max_iterations,
        "final_outcome": history[-1]["outcome"] if history else "no_iterations",
        "fixes_applied": fixes_applied,
        "flagged_for_human": flagged_for_human,
        "history": history,
    }

    return final_report


def format_final_report(report: dict) -> str:
    """Format the final report as human-readable text."""
    lines = []
    lines.append("=" * 60)
    lines.append("AUTONOMOUS FIX LOOP — FINAL REPORT")
    lines.append("=" * 60)
    lines.append(f"Iterations: {report['iterations_run']}/{report['max_iterations']}")
    lines.append(f"Outcome: {report['final_outcome']}")
    lines.append("")

    if report["fixes_applied"]:
        lines.append(f"--- FIXES APPLIED ({len(report['fixes_applied'])}) ---")
        for fix in report["fixes_applied"]:
            lines.append(f"  Iteration {fix['iteration']}: {fix['issue_id']}")
            if fix.get("fix", {}).get("explanation"):
                lines.append(f"    {fix['fix']['explanation']}")
        lines.append("")

    if report["flagged_for_human"]:
        lines.append(f"--- FLAGGED FOR HUMAN REVIEW ({len(report['flagged_for_human'])}) ---")
        for issue in report["flagged_for_human"]:
            severity = f" [{issue.get('severity', '').upper()}]" if issue.get("severity") else ""
            lines.append(f"  {issue['id']}{severity}")
            lines.append(f"    {issue['description']}")
            if issue.get("evidence"):
                lines.append(f"    Evidence: {issue['evidence']}")
        lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Autonomous notebook fix loop"
    )
    parser.add_argument("--generator", type=Path, required=True,
                        help="Path to the notebook generator script")
    parser.add_argument("--notebook", type=Path, required=True,
                        help="Path to the generated notebook .ipynb")
    parser.add_argument("--file-id", required=True,
                        help="Google Drive file ID for the notebook")
    parser.add_argument("--max-iterations", type=int, default=5,
                        help="Maximum fix iterations (default: 5)")
    parser.add_argument("--num-cases", type=int, default=2,
                        help="Number of cases in walkthrough (default: 2)")
    parser.add_argument("--model", default="claude-sonnet-4-20250514",
                        help="Claude model for review + fixes")
    parser.add_argument("--headless", action="store_true",
                        help="Run browser in headless mode")
    parser.add_argument("--output", type=Path, default=None,
                        help="Save final report JSON to file")
    args = parser.parse_args()

    if not args.generator.exists():
        print(f"ERROR: Generator not found: {args.generator}", file=sys.stderr)
        sys.exit(1)

    report = run_fix_loop(
        generator_path=args.generator,
        notebook_path=args.notebook,
        file_id=args.file_id,
        max_iterations=args.max_iterations,
        num_cases=args.num_cases,
        model=args.model,
        headless=args.headless,
    )

    # Print human-readable report
    print(format_final_report(report), file=sys.stderr)

    # Output JSON
    json_output = json.dumps(report, indent=2)
    if args.output:
        args.output.write_text(json_output)
        print(f"\nReport saved to {args.output}", file=sys.stderr)
    else:
        print(json_output)


if __name__ == "__main__":
    main()
