@echo off
setlocal

set "SCRIPT_DIR=%~dp0"
set "VENV_PYW=%SCRIPT_DIR%.venv\Scripts\pythonw.exe"
set "ENTRY=%SCRIPT_DIR%blattwerk.py"

if not exist "%ENTRY%" (
  echo Startdatei nicht gefunden: %ENTRY%
  pause
  exit /b 1
)

if exist "%VENV_PYW%" (
  start "" "%VENV_PYW%" "%ENTRY%"
) else (
  echo Blattwerk-Umgebung fehlt: %VENV_PYW%
  echo.
  echo Bitte einmalig im Ordner Code\blattwerk ausfuehren:
  echo   py -3 -m venv .venv
  echo   .\.venv\Scripts\Activate.ps1
  echo   pip install -r requirements.txt
  echo.
  pause
  exit /b 1
)

endlocal
