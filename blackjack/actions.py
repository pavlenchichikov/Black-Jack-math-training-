"""Player actions and round outcomes."""

from enum import Enum, auto


class Action(Enum):
    HIT = "h"; STAND = "s"; DOUBLE = "d"; SPLIT = "p"; SURRENDER = "r"

    @property
    def display(self) -> str:
        return {"h": "Hit", "s": "Stand", "d": "Double",
                "p": "Split", "r": "Surrender"}[self.value]


class RoundOutcome(Enum):
    WIN = auto(); LOSE = auto(); PUSH = auto()
    BLACKJACK = auto(); SURRENDER = auto()
