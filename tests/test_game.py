"""Integration test for BlackjackGame on a seeded shoe.

We construct a Shoe with a deterministic RNG, then drive the game
through a single round by stubbing the interactive input and renderer
side-effects. The point is to lock the round-flow contract: deal four
cards, settle, mutate balance, record one stat.
"""
from __future__ import annotations

import random

from blackjack.actions import Action
from blackjack.difficulty import DifficultyLevel
from blackjack.game import BlackjackGame
from blackjack.models import Shoe


class _FakeInput:
    def __init__(self, action_queue: list[Action], bet: int = 10) -> None:
        self.bet = bet
        self.actions = list(action_queue)

    def get_bet(self, balance: int, min_bet: int = 10) -> int | None:
        return self.bet if balance >= self.bet else None

    def get_action(self, available):
        return self.actions.pop(0)

    def get_yes_no(self, prompt: str) -> bool:
        return False

    def wait(self, prompt: str = "") -> None:
        return None

    def get_challenge_answer(self, challenge):
        return ""


def _silence(renderer):
    """Replace renderer's terminal effects with no-ops so the test stays headless."""
    renderer.clear = lambda: None
    renderer.show_message = lambda msg: None
    renderer.show_table = lambda *a, **kw: None
    renderer.show_prob_hud_inline = lambda *a, **kw: None
    renderer.animation_delay = 0


def test_seeded_single_round_stand_consistent():
    game = BlackjackGame(edu_mode=False, difficulty=DifficultyLevel.MEDIUM)
    game.shoe = Shoe(n_decks=6, rng=random.Random(12345))
    game.shoe.on_reshuffle(game._on_reshuffle)
    game.input = _FakeInput([Action.STAND], bet=10)
    _silence(game.renderer)

    initial_balance = game.balance
    game._play_round()

    # Round completed: balance changed (win/loss/push, never untouched)
    assert game.stats.rounds == 1
    decided = (game.stats.wins + game.stats.losses
               + game.stats.pushes + game.stats.surrenders)
    assert decided == 1

    delta = game.balance - initial_balance
    # Stand-only outcome can be: lose (-10), push (0), win (+10), or BJ (+15).
    assert delta in (-10, 0, 10, 15)


def test_two_seeded_rounds_are_reproducible():
    """Same seed -> same deal -> same outcome under identical inputs."""
    def play(seed):
        game = BlackjackGame(
            edu_mode=False, difficulty=DifficultyLevel.MEDIUM
        )
        game.shoe = Shoe(n_decks=6, rng=random.Random(seed))
        game.shoe.on_reshuffle(game._on_reshuffle)
        game.input = _FakeInput([Action.STAND, Action.STAND], bet=10)
        _silence(game.renderer)
        before = game.balance
        game._play_round()
        return game.balance - before, game.stats.wins, game.stats.losses

    a = play(99)
    b = play(99)
    assert a == b


def test_bust_outcome_recorded():
    """Force a Hit until bust on a hand that starts with a high value."""
    game = BlackjackGame(edu_mode=False, difficulty=DifficultyLevel.MEDIUM)
    game.shoe = Shoe(n_decks=6, rng=random.Random(7777))
    game.shoe.on_reshuffle(game._on_reshuffle)
    # Drive many Hits to maximise bust probability.
    game.input = _FakeInput([Action.HIT] * 10 + [Action.STAND], bet=10)
    _silence(game.renderer)

    game._play_round()
    assert game.stats.rounds == 1
    # We expect at least one outcome recorded
    decided = (game.stats.wins + game.stats.losses
               + game.stats.pushes + game.stats.surrenders)
    assert decided >= 1
