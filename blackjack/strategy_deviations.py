"""Hi-Lo Index Plays (Illustrious 18 + Fab 4) and bet-sizing helper.

Index plays are deviations from basic strategy that turn on once the
True Count crosses a threshold. Source: Don Schlesinger's "Blackjack
Attack" (3rd edition) for the classic 18+4 set used by most counters.

`recommend_bet` implements a 1-1-2-4-8-12 spread style ramp, capped at
`max_units`. It is a Kelly-shaped proxy: at TC<=1 bet the minimum, at
TC>=5 bet the cap, linear in between.
"""
from __future__ import annotations

from dataclasses import dataclass

from .actions import Action
from .models import Card, Hand, Rank


@dataclass(frozen=True)
class Deviation:
    label: str            # e.g. "16 vs 10"
    threshold: float      # take action when true_count >= threshold (or <= if reverse)
    action: Action        # action to take when threshold met
    reverse: bool = False # True when condition is true_count <= threshold


# Index plays: keyed by (player_total, is_soft, dealer_upcard_points).
# Each entry is (default_below_threshold, Deviation).
# Default_below is what basic strategy says; Deviation describes the
# alternative once the threshold is crossed.
# Stored as a flat list of (key, default, dev) for clarity.

ILLUSTRIOUS_18: list[tuple[tuple[int, bool, int], Action, Deviation]] = [
    # 16 vs 10: Stand if TC >= 0 (otherwise Hit)
    ((16, False, 10), Action.HIT,
     Deviation("16 vs 10", 0.0, Action.STAND)),
    # 15 vs 10: Stand if TC >= +4
    ((15, False, 10), Action.HIT,
     Deviation("15 vs 10", 4.0, Action.STAND)),
    # 13 vs 2: Hit if TC <= -1 (default Stand)
    ((13, False, 2), Action.STAND,
     Deviation("13 vs 2", -1.0, Action.HIT, reverse=True)),
    # 13 vs 3: Hit if TC <= -2
    ((13, False, 3), Action.STAND,
     Deviation("13 vs 3", -2.0, Action.HIT, reverse=True)),
    # 12 vs 3: Stand if TC >= +2 (default Hit)
    ((12, False, 3), Action.HIT,
     Deviation("12 vs 3", 2.0, Action.STAND)),
    # 12 vs 2: Stand if TC >= +3
    ((12, False, 2), Action.HIT,
     Deviation("12 vs 2", 3.0, Action.STAND)),
    # 11 vs A: Double if TC >= +1 (default Hit)
    ((11, False, 11), Action.HIT,
     Deviation("11 vs A", 1.0, Action.DOUBLE)),
    # 9 vs 2: Double if TC >= +1
    ((9, False, 2), Action.HIT,
     Deviation("9 vs 2", 1.0, Action.DOUBLE)),
    # 10 vs 10: Double if TC >= +4
    ((10, False, 10), Action.HIT,
     Deviation("10 vs 10", 4.0, Action.DOUBLE)),
    # 10 vs A: Double if TC >= +4
    ((10, False, 11), Action.HIT,
     Deviation("10 vs A", 4.0, Action.DOUBLE)),
    # 9 vs 7: Double if TC >= +3
    ((9, False, 7), Action.HIT,
     Deviation("9 vs 7", 3.0, Action.DOUBLE)),
    # 16 vs 9: Stand if TC >= +5
    ((16, False, 9), Action.HIT,
     Deviation("16 vs 9", 5.0, Action.STAND)),
    # 13 vs 2 already above; include 12 vs 4..6 reverse plays
    # 12 vs 4: Hit if TC <= 0
    ((12, False, 4), Action.STAND,
     Deviation("12 vs 4", 0.0, Action.HIT, reverse=True)),
    # 12 vs 5: Hit if TC <= -2
    ((12, False, 5), Action.STAND,
     Deviation("12 vs 5", -2.0, Action.HIT, reverse=True)),
    # 12 vs 6: Hit if TC <= -1
    ((12, False, 6), Action.STAND,
     Deviation("12 vs 6", -1.0, Action.HIT, reverse=True)),
    # 14 vs 10: Stand if TC >= +3 (already default Stand; here reverse Hit)
    # Skipping 14 vs 10 because default is already Stand for hard 14.
]


FAB_4_SURRENDERS: list[tuple[tuple[int, bool, int], Deviation]] = [
    # 14 vs 10: Surrender if TC >= +3
    ((14, False, 10),
     Deviation("14 vs 10 surrender", 3.0, Action.SURRENDER)),
    # 15 vs 9: Surrender if TC >= +2
    ((15, False, 9),
     Deviation("15 vs 9 surrender", 2.0, Action.SURRENDER)),
    # 15 vs A: Surrender if TC >= +1
    ((15, False, 11),
     Deviation("15 vs A surrender", 1.0, Action.SURRENDER)),
    # 15 vs 10: always Surrender per basic strategy; deviation downgrades
    # at TC <= -1 to Hit, which is too marginal to bother encoding.
]


INSURANCE_THRESHOLD = 3.0  # take insurance when true_count >= +3


def index_decision(
    hand: Hand,
    dealer_upcard: Card,
    true_count: float,
    *,
    allow_surrender: bool = True,
) -> Action | None:
    """Return an Action if an index play overrides basic strategy.

    Returns None when no index play applies (caller should fall back to
    `basic_strategy.optimal_action`).
    """
    if hand.is_soft:
        return None  # current index set covers hard totals only

    upcard_pts = (11 if dealer_upcard.rank is Rank.ACE
                  else dealer_upcard.rank.points)
    key = (hand.value, False, upcard_pts)

    # Surrenders first: they require a 2-card non-split hand.
    if (allow_surrender and len(hand.cards) == 2 and not hand.is_split):
        for dev_key, dev in FAB_4_SURRENDERS:
            if dev_key == key and true_count >= dev.threshold:
                return dev.action

    for dev_key, _default, dev in ILLUSTRIOUS_18:
        if dev_key != key:
            continue
        if dev.reverse and true_count <= dev.threshold:
            return dev.action
        if not dev.reverse and true_count >= dev.threshold:
            return dev.action

    return None


def should_take_insurance(true_count: float) -> bool:
    """Insurance is a side bet on dealer Blackjack; take it at TC >= +3."""
    return true_count >= INSURANCE_THRESHOLD


def recommend_bet(
    true_count: float,
    min_bet: int,
    *,
    max_units: int = 12,
    ramp_start: float = 1.0,
    ramp_end: float = 5.0,
) -> int:
    """Suggested bet in dollars based on True Count.

    Below `ramp_start` bet the minimum; above `ramp_end` bet
    min_bet * max_units. Linear interpolation in between.
    """
    if true_count <= ramp_start:
        units = 1.0
    elif true_count >= ramp_end:
        units = float(max_units)
    else:
        frac = (true_count - ramp_start) / (ramp_end - ramp_start)
        units = 1.0 + frac * (max_units - 1)
    bet = round(min_bet * units / min_bet) * min_bet  # snap to min_bet grid
    return max(min_bet, int(bet))
