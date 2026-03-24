#!/usr/bin/env python3
"""
Shared Playwright utilities for Colab notebook automation.

Extracted from colab_screenshot.py — provides auth, page loading, dialog
handling, scroll container detection, and shadow DOM traversal used by
multiple Colab tools (screenshot, interact, walkthrough).
"""

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

CONFIG_DIR = Path.home() / ".colab-notebook-tools"
DEFAULT_AUTH_PATH = CONFIG_DIR / "auth.json"
DEFAULT_BROWSER_DATA = CONFIG_DIR / "browser_data"
COLAB_URL_TEMPLATE = "https://colab.research.google.com/drive/{file_id}"
COLAB_URL = "https://colab.research.google.com"
IS_MACOS = platform.system() == "Darwin"
RUN_ALL_KEY = "Meta+F9" if IS_MACOS else "Control+F9"


# ── Auth ───────────────────────────────────────────────────────────────────

def check_auth(auth_path: Path = DEFAULT_AUTH_PATH) -> bool:
    """Check if storageState file exists and is non-empty."""
    if not auth_path.exists():
        return False
    if auth_path.stat().st_size < 10:
        return False
    return True


# ── Page loading ───────────────────────────────────────────────────────────

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


def detect_account_chooser(page) -> bool:
    """Detect Google's 'Choose an account' page."""
    return "accounts.google.com" in page.url and (
        page.query_selector("h1:has-text('Choose an account')") is not None
        or page.query_selector("div[data-identifier]") is not None
    )


def handle_account_chooser(page, email="joelhsaltz@gmail.com"):
    """Auto-click the account on Google's 'Choose an account' page.

    Returns True if an account was clicked, False if the page wasn't
    an account chooser or the account wasn't found.
    """
    if not detect_account_chooser(page):
        return False

    print(f"  Detected 'Choose an account' page, selecting {email}...", file=sys.stderr)

    # Click the account row matching the email
    clicked = page.evaluate(f"""() => {{
        // Look for account row by email text or data-identifier
        const rows = document.querySelectorAll(
            'li[data-identifier], div[data-identifier], div[data-email]'
        );
        for (const row of rows) {{
            const identifier = row.getAttribute('data-identifier') ||
                               row.getAttribute('data-email') || '';
            if (identifier === '{email}') {{
                row.click();
                return true;
            }}
        }}
        // Fallback: find any element containing the email text
        const all = document.querySelectorAll('*');
        for (const el of all) {{
            if (el.children.length === 0 && el.textContent.trim() === '{email}') {{
                // Click the parent row, not the text node
                const row = el.closest('li, div[role="link"], div[tabindex]') || el;
                row.click();
                return true;
            }}
        }}
        return false;
    }}""")

    if clicked:
        print(f"  Clicked account: {email}", file=sys.stderr)
        time.sleep(3)
    else:
        print(f"  WARNING: Could not find account {email} on chooser page", file=sys.stderr)
    return clicked


# ── Auto-reauth ───────────────────────────────────────────────────────────

def needs_reauth(page) -> bool:
    """Check if the page requires re-authentication.

    Detects: sign-in pages, 'Choose an account' with 'Signed out' status,
    password entry pages.
    """
    url = page.url
    if "accounts.google.com" in url:
        return True
    if not check_signed_in(page):
        return True
    return False


