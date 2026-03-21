#!/usr/bin/env python3
"""
Interact with individual cells in a Google Colab notebook via Playwright.

Supports running individual cells, setting dropdown values, taking cell-level
screenshots, and scripted playbook-driven interactions.

Usage:
    python colab_interact.py <file_id> --run-cell 0
    python colab_interact.py <file_id> --set-dropdown 5 "Get C-peptide" --run-cell 5
    python colab_interact.py <file_id> --playbook interactions.json
    python colab_interact.py <file_id> --screenshot-cell 5 --output-dir ./screenshots
"""

import argparse
import json
import sys
import time
from pathlib import Path

from colab_common import (
    DEFAULT_AUTH_PATH,
    PlaywrightTimeout,
    check_auth,
    check_runtime_connected,
    create_browser_context,
    expand_all_sections,
    find_scroll_container,
    handle_colab_dialogs,
    open_colab_notebook,
    scroll_to,
    sync_playwright,
    wait_for_runtime,
)


# ── Cell interaction primitives ──────────────────────────────────────────

def get_cell_info(page) -> list[dict]:
    """Get info about all cells: index, type, title, has_dropdown."""
    return page.evaluate("""() => {
        const cells = document.querySelectorAll('div.cell, colab-cell');
        const result = [];
        for (let i = 0; i < cells.length; i++) {
            const cell = cells[i];
            const isCode = cell.classList.contains('code') ||
                           cell.querySelector('.code-cell-content, .inputarea') !== null;

            // Find title from form view or title annotation
            let title = '';
            const titleEl = cell.querySelector('.cell-title, [class*="title"]');
            if (titleEl) title = titleEl.textContent.trim();

            // Check for dropdowns (Colab @param select elements)
            const selects = cell.querySelectorAll('select');
            let dropdownOptions = [];
            for (const sel of selects) {
                const opts = [];
                for (const opt of sel.options) {
                    opts.push(opt.value);
                }
                dropdownOptions.push(opts);
            }

            // Check for text inputs
            const textInputs = cell.querySelectorAll(
                'input[type="text"], input:not([type]), textarea.param-input'
            );

            result.push({
                index: i,
                type: isCode ? 'code' : 'markdown',
                title: title,
                has_dropdown: dropdownOptions.length > 0,
                dropdown_options: dropdownOptions,
                has_text_input: textInputs.length > 0,
            });
        }
        return result;
    }""")


def scroll_to_cell(page, cell_index: int):
    """Scroll the notebook so a specific cell is visible."""
    page.evaluate(f"""() => {{
        const cells = document.querySelectorAll('div.cell, colab-cell');
        if (cells[{cell_index}]) {{
            cells[{cell_index}].scrollIntoView({{ behavior: 'instant', block: 'center' }});
        }}
    }}""")
    time.sleep(0.5)


