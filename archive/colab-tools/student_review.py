#!/usr/bin/env python3
"""
Screenshot-based student perspective review of Colab notebooks.

Sends Colab screenshots + notebook source to Claude via the Anthropic API
with a structured student-perspective prompt. Returns a JSON report evaluating
the notebook against the pedagogy checklist.

Usage:
    python student_review.py --screenshots ./colab_screenshots --notebook path.ipynb
    python student_review.py --screenshots ./colab_screenshots --notebook path.ipynb --docs docs/
    python student_review.py --screenshots ./colab_screenshots --notebook path.ipynb --output review.json
"""

import argparse
import base64
import json
import os
import sys
from pathlib import Path

try:
    import anthropic
except ImportError:
    print("ERROR: anthropic is not installed. Run: pip install anthropic", file=sys.stderr)
    sys.exit(1)

SCRIPT_DIR = Path(__file__).parent
CHECKLIST_PATH = SCRIPT_DIR.parent.parent / ".claude" / "skills" / "colab-notebook-tools" / "references" / "student-review-checklist.md"

CHECKLIST_ITEMS = [
    "task_complexity",
    "case_variety",
    "ui_clarity",
    "fhir_visibility",
    "feedback_quality",
    "dashboard_readability",
    "activity_flow",
    "code_hidden",
    "game_mechanics",
    "clinical_plausibility",
]

AUTO_FIXABLE = {
    "task_complexity": False,
    "case_variety": True,
    "ui_clarity": True,
    "fhir_visibility": True,
    "feedback_quality": True,
    "dashboard_readability": True,
    "activity_flow": False,
    "code_hidden": True,
    "game_mechanics": True,
    "clinical_plausibility": False,
}


def load_checklist():
    """Load the student review checklist markdown."""
    if CHECKLIST_PATH.exists():
        return CHECKLIST_PATH.read_text()
    # Fallback: inline summary
    return "\n".join(f"- {item}" for item in CHECKLIST_ITEMS)


def load_screenshots(screenshot_dir: Path) -> list[dict]:
    """Load screenshot images as base64 for the API."""
    images = []
    for path in sorted(screenshot_dir.glob("*.png")):
        with open(path, "rb") as f:
            data = base64.standard_b64encode(f.read()).decode("utf-8")
        images.append({
            "filename": path.name,
            "data": data,
            "media_type": "image/png",
        })
    return images


def load_notebook_cells(notebook_path: Path) -> list[dict]:
    """Extract cell info from notebook JSON for context."""
    with open(notebook_path) as f:
        nb = json.load(f)

    cells = []
    for i, cell in enumerate(nb.get("cells", [])):
        source = "".join(cell.get("source", []))
        cell_type = cell.get("cell_type", "unknown")
        metadata = cell.get("metadata", {})
        is_form = metadata.get("cellView") == "form"

        # Extract title from #@title annotation
        title = ""
        for line in source.split("\n"):
            if "#@title" in line:
                title = line.split("#@title", 1)[1].strip()
                break

        cells.append({
            "index": i,
            "type": cell_type,
            "is_form": is_form,
            "title": title,
            "source_preview": source[:500] + ("..." if len(source) > 500 else ""),
        })
    return cells


