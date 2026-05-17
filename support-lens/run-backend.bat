@echo off
echo.
echo  Starting SupportLens Backend...
echo  (Keep this window open)
echo.
cd /d "%~dp0backend"
python -m uvicorn main:app --reload --port 8000
