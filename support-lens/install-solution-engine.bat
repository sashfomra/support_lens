@echo off
echo Installing SupportLens Solution Engine dependencies...
echo.
pip install chromadb praw groq playwright beautifulsoup4 requests lxml
echo.
echo Installing Playwright browsers (chromium)...
playwright install chromium
echo.
echo Done! Copy backend\.env.example to backend\.env and add your API keys.
pause