def build_review_prompt(checklist_md: str, cells: list[dict], docs_text: str = "") -> str:
    """Build the system + user prompt for the review."""
    system = """You are a student experience reviewer for educational Jupyter notebooks.

You adopt the persona of a BMI 512 Clinical Informatics and AI graduate student
at Stony Brook University. You know clinical medicine and medical terminology,
but you are new to FHIR, REST APIs, and AI agents. You are comfortable with
basic Python but not a software engineer.

Your job is to evaluate the notebook from this student's perspective, checking
each item on the provided checklist. For each item, determine if it passes,
fails, or is unclear from the available evidence.

Be critical and specific. The goal is to find issues before students encounter
them. Cite specific screenshots and cell content as evidence.

IMPORTANT: You must output ONLY valid JSON matching the specified schema.
No markdown, no commentary, no code fences — just the JSON object."""

    user_parts = []
    user_parts.append(f"""## Review Checklist

{checklist_md}

## Notebook Structure

The notebook has {len(cells)} cells:

""")

    for cell in cells:
        form_tag = " [FORM/HIDDEN]" if cell["is_form"] else ""
        title_tag = f' — "{cell["title"]}"' if cell["title"] else ""
        user_parts.append(
            f"Cell {cell['index']}: {cell['type']}{form_tag}{title_tag}\n"
        )

    if docs_text:
        user_parts.append(f"\n## Teaching Design Documents\n\n{docs_text}\n")

    user_parts.append("""
## Instructions

Review the screenshots and notebook content against each checklist item.
For each item, evaluate pass/fail/unclear. For failures, provide:
- The specific problem
- Which screenshot(s) show the evidence
- Whether it's auto-fixable
- A suggested fix if applicable

Output JSON in this exact format:
{
  "pass_count": <int>,
  "fail_count": <int>,
  "unclear_count": <int>,
  "items": [
    {
      "id": "<checklist_item_id>",
      "status": "pass" | "fail" | "unclear",
      "description": "<what was observed>",
      "evidence": "<which screenshot(s) or cell(s) — be specific>",
      "severity": "high" | "medium" | "low" | null,
      "auto_fixable": <bool>,
      "suggested_fix": "<specific fix for the generator script>" | null
    }
  ],
  "summary": "<2-3 sentence overall assessment>"
}

Every checklist item must appear exactly once in the items array.
""")

    return system, "".join(user_parts)


def run_review(screenshots: list[dict], cells: list[dict],
               checklist_md: str, docs_text: str = "",
               model: str = "claude-sonnet-4-20250514") -> dict:
    """Send screenshots + notebook to Claude API and get the review."""
    client = anthropic.Anthropic()

    system_prompt, user_text = build_review_prompt(checklist_md, cells, docs_text)

    # Build message content: screenshots first, then text
    content = []
    for img in screenshots:
        content.append({
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": img["media_type"],
                "data": img["data"],
            },
        })
        content.append({
            "type": "text",
            "text": f"[Screenshot: {img['filename']}]",
        })

    content.append({"type": "text", "text": user_text})

    print(f"Sending {len(screenshots)} screenshots + notebook ({len(cells)} cells) to {model}...",
          file=sys.stderr)

    response = client.messages.create(
        model=model,
        max_tokens=4096,
        system=system_prompt,
        messages=[{"role": "user", "content": content}],
    )

    # Parse the response
    response_text = response.content[0].text.strip()

    # Strip markdown code fences if present
    if response_text.startswith("```"):
        lines = response_text.split("\n")
        # Remove first and last lines (```json and ```)
        lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        response_text = "\n".join(lines)

    try:
        result = json.loads(response_text)
    except json.JSONDecodeError as e:
        print(f"WARNING: Could not parse response as JSON: {e}", file=sys.stderr)
        print(f"Raw response:\n{response_text[:1000]}", file=sys.stderr)
        result = {
            "pass_count": 0,
            "fail_count": 0,
            "unclear_count": len(CHECKLIST_ITEMS),
            "items": [],
            "summary": f"Review failed — could not parse API response. Raw: {response_text[:500]}",
            "raw_response": response_text,
        }

    # Validate and enrich the result
    result = validate_review(result)
    return result


def validate_review(result: dict) -> dict:
    """Validate review output: ensure all checklist items present, counts correct."""
    items = result.get("items", [])
    seen_ids = {item["id"] for item in items}

    # Add missing items as "unclear"
    for item_id in CHECKLIST_ITEMS:
        if item_id not in seen_ids:
            items.append({
                "id": item_id,
                "status": "unclear",
                "description": "Not evaluated — missing from review response",
                "evidence": "",
                "severity": None,
                "auto_fixable": AUTO_FIXABLE.get(item_id, False),
                "suggested_fix": None,
            })

    # Ensure auto_fixable matches checklist definition
    for item in items:
        item["auto_fixable"] = AUTO_FIXABLE.get(item["id"], item.get("auto_fixable", False))

    # Recount
    result["items"] = items
    result["pass_count"] = sum(1 for i in items if i["status"] == "pass")
    result["fail_count"] = sum(1 for i in items if i["status"] == "fail")
    result["unclear_count"] = sum(1 for i in items if i["status"] == "unclear")

    return result


