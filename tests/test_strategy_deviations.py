"""Tests for Hi-Lo Index Plays and bet-sizing helper."""
from __future__ import annotations

import pytest

from blackjack.actions import Action
from blackjack.models import Card, Hand, Rank, Suit
from blackjack.strategy_deviations import (
    INSURANCE_THRESHOLD,
    index_decision,
    recommend_bet,
    should_take_insurance,
)


def _card(rank: Rank) -> Card:
    return Card(rank, Suit.SPADES)


def _hand(*ranks: Rank) -> Hand:
    h = Hand()
    for r in ranks:
        h.cards.append(_card(r))
    return h


def test_16_vs_10_stands_when_tc_at_threshold():
    hand = _hand(Rank.NINE, Rank.SEVEN)
    assert index_decision(hand, _card(Rank.TEN), 0.0) is Action.STAND


def test_16_vs_10_no_override_below_threshold():
    hand = _hand(Rank.NINE, Rank.SEVEN)
    assert index_decision(hand, _card(Rank.TEN), -0.5) is None


def test_12_vs_3_stands_at_high_tc():
    hand = _hand(Rank.NINE, Rank.THREE)
    assert index_decision(hand, _card(Rank.THREE), 2.0) is Action.STAND


def test_13_vs_2_hits_at_low_tc():
    hand = _hand(Rank.NINE, Rank.FOUR)
    assert index_decision(hand, _card(Rank.TWO), -1.0) is Action.HIT


def test_14_vs_10_surrender_at_threshold():
    # 9 + 5 = 14, dealer 10. Fab-4 surrenders at TC >= +3.
    hand = _hand(Rank.NINE, Rank.FIVE)
    assert index_decision(hand, _card(Rank.TEN), 3.0) is Action.SURRENDER


def test_14_vs_10_no_surrender_below_threshold():
    hand = _hand(Rank.NINE, Rank.FIVE)
    assert index_decision(hand, _card(Rank.TEN), 2.5) is None


def test_index_does_not_fire_for_soft_hands():
    hand = _hand(Rank.ACE, Rank.FIVE)  # soft 16
    assert index_decision(hand, _card(Rank.TEN), 5.0) is None


@pytest.mark.parametrize("tc, expected", [
    (-1.0, False),
    (0.0, False),
    (2.9, False),
    (3.0, True),
    (5.0, True),
])
def test_insurance_threshold(tc, expected):
    assert should_take_insurance(tc) is expected


def test_insurance_constant_matches_helper():
    assert should_take_insurance(INSURANCE_THRESHOLD) is True
    assert should_take_insurance(INSURANCE_THRESHOLD - 0.01) is False


@pytest.mark.parametrize("tc, expected_units", [
    (-2.0, 1),   # well below ramp_start, min bet
    (0.5, 1),    # below ramp_start
    (1.0, 1),    # at ramp_start
    (3.0, 6),    # middle of ramp: 1 + 0.5*(12-1) = 6.5 -> snapped to 6
    (5.0, 12),   # at ramp_end, max
    (8.0, 12),   # above ramp_end, capped
])
def test_recommend_bet(tc, expected_units):
    min_bet = 10
    bet = recommend_bet(tc, min_bet)
    # snap-to-min_bet rounding can shift by one unit, allow ~1 tolerance
    assert abs(bet - expected_units * min_bet) <= min_bet


def test_recommend_bet_respects_min():
    assert recommend_bet(-10.0, 25) == 25
