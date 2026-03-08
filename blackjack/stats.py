"""Game statistics tracking."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from .actions import RoundOutcome
from .renderer import Ansi

if TYPE_CHECKING:
    from .trainer import MathTrainer


@dataclass
class Stats:
    rounds: int = 0
    wins: int = 0
    losses: int = 0
    pushes: int = 0
    blackjacks: int = 0
    surrenders: int = 0
    initial_balance: int = 1000

    def record(self, outcome: RoundOutcome) -> None:
        match outcome:
            case RoundOutcome.WIN:       self.wins += 1
            case RoundOutcome.LOSE:      self.losses += 1
            case RoundOutcome.PUSH:      self.pushes += 1
            case RoundOutcome.BLACKJACK: self.wins += 1; self.blackjacks += 1
            case RoundOutcome.SURRENDER: self.surrenders += 1

    @property
    def total_decided(self) -> int:
        return self.wins + self.losses + self.pushes + self.surrenders

    @property
    def win_rate(self) -> float:
        return (self.wins / self.total_decided * 100) if self.total_decided else 0.0

    def display(self, balance: int, trainer: MathTrainer | None = None) -> str:
        profit = balance - self.initial_balance
        clr = Ansi.GREEN if profit >= 0 else Ansi.RED

        s = f"""
  {Ansi.BOLD}{'=' * 36}
   СТАТИСТИКА ИГРЫ
  {'=' * 36}{Ansi.RST}
  Раундов:       {self.rounds}
  Побед:         {Ansi.GREEN}{self.wins}{Ansi.RST}
  Поражений:     {Ansi.RED}{self.losses}{Ansi.RST}
  Push:          {Ansi.YELLOW}{self.pushes}{Ansi.RST}
  Surrender:     {self.surrenders}
  Blackjack:     {self.blackjacks}
  Win Rate:      {self.win_rate:.1f}%
  Баланс:        ${balance}
  Профит:        {clr}{'+' if profit >= 0 else ''}{profit}{Ansi.RST}"""

        if trainer and trainer.total_asked > 0:
            s += f"""

  {Ansi.BOLD}{'=' * 36}
   МАТЕМАТИКА
  {'=' * 36}{Ansi.RST}
  Задач решено:  {trainer.total_asked}
  Правильных:    {Ansi.GREEN}{trainer.total_correct}{Ansi.RST} ({trainer.accuracy:.0f}%)
  Серия (макс):  {trainer.max_streak}
  Итого очков:   {Ansi.MAGENTA}{trainer.score}{Ansi.RST}"""

        s += f"\n  {Ansi.BOLD}{'=' * 36}{Ansi.RST}"
        return s
