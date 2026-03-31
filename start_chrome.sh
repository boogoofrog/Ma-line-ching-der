#!/bin/bash
# 啟動專用 Chrome（開放遠端偵錯 port 供機器人使用）
# 第一次執行請手動在這個 Chrome 安裝 LINE 擴充功能並登入。

PROFILE_DIR="${HOME}/.chrome-line-bot"
CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
PORT=9222

# 確認 Chrome 是否已經在指定 port 執行
if curl -s "http://localhost:${PORT}/json/version" > /dev/null 2>&1; then
  echo "[OK] Chrome 已在 port ${PORT} 執行，機器人可直接使用。"
  exit 0
fi

echo "啟動 Chrome (port ${PORT})..."
"${CHROME}" \
  --user-data-dir="${PROFILE_DIR}" \
  --remote-debugging-port="${PORT}" \
  --no-first-run \
  --no-default-browser-check \
  > /dev/null 2>&1 &

sleep 3

if curl -s "http://localhost:${PORT}/json/version" > /dev/null 2>&1; then
  echo "[OK] Chrome 啟動成功！"
  echo ""
  echo "首次使用請："
  echo "  1. 在彈出的 Chrome 安裝 LINE 擴充功能"
  echo "     https://chrome.google.com/webstore/detail/line/ophjlpahpchlmihnnnihgmmeilfjmjjc"
  echo "  2. 登入 LINE"
  echo "  3. 之後執行 python app.py 即可"
else
  echo "[ERROR] Chrome 啟動失敗，請確認路徑是否正確：${CHROME}"
fi
