#!/usr/bin/env python3
"""
Open a notebook in Google Colab via Playwright, run all cells, and take screenshots.

Uses storageState auth (from auth_setup.py) instead of Chrome profile copying.
Outputs JSON to stdout for programmatic use.

Usage:
    python colab_screenshot.py <google_drive_file_id>
    python colab_screenshot.py <file_id> --no-run
    python colab_screenshot.py <file_id> --sections
    python colab_screenshot.py <file_id> --headless --output-dir ./screenshots
"""

import argparse
import json
import sys
import time
from pathlib import Path

from colab_common import (
    DEFAULT_AUTH_PATH,
    RUN_ALL_KEY,
    PlaywrightTimeout,
    check_auth,
    check_runtime_connected,
    click_connect_button,
    create_browser_context,
    expand_all_sections,
    find_scroll_container,
    get_scroll_dimensions,
    handle_colab_dialogs,
    open_colab_notebook,
    scroll_to,
    sync_playwright,
    wait_for_runtime,
)


def run_all_cells(page, timeout_s=300, grant_secrets=True):
    """Trigger Runtime > Run All and wait for execution to complete."""
    print(f"  Triggering Run All ({RUN_ALL_KEY})...", file=sys.stderr)
    page.keyboard.press(RUN_ALL_KEY)
    time.sleep(3)

    # Handle "Run anyway" confirmation dialog
    try:
        run_anyway = page.wait_for_selector(
            "button:has-text('Run anyway'), mwc-button:has-text('Run anyway')",
            timeout=5000,
        )
        if run_anyway:
            run_anyway.click()
            print("  Clicked 'Run anyway' confirmation", file=sys.stderr)
    except PlaywrightTimeout:
        pass

    print(f"  Waiting up to {timeout_s}s for execution...", file=sys.stderr)
    start = time.time()
    last_status = ""
    saw_running = False

    while time.time() - start < timeout_s:
        # Handle dialogs that appear during execution (secrets, sessions, etc.)
        _handled = handle_colab_dialogs(page, grant_secrets=grant_secrets)
        for _h in _handled:
            print(f"  Handled dialog: {_h}", file=sys.stderr)
        if "too many sessions" in _handled:
            # Sessions dialog blocked execution — need to reconnect and re-run
            print("  Reconnecting runtime after session cleanup...", file=sys.stderr)
            time.sleep(3)
            click_connect_button(page)
            for _wait in range(30):
                if check_runtime_connected(page):
                    break
                time.sleep(2)
            time.sleep(2)
            print(f"  Re-triggering Run All ({RUN_ALL_KEY})...", file=sys.stderr)
            page.keyboard.press(RUN_ALL_KEY)
            time.sleep(3)
            try:
                run_anyway = page.wait_for_selector(
                    "button:has-text('Run anyway'), mwc-button:has-text('Run anyway')",
                    timeout=5000,
                )
                if run_anyway:
                    run_anyway.click()
                    print("  Clicked 'Run anyway' confirmation", file=sys.stderr)
            except PlaywrightTimeout:
                pass
            saw_running = False
            start = time.time()
            continue

        running = page.query_selector_all(
            "div.cell-execution-indicator[class*='running'], "
            "div[class*='running-indicator'], "
            "colab-run-button[aria-label*='executing'], "
            "div.executing, "
            "div[class*='pending'], "
            "svg.circular-progress"
        )
        if running:
            saw_running = True
            status = f"  {len(running)} cell(s) still running..."
            if status != last_status:
                print(status, file=sys.stderr)
                last_status = status
            time.sleep(3)
        else:
            if not saw_running and time.time() - start < 15:
                time.sleep(2)
                continue
            time.sleep(5)
            running_check = page.query_selector_all(
                "div.cell-execution-indicator[class*='running'], "
                "div[class*='running-indicator'], "
                "colab-run-button[aria-label*='executing'], "
                "div.executing, "
                "div[class*='pending'], "
                "svg.circular-progress"
            )
            if not running_check:
                elapsed = time.time() - start
                print(f"  Execution complete ({elapsed:.0f}s)", file=sys.stderr)
                return True

    print(f"  WARNING: Execution may not have completed within {timeout_s}s", file=sys.stderr)
    return False


def take_screenshot(page, path: Path, full_page=True, label=""):
    """Take a screenshot and return the path."""
    page.screenshot(path=str(path), full_page=full_page)
    print(f"  Screenshot: {path.name}" + (f" ({label})" if label else ""), file=sys.stderr)
    return str(path)


