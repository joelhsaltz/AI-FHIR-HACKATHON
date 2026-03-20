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
import platform
import sys
import time
from pathlib import Path

try:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
except ImportError:
    print("ERROR: playwright is not installed. Run: pip install playwright && playwright install chromium",
          file=sys.stderr)
    sys.exit(1)

DEFAULT_AUTH_PATH = Path.home() / ".colab-notebook-tools" / "auth.json"
COLAB_URL_TEMPLATE = "https://colab.research.google.com/drive/{file_id}"
IS_MACOS = platform.system() == "Darwin"
RUN_ALL_KEY = "Meta+F9" if IS_MACOS else "Control+F9"


def check_auth(auth_path: Path) -> bool:
    """Check if storageState file exists and is non-empty."""
    if not auth_path.exists():
        return False
    if auth_path.stat().st_size < 10:
        return False
    return True


def wait_for_colab_load(page, timeout_ms=60000):
    """Wait for Colab notebook to finish loading."""
    try:
        page.wait_for_selector(
            "div.notebook-container, colab-notebook",
            timeout=timeout_ms,
        )
    except PlaywrightTimeout:
        print("  WARNING: Notebook container not found, continuing anyway", file=sys.stderr)

    try:
        page.wait_for_selector(
            "div.cell, colab-cell, div[class*='cell']",
            timeout=30000,
        )
    except PlaywrightTimeout:
        print("  WARNING: No cells found", file=sys.stderr)

    time.sleep(3)


def check_signed_in(page) -> bool:
    """Check if the page shows a sign-in prompt (meaning auth expired)."""
    sign_in = page.query_selector(
        "a[href*='ServiceLogin'], "
        "button:has-text('Sign in'), "
        "a:has-text('Sign in')"
    )
    return sign_in is None


def dismiss_dialog(page, btn_text):
    """Click a button by text in any dialog, piercing shadow DOM.

    Returns True if the button was found and clicked, False otherwise.
    """
    clicked = page.evaluate(f"""() => {{
        function findButton(root) {{
            const elements = root.querySelectorAll(
                'button, mwc-button, a, [role="button"], md-text-button, md-filled-button'
            );
            for (const el of elements) {{
                const text = (el.textContent || '').trim();
                if (text === '{btn_text}') {{
                    el.click();
                    return true;
                }}
            }}
            for (const el of root.querySelectorAll('*')) {{
                if (el.shadowRoot) {{
                    const found = findButton(el.shadowRoot);
                    if (found) return true;
                }}
            }}
            return false;
        }}
        return findButton(document);
    }}""")
    if clicked:
        time.sleep(1)
    return clicked


def handle_colab_dialogs(page, grant_secrets=True):
    """Handle common Colab dialogs: secret access, too many sessions, etc.

    Returns a list of dialog names that were handled.
    """
    handled = []

    # "Too many sessions" — click Manage sessions, then terminate others
    if dismiss_dialog(page, "Manage sessions"):
        handled.append("too many sessions")
        time.sleep(2)
        # Look for Terminate buttons in the session manager
        for _ in range(5):
            if dismiss_dialog(page, "Terminate"):
                time.sleep(1)
            else:
                break
        # Close the session manager by pressing Escape
        page.keyboard.press("Escape")
        time.sleep(1)

    # "Notebook does not have secret access" — grant or cancel
    btn_text = "Grant access" if grant_secrets else "Cancel"
    if dismiss_dialog(page, btn_text):
        handled.append("secret access")

    return handled


def expand_all_sections(page):
    """Expand all collapsed section headers so Run All reaches every cell."""
    collapsed = page.query_selector_all(
        "div.section-header.collapsed, "
        "div[class*='section-header'][class*='collapsed'], "
        "h1.collapse-button[aria-expanded='false'], "
        "div.cell h1, div.cell h2"
    )
    if collapsed:
        print(f"  Expanding {len(collapsed)} collapsed section(s)...", file=sys.stderr)
        for header in collapsed:
            try:
                header.click()
                time.sleep(0.3)
            except Exception:
                pass

    page.evaluate("""
        document.querySelectorAll('[class*="section-header"]').forEach(el => {
            if (el.classList.contains('collapsed')) el.click();
        });
        document.querySelectorAll('.cell-collapsed').forEach(el => {
            el.click();
        });
    """)
    time.sleep(1)


def _click_connect_button(page):
    """Click the Connect/Reconnect button, piercing shadow DOM if needed."""
    # Try via JS piercing shadow DOM — most reliable approach.
    # Colab's connect button text varies: "Connect", "Reconnect",
    # "Connect to a new runtime", or just the colab-connect-button element.
    clicked = page.evaluate("""() => {
        function findConnect(root) {
            const buttons = root.querySelectorAll(
                'button, colab-connect-button, [role="button"]'
            );
            for (const btn of buttons) {
                const text = (btn.textContent || '').trim().toLowerCase();
                if (text.includes('connect') && !text.includes('disconnect')) {
                    btn.click();
                    return true;
                }
            }
            for (const el of root.querySelectorAll('*')) {
                if (el.shadowRoot) {
                    const found = findConnect(el.shadowRoot);
                    if (found) return true;
                }
            }
            return false;
        }
        return findConnect(document);
    }""")
    if clicked:
        return True
    # Fallback: try standard selectors
    connect_btn = page.query_selector(
        "button:has-text('Connect'), "
        "button:has-text('Reconnect'), "
        "colab-connect-button, "
        "#connect"
    )
    if connect_btn:
        connect_btn.click()
        return True
    return False


