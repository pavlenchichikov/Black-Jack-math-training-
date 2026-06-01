"""Basic strategy lookup for multi-deck S17 with DAS.

The chart is the standard published basic-strategy matrix for 6 decks,
dealer stands on soft 17, double after split allowed, late surrender
allowed. Returned codes:

    H  = Hit
    S  = Stand
    D  = Double if allowed, else Hit
    Ds = Double if allowed, else Stand
    P  = Split
    R  = Surrender if allowed, else Hit
    Rs = Surrender if allowed, else Stand

A single dispatch function `optimal_action` resolves the code into a
concrete `Action` enum value given table caveats (no double after split,
no surrender on split hands, etc).
"""
from __future__ import annotations

from .actions import Action
from .models import Card, Hand, Rank

# Dealer upcard buckets used as columns. Index 0..9 = upcard 2..10, 10 = Ace.
_UPCARD_COLS = (2, 3, 4, 5, 6, 7, 8, 9, 10, 11)


def _upcard_index(upcard: Card) -> int:
    pts = upcard.rank.points
    return 9 if pts == 11 and upcard.rank is Rank.ACE else pts - 2


# Hard totals 5..21 vs dealer 2..A. Rows indexed by player_total - 5.
HARD_CHART: dict[int, tuple[str, ...]] = {
    5:  ("H", "H", "H", "H", "H", "H", "H", "H", "H", "H"),
    6:  ("H", "H", "H", "H", "H", "H", "H", "H", "H", "H"),
    7:  ("H", "H", "H", "H", "H", "H", "H", "H", "H", "H"),
    8:  ("H", "H", "H", "H", "H", "H", "H", "H", "H", "H"),
    9:  ("H", "D", "D", "D", "D", "H", "H", "H", "H", "H"),
    10: ("D", "D", "D", "D", "D", "D", "D", "D", "H", "H"),
    11: ("D", "D", "D", "D", "D", "D", "D", "D", "D", "H"),
    12: ("H", "H", "S", "S", "S", "H", "H", "H", "H", "H"),
    13: ("S", "S", "S", "S", "S", "H", "H", "H", "H", "H"),
    14: ("S", "S", "S", "S", "S", "H", "H", "H", "H", "H"),
    15: ("S", "S", "S", "S", "S", "H", "H", "H", "R", "H"),
    16: ("S", "S", "S", "S", "S", "H", "H", "R", "R", "R"),
    17: ("S", "S", "S", "S", "S", "S", "S", "S", "S", "S"),
    18: ("S", "S", "S", "S", "S", "S", "S", "S", "S", "S"),
    19: ("S", "S", "S", "S", "S", "S", "S", "S", "S", "S"),
    20: ("S", "S", "S", "S", "S", "S", "S", "S", "S", "S"),
    21: ("S", "S", "S", "S", "S", "S", "S", "S", "S", "S"),
}

# Soft totals A2..A9 (player values 13..20) vs dealer 2..A.
SOFT_CHART: dict[int, tuple[str, ...]] = {
    13: ("H", "H", "H", "D", "D", "H", "H", "H", "H", "H"),   # A2
    14: ("H", "H", "H", "D", "D", "H", "H", "H", "H", "H"),   # A3
    15: ("H", "H", "D", "D", "D", "H", "H", "H", "H", "H"),   # A4
    16: ("H", "H", "D", "D", "D", "H", "H", "H", "H", "H"),   # A5
    17: ("H", "D", "D", "D", "D", "H", "H", "H", "H", "H"),   # A6
    18: ("S", "Ds", "Ds", "Ds", "Ds", "S", "S", "H", "H", "H"),  # A7
    19: ("S", "S", "S", "S", "S", "S", "S", "S", "S", "S"),   # A8
    20: ("S", "S", "S", "S", "S", "S", "S", "S", "S", "S"),   # A9
}

# Pairs vs dealer 2..A. Key = pair card points (Ace stored as 11).
PAIR_CHART: dict[int, tuple[str, ...]] = {
    11: ("P", "P", "P", "P", "P", "P", "P", "P", "P", "P"),   # A,A
    10: ("S", "S", "S", "S", "S", "S", "S", "S", "S", "S"),   # T,T
    9:  ("P", "P", "P", "P", "P", "S", "P", "P", "S", "S"),
    8:  ("P", "P", "P", "P", "P", "P", "P", "P", "P", "P"),
    7:  ("P", "P", "P", "P", "P", "P", "H", "H", "H", "H"),
    6:  ("P", "P", "P", "P", "P", "H", "H", "H", "H", "H"),
    5:  ("D", "D", "D", "D", "D", "D", "D", "D", "H", "H"),   # treat as 10
    4:  ("H", "H", "H", "P", "P", "H", "H", "H", "H", "H"),
    3:  ("P", "P", "P", "P", "P", "P", "H", "H", "H", "H"),
    2:  ("P", "P", "P", "P", "P", "P", "H", "H", "H", "H"),
}


def _resolve(code: str, *, allow_double: bool, allow_split: bool,
             allow_surrender: bool) -> Action:
    if code == "H":
        return Action.HIT
    if code == "S":
        return Action.STAND
    if code == "D":
        return Action.DOUBLE if allow_double else Action.HIT
    if code == "Ds":
        return Action.DOUBLE if allow_double else Action.STAND
    if code == "P":
        return Action.SPLIT if allow_split else Action.HIT
    if code == "R":
        return Action.SURRENDER if allow_surrender else Action.HIT
    if code == "Rs":
        return Action.SURRENDER if allow_surrender else Action.STAND
    raise ValueError(f"Unknown strategy code: {code!r}")


def lookup_code(hand: Hand, dealer_upcard: Card) -> str:
    """Return the raw strategy code (H/S/D/Ds/P/R/Rs) for this situation."""
    col = _upcard_index(dealer_upcard)

    if hand.can_split:
        pair_pts = hand.cards[0].rank.points
        if hand.cards[0].rank is Rank.ACE:
            pair_pts = 11
        chart = PAIR_CHART.get(pair_pts)
        if chart:
            return chart[col]

    if hand.is_soft and 13 <= hand.value <= 20:
        return SOFT_CHART[hand.value][col]

    total = hand.value
    if total < 5:
        return "H"
    if total > 21:
        return "S"  # bust already
    return HARD_CHART[total][col]


def optimal_action(
    hand: Hand,
    dealer_upcard: Card,
    *,
    allow_double: bool = True,
    allow_split: bool = True,
    allow_surrender: bool = True,
) -> Action:
    """Return the basic-strategy optimal Action for this hand vs upcard."""
    code = lookup_code(hand, dealer_upcard)
    return _resolve(
        code,
        allow_double=allow_double,
        allow_split=allow_split,
        allow_surrender=allow_surrender,
    )