def take_sectioned_screenshots(page, base_path: Path, num_sections=5):
    """Take screenshots at evenly-spaced scroll positions through the notebook."""
    container_sel = find_scroll_container(page)
    paths = []

    dims = get_scroll_dimensions(page, container_sel)
    scroll_height = dims["scrollHeight"]
    client_height = dims["clientHeight"]
    max_scroll = max(0, scroll_height - client_height)

    positions = []
    for i in range(num_sections):
        frac = i / max(1, num_sections - 1)
        y = int(frac * max_scroll)
        positions.append((f"section_{i+1}_of_{num_sections}", y))

    for label, y in positions:
        scroll_to(page, container_sel, y)
        time.sleep(1)
        path = base_path.with_stem(f"{base_path.stem}_{label}")
        page.screenshot(path=str(path))
        print(f"  Screenshot: {path.name} ({label})", file=sys.stderr)
        paths.append(str(path))

    return paths


def main():
    parser = argparse.ArgumentParser(description="Screenshot a Colab notebook")
    parser.add_argument("file_id", help="Google Drive file ID of the notebook")
    parser.add_argument("--no-run", action="store_true",
                        help="Don't run cells, just screenshot")
    parser.add_argument("--sections", action="store_true",
                        help="Take sectioned screenshots (top/mid/bottom)")
    parser.add_argument("--headless", action="store_true",
                        help="Run in headless mode (uses new headless with full renderer)")
    parser.add_argument("--timeout", type=int, default=300,
                        help="Max seconds to wait for execution (default: 300)")
    parser.add_argument("--output-dir", type=Path, default=Path("./colab_screenshots"),
                        help="Directory for screenshots (default: ./colab_screenshots)")
    parser.add_argument("--output-prefix", default="colab",
                        help="Screenshot filename prefix (default: colab)")
    parser.add_argument("--storage-state", type=Path, default=DEFAULT_AUTH_PATH,
                        help=f"Path to Playwright storageState JSON (default: {DEFAULT_AUTH_PATH})")
    parser.add_argument("--no-grant-secrets", action="store_true",
                        help="Don't auto-grant secret access (click Cancel instead)")
    parser.add_argument("--num-sections", type=int, default=5,
                        help="Number of section screenshots (default: 5)")
    parser.add_argument("--keep-open", action="store_true",
                        help="Keep browser open after screenshots for manual inspection")
    args = parser.parse_args()

    # Check auth
    if not check_auth(args.storage_state):
        print(json.dumps({
            "success": False,
            "error": f"Auth not found at {args.storage_state}. Run: python auth_setup.py",
            "screenshots": [],
        }))
        sys.exit(1)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    screenshots = []
    result = {"success": False, "drive_file_id": args.file_id, "screenshots": []}
    _grant = not args.no_grant_secrets

    with sync_playwright() as p:
        browser, context = create_browser_context(
            p, auth_path=args.storage_state, headless=args.headless,
        )
        page = context.new_page()
        persistent_context = None  # Track if we switched to persistent profile

        if not open_colab_notebook(page, args.file_id, grant_secrets=_grant,
                                   playwright=p, auth_path=args.storage_state,
                                   browser=browser):
            result["error"] = "Not signed in. Auth may have expired. Run: python auth_setup.py"
            print(json.dumps(result))
            try:
                browser.close()
            except Exception:
                pass
            sys.exit(1)

        # If reauth switched to persistent context, use the new page
        if hasattr(page, '_persistent_page'):
            active_page = page._persistent_page
            persistent_context = page._persistent_context
        else:
            active_page = page

        # Pre-run screenshot
        pre_path = args.output_dir / f"{args.output_prefix}_before_run.png"
        screenshots.append(take_screenshot(active_page, pre_path, label="before execution"))

        if not args.no_run:
            expand_all_sections(active_page)
            wait_for_runtime(active_page, timeout_s=60)
            exec_success = run_all_cells(active_page, timeout_s=args.timeout, grant_secrets=_grant)
            time.sleep(3)

            # Post-run screenshot
            post_path = args.output_dir / f"{args.output_prefix}_after_run.png"
            screenshots.append(take_screenshot(active_page, post_path, label="after execution"))

            if args.sections:
                section_base = args.output_dir / f"{args.output_prefix}_section.png"
                screenshots.extend(take_sectioned_screenshots(active_page, section_base, num_sections=args.num_sections))

            result["success"] = exec_success
            if not exec_success:
                result["warning"] = "Execution may have timed out"
        else:
            if args.sections:
                section_base = args.output_dir / f"{args.output_prefix}_section.png"
                screenshots.extend(take_sectioned_screenshots(active_page, section_base, num_sections=args.num_sections))
            result["success"] = True

        result["screenshots"] = screenshots

        if args.keep_open:
            print("Browser open for inspection. Close window or Ctrl+C to exit.", file=sys.stderr)
            try:
                active_page.wait_for_event("close", timeout=300000)
            except (PlaywrightTimeout, KeyboardInterrupt):
                pass

        if persistent_context:
            persistent_context.close()
        else:
            browser.close()

    # Output JSON result to stdout
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