def _check_runtime_connected(page):
    """Check if Colab runtime is connected, including RAM/Disk indicator.

    Only returns True on definitive positive signals (RAM/Disk usage bars).
    """
    return page.evaluate("""() => {
        // Helper to get all text including shadow DOM
        function getAllText(root) {
            let text = '';
            if (root.textContent) text += root.textContent;
            for (const el of (root.querySelectorAll ? root.querySelectorAll('*') : [])) {
                if (el.shadowRoot) text += getAllText(el.shadowRoot);
            }
            return text;
        }
        // Check the connect button area specifically for RAM/Disk usage bars
        // This is the definitive sign of a connected runtime
        const btn = document.querySelector('colab-connect-button');
        if (btn) {
            const btnText = getAllText(btn).toLowerCase();
            if (btnText.includes('ram') && btnText.includes('disk')) return true;
        }
        // Also check for the resource usage indicator that appears when connected
        const resourceEl = document.querySelector(
            'colab-usage-bar, div[class*="resource"], div[class*="usage"]'
        );
        if (resourceEl) {
            const text = getAllText(resourceEl).toLowerCase();
            if (text.includes('ram') || text.includes('disk')) return true;
        }
        return false;
    }""")


def wait_for_runtime(page, timeout_s=90):
    """Wait for Colab to connect to a runtime, clicking Connect if needed."""
    print("  Waiting for runtime connection...", file=sys.stderr)

    if _check_runtime_connected(page):
        print("  Runtime already connected", file=sys.stderr)
        return True

    if _click_connect_button(page):
        print("  Clicked Connect button", file=sys.stderr)
    else:
        print("  WARNING: Could not find Connect button", file=sys.stderr)

    # Give Colab a moment to start the connection process
    time.sleep(5)

    start = time.time()
    _sessions_handled = False
    while time.time() - start < timeout_s:
        # Handle "Too many sessions" dialog if it appears
        if not _sessions_handled and dismiss_dialog(page, "Manage sessions"):
            print("  Handling 'too many sessions'...", file=sys.stderr)
            time.sleep(2)
            for _ in range(10):
                if dismiss_dialog(page, "Terminate"):
                    time.sleep(1)
                else:
                    break
            page.keyboard.press("Escape")
            time.sleep(3)
            _sessions_handled = True
            # Reset timer — give full timeout after session cleanup
            start = time.time()
            # Retry Connect after terminating sessions
            if _click_connect_button(page):
                print("  Retrying Connect after terminating sessions", file=sys.stderr)
            else:
                # If no connect button found, page may need reload
                print("  No Connect button found, reloading page...", file=sys.stderr)
                page.reload(wait_until="domcontentloaded", timeout=30000)
                wait_for_colab_load(page)
                _click_connect_button(page)
                print("  Clicked Connect after reload", file=sys.stderr)
            continue

        if _check_runtime_connected(page):
            elapsed = time.time() - start
            print(f"  Runtime connected ({elapsed:.0f}s)", file=sys.stderr)
            return True
        time.sleep(2)

    print("  WARNING: Runtime may not be connected", file=sys.stderr)
    return False


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
            _click_connect_button(page)
            # Wait for runtime to connect before re-triggering
            for _wait in range(30):
                if _check_runtime_connected(page):
                    break
                time.sleep(2)
            time.sleep(2)
            print(f"  Re-triggering Run All ({RUN_ALL_KEY})...", file=sys.stderr)
            page.keyboard.press(RUN_ALL_KEY)
            time.sleep(3)
            # Handle "Run anyway" confirmation
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
            start = time.time()  # Reset timer
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


def find_scroll_container(page):
    """Find the scrollable container in Colab's DOM.

    Colab uses a custom <colab-scroller> element (id='notebook-main') as its
    main scrollable container, not the window. We detect this dynamically by
    looking for elements with significant scroll overflow.
    """
    container = page.evaluate("""() => {
        // Known Colab scroll container selectors (most specific first)
        const selectors = [
            'colab-scroller#notebook-main',
            'colab-scroller.notebook-container',
            '#notebook-main',
            '#main-area',
            'div.notebook-container',
        ];
        for (const sel of selectors) {
            const el = document.querySelector(sel);
            if (el && el.scrollHeight > el.clientHeight + 100) {
                return sel;
            }
        }
        // Fallback: find any element with large scroll overflow
        const all = document.querySelectorAll('*');
        for (const el of all) {
            if (el.scrollHeight > 2000 && el.scrollHeight > el.clientHeight + 100
                && el.clientHeight > 100) {
                const style = getComputedStyle(el);
                if (style.overflow === 'auto' || style.overflow === 'scroll'
                    || style.overflowY === 'auto' || style.overflowY === 'scroll'
                    || style.overflow.includes('scroll') || style.overflow.includes('auto')) {
                    // Build a selector for this element
                    if (el.id) return '#' + el.id;
                    if (el.tagName) return el.tagName.toLowerCase();
                    return null;
                }
            }
        }
        return null;
    }""")
    return container


