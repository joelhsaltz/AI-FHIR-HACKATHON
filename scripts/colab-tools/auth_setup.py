#!/usr/bin/env python3
"""
One-time Google auth setup for Colab notebook tools.

Uses launch_persistent_context with a user_data_dir — this creates a real
browser profile that Google accepts for sign-in (unlike ephemeral contexts
which Google flags as automation browsers).

After sign-in, exports storageState to ~/.colab-notebook-tools/auth.json
for use by colab_screenshot.py and other tools.

The persistent browser profile is also kept at ~/.colab-notebook-tools/browser_data/
so subsequent auth_setup runs can reuse the existing session.

Usage:
    python auth_setup.py
    python auth_setup.py --output ~/.colab-notebook-tools/auth.json
"""

import argparse
import sys
import time
from pathlib import Path

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("ERROR: playwright is not installed. Run: pip install playwright && playwright install chromium")
    sys.exit(1)

CONFIG_DIR = Path.home() / ".colab-notebook-tools"
DEFAULT_AUTH_PATH = CONFIG_DIR / "auth.json"
DEFAULT_BROWSER_DATA = CONFIG_DIR / "browser_data"
COLAB_URL = "https://colab.research.google.com"
GOOGLE_LOGIN_URL = "https://accounts.google.com"


def wait_for_signin(page, timeout_s=300):
    """Poll until the user completes Google sign-in."""
    print("\n" + "=" * 60)
    print("  Please sign in to your Google account in the browser window.")
    print(f"  Waiting up to {timeout_s}s for sign-in to complete...")
    print("=" * 60 + "\n")

    start = time.time()
    while time.time() - start < timeout_s:
        url = page.url
        # After successful sign-in, Google redirects away from accounts.google.com
        if "accounts.google.com" not in url and "ServiceLogin" not in url:
            return True
        # Also check for profile avatar (sign-in indicator)
        avatar = page.query_selector(
            "img[aria-label*='Account'], "
            "img[data-profile-identifier], "
            "a[aria-label*='Account']"
        )
        if avatar:
            return True
        time.sleep(2)
    return False


def check_already_signed_in(page):
    """Check if the page shows we're already signed in to Google."""
    url = page.url
    if "accounts.google.com" not in url and "ServiceLogin" not in url:
        return True
    avatar = page.query_selector(
        "img[aria-label*='Account'], "
        "img[data-profile-identifier], "
        "a[aria-label*='Account']"
    )
    return avatar is not None


def main():
    parser = argparse.ArgumentParser(description="Set up Google auth for Colab tools")
    parser.add_argument(
        "--output", "-o",
        type=Path,
        default=DEFAULT_AUTH_PATH,
        help=f"Path to save storageState (default: {DEFAULT_AUTH_PATH})",
    )
    parser.add_argument(
        "--browser-data",
        type=Path,
        default=DEFAULT_BROWSER_DATA,
        help=f"Path for persistent browser profile (default: {DEFAULT_BROWSER_DATA})",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=300,
        help="Max seconds to wait for sign-in (default: 300)",
    )
    args = parser.parse_args()

    # Ensure directories exist
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.browser_data.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        # Use launch_persistent_context — creates a real browser profile that
        # Google accepts for sign-in. This is the pattern that works (tested
        # in the Kubera project). Ephemeral contexts and channel="chrome" both
        # get blocked by Google's automation detection.
        # Delete stale browser data if previous attempts failed with Google
        # blocking — a fresh profile with anti-detection args works better
        # than a profile that Google has already flagged.
        print(f"Launching browser with persistent profile at: {args.browser_data}")
        context = p.chromium.launch_persistent_context(
            user_data_dir=str(args.browser_data),
            headless=False,
            viewport={"width": 1280, "height": 900},
            args=[
                "--disable-blink-features=AutomationControlled",
            ],
            ignore_default_args=["--enable-automation"],
        )

        page = context.pages[0] if context.pages else context.new_page()

        # Navigate to Google — check if we're already signed in from a prior run
        print("Navigating to Google sign-in...")
        page.goto(GOOGLE_LOGIN_URL, wait_until="domcontentloaded", timeout=30000)
        time.sleep(2)

        if check_already_signed_in(page):
            print("Already signed in from previous session!")
        else:
            signed_in = wait_for_signin(page, timeout_s=args.timeout)
            if not signed_in:
                print("\nERROR: Sign-in timed out. Please try again.")
                context.close()
                sys.exit(1)

        print("Sign-in confirmed! Navigating to Colab to capture cookies...")

        # Navigate to Colab to capture its cookies too
        page.goto(COLAB_URL, wait_until="domcontentloaded", timeout=30000)
        time.sleep(3)

        # Export storageState for use by other tools (colab_screenshot.py etc.)
        context.storage_state(path=str(args.output))
        print(f"Session exported to: {args.output}")

        context.close()

    print(f"\nDone!")
    print(f"  Auth file:     {args.output}")
    print(f"  Browser data:  {args.browser_data}")
    print(f"Google session cookies typically last ~2 years.")
    print(f"Re-run this script if auth expires.")


if __name__ == "__main__":
    main()
