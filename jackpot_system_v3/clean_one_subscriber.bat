@echo off
echo ========================================
echo  V3 Subscriber Cleaner - One File Mode
echo ========================================
echo.

set /p filename="Enter the legacy subscriber JSON filename (ex: JDS.json): "

echo.
echo Running cleaner for: %filename%
echo.

python - <<END
from pathlib import Path
from core.subscriber_cleaner import clean_subscriber_file

root = Path(r"C:\MyBestOdds\jackpot_system_v3")
file_path = root / "data" / "subscribers" / "%filename%"

if file_path.exists():
    clean_subscriber_file(file_path, root)
else:
    print(f"[ERROR] File not found: {file_path}")
END

echo.
echo Done!
pause
