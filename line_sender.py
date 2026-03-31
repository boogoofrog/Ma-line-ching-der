"""
LINE Chrome Extension automation via Playwright.

Prerequisites:
  1. Google Chrome must be installed with the LINE extension.
  2. First launch: python line_sender.py --setup
     Opens Chrome so you can log into LINE extension via QR scan.
     The session is saved in CHROME_USER_DATA_DIR.
  3. Subsequent sends reuse the saved session (no re-login needed).
"""

import os
import sys
import glob
import argparse

from dotenv import load_dotenv
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

load_dotenv()

CHROME_USER_DATA_DIR = os.environ.get(
    "CHROME_USER_DATA_DIR",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "chrome_user_data"),
)

LINE_EXT_ID = os.environ.get("LINE_EXT_ID", "ophjlpahpchlmihnnnihgmmeilfjmjjc")
LINE_EXT_URL = f"chrome-extension://{LINE_EXT_ID}/index.html"


# ---------- Detect LINE extension path ----------

def _find_line_ext_path() -> str:
    """Return path to the LINE extension directory from the user's Chrome installation."""
    # Allow manual override via env
    env_path = os.environ.get("LINE_EXT_PATH", "").strip()
    if env_path and os.path.isdir(env_path):
        return env_path

    candidates = []

    if sys.platform == "darwin":
        candidates = [
            os.path.expanduser(
                f"~/Library/Application Support/Google/Chrome/Default/Extensions/{LINE_EXT_ID}"
            ),
            os.path.expanduser(
                f"~/Library/Application Support/Google/Chrome/Profile 1/Extensions/{LINE_EXT_ID}"
            ),
        ]
    elif sys.platform == "win32":
        local_app = os.environ.get("LOCALAPPDATA", "")
        candidates = [
            os.path.join(local_app, f"Google\\Chrome\\User Data\\Default\\Extensions\\{LINE_EXT_ID}"),
        ]
    else:  # Linux
        candidates = [
            os.path.expanduser(f"~/.config/google-chrome/Default/Extensions/{LINE_EXT_ID}"),
            os.path.expanduser(f"~/.config/chromium/Default/Extensions/{LINE_EXT_ID}"),
        ]

    for base in candidates:
        if not os.path.isdir(base):
            continue
        # Pick the latest version folder
        versions = sorted(
            [d for d in os.listdir(base) if os.path.isdir(os.path.join(base, d))],
            reverse=True,
        )
        if versions:
            return os.path.join(base, versions[0])

    return ""


# ---------- Launch helper ----------

def _launch(playwright, headless: bool):
    """Launch Chrome with LINE extension loaded into a persistent context."""
    ext_path = _find_line_ext_path()

    args = [
        "--no-sandbox",
        "--disable-dev-shm-usage",
    ]

    if ext_path:
        args += [
            f"--load-extension={ext_path}",
            f"--disable-extensions-except={ext_path}",
        ]
        print(f"[INFO] LINE extension found: {ext_path}")
    else:
        print(
            "[WARN] LINE extension not found automatically.\n"
            "       Set LINE_EXT_PATH in .env to the unpacked extension directory."
        )

    if headless:
        # Move window far off-screen (extensions don't work in true headless)
        args += ["--window-position=-32000,-32000", "--window-size=1280,900"]

    context = playwright.chromium.launch_persistent_context(
        user_data_dir=CHROME_USER_DATA_DIR,
        headless=False,          # extensions require non-headless
        channel="chrome",
        args=args,
        no_viewport=True,
    )
    return context


# ---------- Public API ----------

def setup_login():
    """Open Chrome visibly so the user can log in via LINE QR code (run once)."""
    print("Chrome 啟動中，請點擊右上角 LINE 擴充功能圖示掃描 QR code 登入...")
    with sync_playwright() as p:
        context = _launch(p, headless=False)
        page = context.new_page()
        page.goto("https://www.google.com", wait_until="domcontentloaded")
        print("\n[INFO] 瀏覽器已開啟。")
        print("[INFO] 請點擊右上角的 LINE 擴充功能圖示，掃描 QR code 完成登入。")
        input("\n登入完成後，按 ENTER 關閉瀏覽器並儲存 session...\n")
        context.close()
    print("[OK] 登入 session 已儲存。")


def send_message(target_name: str, message: str, headless: bool = True) -> bool:
    """
    Send `message` to a LINE contact/group named `target_name`.
    Returns True on success, raises Exception on failure.
    """
    with sync_playwright() as p:
        context = _launch(p, headless=headless)
        try:
            page = context.new_page()
            # Retry navigating to extension URL — extension needs a moment to register
            for attempt in range(5):
                try:
                    page.goto(LINE_EXT_URL, wait_until="domcontentloaded", timeout=10000)
                    break
                except Exception:
                    if attempt == 4:
                        raise RuntimeError(
                            f"無法開啟 LINE 擴充功能 ({LINE_EXT_URL})。"
                            "請確認已安裝 LINE Chrome 擴充功能並執行過 --setup 登入。"
                        )
                    page.wait_for_timeout(2000)
            page.wait_for_timeout(2000)

            # --- Search for contact / group ---
            search_box = _find_search_box(page)
            search_box.click()
            search_box.fill(target_name)
            page.wait_for_timeout(1500)

            # Click first search result
            first_result = page.locator(
                "li.chatList-item, "
                "li[class*='chatListItem'], "
                "div[class*='contact-item'], "
                "li[class*='RoomListItem']"
            ).first
            first_result.wait_for(timeout=8000)
            first_result.click()
            page.wait_for_timeout(1000)

            # --- Type and send ---
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
            page.wait_for_timeout(1500)

            print(f"[OK] Sent to '{target_name}': {message[:60]}")
            return True
        finally:
            context.close()


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
        "找不到 LINE 搜尋框。請確認已登入（先執行 python line_sender.py --setup）"
    )


# ---------- CLI ----------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="LINE Chrome Extension 自動發訊息")
    parser.add_argument("--setup", action="store_true", help="開啟瀏覽器進行 LINE 登入")
    parser.add_argument(
        "--send", nargs=2, metavar=("TARGET", "MESSAGE"),
        help="立即發送：--send '聯絡人名稱' '訊息內容'",
    )
    parser.add_argument("--headed", action="store_true", help="顯示瀏覽器視窗")
    args = parser.parse_args()

    if args.setup:
        setup_login()
    elif args.send:
        target, msg = args.send
        send_message(target, msg, headless=not args.headed)
    else:
        parser.print_help()
