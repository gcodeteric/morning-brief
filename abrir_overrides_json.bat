@echo off
setlocal

set "ROOT=%~dp0"
set "DATA_DIR=%ROOT%data"
set "TARGET=%DATA_DIR%\manual_overrides.json"

if not exist "%DATA_DIR%" mkdir "%DATA_DIR%"

if not exist "%TARGET%" (
  >"%TARGET%" (
    echo {
    echo   "instagram_sim_racing": 0,
    echo   "instagram_motorsport": 0,
    echo   "x_thread_1": 0,
    echo   "x_thread_2": 0,
    echo   "youtube_daily": 0,
    echo   "discord_post": 0
    echo }
  )
)

if exist "%TARGET%" (
  start "" notepad "%TARGET%"
) else (
  echo Nao foi possivel abrir data\manual_overrides.json
)

endlocal
