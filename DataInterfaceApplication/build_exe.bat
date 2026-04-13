@echo off
REM =========================================================================
REM  LSMD Data Interface — Build Script
REM  Double-click this file to build the .exe
REM  Output: dist\LSMD_Interface.exe
REM =========================================================================

echo.
echo ============================================
echo   LSMD Data Interface — EXE Builder
echo ============================================
echo.

python --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Python not found on PATH.
    echo         Install Python 3.12.x and check "Add Python to PATH".
    pause
    exit /b 1
)

echo [1/3] Installing required Python packages...
echo.

pip install --upgrade pip
pip install pyinstaller
pip install bleak
pip install PyQt6
pip install pyserial
pip install numpy
pip install pyqtgraph
pip install pandas

echo.
echo [2/3] Building executable...
echo      This may take 2-5 minutes on first build.
echo.

pyinstaller LSMD_Interface.spec --noconfirm

echo.

if exist "dist\LSMD_Interface.exe" (
    echo ============================================
    echo   BUILD SUCCESSFUL
    echo ============================================
    echo.
    echo   Your executable is ready at:
    echo     dist\LSMD_Interface.exe
    echo.
) else (
    echo ============================================
    echo   BUILD FAILED
    echo ============================================
    echo.
    echo   Check the output above for error messages.
    echo.
)

pause