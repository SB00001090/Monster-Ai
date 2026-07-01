@echo off
cd /d "%~dp0\..\.."
if not exist .venv\Scripts\python.exe (
  python -m venv .venv
  call .venv\Scripts\activate.bat
  pip install -r requirements.txt -q
) else (
  call .venv\Scripts\activate.bat
)
python scripts\install_mini_monster_ai.py
start http://127.0.0.1:7860/mini/index.html
python main.py