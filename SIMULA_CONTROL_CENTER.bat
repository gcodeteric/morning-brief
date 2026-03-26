@echo off
setlocal EnableExtensions EnableDelayedExpansion
title SimulaNewsMachine - Control Center
cd /d "%~dp0"

:bootstrap
if exist ".venv\Scripts\activate.bat" (
    call ".venv\Scripts\activate.bat"
) else (
    echo [INFO] .venv nao encontrada. A usar o Python disponivel no sistema.
)

where python >nul 2>&1
if errorlevel 1 (
    echo [ERRO] Python nao encontrado.
    echo Instala Python ou configura uma .venv antes de continuar.
    pause
    exit /b 1
)

:menu
cls
echo ========================================
echo   SimulaNewsMachine - Control Center
echo ========================================
echo.
echo  1. Run pipeline + open dashboard
echo  2. Open dashboard only
echo  3. Open manual overrides file
echo  4. Open latest brief folder
echo  5. Open cards folder
echo  6. Exit
echo.
choice /c 123456 /n /m "Escolhe uma opcao: "

if errorlevel 6 goto :end
if errorlevel 5 goto :cards
if errorlevel 4 goto :brief
if errorlevel 3 goto :overrides
if errorlevel 2 goto :dashboard
if errorlevel 1 goto :pipeline

:pipeline
cls
echo ========================================
echo   Run pipeline + open dashboard
echo ========================================
echo.
echo [INFO] Vai correr "python main.py" com a configuracao actual.
echo [INFO] Brief, cards e email opcional seguem exactamente o estado actual do config.py.
echo.
python main.py
if errorlevel 1 (
    echo.
    echo [ERRO] O pipeline falhou. O dashboard nao sera aberto automaticamente.
    pause
    goto :menu
)
echo.
python launch_dashboard.py dashboard
if errorlevel 1 (
    echo.
    echo [ERRO] O dashboard nao arrancou correctamente.
    pause
)
goto :menu

:dashboard
cls
echo ========================================
echo   Open dashboard only
echo ========================================
echo.
python launch_dashboard.py dashboard
if errorlevel 1 (
    echo.
    echo [ERRO] O dashboard nao arrancou correctamente.
    pause
)
goto :menu

:overrides
cls
echo ========================================
echo   Open manual overrides file
echo ========================================
echo.
python launch_dashboard.py open overrides
if errorlevel 1 pause
goto :menu

:brief
cls
echo ========================================
echo   Open latest brief folder
echo ========================================
echo.
python launch_dashboard.py open brief-folder
if errorlevel 1 pause
goto :menu

:cards
cls
echo ========================================
echo   Open cards folder
echo ========================================
echo.
python launch_dashboard.py open cards-folder
if errorlevel 1 pause
goto :menu

:end
exit /b 0
