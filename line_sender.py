"""
LINE Chrome Extension automation via Playwright.

Prerequisites:
  1. Run `playwright install chromium` once.
  2. First launch: python line_sender.py --setup
     This opens Chrome so you can log into LINE extension manually (QR scan).
  3. After login, the session is saved in CHROME_USER_DATA_DIR.
     Subsequent sends reuse the saved session (no re-login needed).

LINE Chrome extension ID (official): ophjlpahpchlmihnnnihgmmeilfjmjjc
"""

import os
import sys
import time
import argparse

from dotenv import load_dotenv
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

load_dotenv()

# Path where Chrome user data (cookies/login session) is stored
CHROME_USER_DATA_DIR = os.environ.get(
    "CHROME_USER_DATA_DIR",
    os.path.join(os.path.dirname(__file__), "chrome_user_data"),
)

# Official LINE Chrome extension ID
LINE_EXT_ID = os.environ.get("LINE_EXT_ID", "ophjlpahpchlmihnnnihgmmeilfjmjjc")

# Extension popup entry point
LINE_EXT_URL = f"chrome-extension://{LINE_EXT_ID}/index.html"


def _launch_browser(playwright, headless: bool = True):
    """Launch Chromium with the LINE extension via a persistent context."""
    context = playwright.chromium.launch_persistent_context(
        user_data_dir=CHROME_USER_DATA_DIR,
        headless=headless,
        channel="chrome",          # use installed Google Chrome (has extension support)
        args=[
            f"--disable-extensions-except={_ext_path()}",
            f"--load-extension={_ext_path()}",
        ],
        no_viewport=True,
    )
    return context


def _ext_path() -> str:
    """
    Return path to unpacked LINE extension if available,
    otherwise return empty string (rely on extension already installed in profile).
    """
    path = os.environ.get("LINE_EXT_PATH", "")
    return path


def setup_login():
    """
    Open Chrome in headed mode so the user can log in via QR code.
    Call this once before the first automated send.
    """
    print("Opening Chrome for LINE login. Scan QR code in the LINE extension.")
    print("Close the browser when you are fully logged in.")
    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=CHROME_USER_DATA_DIR,
            headless=False,
            channel="chrome",
        )
        page = context.new_page()
        page.goto(LINE_EXT_URL)
        input("Press ENTER here after you have logged in and closed the QR screen...")
        context.close()


def send_message(target_name: str, message: str, headless: bool = True) -> bool:
    """
    Send `message` to a LINE contact/group named `target_name`.

    Returns True on success, raises on failure.
    """
    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=CHROME_USER_DATA_DIR,
            headless=headless,
            channel="chrome",
            args=["--no-sandbox"],
        )
        try:
            page = context.new_page()
            page.goto(LINE_EXT_URL, wait_until="domcontentloaded")
            page.wait_for_timeout(2000)

            # --- Search for contact / group ---
            search_box = _find_search_box(page)
            search_box.click()
            search_box.fill(target_name)
            page.wait_for_timeout(1500)

            # Click first result
            first_result = page.locator(
                "li.chatList-item, li[class*='chatListItem'], div[class*='contact-item']"
            ).first
            first_result.wait_for(timeout=8000)
            first_result.click()
            page.wait_for_timeout(1000)

            # --- Type and send message ---
            input_box = page.locator(
                "div[contenteditable='true'], textarea[class*='input'], div[class*='messageInput']"
            ).first
            input_box.wait_for(timeout=8000)
            input_box.click()
            input_box.fill(message)
            page.wait_for_timeout(300)
            input_box.press("Enter")
            page.wait_for_timeout(1000)

            print(f"[OK] Sent to '{target_name}': {message[:50]}")
            return True
        finally:
            context.close()


def _find_search_box(page):
    """Try several common selectors for the LINE search input."""
    selectors = [
        "input[placeholder*='搜尋']",
        "input[placeholder*='search' i]",
        "input[type='search']",
        "input[class*='search']",
        "div[class*='search'] input",
    ]
    for sel in selectors:
        loc = page.locator(sel).first
        try:
            loc.wait_for(timeout=3000)
            return loc
        except PlaywrightTimeout:
            continue
    raise RuntimeError("Cannot find LINE search box. Make sure you are logged in.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--setup", action="store_true", help="Open browser to log in")
    parser.add_argument("--send", nargs=2, metavar=("TARGET", "MESSAGE"),
                        help="Send a message immediately: --send '群組名' '訊息內容'")
    parser.add_argument("--headed", action="store_true", help="Show browser window")
    args = parser.parse_args()

    if args.setup:
        setup_login()
    elif args.send:
        target, msg = args.send
        send_message(target, msg, headless=not args.headed)
    else:
        parser.print_help()
