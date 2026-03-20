#!/usr/bin/env python3
"""
Open a notebook in Google Colab via Playwright, run all cells, and take screenshots.

Uses Joel's existing Chrome profile so Google auth is already established.
Screenshots are saved to prototypes/colab_screenshots/.

Usage:
    python screenshot_colab.py <google_drive_file_id>
    python screenshot_colab.py <google_drive_file_id> --no-run   # screenshot without running cells
    python screenshot_colab.py <google_drive_file_id> --sections  # take sectioned screenshots
"""

import argparse
import os
import shutil
import sys
import tempfile
import time
from pathlib import Path

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

SCRIPT_DIR = Path(__file__).parent
SCREENSHOT_DIR = SCRIPT_DIR / "prototypes" / "colab_screenshots"
CHROME_USER_DATA = Path.home() / "Library" / "Application Support" / "Google" / "Chrome"
COLAB_URL_TEMPLATE = "https://colab.research.google.com/drive/{file_id}"


def create_lightweight_profile(source_profile):
    """Copy only auth-related files from Chrome profile to a temp directory."""
    tmp = tempfile.mkdtemp(prefix="colab_chrome_")
    src_default = Path(source_profile) / "Default"
    dst_default = Path(tmp) / "Default"
    dst_default.mkdir(parents=True)

    # Files needed for Google auth in Colab
    auth_files = [
        "Cookies", "Cookies-journal",
        "Login Data", "Login Data-journal",
        "Web Data", "Web Data-journal",
        "Preferences", "Secure Preferences",
    ]
    for fname in auth_files:
        src = src_default / fname
        if src.exists():
            shutil.copy2(src, dst_default / fname)

    # Copy Local State (needed for cookie decryption on macOS)
    local_state = Path(source_profile) / "Local State"
    if local_state.exists():
        shutil.copy2(local_state, Path(tmp) / "Local State")

    print(f"  Lightweight profile created at: {tmp}")
    return tmp


def take_full_screenshot(page, path, label=""):
    """Take a full-page screenshot."""
    page.screenshot(path=str(path), full_page=True)
    print(f"  Screenshot saved: {path.name}" + (f" ({label})" if label else ""))


