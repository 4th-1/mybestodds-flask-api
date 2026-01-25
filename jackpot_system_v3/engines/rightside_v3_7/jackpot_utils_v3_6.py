"""
jackpot_utils_v3_6.py

Utility helpers for right-side (jackpot) logic in My Best Odds v3.6.
"""

from __future__ import annotations
from typing import List, Sequence, Tuple


def sort_numbers(nums: Sequence[int]) -> List[int]:
    """Return a sorted copy of the given numbers."""
    return sorted(int(n) for n in nums)


def format_main_numbers(nums: Sequence[int]) -> str:
    """Return numbers formatted like '03-18-24-41-55'."""
    return "-".join(f"{int(n):02d}" for n in sort_numbers(nums))


def delta_pattern(nums: Sequence[int]) -> Tuple[int, ...]:
    """
    Convert a number combination into its delta pattern.

    Example:
        [3, 18, 24, 41, 55] → (15, 6, 17, 14)
    """
    ordered = sort_numbers(nums)
    return tuple(ordered[i + 1] - ordered[i] for i in range(len(ordered) - 1))


def normalize_confidence(conf: float) -> float:
    """
    Clamp a confidence score into [0.10, 0.90].
    """
    return max(0.10, min(0.90, float(conf)))