def run_cell(page, cell_index: int, timeout_s=180, grant_secrets=True):
    """Run a single cell by index and wait for completion.

    Uses Ctrl+Enter / Cmd+Enter after focusing the cell.
    Returns True if cell completed, False if timeout.
    """
    print(f"  Running cell {cell_index}...", file=sys.stderr)

    # Scroll to cell and click to focus
    scroll_to_cell(page, cell_index)

    # Click the cell to focus it
    page.evaluate(f"""() => {{
        const cells = document.querySelectorAll('div.cell, colab-cell');
        if (cells[{cell_index}]) {{
            cells[{cell_index}].click();
        }}
    }}""")
    time.sleep(0.5)

    # Try clicking the run button first (more reliable for form cells)
    clicked_run = page.evaluate(f"""() => {{
        const cells = document.querySelectorAll('div.cell, colab-cell');
        const cell = cells[{cell_index}];
        if (!cell) return false;

        // Look for run button in the cell
        const runBtn = cell.querySelector(
            'colab-run-button, button[aria-label*="Run"], ' +
            'button[aria-label*="run"], div.cell-execution-container button'
        );
        if (runBtn) {{
            runBtn.click();
            return true;
        }}

        // Also check shadow DOM
        function findRunBtn(root) {{
            const btns = root.querySelectorAll('button, colab-run-button');
            for (const btn of btns) {{
                const label = (btn.getAttribute('aria-label') || '').toLowerCase();
                if (label.includes('run') && !label.includes('runtime')) {{
                    btn.click();
                    return true;
                }}
            }}
            for (const el of root.querySelectorAll('*')) {{
                if (el.shadowRoot) {{
                    if (findRunBtn(el.shadowRoot)) return true;
                }}
            }}
            return false;
        }}
        return findRunBtn(cell);
    }}""")

    if not clicked_run:
        # Fallback: use keyboard shortcut (Ctrl/Cmd+Enter)
        import platform
        key = "Meta+Enter" if platform.system() == "Darwin" else "Control+Enter"
        page.keyboard.press(key)

    time.sleep(1)

    # Handle dialogs that might appear
    handle_colab_dialogs(page, grant_secrets=grant_secrets)

    # Wait for cell to complete
    start = time.time()
    while time.time() - start < timeout_s:
        is_running = page.evaluate(f"""() => {{
            const cells = document.querySelectorAll('div.cell, colab-cell');
            const cell = cells[{cell_index}];
            if (!cell) return false;

            // Check for running indicators
            const running = cell.querySelector(
                'div.cell-execution-indicator[class*="running"], ' +
                'svg.circular-progress, ' +
                'div.executing, div[class*="pending"]'
            );
            return running !== null;
        }}""")

        if not is_running and time.time() - start > 2:
            # Double-check after a brief pause
            time.sleep(1)
            still_running = page.evaluate(f"""() => {{
                const cells = document.querySelectorAll('div.cell, colab-cell');
                const cell = cells[{cell_index}];
                if (!cell) return false;
                const running = cell.querySelector(
                    'div.cell-execution-indicator[class*="running"], ' +
                    'svg.circular-progress, div.executing, div[class*="pending"]'
                );
                return running !== null;
            }}""")
            if not still_running:
                elapsed = time.time() - start
                print(f"  Cell {cell_index} completed ({elapsed:.0f}s)", file=sys.stderr)
                return True

        # Handle dialogs during execution
        handle_colab_dialogs(page, grant_secrets=grant_secrets)
        time.sleep(2)

    print(f"  WARNING: Cell {cell_index} may not have completed within {timeout_s}s",
          file=sys.stderr)
    return False


def set_dropdown(page, cell_index: int, value: str, dropdown_index: int = 0):
    """Set a Colab @param dropdown to a specific value.

    Colab renders @param dropdowns as <select> elements inside form cells.
    The dropdown_index parameter selects which dropdown if there are multiple.
    """
    print(f"  Setting dropdown in cell {cell_index} to '{value}'...", file=sys.stderr)

    scroll_to_cell(page, cell_index)

    result = page.evaluate(f"""() => {{
        const cells = document.querySelectorAll('div.cell, colab-cell');
        const cell = cells[{cell_index}];
        if (!cell) return {{ success: false, error: 'Cell not found' }};

        const selects = cell.querySelectorAll('select');
        if (selects.length === 0) return {{ success: false, error: 'No dropdown found' }};
        if (selects.length <= {dropdown_index}) return {{
            success: false,
            error: 'Dropdown index ' + {dropdown_index} + ' out of range (found ' + selects.length + ')'
        }};

        const select = selects[{dropdown_index}];
        const targetValue = '{value}';

        // Find matching option
        let found = false;
        for (const opt of select.options) {{
            if (opt.value === targetValue || opt.textContent.trim() === targetValue) {{
                select.value = opt.value;
                found = true;
                break;
            }}
        }}
        if (!found) {{
            const available = Array.from(select.options).map(o => o.value);
            return {{ success: false, error: 'Value not found', available: available }};
        }}

        // Dispatch change event so Colab picks up the new value
        select.dispatchEvent(new Event('change', {{ bubbles: true }}));
        select.dispatchEvent(new Event('input', {{ bubbles: true }}));
        return {{ success: true }};
    }}""")

    if not result.get("success"):
        print(f"  WARNING: Dropdown set failed: {result.get('error')}", file=sys.stderr)
        if "available" in result:
            print(f"  Available options: {result['available']}", file=sys.stderr)
    else:
        time.sleep(0.5)
    return result


