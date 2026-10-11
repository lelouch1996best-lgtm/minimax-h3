@echo off
setlocal
REM ============================================================
REM  Bilibili QR login helper
REM  biliup.exe hard-requires a real TTY, so this must be run
REM  from a local terminal window (double-click is fine).
REM
REM  Usage:  bili_login.cmd [account_label]
REM  Default label: hehuajiu   (Bilibili nickname: HeHuaJiu)
REM ============================================================

set "SAU_HOME=D:\work\social-auto-upload"
set "ACCOUNT=%~1"

REM No hard-coded default on purpose: the account label becomes the cookie
REM file name, and a Chinese label cannot be embedded in this ASCII-only
REM script. Always pass the label explicitly, e.g.:
REM     bili_login.cmd hehuajiu
if "%ACCOUNT%"=="" (
  echo.
  echo   Usage: bili_login.cmd ^<account_label^>
  echo   Example: bili_login.cmd hehuajiu
  echo   Cookie will be written to cookies\bilibili_^<label^>.json
  echo.
  echo   Existing labels: bilibili_main / main / xiongda
  echo.
  pause
  exit /b 1
)

echo.
echo   Account label : %ACCOUNT%
echo   Cookie target : %SAU_HOME%\cookies\bilibili_%ACCOUNT%.json
echo.
echo   Use the Bilibili App on your phone to scan the QR code.
echo   If the QR code above looks broken or squashed, open this
echo   image instead and scan that:
echo       %SAU_HOME%\qrcode.png
echo.

if not exist "%SAU_HOME%\.venv\Scripts\sau.exe" (
  echo   [FAIL] sau.exe not found at %SAU_HOME%\.venv\Scripts\sau.exe
  echo.
  pause
  exit /b 1
)

cd /d "%SAU_HOME%"
".venv\Scripts\sau.exe" bilibili login --account "%ACCOUNT%"
set "RC=%ERRORLEVEL%"

echo.
if "%RC%"=="0" (
  echo   [OK] login finished. Verifying cookie ...
  echo.
  ".venv\Scripts\sau.exe" bilibili check --account "%ACCOUNT%"
) else (
  echo   [FAIL] login exited with code %RC%
)
echo.
pause
endlocal
