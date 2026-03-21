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

DEFAULT_AUTH_PATH = Path.home() / ".colab-notebook-tools" / "auth.json"
COLAB_URL_TEMPLATE = "https://colab.research.google.com/drive/{file_id}"
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


def open_colab_notebook(page, file_id, grant_secrets=True):
    """Navigate to a Colab notebook, wait for load, check auth, handle dialogs.

    Returns True if notebook loaded successfully, False if auth failed.
    """
    url = COLAB_URL_TEMPLATE.format(file_id=file_id)
    print(f"Opening: {url}", file=sys.stderr)

    page.goto(url, wait_until="domcontentloaded", timeout=60000)
    print("Waiting for Colab to load...", file=sys.stderr)
    wait_for_colab_load(page)

    if not check_signed_in(page):
        print("ERROR: Not signed in. Auth may have expired. Run: python auth_setup.py",
              file=sys.stderr)
        return False

    handled = handle_colab_dialogs(page, grant_secrets=grant_secrets)
    for h in handled:
        print(f"  Handled dialog: {h}", file=sys.stderr)

    return True
