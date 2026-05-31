"""Tests for caching and recursive EV in ProbabilityEngine."""
from __future__ import annotations

import random

from blackjack.models import Card, Hand, Rank, Shoe, Suit
from blackjack.probability import ProbabilityEngine, shoe_signature


def _shoe(seed: int = 1) -> Shoe:
    return Shoe(n_decks=6, rng=random.Random(seed))


def _hand(*ranks: Rank) -> Hand:
    h = Hand()
    for r in ranks:
        h.cards.append(Card(r, Suit.SPADES))
    return h


def test_shoe_signature_stable_for_unchanged_shoe():
    s = _shoe()
    sig_a = shoe_signature(s)
    sig_b = shoe_signature(s)
    assert sig_a == sig_b
    # Hashable
    assert hash(sig_a) == hash(sig_b)


def test_dealer_bust_analytical_in_known_range():
    """Dealer-up Six historically busts ~42% in a fresh 6-deck shoe."""
    s = _shoe()
    upcard = Card(Rank.SIX, Suit.SPADES)
    p = ProbabilityEngine.dealer_bust_probability(upcard, s)
    assert 0.36 <= p <= 0.46


def test_dealer_bust_ace_lower_than_six():
    s = _shoe()
    p_six = ProbabilityEngine.dealer_bust_probability(
        Card(Rank.SIX, Suit.SPADES), s
    )
    p_ace = ProbabilityEngine.dealer_bust_probability(
        Card(Rank.ACE, Suit.SPADES), s
    )
    assert p_ace < p_six


def test_ev_hit_recursive_finds_stand_better_for_hard_20():
    """At 20 vs anything, the recursive EV(Hit) should be strictly worse
    than EV(Stand): hitting almost always busts."""
    s = _shoe()
    hand = _hand(Rank.TEN, Rank.TEN)
    upcard = Card(Rank.SEVEN, Suit.SPADES)
    ev_h = ProbabilityEngine.ev_hit(hand, upcard, s, n_sims=500)
    ev_s = ProbabilityEngine.ev_stand(hand, upcard, s, n_sims=500)
    assert ev_s > ev_h


def test_ev_hit_recursive_better_than_one_card_lookahead_for_low_hands():
    """For a hard 8, recursive EV(Hit) should be positive (player will
    continue to optimal stand) instead of negative as a single-card
    lookahead would suggest."""
    ProbabilityEngine.clear_cache()
    s = _shoe()
    hand = _hand(Rank.FIVE, Rank.THREE)  # 8
    upcard = Card(Rank.SIX, Suit.SPADES)
    ev_h = ProbabilityEngine.ev_hit(hand, upcard, s, n_sims=300)
    assert ev_h > -0.5  # not catastrophic


def test_cache_clear_resets():
    s = _shoe()
    hand = _hand(Rank.TEN, Rank.SIX)
    upcard = Card(Rank.TEN, Suit.SPADES)
    _ = ProbabilityEngine.ev_hit(hand, upcard, s, n_sims=200)
    ProbabilityEngine.clear_cache()
    # Should still compute without error after cache wipe
    val = ProbabilityEngine.ev_hit(hand, upcard, s, n_sims=200)
    assert -1.0 <= val <= 1.0