def auto_reauth(playwright, auth_path=DEFAULT_AUTH_PATH,
                browser_data=DEFAULT_BROWSER_DATA):
    """Attempt automatic re-authentication using the persistent browser profile.

    Opens the persistent browser context (which may still have a valid Google
    session), navigates to Colab, and exports fresh cookies.

    If the persistent profile's session is also expired, opens a visible browser
    window and waits for the user to sign in — but all in one step, no separate
    script needed.

    Returns True if re-auth succeeded and new cookies were exported.
    """
    print("\n  Auth expired — attempting automatic re-authentication...", file=sys.stderr)
    browser_data.mkdir(parents=True, exist_ok=True)

    context = playwright.chromium.launch_persistent_context(
        user_data_dir=str(browser_data),
        headless=False,
        viewport={"width": 1280, "height": 900},
        args=["--disable-blink-features=AutomationControlled"],
        ignore_default_args=["--enable-automation"],
    )

    page = context.pages[0] if context.pages else context.new_page()

    # Navigate to Colab
    print("  Opening Colab in persistent browser...", file=sys.stderr)
    page.goto(COLAB_URL, wait_until="domcontentloaded", timeout=30000)
    time.sleep(3)

    # Handle "Choose an account" if it appears
    if detect_account_chooser(page):
        handle_account_chooser(page)
        time.sleep(3)

    # Check if we're now signed in (persistent profile may have valid session)
    url = page.url
    if "accounts.google.com" not in url and "ServiceLogin" not in url:
        # We're in! Export cookies.
        print("  Re-authenticated via persistent browser profile!", file=sys.stderr)
        context.storage_state(path=str(auth_path))
        print(f"  Fresh cookies exported to {auth_path}", file=sys.stderr)
        context.close()
        return True

    # Persistent profile session also expired — need user to sign in
    print("\n" + "=" * 60, file=sys.stderr)
    print("  Google session expired. Please sign in to your Google", file=sys.stderr)
    print("  account in the browser window that just opened.", file=sys.stderr)
    print("  (This is the same browser profile used for Colab tools.)", file=sys.stderr)
    print("=" * 60 + "\n", file=sys.stderr)

    # Wait for sign-in (up to 5 minutes)
    start = time.time()
    while time.time() - start < 300:
        url = page.url
        if "accounts.google.com" not in url and "ServiceLogin" not in url:
            break
        time.sleep(2)
    else:
        print("  ERROR: Sign-in timed out after 5 minutes", file=sys.stderr)
        context.close()
        return False

    # Navigate to Colab to capture Colab-specific cookies
    page.goto(COLAB_URL, wait_until="domcontentloaded", timeout=30000)
    time.sleep(3)

    context.storage_state(path=str(auth_path))
    print(f"  Fresh cookies exported to {auth_path}", file=sys.stderr)
    context.close()
    return True


# ── Shadow DOM traversal ──────────────────────────────────────────────────

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


def find_button_by_text(page, text, partial=False):
    """Find a button by text, piercing shadow DOM. Returns True if found and clicked."""
    op = "includes" if partial else "==="
    return page.evaluate(f"""() => {{
        function findBtn(root) {{
            const elements = root.querySelectorAll(
                'button, mwc-button, a, [role="button"], md-text-button, md-filled-button'
            );
            for (const el of elements) {{
                const t = (el.textContent || '').trim();
                if (t {op} '{text}') {{
                    el.click();
                    return true;
                }}
            }}
            for (const el of root.querySelectorAll('*')) {{
                if (el.shadowRoot) {{
                    const found = findBtn(el.shadowRoot);
                    if (found) return true;
                }}
            }}
            return false;
        }}
        return findBtn(document);
    }}""")


# ── Dialog handling ───────────────────────────────────────────────────────

def handle_colab_dialogs(page, grant_secrets=True):
    """Handle common Colab dialogs: secret access, too many sessions, etc.

    Returns a list of dialog names that were handled.
    """
    handled = []

    # "Too many sessions" — click Manage sessions, then terminate others
    if dismiss_dialog(page, "Manage sessions"):
        handled.append("too many sessions")
        time.sleep(2)
        for _ in range(5):
            if dismiss_dialog(page, "Terminate"):
                time.sleep(1)
            else:
                break
        page.keyboard.press("Escape")
        time.sleep(1)

    # "Notebook does not have secret access" — grant or cancel
    btn_text = "Grant access" if grant_secrets else "Cancel"
    if dismiss_dialog(page, btn_text):
        handled.append("secret access")

    return handled


# ── Runtime connection ────────────────────────────────────────────────────

def click_connect_button(page):
    """Click the Connect/Reconnect button, piercing shadow DOM if needed."""
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


