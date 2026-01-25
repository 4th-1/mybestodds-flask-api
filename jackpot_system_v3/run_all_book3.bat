@echo off
setlocal enabledelayedexpansion

echo ============================================
echo         BOOK3 MASS RUNNER (BAT VERSION)
echo ============================================
echo.

set ROOT=C:\MyBestOdds\jackpot_system_v3
set SUBDIR=%ROOT%\data\subscribers\BOOK3

echo Running all BOOK3 subscriber files in:
echo %SUBDIR%
echo.

for %%F in ("%SUBDIR%\*.json") do (
    echo --------------------------------------------
    echo Running: %%~nxF
    python "%ROOT%\run_kit_v3.py" "BOOK3/%%~nxF" BOOK3
    echo --------------------------------------------
    echo.
)

echo ============================================
echo    BOOK3 MASS RUN COMPLETE
echo ============================================
pause
