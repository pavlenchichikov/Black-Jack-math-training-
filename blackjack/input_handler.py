"""Terminal input handler for player actions, bets, and challenge answers."""

from __future__ import annotations

from .actions import Action
from .renderer import Ansi
from .trainer import Challenge


class TerminalInput:

    _ACTION_KEYS: dict[str, Action] = {
        "h": Action.HIT, "1": Action.HIT, "н": Action.HIT,
        "s": Action.STAND, "2": Action.STAND, "с": Action.STAND,
        "d": Action.DOUBLE, "3": Action.DOUBLE, "д": Action.DOUBLE,
        "p": Action.SPLIT, "4": Action.SPLIT, "п": Action.SPLIT,
        "r": Action.SURRENDER, "5": Action.SURRENDER, "к": Action.SURRENDER,
    }

    def get_bet(self, balance: int, min_bet: int = 10) -> int | None:
        while True:
            print(f"\n  {Ansi.CYAN}Баланс: ${balance}{Ansi.RST}")
            raw = input(
                f"  {Ansi.BOLD}Ставка ({min_bet}-{balance}, q=выход): {Ansi.RST}"
            ).strip()
            if raw.lower() in ("q", "quit", "exit", "й"):
                return None
            try:
                bet = int(raw)
            except ValueError:
                print(f"  {Ansi.RED}Введи число!{Ansi.RST}")
                continue
            if min_bet <= bet <= balance:
                return bet
            print(f"  {Ansi.RED}Введи от {min_bet} до {balance}{Ansi.RST}")

    def get_action(self, available: list[Action]) -> Action:
        keys_map = {k: v for k, v in self._ACTION_KEYS.items() if v in available}
        hints = []
        for act in available:
            label = act.display
            key = act.value.upper()
            hints.append(f"({Ansi.GREEN}{key}{Ansi.RST}){label[1:]}")

        while True:
            raw = input(f"\n  {' | '.join(hints)}: ").strip().lower()
            if raw in keys_map:
                return keys_map[raw]

    def get_yes_no(self, prompt: str) -> bool:
        raw = input(f"\n  {Ansi.YELLOW}{prompt} (y/n): {Ansi.RST}").strip().lower()
        return raw in ("y", "д", "да", "yes")

    def wait(self, prompt: str = "Enter для продолжения...") -> None:
        input(f"\n  {Ansi.DIM}{prompt}{Ansi.RST}")

    def get_challenge_answer(self, challenge: Challenge) -> str:
        print(f"\n  {Ansi.MAGENTA}{Ansi.BOLD}--- ЗАДАЧА "
              f"({challenge.difficulty.name}, +{challenge.points} очков) ---{Ansi.RST}")
        print(f"  {Ansi.MAGENTA}{challenge.question}{Ansi.RST}")
        if challenge.choices:
            for i, ch in enumerate(challenge.choices, 1):
                print(f"    {i}. {ch}")
        unit_hint = f" ({challenge.unit})" if challenge.unit else ""
        return input(f"  {Ansi.BOLD}Ответ{unit_hint}: {Ansi.RST}").strip()
