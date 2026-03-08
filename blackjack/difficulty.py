"""Difficulty levels and their configuration."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto


class DifficultyLevel(Enum):
    EASY = auto()
    MEDIUM = auto()
    HARD = auto()

    @property
    def label(self) -> str:
        return {
            DifficultyLevel.EASY: "Легкий",
            DifficultyLevel.MEDIUM: "Средний",
            DifficultyLevel.HARD: "Сложный",
        }[self]

    @property
    def label_en(self) -> str:
        return self.name


@dataclass(frozen=True)
class DifficultyConfig:
    level: DifficultyLevel
    starting_balance: int
    n_decks: int
    dealer_hits_soft17: bool
    blackjack_payout: float       # 1.5 = 3:2, 1.2 = 6:5
    min_bet: int
    # Edu settings
    challenge_chance: float       # probability of a challenge per round
    tolerance_mult: float         # multiplier for answer tolerance
    show_prob_hud: bool           # show P(bust), cards to 21 during play
    show_optimal_hint: bool       # show "optimal action" hint after decision
    allowed_challenge_levels: tuple[int, ...] = (1, 2, 3)  # Difficulty.value

    @property
    def description(self) -> str:
        lines = [
            f"Баланс: ${self.starting_balance}",
            f"Колоды: {self.n_decks}",
            f"Дилер soft 17: {'Hit' if self.dealer_hits_soft17 else 'Stand'}",
            f"BJ выплата: {'6:5' if self.blackjack_payout < 1.3 else '3:2'}",
            f"Мин. ставка: ${self.min_bet}",
        ]
        return " | ".join(lines)


# ── Presets ───────────────────────────────────────────────────────────────────

DIFFICULTY_PRESETS: dict[DifficultyLevel, DifficultyConfig] = {
    DifficultyLevel.EASY: DifficultyConfig(
        level=DifficultyLevel.EASY,
        starting_balance=2000,
        n_decks=4,
        dealer_hits_soft17=False,
        blackjack_payout=1.5,
        min_bet=10,
        challenge_chance=0.4,
        tolerance_mult=2.0,
        show_prob_hud=True,
        show_optimal_hint=True,
        allowed_challenge_levels=(1, 2),     # Easy + Medium only
    ),
    DifficultyLevel.MEDIUM: DifficultyConfig(
        level=DifficultyLevel.MEDIUM,
        starting_balance=1000,
        n_decks=6,
        dealer_hits_soft17=False,
        blackjack_payout=1.5,
        min_bet=10,
        challenge_chance=0.6,
        tolerance_mult=1.0,
        show_prob_hud=True,
        show_optimal_hint=False,
        allowed_challenge_levels=(1, 2, 3),  # All
    ),
    DifficultyLevel.HARD: DifficultyConfig(
        level=DifficultyLevel.HARD,
        starting_balance=500,
        n_decks=8,
        dealer_hits_soft17=True,
        blackjack_payout=1.2,                # 6:5
        min_bet=25,
        challenge_chance=0.8,
        tolerance_mult=0.5,
        show_prob_hud=False,
        show_optimal_hint=False,
        allowed_challenge_levels=(2, 3),     # Medium + Hard only
    ),
}
