@echo off
chcp 65001 >nul
cd /d "%~dp0"

if "%~1"=="" (
  echo 把 mesh 檔拖到這個圖示上 / メッシュファイルをこのアイコンにドラッグ
  pause
  exit /b
)

if not exist ".venv\Scripts\python.exe" (
  echo 第一次使用，安裝中，約 2 分鐘 / 初回セットアップ中、約2分
  py -3 -m venv .venv 2>nul || python -m venv .venv
  if not exist ".venv\Scripts\python.exe" (
    echo 找不到 Python，請先到 python.org 安裝 / Python が見つかりません。python.org からインストール
    pause
    exit /b
  )
  ".venv\Scripts\python.exe" -m pip install -q -r requirements.txt
)

".venv\Scripts\python.exe" mesh2wood.py "%~1"
if errorlevel 1 goto end
start "" "%~dpn1_wood\viewer.html"

:end
pause
