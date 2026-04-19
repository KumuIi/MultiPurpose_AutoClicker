@echo off
echo Installing build tools...
python -m pip install pyinstaller pynput -q

echo.
echo Building AutoClicker.exe ...
pyinstaller --onefile --windowed --name AutoClicker autoclicker.py

echo.
if exist "dist\AutoClicker.exe" (
    echo Build successful!
    echo Your executable is at: dist\AutoClicker.exe
) else (
    echo Build failed. Check the output above for errors.
)
pause
