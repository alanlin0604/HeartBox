@echo off
REM HeartBox local LLM server starter.
REM Runs uvicorn + FastAPI in the foreground. Ctrl-C to stop.
REM
REM Prereqs:
REM   1. %USERPROFILE%\.heartbox-llm.env exists with API_KEY=<value>
REM   2. ..\backend\venv has been set up via:
REM        python -m venv backend\venv
REM        backend\venv\Scripts\pip install -r backend\requirements-llm.txt
REM   3. HF models cached under %USERPROFILE%\.cache\huggingface\hub\

setlocal
set ROOT=%~dp0..

if not exist "%USERPROFILE%\.heartbox-llm.env" (
    echo ERROR: %USERPROFILE%\.heartbox-llm.env not found.
    echo Create one with:
    echo     API_KEY=^<random hex^>
    echo     HF_HOME=%USERPROFILE%\.cache\huggingface
    exit /b 1
)

if not exist "%ROOT%\backend\venv\Scripts\python.exe" (
    echo ERROR: virtualenv not found at backend\venv.
    exit /b 1
)

echo Starting HeartBox LLM server on 127.0.0.1:8765 ...
"%ROOT%\backend\venv\Scripts\python.exe" -m llm_server
endlocal