def take_sectioned_screenshots(page, base_path: Path, num_sections=5):
    """Take screenshots at evenly-spaced scroll positions through the notebook.

    Uses num_sections (default 5) to cover the full notebook length.
    Detects Colab's scroll container so scrolling actually works.
    """
    container_sel = find_scroll_container(page)
    paths = []

    if container_sel:
        # Scroll inside the Colab container
        dims = page.evaluate(f"""() => {{
            const el = document.querySelector('{container_sel}');
            return {{ scrollHeight: el.scrollHeight, clientHeight: el.clientHeight }};
        }}""")
        scroll_height = dims["scrollHeight"]
        client_height = dims["clientHeight"]
        max_scroll = max(0, scroll_height - client_height)

        positions = []
        for i in range(num_sections):
            frac = i / max(1, num_sections - 1)
            y = int(frac * max_scroll)
            positions.append((f"section_{i+1}_of_{num_sections}", y))

        for label, y in positions:
            page.evaluate(f"""() => {{
                const el = document.querySelector('{container_sel}');
                el.scrollTo(0, {y});
            }}""")
            time.sleep(1)
            path = base_path.with_stem(f"{base_path.stem}_{label}")
            page.screenshot(path=str(path))
            print(f"  Screenshot: {path.name} ({label})", file=sys.stderr)
            paths.append(str(path))
    else:
        # Fallback to window scroll
        scroll_height = page.evaluate("document.documentElement.scrollHeight")
        viewport_height = page.viewport_size["height"]
        max_scroll = max(0, scroll_height - viewport_height)

        positions = []
        for i in range(num_sections):
            frac = i / max(1, num_sections - 1)
            y = int(frac * max_scroll)
            positions.append((f"section_{i+1}_of_{num_sections}", y))

        for label, y in positions:
            page.evaluate(f"window.scrollTo(0, {y})")
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
    url = COLAB_URL_TEMPLATE.format(file_id=args.file_id)
    screenshots = []
    result = {"success": False, "drive_file_id": args.file_id, "screenshots": []}

    print(f"Opening: {url}", file=sys.stderr)

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless="new" if args.headless else False,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-first-run",
            ],
        )
        context = browser.new_context(
            storage_state=str(args.storage_state),
            viewport={"width": 1280, "height": 900},
        )

        page = context.new_page()
        page.goto(url, wait_until="domcontentloaded", timeout=60000)

        print("Waiting for Colab to load...", file=sys.stderr)
        wait_for_colab_load(page)

        # Check if signed in
        if not check_signed_in(page):
            result["error"] = "Not signed in. Auth may have expired. Run: python auth_setup.py"
            print(json.dumps(result))
            browser.close()
            sys.exit(1)

        # Handle any dialogs that appear on load (secrets, too many sessions, etc.)
        _grant = not args.no_grant_secrets
        _handled = handle_colab_dialogs(page, grant_secrets=_grant)
        for _h in _handled:
            print(f"  Handled dialog: {_h}", file=sys.stderr)

        # Pre-run screenshot
        pre_path = args.output_dir / f"{args.output_prefix}_before_run.png"
        screenshots.append(take_screenshot(page, pre_path, label="before execution"))

        if not args.no_run:
            expand_all_sections(page)
            wait_for_runtime(page, timeout_s=60)
            exec_success = run_all_cells(page, timeout_s=args.timeout, grant_secrets=_grant)
            time.sleep(3)

            # Post-run screenshot
            post_path = args.output_dir / f"{args.output_prefix}_after_run.png"
            screenshots.append(take_screenshot(page, post_path, label="after execution"))

            if args.sections:
                section_base = args.output_dir / f"{args.output_prefix}_section.png"
                screenshots.extend(take_sectioned_screenshots(page, section_base))

            result["success"] = exec_success
            if not exec_success:
                result["warning"] = "Execution may have timed out"
        else:
            if args.sections:
                section_base = args.output_dir / f"{args.output_prefix}_section.png"
                screenshots.extend(take_sectioned_screenshots(page, section_base))
            result["success"] = True

        result["screenshots"] = screenshots

        if args.keep_open:
            print("Browser open for inspection. Close window or Ctrl+C to exit.", file=sys.stderr)
            try:
                page.wait_for_event("close", timeout=300000)
            except (PlaywrightTimeout, KeyboardInterrupt):
                pass

        browser.close()

    # Output JSON result to stdout
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
