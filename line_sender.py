"""
LINE Web (web.line.me) automation via Playwright.

Flow:
  1. python line_sender.py --setup   # 開瀏覽器掃 QR 登入，session 存在 browser_session/
  2. python line_sender.py --send "聯絡人" "訊息"  # 測試發訊息
  3. python app.py                   # 啟動排程機器人

不需要 Chrome extension，不需要 API Token。
"""

import os
import argparse

from dotenv import load_dotenv
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

load_dotenv()

LINE_WEB_URL = "https://web.line.me/"

SESSION_DIR = os.environ.get(
    "SESSION_DIR",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "browser_session"),
)


# ---------- Launch ----------

def _launch(playwright, headless: bool = False):
    return playwright.chromium.launch_persistent_context(
        user_data_dir=SESSION_DIR,
        headless=headless,
        args=["--no-sandbox", "--disable-dev-shm-usage"],
        viewport={"width": 1280, "height": 900},
    )


# ---------- Public API ----------

def setup_login():
    """Open browser for QR code login. Run once."""
    print("開啟 LINE Web，請用手機掃描 QR Code 登入...")
    with sync_playwright() as p:
        context = _launch(p, headless=False)
        page = context.new_page()
        page.goto(LINE_WEB_URL, wait_until="domcontentloaded")
        print("掃描完成後按 ENTER 儲存 session...")
        input()
        context.close()
    print("[OK] Session 已儲存，之後不需要重新登入。")


def send_message(target_name: str, message: str, **_) -> bool:
    """
    Send `message` to LINE contact/group `target_name` via LINE Web.
    Returns True on success, raises on failure.
    """
    with sync_playwright() as p:
        context = _launch(p, headless=True)
        try:
            page = context.new_page()
            page.goto(LINE_WEB_URL, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(3000)

            # Search for contact
            _search_and_open(page, target_name)

            # Type and send message
            _type_and_send(page, message)

            print(f"[OK] Sent to '{target_name}': {message[:60]}")
            return True
        finally:
            context.close()


def _search_and_open(page, target_name: str):
    """Find and click the chat with target_name."""
    search_selectors = [
        "input[placeholder*='搜尋']",
        "input[placeholder*='Search' i]",
        "button[class*='search' i]",
        "span[class*='search' i]",
    ]

    # Try to click search icon / box
    for sel in search_selectors:
        try:
            el = page.locator(sel).first
            el.wait_for(timeout=4000)
            el.click()
            break
        except PlaywrightTimeout:
            continue

    page.wait_for_timeout(500)

    # Type in search box
    search_input_selectors = [
        "input[placeholder*='搜尋']",
        "input[placeholder*='Search' i]",
        "input[type='search']",
        "input[class*='search' i]",
    ]
    search_input = None
    for sel in search_input_selectors:
        try:
            el = page.locator(sel).first
            el.wait_for(timeout=3000)
            search_input = el
            break
        except PlaywrightTimeout:
            continue

    if search_input is None:
        raise RuntimeError(
            "找不到搜尋框。\n"
            "請確認已登入 LINE Web（執行 python line_sender.py --setup）"
        )

    search_input.fill(target_name)
    page.wait_for_timeout(1500)

    # Click first result
    result_selectors = [
        f"span[title='{target_name}']",
        "li[class*='chat'] span[class*='name']",
        "div[class*='chatItem']",
        "li[class*='RoomListItem']",
        "div[class*='searchResult'] li",
    ]
    for sel in result_selectors:
        try:
            el = page.locator(sel).first
            el.wait_for(timeout=4000)
            el.click()
            page.wait_for_timeout(800)
            return
        except PlaywrightTimeout:
            continue

    raise RuntimeError(f"找不到聯絡人：{target_name}")


def _type_and_send(page, message: str):
    """Type message and press Enter."""
    input_selectors = [
        "div[contenteditable='true'][class*='message' i]",
        "div[contenteditable='true']",
        "textarea[class*='input' i]",
    ]
    for sel in input_selectors:
        try:
            el = page.locator(sel).last
            el.wait_for(timeout=5000)
            el.click()
            el.fill(message)
            page.wait_for_timeout(300)
            el.press("Enter")
            page.wait_for_timeout(1000)
            return
        except PlaywrightTimeout:
            continue

    raise RuntimeError("找不到訊息輸入框")


# ---------- CLI ----------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="LINE Web 自動發訊息")
    parser.add_argument("--setup", action="store_true",
                        help="開啟瀏覽器進行 LINE Web QR 登入")
    parser.add_argument("--send", nargs=2, metavar=("TARGET", "MESSAGE"),
                        help="立即發送：--send '聯絡人' '訊息'")
    args = parser.parse_args()

    if args.setup:
        setup_login()
    elif args.send:
        target, msg = args.send
        send_message(target, msg)
    else:
        parser.print_help()
