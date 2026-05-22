@echo off
title Sistema de Inteligencia Turistica - Canarias AI
echo ========================================================
echo   INICIANDO ARQUITECTURA DE PRODUCCION (CANARIAS AI)
echo ========================================================
echo.

echo [+] 1/2 Iniciando API de Inferencia (FastAPI + Uvicorn) en puerto 8000...
start /min "FastAPI Backend" uvicorn src.api:app --host 127.0.0.1 --port 8000
timeout /t 3 /nobreak > nul

echo [+] 2/2 Iniciando Aplicacion Cliente (Streamlit) en puerto 8501...
streamlit run src/app.py

pause
