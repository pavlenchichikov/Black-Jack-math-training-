"""Domain models: Card, Rank, Suit, Hand, Shoe."""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from enum import Enum, auto


# ── Suit ──────────────────────────────────────────────────────────────────────

class Suit(Enum):
    HEARTS = auto(); DIAMONDS = auto(); CLUBS = auto(); SPADES = auto()

    @property
    def symbol(self) -> str:
        return {Suit.HEARTS: "\u2665", Suit.DIAMONDS: "\u2666",
                Suit.CLUBS: "\u2663", Suit.SPADES: "\u2660"}[self]

    @property
    def is_red(self) -> bool:
        return self in (Suit.HEARTS, Suit.DIAMONDS)


# ── Rank ──────────────────────────────────────────────────────────────────────

class Rank(Enum):
    TWO = 2; THREE = 3; FOUR = 4; FIVE = 5; SIX = 6
    SEVEN = 7; EIGHT = 8; NINE = 9; TEN = 10
    JACK = 11; QUEEN = 12; KING = 13; ACE = 14

    @property
    def label(self) -> str:
        return {Rank.JACK: "J", Rank.QUEEN: "Q", Rank.KING: "K",
                Rank.ACE: "A"}.get(self, str(self.value))

    @property
    def points(self) -> int:
        if self is Rank.ACE:
            return 11
        return min(self.value, 10)

    @property
    def hilo_value(self) -> int:
        """Hi-Lo card counting: 2-6 = +1, 7-9 = 0, 10-A = -1."""
        if self.value <= 6:
            return +1
        if self.value <= 9:
            return 0
        return -1


# ── Card ──────────────────────────────────────────────────────────────────────

@dataclass(frozen=True, slots=True)
class Card:
    rank: Rank
    suit: Suit

    @property
    def points(self) -> int:
        return self.rank.points

    def __str__(self) -> str:
        return f"{self.rank.label}{self.suit.symbol}"


# ── Shoe ──────────────────────────────────────────────────────────────────────

class Shoe:
    """Multi-deck shoe with dealt-card tracking."""

    def __init__(self, n_decks: int = 6, reshuffle_at: int = 52):
        self._n_decks = n_decks
        self._reshuffle_at = reshuffle_at
        self._cards: list[Card] = []
        self._dealt: list[Card] = []
        self._on_reshuffle: list[callable] = []
        self.shuffle()

    def shuffle(self) -> None:
        self._cards = [
            Card(rank, suit)
            for _ in range(self._n_decks)
            for suit in Suit
            for rank in Rank
        ]
        random.shuffle(self._cards)
        self._dealt.clear()

    def draw(self) -> Card:
        if len(self._cards) < self._reshuffle_at:
            for cb in self._on_reshuffle:
                cb()
            self.shuffle()
        card = self._cards.pop()
        self._dealt.append(card)
        return card

    def on_reshuffle(self, callback: callable) -> None:
        self._on_reshuffle.append(callback)

    @property
    def n_decks(self) -> int:
        return self._n_decks

    @property
    def remaining(self) -> int:
        return len(self._cards)

    @property
    def remaining_decks(self) -> float:
        return self.remaining / 52

    @property
    def dealt_cards(self) -> list[Card]:
        return self._dealt.copy()

    def count_remaining(self, rank: Rank) -> int:
        return sum(1 for c in self._cards if c.rank is rank)

    def remaining_by_points(self) -> dict[int, int]:
        counts: dict[int, int] = {}
        for c in self._cards:
            p = c.rank.points
            counts[p] = counts.get(p, 0) + 1
        return counts

    @property
    def cards_snapshot(self) -> list[Card]:
        """Snapshot of remaining cards (for simulations)."""
        return list(self._cards)


# ── HandState ─────────────────────────────────────────────────────────────────

class HandState(Enum):
    ACTIVE = auto(); STAND = auto(); BUST = auto()
    BLACKJACK = auto(); SURRENDER = auto()


# ── Hand ──────────────────────────────────────────────────────────────────────

@dataclass
class Hand:
    cards: list[Card] = field(default_factory=list)
    bet: int = 0
    state: HandState = HandState.ACTIVE
    is_split: bool = False
    is_doubled: bool = False

    @property
    def value(self) -> int:
        total = sum(c.points for c in self.cards)
        aces = sum(1 for c in self.cards if c.rank is Rank.ACE)
        while total > 21 and aces:
            total -= 10
            aces -= 1
        return total

    @property
    def is_soft(self) -> bool:
        total = sum(c.points for c in self.cards)
        aces = sum(1 for c in self.cards if c.rank is Rank.ACE)
        while total > 21 and aces:
            total -= 10
            aces -= 1
        return aces > 0

    @property
    def is_bust(self) -> bool:
        return self.value > 21

    @property
    def is_blackjack(self) -> bool:
        return len(self.cards) == 2 and self.value == 21 and not self.is_split

    @property
    def can_split(self) -> bool:
        return (len(self.cards) == 2
                and self.cards[0].rank.points == self.cards[1].rank.points)

    @property
    def can_double(self) -> bool:
        return len(self.cards) == 2

    def add(self, card: Card) -> None:
        self.cards.append(card)
        if self.is_bust:
            self.state = HandState.BUST
        elif self.is_blackjack:
            self.state = HandState.BLACKJACK

    def stand(self) -> None:
        self.state = HandState.STAND

    def surrender(self) -> None:
        self.state = HandState.SURRENDER
