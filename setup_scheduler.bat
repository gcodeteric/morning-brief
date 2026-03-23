@echo off
echo ========================================
echo   SimulaNewsMachine — Configuracao
echo ========================================
echo.

REM Detectar caminho do Python
where python >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo ERRO: Python nao encontrado no PATH.
    echo Instala Python de python.org e marca "Add to PATH".
    pause
    exit /b 1
)

REM Obter caminho absoluto do Python
for /f "delims=" %%i in ('where python') do set PYTHON_PATH=%%i
set WORK_DIR=%~dp0

REM Criar tarefa com caminho absoluto, working directory, e log redirect
schtasks /create /tn "SimulaNewsMachine" ^
    /tr "cmd /c cd /d %WORK_DIR% && \"%PYTHON_PATH%\" main.py >> logs\scheduler.log 2>&1" ^
    /sc daily /st 05:00 /f

echo.
echo Tarefa agendada para as 05:00 todos os dias.
echo Python: %PYTHON_PATH%
echo Pasta: %WORK_DIR%
echo Para verificar: Task Scheduler ^> SimulaNewsMachine
pause
