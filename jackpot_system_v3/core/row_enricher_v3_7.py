import datetime

# ============================================================
# CONFIG
# ============================================================

DEBUG_ENRICH = False  # ← set True only when diagnosing


# ============================================================
# NORTH NODE LOGIC
# ============================================================

def get_true_north_node(dob_date):
    """
    Calculates the TRUE North Node using Swiss Ephemeris switch dates.
    The Node moves BACKWARDS (Retrograde).
    """
    y, m, d = dob_date.year, dob_date.month, dob_date.day
    date_val = y * 10000 + m * 100 + d

    cycles = [
        (20250112, "Pisces"), (20230718, "Aries"), (20220119, "Taurus"),
        (20200505, "Gemini"), (20181107, "Cancer"), (20170509, "Leo"),
        (20151112, "Virgo"), (20140219, "Libra"), (20120830, "Scorpio"),
        (20110303, "Sagittarius"), (20090822, "Capricorn"),
        (20071219, "Aquarius"), (20060623, "Pisces"),
        (20041227, "Aries"), (20030415, "Taurus"),
        (20011014, "Gemini"), (20000410, "Cancer"),
        (19981021, "Leo"), (19970126, "Virgo"),
        (19950801, "Libra"), (19940202, "Scorpio"),
        (19920802, "Sagittarius"), (19910127, "Capricorn"),
        (19890523, "Aquarius"), (19871203, "Pisces"),
        (19860407, "Aries"), (19840912, "Taurus"),
        (19830317, "Gemini"), (19810925, "Cancer"),
        (19800106, "Leo"), (19780706, "Virgo"),
        (19770108, "Libra"), (19750711, "Scorpio"),
        (19731028, "Sagittarius"), (19720428, "Capricorn"),
        (19701103, "Aquarius"), (19690420, "Pisces"),
        (19670820, "Aries"), (19660220, "Taurus"),
        (19640826, "Gemini"), (19630329, "Cancer"),
        (19610927, "Leo"), (19600329, "Virgo"),
        (19580617, "Libra"), (19561005, "Scorpio"),
        (19550403, "Sagittarius"), (19531010, "Capricorn"),
        (19520329, "Aquarius"), (19500727, "Pisces"),
    ]

    for start_date, sign in cycles:
        if date_val >= start_date:
            return sign

    return "Universal"


def get_karmic_advice(node_sign):
    advice = {
        "Aries": "Destiny favors independence. Trust your solo picks.",
        "Taurus": "Stability is key. Stick to your long-term numbers.",
        "Gemini": "High adaptability. Change strategy daily.",
        "Cancer": "Intuition is peak. Trust gut feeling numbers.",
        "Leo": "Confidence wins. Don't hedge—play bold.",
        "Virgo": "Pattern recognition. Analyze frequency charts.",
        "Libra": "Seek balance. Play High/Low evenly.",
        "Scorpio": "Transformation. Re-play old numbers.",
        "Sagittarius": "Luck is natural. Expand your range.",
        "Capricorn": "Discipline. Avoid impulse plays.",
        "Aquarius": "Disrupt patterns. Pick unusual numbers.",
        "Pisces": "Dream logic. Trust intuition.",
        "Universal": "Flow with daily energy.",
    }
    return f"{node_sign} North Node: {advice.get(node_sign, '')}"


# ============================================================
# ENRICHMENT ENGINE
# ============================================================

def enrich_row_v3_7(row, subscriber):
    """
    Final enrichment layer.
    Must NEVER mutate draw_time or game_code.
    """
    try:
        if DEBUG_ENRICH:
            print("[DEBUG][ENRICH][IN ] draw_time:",
                  row.get("draw_time"),
                  "game:",
                  row.get("game_code"))

        number_str = str(row.get("number", "")).strip()

        # --- Forecast Date ---
        try:
            draw_date = datetime.datetime.strptime(
                row.get("forecast_date", ""),
                "%Y-%m-%d"
            ).date()
        except Exception:
            draw_date = datetime.date.today()

        # --- DOB / North Node ---
        dob_str = subscriber.get("dob")
        node_sign = "Universal"

        if dob_str:
            try:
                dob_date = datetime.datetime.strptime(dob_str, "%Y-%m-%d").date()
                node_sign = get_true_north_node(dob_date)
            except Exception:
                pass

        # ====================================================
        # SCORE ENGINE
        # ====================================================

        base_score = 0.70

        engine_source = row.get("engine_source", "")

        if engine_source == "PROFILE_MMFSN":
            base_score += 0.20
        elif engine_source == "SYSTEM_ALGO":
            base_score += 0.05

        if f"{draw_date.day:02d}" in number_str:
            base_score += 0.04

        final_score = min(0.999, base_score)

        if final_score >= 0.90:
            band = "GREEN"
            verdict = "STRONG PLAY"
        elif final_score >= 0.75:
            band = "YELLOW"
            verdict = "MODERATE"
        else:
            band = "RED"
            verdict = "WATCH"

        # --- Profile Override ---
        if engine_source == "PROFILE_MMFSN":
            final_score = max(final_score, 0.92)
            band = "GREEN"
            verdict = "STRONG PLAY (PROFILE)"

        # ====================================================
        # OUTPUT FIELDS
        # ====================================================

        row["confidence_score"] = final_score
        row["confidence_band"] = band
        row["play_flag"] = verdict
        row["north_node_insight"] = get_karmic_advice(node_sign)

        game_code = row.get("game_code", "")

        if game_code == "CASH3":
            row["mbo_odds_text"] = "1 in 333 (Box)"
        elif game_code == "CASH4":
            row["mbo_odds_text"] = "1 in 416 (Box)"
        else:
            row["mbo_odds_text"] = "High Volatility"

        if DEBUG_ENRICH:
            print("[DEBUG][ENRICH][OUT] draw_time:",
                  row.get("draw_time"),
                  "game:",
                  row.get("game_code"))

        return row

    except Exception:
        row["confidence_score"] = 0.0
        row["confidence_band"] = "RED"
        row["play_flag"] = "DATA ERROR"
        return row
