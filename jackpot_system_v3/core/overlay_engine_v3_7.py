#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
overlay_engine_v3_7.py
----------------------
Computes the v3.7 overlay columns:

- moon_phase
- moon_weight
- zodiac_sign
- zodiac_weight
- numerology_code
- numerology_weight
- planetary_hour
- planetary_weight
- overlay_score

This is Step 5A of Option C.
"""

import datetime
from math import floor


# ================================================================
# 1. MOON PHASE
# ================================================================
def moon_phase_from_date(date_obj):
    """Very lightweight moon calculation (good enough for overlays)."""
    diff = date_obj - datetime.date(2001, 1, 1)
    days = diff.days % 29.53

    if days < 1.0:
        return "New Moon", 0.25
    elif days < 7.4:
        return "Waxing Crescent", 0.50
    elif days < 10.7:
        return "First Quarter", 0.65
    elif days < 14.8:
        return "Waxing Gibbous", 0.80
    elif days < 17.0:
        return "Full Moon", 1.00
    elif days < 22.1:
        return "Waning Gibbous", 0.70
    elif days < 26.4:
        return "Last Quarter", 0.50
    else:
        return "Waning Crescent", 0.30


# ================================================================
# 2. ZODIAC SIGN
# ================================================================
def zodiac_sign_from_date(date_obj):
    m = date_obj.month
    d = date_obj.day

    # Aries bias towards Cash 3
    zodiac_weights = {
        "Aries": 0.85,
        "Taurus": 0.60,
        "Gemini": 0.70,
        "Cancer": 0.55,
        "Leo": 0.80,
        "Virgo": 0.65,
        "Libra": 0.50,
        "Scorpio": 0.75,
        "Sagittarius": 0.90,
        "Capricorn": 0.70,
        "Aquarius": 0.60,
        "Pisces": 0.55,
    }

    if   (m==3 and d>=21) or (m==4 and d<=19): sign="Aries"
    elif (m==4 and d>=20) or (m==5 and d<=20): sign="Taurus"
    elif (m==5 and d>=21) or (m==6 and d<=20): sign="Gemini"
    elif (m==6 and d>=21) or (m==7 and d<=22): sign="Cancer"
    elif (m==7 and d>=23) or (m==8 and d<=22): sign="Leo"
    elif (m==8 and d>=23) or (m==9 and d<=22): sign="Virgo"
    elif (m==9 and d>=23) or (m==10 and d<=22): sign="Libra"
    elif (m==10 and d>=23) or (m==11 and d<=21): sign="Scorpio"
    elif (m==11 and d>=22) or (m==12 and d<=21): sign="Sagittarius"
    elif (m==12 and d>=22) or (m==1 and d<=19): sign="Capricorn"
    elif (m==1 and d>=20) or (m==2 and d<=18): sign="Aquarius"
    else: sign="Pisces"

    return sign, zodiac_weights[sign]


# ================================================================
# 3. NUMEROLOGY
# ================================================================
def numerology_code_from_date(date_obj):
    date_sum = sum(int(x) for x in date_obj.strftime("%Y%m%d"))

    while date_sum > 9 and date_sum not in (11,22,33):
        date_sum = sum(int(x) for x in str(date_sum))

    if date_sum in (11,22,33):
        weight = 0.90
    else:
        weight = (date_sum / 9.0)

    return str(date_sum), round(weight, 2)


# ================================================================
# 4. PLANETARY HOUR (Symbolic Approx)
# ================================================================
def planetary_hour_from_time(timestr):
    time_map = {
        "Midday": ("Sun", 0.9),
        "Morning": ("Mercury", 0.6),
        "Evening": ("Venus", 0.7),
        "Night": ("Mars", 0.8),
    }

    if timestr in time_map:
        p, w = time_map[timestr]
        return p + " Hour", w

    return "Unknown", 0.5


# ================================================================
# 5. COMBINED OVERLAY SCORE
# ================================================================
def combined_overlay_score(m, z, n, p):
    return round((m + z + n + p) / 4.0, 3)


# ================================================================
# 6. PUBLIC API
# ================================================================
def compute_overlays(draw_date, draw_time):
    """
    draw_date = 'YYYY-MM-DD'
    draw_time = 'Midday' | 'Morning' | 'Evening' | 'Night'
    Returns dict with all overlay fields.
    """

    date_obj = datetime.datetime.strptime(draw_date, "%Y-%m-%d").date()

    moon_phase, moon_w = moon_phase_from_date(date_obj)
    zodiac_sign, zodiac_w = zodiac_sign_from_date(date_obj)
    num_code, num_w = numerology_code_from_date(date_obj)
    planet_hour, planet_w = planetary_hour_from_time(draw_time)

    overlay = combined_overlay_score(moon_w, zodiac_w, num_w, planet_w)

    return {
        "moon_phase": moon_phase,
        "moon_weight": str(moon_w),
        "zodiac_sign": zodiac_sign,
        "zodiac_weight": str(zodiac_w),
        "numerology_code": num_code,
        "numerology_weight": str(num_w),
        "planetary_hour": planet_hour,
        "planetary_weight": str(planet_w),
        "overlay_score": str(overlay)
    }
