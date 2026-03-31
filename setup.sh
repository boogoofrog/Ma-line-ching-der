#!/bin/bash
set -e

echo "=== 建立虛擬環境 (.venv) ==="
python3 -m venv .venv
source .venv/bin/activate

echo "=== 安裝 Python 套件 ==="
pip install -r requirements.txt

echo "=== 複製環境設定 ==="
if [ ! -f .env ]; then
  cp .env.example .env
fi

echo ""
echo "安裝完成！"
echo ""
echo "使用前請確認："
echo "  1. LINE for Mac 已安裝並登入（App Store 搜尋 LINE）"
echo "  2. 系統偏好設定 → 隱私權與安全性 → 輔助使用"
echo "     → 允許 Terminal（或 iTerm2）控制電腦"
echo ""
echo "測試發訊息："
echo "  source .venv/bin/activate"
echo "  python line_sender.py --send '聯絡人名稱' '訊息內容'"
echo ""
echo "啟動排程機器人："
echo "  python app.py  →  http://localhost:5000"
