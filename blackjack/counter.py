"""Hi-Lo card counting tracker."""

from __future__ import annotations

from .models import Card


class CardCounter:

    def __init__(self) -> None:
        self._running_count: int = 0
        self._cards_seen: int = 0

    def update(self, card: Card) -> None:
        self._running_count += card.rank.hilo_value
        self._cards_seen += 1

    def reset(self) -> None:
        self._running_count = 0
        self._cards_seen = 0

    @property
    def running_count(self) -> int:
        return self._running_count

    def true_count(self, remaining_decks: float) -> float:
        if remaining_decks < 0.5:
            remaining_decks = 0.5
        return self._running_count / remaining_decks

    @property
    def cards_seen(self) -> int:
        return self._cards_seen