def format_report(result: dict) -> str:
    """Format review result as human-readable text."""
    lines = []
    lines.append("=" * 60)
    lines.append("STUDENT PERSPECTIVE REVIEW")
    lines.append("=" * 60)
    lines.append(f"Pass: {result['pass_count']}  Fail: {result['fail_count']}  "
                 f"Unclear: {result['unclear_count']}")
    lines.append("")

    if result.get("summary"):
        lines.append(result["summary"])
        lines.append("")

    # Group by status
    for status, label in [("fail", "FAILURES"), ("unclear", "UNCLEAR"), ("pass", "PASSING")]:
        group = [i for i in result["items"] if i["status"] == status]
        if not group:
            continue
        lines.append(f"--- {label} ---")
        for item in group:
            severity = f" [{item.get('severity', '').upper()}]" if item.get("severity") else ""
            fixable = " (auto-fixable)" if item.get("auto_fixable") else ""
            lines.append(f"  {item['id']}{severity}{fixable}")
            if item.get("description"):
                lines.append(f"    {item['description']}")
            if item.get("evidence"):
                lines.append(f"    Evidence: {item['evidence']}")
            if item.get("suggested_fix"):
                lines.append(f"    Fix: {item['suggested_fix']}")
            lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Student perspective review of Colab notebook screenshots"
    )
    parser.add_argument("--screenshots", type=Path, required=True,
                        help="Directory containing Colab screenshots (PNG files)")
    parser.add_argument("--notebook", type=Path, required=True,
                        help="Path to the notebook .ipynb file")
    parser.add_argument("--docs", type=Path, default=None,
                        help="Optional: directory of teaching design docs for context")
    parser.add_argument("--output", type=Path, default=None,
                        help="Write JSON result to file (default: stdout)")
    parser.add_argument("--model", default="claude-sonnet-4-20250514",
                        help="Claude model to use (default: claude-sonnet-4-20250514)")
    parser.add_argument("--human-readable", action="store_true",
                        help="Print human-readable report to stderr")
    args = parser.parse_args()

    # Validate inputs
    if not args.screenshots.is_dir():
        print(f"ERROR: Screenshot directory not found: {args.screenshots}", file=sys.stderr)
        sys.exit(1)
    if not args.notebook.exists():
        print(f"ERROR: Notebook not found: {args.notebook}", file=sys.stderr)
        sys.exit(1)

    screenshots = load_screenshots(args.screenshots)
    if not screenshots:
        print(f"ERROR: No PNG files found in {args.screenshots}", file=sys.stderr)
        sys.exit(1)

    cells = load_notebook_cells(args.notebook)
    checklist_md = load_checklist()

    # Load optional docs
    docs_text = ""
    if args.docs and args.docs.is_dir():
        for doc_path in sorted(args.docs.glob("*.md")):
            docs_text += f"\n### {doc_path.name}\n\n"
            docs_text += doc_path.read_text()[:3000]  # Cap per doc

    # Run the review
    result = run_review(
        screenshots=screenshots,
        cells=cells,
        checklist_md=checklist_md,
        docs_text=docs_text,
        model=args.model,
    )

    # Output
    if args.human_readable:
        print(format_report(result), file=sys.stderr)

    json_output = json.dumps(result, indent=2)
    if args.output:
        args.output.write_text(json_output)
        print(f"Review saved to {args.output}", file=sys.stderr)
    else:
        print(json_output)


if __name__ == "__main__":
    main()
