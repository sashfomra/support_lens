@echo off
echo SupportLens - Installing dependencies
echo =====================================

cd /d %~dp0backend

echo.
echo [1/2] Installing Python backend packages...
pip install fastapi "uvicorn[standard]" sqlalchemy pydantic pydantic-settings httpx numpy scikit-learn python-multipart aiofiles python-dateutil sentence-transformers faiss-cpu transformers torch spacy

echo.
echo [2/2] Installing spaCy language model...
python -m spacy download en_core_web_sm

echo.
echo [3/3] Installing frontend dependencies...
cd /d %~dp0frontend
call npm install

echo.
echo ==============================
echo Installation complete!
echo Run start.bat to launch the app
echo ==============================
pause
