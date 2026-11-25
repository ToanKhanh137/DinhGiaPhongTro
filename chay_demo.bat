@echo off
REM Nhap dup de mo demo web tai http://localhost:8000 . Dong cua so nay de tat.
chcp 65001 > nul
cd /d "%~dp0"
python web\server.py --open
pause
