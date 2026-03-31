"""
LINE Desktop App automation via macOS AppleScript.

Prerequisites:
  - LINE for Mac installed (App Store)
  - LINE logged in on the desktop app
  - 系統偏好設定 → 隱私權 → 輔助使用 → 允許 Terminal（或 Python）控制電腦

Usage:
  python line_sender.py --send "Patina Ho" "測試測試"
"""

import os
import time
import subprocess
import argparse


def _run_applescript(script: str) -> str:
    result = subprocess.run(
        ["osascript", "-e", script],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"AppleScript 失敗：{result.stderr.strip()}")
    return result.stdout.strip()


def send_message(target_name: str, message: str, **_) -> bool:
    """
    Send `message` to LINE contact/group `target_name` via LINE desktop app.
    """
    # Escape special characters for AppleScript strings
    safe_target  = target_name.replace('"', '\\"').replace("\\", "\\\\")
    safe_message = message.replace('"', '\\"').replace("\\", "\\\\")

    script = f"""
tell application "LINE"
    activate
end tell

delay 1.5

tell application "System Events"
    tell process "LINE"
        -- 開啟搜尋 (Cmd+F)
        keystroke "f" using command down
        delay 0.8

        -- 輸入聯絡人名稱
        keystroke "{safe_target}"
        delay 1.5

        -- 按下 Enter 進入對話
        key code 36
        delay 1.0

        -- 輸入訊息
        keystroke "{safe_message}"
        delay 0.5

        -- 送出 (Enter)
        key code 36
        delay 0.5
    end tell
end tell
"""

    _run_applescript(script)
    print(f"[OK] Sent to '{target_name}': {message[:60]}")
    return True


def check_line_installed() -> bool:
    """Return True if LINE.app exists."""
    result = subprocess.run(
        ["osascript", "-e", 'id of application "LINE"'],
        capture_output=True, text=True,
    )
    return result.returncode == 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="LINE 桌面版自動發訊息 (macOS)")
    parser.add_argument(
        "--send", nargs=2, metavar=("TARGET", "MESSAGE"),
        help="立即發送：--send '聯絡人名稱' '訊息內容'",
    )
    parser.add_argument("--check", action="store_true",
                        help="確認 LINE App 是否已安裝")
    args = parser.parse_args()

    if args.check:
        if check_line_installed():
            print("[OK] LINE App 已安裝")
        else:
            print("[ERROR] 找不到 LINE App，請從 App Store 安裝")
    elif args.send:
        target, msg = args.send
        send_message(target, msg)
    else:
        parser.print_help()
