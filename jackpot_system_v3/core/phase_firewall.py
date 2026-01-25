# core/v3_7/phase_firewall.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, Optional, List

@dataclass(frozen=True)
class SubscriberContext:
    """Only allowed in Phase 3+ (personalization and beyond)."""
    subscriber_id: str
    mmfsn_cash3: List[str]
    mmfsn_cash4: List[str]
    birth: Optional[Dict[str, Any]] = None
    timezone: Optional[str] = None

def assert_no_personal_inputs(*, phase_name: str, subscriber_ctx: Any = None, mmfsn: Any = None) -> None:
    """Hard guard: Phase 1 & 2 must never receive subscriber/MMFSN."""
    if subscriber_ctx is not None:
        raise RuntimeError(f"[FIREWALL] {phase_name}: subscriber_ctx is not allowed in this phase.")
    if mmfsn is not None:
        raise RuntimeError(f"[FIREWALL] {phase_name}: mmfsn is not allowed in this phase.")

def assert_mmfsn_sets_only(mmfsn_list: List[str], *, digits: int, label: str) -> None:
    """Enforces: MMFSN are immutable sets (3-digit sets for Cash3, 4-digit sets for Cash4)."""
    if not isinstance(mmfsn_list, list):
        raise ValueError(f"[FIREWALL] {label}: must be a list of strings.")
    bad = [x for x in mmfsn_list if (not isinstance(x, str) or len(x) != digits or not x.isdigit())]
    if bad:
        raise ValueError(f"[FIREWALL] {label}: invalid MMFSN values: {bad[:10]}")

def assert_no_mmfsn_exact_match(candidate_number: str, mmfsn_list: List[str], *, label: str) -> None:
    """Exact match must be rejected in Phase 3."""
    if candidate_number in set(mmfsn_list):
        raise RuntimeError(f"[FIREWALL] Exact MMFSN match must be rejected: {label} {candidate_number}")
