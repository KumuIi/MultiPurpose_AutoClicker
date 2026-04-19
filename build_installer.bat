@echo off
echo =============================================
echo  AutoClicker - Installer Builder
echo =============================================
echo.

echo [1/3] Installing build tools...
python -m pip install pyinstaller pillow pynput -q
echo Done.
echo.

echo [2/3] Building AutoClicker.exe...
python -m PyInstaller --onefile --windowed --icon=icon.ico --name AutoClicker autoclicker.py --distpath dist --workpath build --noconfirm
if not exist "dist\AutoClicker.exe" (
    echo ERROR: exe build failed.
    pause & exit /b 1
)
echo Done.
echo.

echo [3/3] Building installer...

set INNO="C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if not exist %INNO% set INNO="C:\Program Files\Inno Setup 6\ISCC.exe"
if not exist %INNO% set INNO="%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"

if not exist %INNO% (
    echo.
    echo Inno Setup not found. Please install it from:
    echo   https://jrsoftware.org/isdl.php
    echo Then re-run this script.
    pause & exit /b 1
)

if not exist "installer_output" mkdir installer_output
%INNO% installer.iss
echo.

if exist "installer_output\AutoClicker_Setup.exe" (
    echo =============================================
    echo  SUCCESS!
    echo  Installer: installer_output\AutoClicker_Setup.exe
    echo =============================================
) else (
    echo Build failed. Check output above.
)
pause
