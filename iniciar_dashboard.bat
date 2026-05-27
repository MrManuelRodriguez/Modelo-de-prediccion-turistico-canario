@echo off
title Sistema de Inteligencia Turistica - Canarias AI
echo ========================================================
echo   INICIANDO ARQUITECTURA DE PRODUCCION (CANARIAS AI)
echo ========================================================
echo.

:: --- Comprobacion e instalacion de dependencias ---
echo [*] Verificando dependencias de Python...
python -c "import streamlit, fastapi, uvicorn, xgboost, pymongo, plotly, sklearn, dotenv" 2>nul
if %errorlevel% neq 0 (
    echo [!] Modulos no encontrados. Instalando desde requirements.txt...
    pip install -r requirements.txt
    if %errorlevel% neq 0 (
        echo [ERROR] Fallo al instalar dependencias. Comprueba tu conexion a internet y que Python este en el PATH.
        pause
        exit /b 1
    )
    echo [OK] Dependencias instaladas correctamente.
) else (
    echo [OK] Todas las dependencias ya estan instaladas.
)
echo.

echo [+] 1/2 Iniciando API de Inferencia (FastAPI + Uvicorn) en puerto 8000...
start /min "FastAPI Backend" python -m uvicorn src.api:app --host 127.0.0.1 --port 8000
timeout /t 3 /nobreak > nul

echo [+] 2/2 Iniciando Aplicacion Cliente (Streamlit) en puerto 8501...
python -m streamlit run src/app.py

pause
