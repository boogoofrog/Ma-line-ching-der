"""
LINE Chrome Extension automation via Playwright + CDP.

Flow:
  1. bash start_chrome.sh          # 啟動專用 Chrome（只需第一次設定）
  2. 在該 Chrome 安裝 LINE 擴充功能並登入
  3. python app.py                 # 啟動排程機器人

Playwright 透過 CDP 連接到已執行的 Chrome，不另開新視窗。
"""

import os
import argparse

from dotenv import load_dotenv
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

load_dotenv()

LINE_EXT_ID  = os.environ.get("LINE_EXT_ID", "ophjlpahpchlmihnnnihgmmeilfjmjjc")
LINE_EXT_URL = f"chrome-extension://{LINE_EXT_ID}/index.html"
CDP_URL      = os.environ.get("CHROME_CDP_URL", "http://localhost:9222")


# ---------- Internal helpers ----------

def _connect():
    """Return (playwright_instance, browser) connected via CDP."""
    p = sync_playwright().start()
    try:
        browser = p.chromium.connect_over_cdp(CDP_URL)
    except Exception:
        p.stop()
        raise RuntimeError(
            f"無法連接 Chrome ({CDP_URL})。\n"
            "請先執行：bash start_chrome.sh"
        )
    return p, browser


def _get_line_page(context):
    """Return existing LINE tab, or open a new one."""
    for pg in context.pages:
        if LINE_EXT_ID in pg.url:
            pg.bring_to_front()
            return pg

    pg = context.new_page()
    pg.goto(LINE_EXT_URL, wait_until="domcontentloaded", timeout=15000)
    pg.wait_for_timeout(2000)
    return pg


def _find_search_box(page):
    selectors = [
        "input[placeholder*='搜尋']",
        "input[placeholder*='Search' i]",
        "input[type='search']",
        "input[class*='search' i]",
        "div[class*='search' i] input",
    ]
    for sel in selectors:
        loc = page.locator(sel).first
        try:
            loc.wait_for(timeout=3000)
            return loc
        except PlaywrightTimeout:
            continue
    raise RuntimeError(
        "找不到 LINE 搜尋框。\n"
        "請確認 LINE 擴充功能已安裝並登入（bash start_chrome.sh）"
    )


# ---------- Public API ----------

def send_message(target_name: str, message: str, **_) -> bool:
    """
    Send `message` to LINE contact/group `target_name`.
    Returns True on success, raises on failure.
    """
    p, browser = _connect()
    try:
        context = browser.contexts[0]
        page = _get_line_page(context)

        # Search contact / group
        search_box = _find_search_box(page)
        search_box.click()
        search_box.triple_click()
        search_box.fill(target_name)
        page.wait_for_timeout(1500)

        # Click first result
        first_result = page.locator(
            "li.chatList-item, "
            "li[class*='chatListItem'], "
            "div[class*='contact-item'], "
            "li[class*='RoomListItem'], "
            "div[class*='ChatListItem']"
        ).first
        first_result.wait_for(timeout=8000)
        first_result.click()
        page.wait_for_timeout(800)

        # Type and send
        input_box = page.locator(
            "div[contenteditable='true'], "
            "textarea[class*='input'], "
            "div[class*='messageInput'], "
            "div[class*='textInput']"
        ).first
        input_box.wait_for(timeout=8000)
        input_box.click()
        input_box.fill(message)
        page.wait_for_timeout(300)
        input_box.press("Enter")
        page.wait_for_timeout(1000)

        print(f"[OK] Sent to '{target_name}': {message[:60]}")
        return True
    finally:
        browser.close()
        p.stop()


# ---------- CLI ----------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="LINE 自動發訊息（透過 CDP 連接 Chrome）")
    parser.add_argument(
        "--send", nargs=2, metavar=("TARGET", "MESSAGE"),
        help="立即發送：--send '聯絡人名稱' '訊息內容'",
    )
    parser.add_argument("--check", action="store_true",
                        help="確認是否可成功連接 Chrome")
    args = parser.parse_args()

    if args.check:
        p, browser = _connect()
        print(f"[OK] 已連接 Chrome，共 {len(browser.contexts[0].pages)} 個分頁")
        browser.close()
        p.stop()
    elif args.send:
        target, msg = args.send
        send_message(target, msg)
    else:
        parser.print_help()
