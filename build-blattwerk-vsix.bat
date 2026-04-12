@echo off
setlocal

set "REPO_DIR=%~dp0"
set "EXT_DIR=%REPO_DIR%vscode-extension\blattwerk-language"
set "EXIT_CODE=0"
set "VSIX_FILE="
set "NODE_EXE="
set "NODE_DIR="
set "NPM_CMD="
set "NPX_CMD="

if not exist "%EXT_DIR%\package.json" (
  echo [ERROR] Extension folder not found: %EXT_DIR%
  set "EXIT_CODE=1"
  goto :finalize
)

for /f "delims=" %%F in ('where node.exe 2^>nul') do (
  set "NODE_EXE=%%F"
  goto :node_found
)

if exist "%ProgramFiles%\nodejs\node.exe" (
  set "NODE_EXE=%ProgramFiles%\nodejs\node.exe"
)
if "%NODE_EXE%"=="" if exist "%ProgramFiles(x86)%\nodejs\node.exe" (
  set "NODE_EXE=%ProgramFiles(x86)%\nodejs\node.exe"
)
if "%NODE_EXE%"=="" if exist "D:\Program Files\nodejs\node.exe" (
  set "NODE_EXE=D:\Program Files\nodejs\node.exe"
)

:node_found
if "%NODE_EXE%"=="" (
  echo [ERROR] node.exe not found. Install Node.js and retry.
  set "EXIT_CODE=1"
  goto :finalize
)

for %%D in ("%NODE_EXE%") do set "NODE_DIR=%%~dpD"

if exist "%NODE_DIR%npm.cmd" set "NPM_CMD=%NODE_DIR%npm.cmd"
if exist "%NODE_DIR%npx.cmd" set "NPX_CMD=%NODE_DIR%npx.cmd"

if "%NPM_CMD%"=="" (
  echo [ERROR] npm.cmd not found next to node.exe at: %NODE_DIR%
  set "EXIT_CODE=1"
  goto :finalize
)

if "%NPX_CMD%"=="" (
  echo [ERROR] npx.cmd not found next to node.exe at: %NODE_DIR%
  set "EXIT_CODE=1"
  goto :finalize
)

pushd "%EXT_DIR%"
if errorlevel 1 (
  echo [ERROR] Cannot enter extension folder.
  set "EXIT_CODE=1"
  goto :finalize
)

echo [1/3] Installing/updating node packages...
call "%NPM_CMD%" install
if errorlevel 1 goto :fail

echo [2/3] Building extension...
call "%NPM_CMD%" run build
if errorlevel 1 goto :fail

echo [3/3] Packaging VSIX...
call "%NPX_CMD%" @vscode/vsce package
if errorlevel 1 goto :fail

for /f "delims=" %%F in ('dir /b /o-d "*.vsix"') do (
  set "VSIX_FILE=%%F"
  goto :copy
)

echo [WARN] Packaging finished but no VSIX file was found.
goto :done

:copy
copy /y "%VSIX_FILE%" "%REPO_DIR%%VSIX_FILE%" >nul
echo [OK] VSIX created: %EXT_DIR%\%VSIX_FILE%
echo [OK] Copy in repo root: %REPO_DIR%%VSIX_FILE%
goto :done

:fail
echo [ERROR] Build or packaging failed.
set "EXIT_CODE=1"
goto :done

:done
popd
goto :finalize

:finalize
echo.
echo ===== Next step in VS Code =====
if "%VSIX_FILE%"=="" (
  echo VSIX file was not created. Fix the error above and run this script again.
) else (
  echo 1^) In VS Code press Ctrl+Shift+P
  echo 2^) Run: Extensions: Install from VSIX...
  echo 3^) Select: %REPO_DIR%%VSIX_FILE%
  echo.
  echo Optional CLI install:
  echo   code --install-extension "%REPO_DIR%%VSIX_FILE%"
)
echo.
pause
exit /b %EXIT_CODE%
