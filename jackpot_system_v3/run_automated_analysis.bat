@echo off
echo 🚀 SMART LOGIC AUTOMATED PERFORMANCE ANALYSIS
echo ==============================================

cd /d "C:\MyBestOdds\jackpot_system_v3"

echo.
echo 🔍 Fetching latest lottery results from API...
C:\MyBestOdds\.venv\Scripts\python.exe automated_lottery_results_v3_7.py

echo.
echo ✅ Automated analysis complete!
echo.
echo 📊 Check the generated reports in the outputs folder
echo 🎯 MMFSN weights have been automatically adjusted based on performance
echo.
pause