def check_runtime_connected(page):
    """Check if Colab runtime is connected (RAM/Disk indicator visible)."""
    return page.evaluate("""() => {
        function getAllText(root) {
            let text = '';
            if (root.textContent) text += root.textContent;
            for (const el of (root.querySelectorAll ? root.querySelectorAll('*') : [])) {
                if (el.shadowRoot) text += getAllText(el.shadowRoot);
            }
            return text;
        }
        const btn = document.querySelector('colab-connect-button');
        if (btn) {
            const btnText = getAllText(btn).toLowerCase();
            if (btnText.includes('ram') && btnText.includes('disk')) return true;
        }
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

    if check_runtime_connected(page):
        print("  Runtime already connected", file=sys.stderr)
        return True

    if click_connect_button(page):
        print("  Clicked Connect button", file=sys.stderr)
    else:
        print("  WARNING: Could not find Connect button", file=sys.stderr)

    time.sleep(5)

    start = time.time()
    _sessions_handled = False
    while time.time() - start < timeout_s:
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
            start = time.time()
            if click_connect_button(page):
                print("  Retrying Connect after terminating sessions", file=sys.stderr)
            else:
                print("  No Connect button found, reloading page...", file=sys.stderr)
                page.reload(wait_until="domcontentloaded", timeout=30000)
                wait_for_colab_load(page)
                click_connect_button(page)
                print("  Clicked Connect after reload", file=sys.stderr)
            continue

        if check_runtime_connected(page):
            elapsed = time.time() - start
            print(f"  Runtime connected ({elapsed:.0f}s)", file=sys.stderr)
            return True
        time.sleep(2)

    print("  WARNING: Runtime may not be connected", file=sys.stderr)
    return False


# ── Section expansion ─────────────────────────────────────────────────────

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


# ── Scroll container ─────────────────────────────────────────────────────

def find_scroll_container(page):
    """Find the scrollable container in Colab's DOM.

    Colab uses a custom <colab-scroller> element (id='notebook-main') as its
    main scrollable container, not the window.
    """
    container = page.evaluate("""() => {
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
        const all = document.querySelectorAll('*');
        for (const el of all) {
            if (el.scrollHeight > 2000 && el.scrollHeight > el.clientHeight + 100
                && el.clientHeight > 100) {
                const style = getComputedStyle(el);
                if (style.overflow === 'auto' || style.overflow === 'scroll'
                    || style.overflowY === 'auto' || style.overflowY === 'scroll'
                    || style.overflow.includes('scroll') || style.overflow.includes('auto')) {
                    if (el.id) return '#' + el.id;
                    if (el.tagName) return el.tagName.toLowerCase();
                    return null;
                }
            }
        }
        return null;
    }""")
    return container


def scroll_to(page, container_sel, y):
    """Scroll the Colab notebook to a given y position."""
    if container_sel:
        page.evaluate(f"""() => {{
            const el = document.querySelector('{container_sel}');
            el.scrollTo(0, {y});
        }}""")
    else:
        page.evaluate(f"window.scrollTo(0, {y})")


def get_scroll_dimensions(page, container_sel):
    """Get scrollHeight and clientHeight of the scroll container."""
    if container_sel:
        return page.evaluate(f"""() => {{
            const el = document.querySelector('{container_sel}');
            return {{ scrollHeight: el.scrollHeight, clientHeight: el.clientHeight }};
        }}""")
    else:
        return {
            "scrollHeight": page.evaluate("document.documentElement.scrollHeight"),
            "clientHeight": page.viewport_size["height"],
        }


# ── Cell utilities ────────────────────────────────────────────────────────

def get_cell_count(page):
    """Get the number of cells in the notebook."""
    return page.evaluate("""() => {
        const cells = document.querySelectorAll('div.cell, colab-cell');
        return cells.length;
    }""")


def get_cell_elements(page):
    """Get cell elements info (index, type, title if present)."""
    return page.evaluate("""() => {
        const cells = document.querySelectorAll('div.cell, colab-cell');
        const result = [];
        for (let i = 0; i < cells.length; i++) {
            const cell = cells[i];
            const isCode = cell.classList.contains('code') ||
                           cell.querySelector('.code-cell-content, .inputarea') !== null;
            // Try to find title from @title annotation
            const codeEl = cell.querySelector('.inputarea textarea, .CodeMirror');
            let title = '';
            const titleEl = cell.querySelector('.cell-title, [class*="title"]');
            if (titleEl) title = titleEl.textContent.trim();
            result.push({
                index: i,
                type: isCode ? 'code' : 'markdown',
                title: title,
            });
        }
        return result;
    }""")


# ── Browser context factory ──────────────────────────────────────────────

def create_browser_context(playwright, auth_path=DEFAULT_AUTH_PATH, headless=False,
                           viewport_width=1280, viewport_height=900):
    """Create a Playwright browser + context with standard Colab settings.

    Returns (browser, context) tuple. Caller is responsible for closing.
    """
    browser = playwright.chromium.launch(
        headless="new" if headless else False,
        args=[
            "--disable-blink-features=AutomationControlled",
            "--no-first-run",
        ],
    )
    context = browser.new_context(
        storage_state=str(auth_path),
        viewport={"width": viewport_width, "height": viewport_height},
    )
    return browser, context


def open_colab_notebook(page, file_id, grant_secrets=True, playwright=None,
                        auth_path=DEFAULT_AUTH_PATH, browser=None):
    """Navigate to a Colab notebook, wait for load, check auth, handle dialogs.

    If auth fails and playwright is provided, automatically re-authenticates
    using the persistent browser profile, then retries with fresh cookies.

    Returns True if notebook loaded successfully, False if auth failed.
    """
    url = COLAB_URL_TEMPLATE.format(file_id=file_id)
    print(f"Opening: {url}", file=sys.stderr)

    page.goto(url, wait_until="domcontentloaded", timeout=60000)
    print("Waiting for Colab to load...", file=sys.stderr)
    wait_for_colab_load(page)

    # Handle "Choose an account" page
    if detect_account_chooser(page):
        handle_account_chooser(page)
        time.sleep(3)
        # Check if we landed on the notebook or need re-auth
        if "colab.research.google.com/drive/" in page.url:
            wait_for_colab_load(page)
        elif needs_reauth(page) and playwright:
            return _reauth_and_retry(playwright, page, file_id, grant_secrets,
                                     auth_path, browser)
        elif needs_reauth(page):
            print("ERROR: Not signed in. Auth may have expired. Run: python auth_setup.py",
                  file=sys.stderr)
            return False

    # Check if signed in
    if needs_reauth(page):
        if playwright:
            return _reauth_and_retry(playwright, page, file_id, grant_secrets,
                                     auth_path, browser)
        print("ERROR: Not signed in. Auth may have expired. Run: python auth_setup.py",
              file=sys.stderr)
        return False

    handled = handle_colab_dialogs(page, grant_secrets=grant_secrets)
    for h in handled:
        print(f"  Handled dialog: {h}", file=sys.stderr)

    return True


def _reauth_and_retry(playwright, page, file_id, grant_secrets, auth_path, browser):
    """Re-authenticate by switching to the persistent browser profile.

    The persistent profile maintains Google's full auth state (not just cookies),
    so it can authenticate where exported cookies cannot. We close the ephemeral
    browser and reopen the notebook directly in the persistent profile.

    The caller's `page` object is replaced — subsequent code should use the
    returned page's context. Returns True/False, and the page object is modified
    in-place to point to the re-authenticated notebook.
    """
    print("\n  Auth failed with exported cookies.", file=sys.stderr)
    print("  Switching to persistent browser profile...", file=sys.stderr)

    # Close the ephemeral browser
    if browser:
        browser.close()

    # Open directly with persistent context
    DEFAULT_BROWSER_DATA.mkdir(parents=True, exist_ok=True)
    context = playwright.chromium.launch_persistent_context(
        user_data_dir=str(DEFAULT_BROWSER_DATA),
        headless=False,
        viewport={"width": 1280, "height": 900},
        args=["--disable-blink-features=AutomationControlled"],
        ignore_default_args=["--enable-automation"],
    )

    new_page = context.pages[0] if context.pages else context.new_page()
    url = COLAB_URL_TEMPLATE.format(file_id=file_id)
    print(f"  Opening notebook in persistent browser: {url}", file=sys.stderr)
    new_page.goto(url, wait_until="domcontentloaded", timeout=60000)
    wait_for_colab_load(new_page)

    # Handle account chooser if needed
    if detect_account_chooser(new_page):
        handle_account_chooser(new_page)
        time.sleep(5)
        wait_for_colab_load(new_page)

    if needs_reauth(new_page):
        # Persistent profile also expired — need manual sign-in
        print("\n" + "=" * 60, file=sys.stderr)
        print("  Google session expired. Please sign in to your Google", file=sys.stderr)
        print("  account in the browser window that just opened.", file=sys.stderr)
        print("=" * 60 + "\n", file=sys.stderr)

        start = time.time()
        while time.time() - start < 300:
            current_url = new_page.url
            if "accounts.google.com" not in current_url and "ServiceLogin" not in current_url:
                break
            time.sleep(2)
        else:
            print("  ERROR: Sign-in timed out.", file=sys.stderr)
            context.close()
            return False

        # Navigate to the notebook after sign-in
        new_page.goto(url, wait_until="domcontentloaded", timeout=60000)
        wait_for_colab_load(new_page)

    if needs_reauth(new_page):
        print("ERROR: Still not signed in after re-authentication.", file=sys.stderr)
        context.close()
        return False

    print("  Successfully authenticated with persistent profile!", file=sys.stderr)

    # Export fresh cookies for next time
    context.storage_state(path=str(auth_path))
    print(f"  Updated {auth_path} with fresh cookies", file=sys.stderr)

    handled = handle_colab_dialogs(new_page, grant_secrets=grant_secrets)
    for h in handled:
        print(f"  Handled dialog: {h}", file=sys.stderr)

    # Copy the new page's state into the caller's page object.
    # Since we can't actually replace the page reference, we store the
    # persistent context info so the caller can use it.
    # We use a simple approach: store the new page and context on the old page.
    page._persistent_page = new_page
    page._persistent_context = context

    return True
