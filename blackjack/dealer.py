"""Dealer strategy."""

from __future__ import annotations

from .models import Hand


class StandardDealer:
    """Configurable dealer: stand or hit on soft 17."""

    def __init__(self, hit_soft_17: bool = False) -> None:
        self._hit_soft_17 = hit_soft_17

    def should_hit(self, hand: Hand) -> bool:
        if hand.value < 17:
            return True
        if hand.value == 17 and hand.is_soft and self._hit_soft_17:
            return True
        return False
