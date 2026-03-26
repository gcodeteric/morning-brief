@echo off
setlocal
title SimulaNewsMachine - Iniciar Dashboard
cd /d "%~dp0"

echo ========================================
echo   SimulaNewsMachine - Iniciar Dashboard
echo ========================================
echo.

if exist ".venv\Scripts\activate.bat" (
    call ".venv\Scripts\activate.bat"
) else (
    echo [INFO] .venv nao encontrada. A usar o Python disponivel no sistema.
)

where python >nul 2>&1
if errorlevel 1 (
    echo [ERRO] Python nao encontrado.
    echo Instala Python ou cria .venv\Scripts\activate.bat antes de continuar.
    pause
    exit /b 1
)

python -m streamlit --version >nul 2>&1
if errorlevel 1 (
    echo [ERRO] Streamlit nao esta disponivel neste ambiente.
    echo Executa: pip install -r requirements.txt
    pause
    exit /b 1
)

python launch_dashboard.py dashboard
if errorlevel 1 (
    echo.
    echo [ERRO] O dashboard nao arrancou correctamente.
    pause
    exit /b 1
)

echo.
echo [OK] Dashboard tratado com readiness check.
exit /b 0
