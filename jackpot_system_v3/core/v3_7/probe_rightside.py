from rightside_engine_v3_6 import build_engine_for_game
import datetime

engine = build_engine_for_game(
    "megamillions",
    "BOOK3",
    r"C:\MyBestOdds\jackpot_system_v3\data\results\jackpot_results\MegaMillions.csv"
)

d = datetime.date(2025, 12, 17)

print("Exact day:", engine.generate_picks_for_range(d, d))
print("+/-7 days:", engine.generate_picks_for_range(d-datetime.timedelta(days=7), d+datetime.timedelta(days=7)))
print("None,None:", engine.generate_picks_for_range(None, None))
