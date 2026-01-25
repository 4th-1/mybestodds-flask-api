@echo off
echo 🔄 Running MMFSN Course Correction Analysis...
echo ===============================================

cd /d "C:\MyBestOdds\jackpot_system_v3"

REM Run course correction analysis
C:\MyBestOdds\.venv\Scripts\python.exe mmfsn_course_corrector_v3_7.py "outputs" "data\actual_results_december_2025.json" "config_v3_5.json"

echo.
echo ✅ Course correction complete!
pause