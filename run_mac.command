#!/bin/bash
# 雙擊執行，把 mesh 檔拖進視窗，按 Enter。/ ダブルクリックして、メッシュをウィンドウにドラッグし Enter。
cd "$(dirname "$0")"

if [ ! -x .venv/bin/python ]; then
  echo "第一次使用，安裝中，約 2 分鐘 / 初回セットアップ中、約2分"
  python3 -m venv .venv || { echo "找不到 Python，請先到 python.org 安裝"; read -r _; exit 1; }
  .venv/bin/python -m pip install -q -r requirements.txt
fi

echo "把 mesh 檔拖到這裡，按 Enter / メッシュをここにドラッグして Enter"
read -r mesh
mesh="${mesh%\'}"; mesh="${mesh#\'}"; mesh="${mesh//\\ / }"
mesh="${mesh%"${mesh##*[![:space:]]}"}"

.venv/bin/python mesh2wood.py "$mesh" && open "${mesh%.*}_wood/viewer.html"
read -r -p "按 Enter 關閉 / Enter で閉じる" _
