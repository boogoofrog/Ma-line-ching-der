#!/bin/bash
# 一鍵安裝與初始化
set -e

echo "=== 安裝 Python 套件 ==="
python3 -m pip install -r requirements.txt

echo "=== 安裝 Playwright Chromium ==="
python3 -m playwright install chromium

echo "=== 複製環境設定 ==="
if [ ! -f .env ]; then
  cp .env.example .env
  echo "已建立 .env，請視需要編輯"
fi

echo ""
echo "=== 首次登入 LINE ==="
echo "請執行下列指令，在彈出的瀏覽器視窗中掃描 QR code 登入 LINE："
echo ""
echo "  python line_sender.py --setup"
echo ""
echo "登入完成後，執行以下指令啟動機器人："
echo ""
echo "  python app.py"
echo ""
echo "然後開啟瀏覽器前往 http://localhost:5000"
