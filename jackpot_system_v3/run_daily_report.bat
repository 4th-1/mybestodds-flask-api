@echo off
REM =============================================
REM DAILY LOTTERY PERFORMANCE REPORT AUTOMATION
REM =============================================
REM This script runs every morning to generate performance reports
REM analyzing yesterday's lottery results against SMART LOGIC predictions

echo.
echo 🎯 SMART LOGIC DAILY PERFORMANCE REPORT
echo =======================================
echo %DATE% %TIME%
echo.

cd /d "c:\MyBestOdds\jackpot_system_v3"

REM Activate virtual environment
call "c:\MyBestOdds\.venv\Scripts\activate.bat"

REM Run the daily performance reporter
echo 📊 Generating daily performance report...
python daily_performance_reporter.py

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ✅ Daily report generated successfully!
    echo 📁 Check daily_reports/ folder for results
    echo.
) else (
    echo.
    echo ❌ Error generating daily report
    echo.
)

REM Optional: Email the report (uncomment and configure if needed)
REM python email_daily_report.py

pause