"""Tests for the basic-strategy lookup table."""
from __future__ import annotations

import pytest

from blackjack.actions import Action
from blackjack.basic_strategy import lookup_code, optimal_action
from blackjack.models import Card, Hand, Rank, Suit


def _card(rank: Rank, suit: Suit = Suit.SPADES) -> Card:
    return Card(rank, suit)


def _hand(*ranks: Rank) -> Hand:
    h = Hand()
    for r in ranks:
        h.cards.append(_card(r))
    return h


@pytest.mark.parametrize("player, upcard, expected", [
    # Classic textbook spots
    ((Rank.TEN, Rank.SIX), Rank.TEN, Action.SURRENDER),  # 16 vs 10 surrenders
    ((Rank.TEN, Rank.SIX), Rank.SIX, Action.STAND),      # 16 vs 6 stands
    ((Rank.TEN, Rank.SEVEN), Rank.TEN, Action.STAND),    # 17 vs 10 stands
    ((Rank.SIX, Rank.FIVE), Rank.FIVE, Action.DOUBLE),   # 11 vs 5 doubles
    ((Rank.SIX, Rank.THREE), Rank.SEVEN, Action.HIT),    # 9 vs 7 hits
    ((Rank.SIX, Rank.THREE), Rank.FIVE, Action.DOUBLE),  # 9 vs 5 doubles
])
def test_hard_total_decisions(player, upcard, expected):
    hand = _hand(*player)
    assert optimal_action(hand, _card(upcard)) is expected


def test_16_vs_10_hits_when_surrender_disabled():
    hand = _hand(Rank.TEN, Rank.SIX)
    action = optimal_action(hand, _card(Rank.TEN), allow_surrender=False)
    assert action is Action.HIT


@pytest.mark.parametrize("player, upcard, expected", [
    # A7 (soft 18)
    ((Rank.ACE, Rank.SEVEN), Rank.TWO, Action.STAND),
    ((Rank.ACE, Rank.SEVEN), Rank.NINE, Action.HIT),
    ((Rank.ACE, Rank.SEVEN), Rank.SIX, Action.DOUBLE),
    # A6 (soft 17): double vs 3-6, hit otherwise
    ((Rank.ACE, Rank.SIX), Rank.FIVE, Action.DOUBLE),
    ((Rank.ACE, Rank.SIX), Rank.NINE, Action.HIT),
])
def test_soft_total_decisions(player, upcard, expected):
    hand = _hand(*player)
    assert optimal_action(hand, _card(upcard)) is expected


@pytest.mark.parametrize("pair, upcard, expected", [
    (Rank.ACE, Rank.SIX, Action.SPLIT),           # always split aces
    (Rank.EIGHT, Rank.TEN, Action.SPLIT),         # always split 8s
    (Rank.TEN, Rank.SIX, Action.STAND),           # never split tens
    (Rank.FIVE, Rank.SIX, Action.DOUBLE),         # treat 5,5 as 10
    (Rank.NINE, Rank.SEVEN, Action.STAND),        # 9,9 stands vs 7
    (Rank.NINE, Rank.SIX, Action.SPLIT),          # 9,9 splits vs 6
])
def test_pair_decisions(pair, upcard, expected):
    hand = _hand(pair, pair)
    assert optimal_action(hand, _card(upcard)) is expected


def test_double_not_allowed_falls_back_to_hit():
    hand = _hand(Rank.SIX, Rank.FIVE)  # 11 vs anything wants Double
    action = optimal_action(hand, _card(Rank.SEVEN), allow_double=False)
    assert action is Action.HIT


def test_double_not_allowed_falls_back_to_stand_for_Ds():
    hand = _hand(Rank.ACE, Rank.SEVEN)  # A7 vs 3 is Ds (Double, else Stand)
    code = lookup_code(hand, _card(Rank.THREE))
    assert code == "Ds"
    action = optimal_action(hand, _card(Rank.THREE), allow_double=False)
    assert action is Action.STAND


def test_surrender_falls_back_to_hit():
    hand = _hand(Rank.NINE, Rank.SEVEN)  # 16 vs 10 = R per chart
    code = lookup_code(hand, _card(Rank.TEN))
    assert code == "R"
    action = optimal_action(hand, _card(Rank.TEN), allow_surrender=False)
    assert action is Action.HIT


def test_split_disabled_returns_hit_for_pairs():
    hand = _hand(Rank.EIGHT, Rank.EIGHT)
    action = optimal_action(hand, _card(Rank.TEN), allow_split=False)
    assert action is Action.HIT
