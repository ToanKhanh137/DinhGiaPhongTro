@echo off
REM Nhấp đúp để chạy crawl lặp mỗi 12 giờ (để treo máy). Đóng cửa sổ để dừng.
chcp 65001 > nul
cd /d "%~dp0"
python src\crawl_all.py --loop-hours 12
pause