def set_text_input(page, cell_index: int, value: str, input_index: int = 0):
    """Set a Colab @param text input to a specific value."""
    print(f"  Setting text input in cell {cell_index}...", file=sys.stderr)

    scroll_to_cell(page, cell_index)

    result = page.evaluate(f"""() => {{
        const cells = document.querySelectorAll('div.cell, colab-cell');
        const cell = cells[{cell_index}];
        if (!cell) return {{ success: false, error: 'Cell not found' }};

        const inputs = cell.querySelectorAll(
            'input[type="text"], input:not([type]), textarea.param-input'
        );
        if (inputs.length <= {input_index}) return {{
            success: false, error: 'Input index out of range'
        }};

        const input = inputs[{input_index}];
        // Clear and set new value
        input.value = '';
        input.focus();
        input.value = `{value}`;
        input.dispatchEvent(new Event('input', {{ bubbles: true }}));
        input.dispatchEvent(new Event('change', {{ bubbles: true }}));
        return {{ success: true }};
    }}""")

    if not result.get("success"):
        print(f"  WARNING: Text input set failed: {result.get('error')}", file=sys.stderr)
    else:
        time.sleep(0.5)
    return result


def screenshot_cell(page, cell_index: int, output_path: Path):
    """Take a screenshot focused on a specific cell and its output."""
    scroll_to_cell(page, cell_index)
    time.sleep(0.5)

    # Try to get the cell's bounding box for a focused screenshot
    bbox = page.evaluate(f"""() => {{
        const cells = document.querySelectorAll('div.cell, colab-cell');
        const cell = cells[{cell_index}];
        if (!cell) return null;
        const rect = cell.getBoundingClientRect();
        return {{
            x: Math.max(0, rect.x),
            y: Math.max(0, rect.y),
            width: Math.min(rect.width, window.innerWidth),
            height: Math.min(rect.height, window.innerHeight)
        }};
    }}""")

    if bbox and bbox["height"] > 0 and bbox["height"] < 2000:
        # Cell fits in a reasonable screenshot — clip to it
        page.screenshot(path=str(output_path), clip=bbox)
    else:
        # Cell too large or not found — take full viewport screenshot
        page.screenshot(path=str(output_path))

    print(f"  Screenshot: {output_path.name} (cell {cell_index})", file=sys.stderr)
    return str(output_path)


def get_cell_output_text(page, cell_index: int) -> str:
    """Extract the text content of a cell's output area."""
    return page.evaluate(f"""() => {{
        const cells = document.querySelectorAll('div.cell, colab-cell');
        const cell = cells[{cell_index}];
        if (!cell) return '';

        // Look for output area
        const output = cell.querySelector(
            '.output-area, .cell-output-container, .output, [class*="output"]'
        );
        if (!output) return '';
        return output.textContent || '';
    }}""")


# ── Playbook execution ───────────────────────────────────────────────────

def execute_playbook(page, playbook: list[dict], output_dir: Path,
                     grant_secrets: bool = True) -> list[dict]:
    """Execute a sequence of actions from a playbook JSON.

    Playbook format:
    [
        {"action": "run_cell", "cell": 0},
        {"action": "wait", "seconds": 5},
        {"action": "set_dropdown", "cell": 5, "value": "Get C-peptide"},
        {"action": "set_text", "cell": 7, "value": "Classify this patient"},
        {"action": "run_cell", "cell": 5},
        {"action": "screenshot", "label": "after_cpeptide"},
        {"action": "screenshot_cell", "cell": 5, "label": "cpeptide_output"},
        {"action": "get_output", "cell": 5}
    ]

    Returns a list of results, one per action.
    """
    results = []
    output_dir.mkdir(parents=True, exist_ok=True)

    for i, step in enumerate(playbook):
        action = step.get("action")
        print(f"  Playbook step {i+1}/{len(playbook)}: {action}", file=sys.stderr)

        if action == "run_cell":
            cell_idx = step["cell"]
            timeout = step.get("timeout", 180)
            success = run_cell(page, cell_idx, timeout_s=timeout, grant_secrets=grant_secrets)
            results.append({"action": action, "cell": cell_idx, "success": success})

        elif action == "wait":
            seconds = step.get("seconds", 2)
            time.sleep(seconds)
            results.append({"action": action, "seconds": seconds})

        elif action == "set_dropdown":
            cell_idx = step["cell"]
            value = step["value"]
            dd_idx = step.get("dropdown_index", 0)
            result = set_dropdown(page, cell_idx, value, dropdown_index=dd_idx)
            results.append({"action": action, "cell": cell_idx, "value": value, **result})

        elif action == "set_text":
            cell_idx = step["cell"]
            value = step["value"]
            input_idx = step.get("input_index", 0)
            result = set_text_input(page, cell_idx, value, input_index=input_idx)
            results.append({"action": action, "cell": cell_idx, "value": value, **result})

        elif action == "screenshot":
            label = step.get("label", f"step_{i+1}")
            path = output_dir / f"playbook_{label}.png"
            page.screenshot(path=str(path))
            print(f"  Screenshot: {path.name}", file=sys.stderr)
            results.append({"action": action, "label": label, "path": str(path)})

        elif action == "screenshot_cell":
            cell_idx = step["cell"]
            label = step.get("label", f"cell_{cell_idx}")
            path = output_dir / f"playbook_{label}.png"
            screenshot_cell(page, cell_idx, path)
            results.append({"action": action, "cell": cell_idx, "path": str(path)})

        elif action == "get_output":
            cell_idx = step["cell"]
            text = get_cell_output_text(page, cell_idx)
            results.append({"action": action, "cell": cell_idx, "output": text[:2000]})

        else:
            print(f"  WARNING: Unknown action '{action}'", file=sys.stderr)
            results.append({"action": action, "error": "unknown action"})

    return results


