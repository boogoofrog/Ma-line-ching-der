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
sleep 3

# 用 open -a 啟動（macOS 最相容的方式）
open -a "Google Chrome" --args \
  --remote-debugging-port="${PORT}" \
  --no-first-run

# 等待 Chrome 就緒（最多 15 秒）
echo -n "等待 Chrome 就緒"
for i in $(seq 1 15); do
  sleep 1
  echo -n "."
  if curl -s "http://localhost:${PORT}/json/version" > /dev/null 2>&1; then
    echo ""
    echo "[OK] Chrome 啟動成功！可以執行 python app.py"
    exit 0
  fi
done

echo ""
echo "[ERROR] Chrome 在 15 秒內未能開放 port ${PORT}。"
echo "        請手動確認 Chrome 是否正確開啟，然後執行："
echo "        curl http://localhost:${PORT}/json/version"