def take_sectioned_screenshots(page, base_path):
    """Take screenshots of top, middle, and bottom of the notebook."""
    viewport_height = page.viewport_size["height"]
    scroll_height = page.evaluate("document.documentElement.scrollHeight")

    positions = [
        ("top", 0),
        ("middle", max(0, scroll_height // 2 - viewport_height // 2)),
        ("bottom", max(0, scroll_height - viewport_height)),
    ]

    for label, y in positions:
        page.evaluate(f"window.scrollTo(0, {y})")
        time.sleep(0.5)  # let rendering settle
        path = base_path.with_stem(f"{base_path.stem}_{label}")
        page.screenshot(path=str(path))
        print(f"  Screenshot saved: {path.name} ({label})")


def wait_for_colab_load(page, timeout_ms=60000):
    """Wait for Colab notebook to finish loading."""
    # Wait for the notebook container to appear
    try:
        page.wait_for_selector("div.notebook-container, colab-notebook", timeout=timeout_ms)
        print("  Notebook container loaded")
    except PlaywrightTimeout:
        print("  WARNING: Notebook container not found, continuing anyway")

    # Wait for cells to appear
    try:
        page.wait_for_selector(
            "div.cell, colab-cell, div[class*='cell']",
            timeout=30000,
        )
        print("  Cells visible")
    except PlaywrightTimeout:
        print("  WARNING: No cells found")

    # Extra settle time for Colab JS
    time.sleep(3)


def expand_all_sections(page):
    """Expand all collapsed section headers so Run All can reach every cell."""
    # Colab collapses cells under section headers — click all collapsed ones
    collapsed = page.query_selector_all(
        "div.section-header.collapsed, "
        "div[class*='section-header'][class*='collapsed'], "
        "h1.collapse-button[aria-expanded='false'], "
        "div.cell h1, div.cell h2"  # clicking section headers toggles them
    )
    if collapsed:
        print(f"  Expanding {len(collapsed)} collapsed section(s)...")
        for header in collapsed:
            try:
                header.click()
                time.sleep(0.3)
            except Exception:
                pass

    # Also try the Colab-specific expand via keyboard: Ctrl/Cmd+Shift+O opens TOC
    # and we can use the menu: View > Expand sections
    # Simpler: use Colab's JS API if available
    page.evaluate("""
        // Try to expand all sections via Colab's internal API
        document.querySelectorAll('[class*="section-header"]').forEach(el => {
            if (el.classList.contains('collapsed')) el.click();
        });
        // Also click any collapsed cell group headers
        document.querySelectorAll('.cell-collapsed').forEach(el => {
            el.click();
        });
    """)
    time.sleep(1)


def wait_for_runtime(page, timeout_s=60):
    """Wait for Colab to connect to a runtime, or click Connect if needed."""
    print("  Waiting for runtime connection...")

    # Check if already connected
    connected = page.query_selector(
        "div[class*='connected'], "
        "span:has-text('Python 3'), "
        "colab-connect-button[connected]"
    )
    if connected:
        print("  Runtime already connected")
        return True

    # Click the Connect button if present
    connect_btn = page.query_selector(
        "button:has-text('Connect'), "
        "colab-connect-button, "
        "#connect"
    )
    if connect_btn:
        connect_btn.click()
        print("  Clicked Connect button")

    # Wait for runtime to be ready
    start = time.time()
    while time.time() - start < timeout_s:
        ready = page.query_selector(
            "span:has-text('Python 3'), "
            "div[class*='connected']:not([class*='disconnected'])"
        )
        if ready:
            print(f"  Runtime connected ({time.time() - start:.0f}s)")
            return True
        time.sleep(2)

    print("  WARNING: Runtime may not be connected")
    return False


def run_all_cells(page, timeout_s=180):
    """Trigger Runtime > Run All and wait for execution to complete."""
    # Use Cmd+F9 (macOS) to trigger Run All — more reliable than menu clicking
    print("  Triggering Run All (Cmd+F9)...")
    page.keyboard.press("Meta+F9")

    time.sleep(3)

    # If a confirmation dialog appears (e.g., "Run anyway"), click through
    try:
        run_anyway = page.wait_for_selector(
            "button:has-text('Run anyway'), "
            "mwc-button:has-text('Run anyway')",
            timeout=5000,
        )
        if run_anyway:
            run_anyway.click()
            print("  Clicked 'Run anyway' confirmation")
    except PlaywrightTimeout:
        pass  # No confirmation needed

    # Wait for execution — look for cell execution counts to appear
    print(f"  Waiting up to {timeout_s}s for execution to complete...")
    start = time.time()
    last_status = ""
    saw_running = False

    while time.time() - start < timeout_s:
        # Check multiple indicators of running cells
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
                print(status)
                last_status = status
            time.sleep(3)
        else:
            if not saw_running and time.time() - start < 15:
                # Haven't seen any running indicators yet — keep waiting
                time.sleep(2)
                continue
            # Idle — double check
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
                print(f"  Execution complete ({elapsed:.0f}s)")
                return True

    print(f"  WARNING: Execution may not have completed within {timeout_s}s")
    return False


def main():
    parser = argparse.ArgumentParser(description="Screenshot a Colab notebook")
    parser.add_argument("file_id", help="Google Drive file ID of the notebook")
    parser.add_argument("--no-run", action="store_true", help="Don't run cells, just screenshot")
    parser.add_argument("--sections", action="store_true", help="Take sectioned screenshots (top/mid/bottom)")
    parser.add_argument("--timeout", type=int, default=180, help="Max seconds to wait for execution (default: 180)")
    parser.add_argument("--output-prefix", default="colab", help="Screenshot filename prefix (default: colab)")
    args = parser.parse_args()

    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
    url = COLAB_URL_TEMPLATE.format(file_id=args.file_id)

    print(f"Opening: {url}")
    print(f"Chrome profile source: {CHROME_USER_DATA}")

    # Create a lightweight copy of the Chrome profile with just auth data
    tmp_profile = create_lightweight_profile(CHROME_USER_DATA)

    with sync_playwright() as p:
        # Launch Chrome with lightweight profile copy (avoids lock conflicts)
        browser = p.chromium.launch_persistent_context(
            user_data_dir=tmp_profile,
            channel="chrome",
            headless=False,  # Colab requires visible browser for full rendering
            viewport={"width": 1280, "height": 900},
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-first-run",
            ],
        )

        page = browser.pages[0] if browser.pages else browser.new_page()
        page.goto(url, wait_until="domcontentloaded", timeout=60000)

        print("Waiting for Colab to load...")
        wait_for_colab_load(page)

        # Check if signed in — if not, pause for manual sign-in
        sign_in_btn = page.query_selector("a[href*='ServiceLogin'], button:has-text('Sign in'), a:has-text('Sign in')")
        if sign_in_btn:
            signal_file = SCREENSHOT_DIR / ".signed_in"
            signal_file.unlink(missing_ok=True)
            print("\n" + "=" * 60)
            print("  NOT SIGNED IN — Please sign into Google in the browser.")
            print(f"  Then run: touch {signal_file}")
            print("  Waiting for signal file...")
            print("=" * 60)
            while not signal_file.exists():
                time.sleep(2)
            signal_file.unlink(missing_ok=True)
            print("  Sign-in signal received! Reloading notebook...")
            # Reload the notebook after sign-in
            page.goto(url, wait_until="domcontentloaded", timeout=60000)
            wait_for_colab_load(page)

        # Pre-run screenshot
        pre_path = SCREENSHOT_DIR / f"{args.output_prefix}_before_run.png"
        take_full_screenshot(page, pre_path, "before execution")

        if not args.no_run:
            # Expand collapsed sections so all cells are reachable
            expand_all_sections(page)

            # Ensure runtime is connected before running
            wait_for_runtime(page, timeout_s=60)

            success = run_all_cells(page, timeout_s=args.timeout)
            time.sleep(3)  # let outputs settle

            # Post-run screenshot
            post_path = SCREENSHOT_DIR / f"{args.output_prefix}_after_run.png"
            take_full_screenshot(page, post_path, "after execution")

            if args.sections:
                section_base = SCREENSHOT_DIR / f"{args.output_prefix}_section.png"
                take_sectioned_screenshots(page, section_base)

            if not success:
                print("\nWARNING: Execution may have timed out. Check screenshots for errors.")
        else:
            if args.sections:
                section_base = SCREENSHOT_DIR / f"{args.output_prefix}_section.png"
                take_sectioned_screenshots(page, section_base)

        print(f"\nScreenshots saved to: {SCREENSHOT_DIR}")
        print("Close the browser window when done reviewing, or press Ctrl+C.")

        # Keep browser open so user can inspect
        try:
            page.wait_for_event("close", timeout=300000)  # 5 min
        except (PlaywrightTimeout, KeyboardInterrupt):
            pass

        browser.close()

    # Clean up temp profile
    shutil.rmtree(tmp_profile, ignore_errors=True)
    print("  Temp profile cleaned up")


if __name__ == "__main__":
    main()
