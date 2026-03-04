@echo off
REM Streamlit Launcher with PYTHONPATH Fix
REM
REM This script ensures that the project root is in PYTHONPATH,
REM allowing Streamlit to import modules with 'from src...' syntax.
REM
REM Usage: run_streamlit.cmd

echo.
echo ========================================
echo  CV Governance Agent - Streamlit UI
echo ========================================
echo.
echo Setting PYTHONPATH to project root...
set PYTHONPATH=%CD%

echo Starting Streamlit app...
echo.
echo Access at: http://localhost:8501
echo.

streamlit run src/streamlit_app.py

echo.
echo Streamlit stopped.
pause