# ── Main ─────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Interact with Colab notebook cells")
    parser.add_argument("file_id", help="Google Drive file ID of the notebook")
    parser.add_argument("--run-cell", type=int, action="append", default=[],
                        help="Run a specific cell by index (can be repeated)")
    parser.add_argument("--set-dropdown", nargs=2, action="append", default=[],
                        metavar=("CELL_INDEX", "VALUE"),
                        help="Set dropdown in cell to value (can be repeated)")
    parser.add_argument("--screenshot-cell", type=int, action="append", default=[],
                        help="Screenshot a specific cell (can be repeated)")
    parser.add_argument("--playbook", type=Path, default=None,
                        help="JSON playbook file for scripted interactions")
    parser.add_argument("--list-cells", action="store_true",
                        help="List all cells with their info and exit")
    parser.add_argument("--headless", action="store_true",
                        help="Run in headless mode")
    parser.add_argument("--timeout", type=int, default=180,
                        help="Max seconds per cell execution (default: 180)")
    parser.add_argument("--output-dir", type=Path, default=Path("./colab_screenshots"),
                        help="Directory for screenshots")
    parser.add_argument("--storage-state", type=Path, default=DEFAULT_AUTH_PATH,
                        help=f"Auth file path (default: {DEFAULT_AUTH_PATH})")
    parser.add_argument("--no-grant-secrets", action="store_true",
                        help="Don't auto-grant secret access")
    parser.add_argument("--keep-open", action="store_true",
                        help="Keep browser open after interactions")
    args = parser.parse_args()

    if not check_auth(args.storage_state):
        print(json.dumps({"success": False,
                          "error": f"Auth not found at {args.storage_state}. Run: python auth_setup.py"}))
        sys.exit(1)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    _grant = not args.no_grant_secrets
    result = {"success": False, "drive_file_id": args.file_id}

    with sync_playwright() as p:
        browser, context = create_browser_context(
            p, auth_path=args.storage_state, headless=args.headless,
        )
        page = context.new_page()

        if not open_colab_notebook(page, args.file_id, grant_secrets=_grant):
            result["error"] = "Not signed in. Run: python auth_setup.py"
            print(json.dumps(result))
            browser.close()
            sys.exit(1)

        # List cells mode
        if args.list_cells:
            cells = get_cell_info(page)
            result["success"] = True
            result["cells"] = cells
            print(json.dumps(result, indent=2))
            browser.close()
            return

        # Connect runtime for cell execution
        expand_all_sections(page)
        wait_for_runtime(page, timeout_s=60)

        results = []

        # Execute playbook if provided
        if args.playbook:
            with open(args.playbook) as f:
                playbook = json.load(f)
            results = execute_playbook(page, playbook, args.output_dir, grant_secrets=_grant)

        # Execute individual commands
        for cell_idx, value in args.set_dropdown:
            set_dropdown(page, int(cell_idx), value)

        for cell_idx in args.run_cell:
            success = run_cell(page, cell_idx, timeout_s=args.timeout, grant_secrets=_grant)
            results.append({"action": "run_cell", "cell": cell_idx, "success": success})

        for cell_idx in args.screenshot_cell:
            path = args.output_dir / f"cell_{cell_idx}.png"
            screenshot_cell(page, cell_idx, path)
            results.append({"action": "screenshot_cell", "cell": cell_idx, "path": str(path)})

        result["success"] = True
        result["results"] = results

        if args.keep_open:
            print("Browser open for inspection. Close window or Ctrl+C to exit.",
                  file=sys.stderr)
            try:
                page.wait_for_event("close", timeout=300000)
            except (PlaywrightTimeout, KeyboardInterrupt):
                pass

        browser.close()

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
