@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if not errorlevel 1 (
  py -3 editor.py %*
  if errorlevel 1 pause
  exit /b
)
where python >nul 2>nul
if not errorlevel 1 (
  python editor.py %*
  if errorlevel 1 pause
  exit /b
)
echo Brak Pythona. Zainstaluj Python 3.10 lub nowszy z obsluga Tcl/Tk.
echo Program nie wymaga zadnych pakietow pip.
pause
