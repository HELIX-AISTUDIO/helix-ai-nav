@echo off
chcp 65001 >nul
setlocal
set PYTHONIOENCODING=utf-8
cd /d "%~dp0"

echo.
echo === HELIX-AI channel site -^> GitHub Pages ===
echo.
echo Locating Python...
set PY=

if exist "%USERPROFILE%\AppData\Local\Programs\Python\Python312\python.exe" set PY="%USERPROFILE%\AppData\Local\Programs\Python\Python312\python.exe"
if not defined PY if exist "C:\Users\admin\.workbuddy\binaries\python\versions\3.13.12\python.exe" set PY="C:\Users\admin\.workbuddy\binaries\python\versions\3.13.12\python.exe"
if not defined PY where py >nul 2>nul && set PY=py
if not defined PY where python >nul 2>nul && set PY=python

if not defined PY (
  echo [ERROR] Python 3 not found. Please install it first.
  pause
  exit /b 1
)

echo Using: %PY%
echo.
%PY% deploy-github.py

endlocal
