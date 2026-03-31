#!/bin/bash
# 以遠端偵錯模式啟動 Chrome（使用你原本的 Chrome profile，LINE 已裝好）
CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
PORT=9222

# 如果已在跑，直接結束
if curl -s "http://localhost:${PORT}/json/version" > /dev/null 2>&1; then
  echo "[OK] Chrome 已在 port ${PORT} 執行，可以使用。"
  exit 0
fi

echo "關閉現有 Chrome，以遠端偵錯模式重新啟動..."
osascript -e 'quit app "Google Chrome"' 2>/dev/null \
  || killall "Google Chrome" 2>/dev/null \
  || true
sleep 2

# 用預設 profile 啟動（LINE 已安裝、已登入）
"${CHROME}" \
  --remote-debugging-port="${PORT}" \
  --no-first-run \
  > /dev/null 2>&1 &

sleep 3

if curl -s "http://localhost:${PORT}/json/version" > /dev/null 2>&1; then
  echo "[OK] Chrome 啟動成功！"
  echo "     你的 LINE 擴充功能已就緒，可以執行 python app.py"
else
  echo "[ERROR] Chrome 啟動失敗。"
  echo "        請確認路徑正確：${CHROME}"
fi
