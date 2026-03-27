"""Tests for probability engine."""

import pytest
from blackjack.models import Card, Hand, Rank, Shoe, Suit


# Import after models so we can construct test objects
from blackjack.probability import ProbabilityEngine as PE


def _card(rank, suit=Suit.HEARTS):
    return Card(rank, suit)


def _hand(*ranks, bet=0):
    return Hand(cards=[_card(r) for r in ranks], bet=bet)


class TestBustProbability:
    def test_21_always_busts(self):
        shoe = Shoe(n_decks=1)
        hand = _hand(Rank.TEN, Rank.ACE)  # 21
        assert PE.bust_probability(hand, shoe) == 1.0

    def test_over_21_always_busts(self):
        shoe = Shoe(n_decks=1)
        hand = Hand(cards=[_card(Rank.TEN), _card(Rank.EIGHT), _card(Rank.FIVE)])
        assert PE.bust_probability(hand, shoe) == 1.0

    def test_low_hand_never_busts(self):
        shoe = Shoe(n_decks=1)
        hand = _hand(Rank.TWO, Rank.THREE)  # value=5, max_safe=16, any card is safe
        assert PE.bust_probability(hand, shoe) == 0.0

    def test_empty_shoe(self):
        shoe = Shoe(n_decks=1)
        # Draw all cards
        while shoe.remaining > 0:
            try:
                shoe._cards.pop()
            except IndexError:
                break
        hand = _hand(Rank.TEN, Rank.FIVE)
        assert PE.bust_probability(hand, shoe) == 0.0

    def test_bust_prob_in_range(self):
        shoe = Shoe(n_decks=6)
        hand = _hand(Rank.TEN, Rank.SIX)  # 16 — risky
        p = PE.bust_probability(hand, shoe)
        assert 0.0 < p < 1.0


class TestCardsToTarget:
    def test_need_ace_for_21(self):
        shoe = Shoe(n_decks=1)
        hand = _hand(Rank.TEN)  # value=10, need 11 -> ace
        count, labels = PE.cards_to_target(hand, 21, shoe)
        assert count == 4  # 4 aces in fresh deck
        assert any("A" in lbl for lbl in labels)

    def test_impossible_target(self):
        shoe = Shoe(n_decks=1)
        hand = _hand(Rank.TEN, Rank.ACE)  # value=21, need 0
        count, labels = PE.cards_to_target(hand, 21, shoe)
        assert count == 0

    def test_need_ten_value(self):
        shoe = Shoe(n_decks=1)
        hand = _hand(Rank.ACE)  # value=11, need 10
        count, labels = PE.cards_to_target(hand, 21, shoe)
        assert count == 16  # 10,J,Q,K × 4 suits


class TestDealerBust:
    def test_returns_float_in_range(self):
        shoe = Shoe(n_decks=6)
        upcard = _card(Rank.SIX)
        p = PE.dealer_bust_probability(upcard, shoe, n_sims=500)
        assert 0.0 <= p <= 1.0

    def test_small_shoe_returns_zero(self):
        shoe = Shoe(n_decks=1)
        shoe._cards = shoe._cards[:3]  # only 3 cards left
        upcard = _card(Rank.SIX)
        assert PE.dealer_bust_probability(upcard, shoe) == 0.0

    def test_six_busts_more_than_ace(self):
        shoe = Shoe(n_decks=6)
        p_six = PE.dealer_bust_probability(_card(Rank.SIX), shoe, n_sims=2000)
        p_ace = PE.dealer_bust_probability(_card(Rank.ACE), shoe, n_sims=2000)
        # Dealer with 6 should bust more often than with ace (statistically)
        assert p_six > p_ace


class TestEVStand:
    def test_bust_hand_returns_minus_one(self):
        shoe = Shoe(n_decks=6)
        hand = Hand(cards=[_card(Rank.TEN), _card(Rank.EIGHT), _card(Rank.FIVE)])
        ev = PE.ev_stand(hand, _card(Rank.SIX), shoe)
        assert ev == -1.0

    def test_small_shoe_returns_zero(self):
        shoe = Shoe(n_decks=1)
        shoe._cards = shoe._cards[:2]
        hand = _hand(Rank.TEN, Rank.EIGHT)
        ev = PE.ev_stand(hand, _card(Rank.SIX), shoe)
        assert ev == 0.0

    def test_ev_in_range(self):
        shoe = Shoe(n_decks=6)
        hand = _hand(Rank.TEN, Rank.EIGHT)
        ev = PE.ev_stand(hand, _card(Rank.SIX), shoe, n_sims=500)
        assert -1.0 <= ev <= 1.0


class TestEVHit:
    def test_small_shoe_returns_zero(self):
        shoe = Shoe(n_decks=1)
        shoe._cards = shoe._cards[:2]
        hand = _hand(Rank.TEN, Rank.SIX)
        ev = PE.ev_hit(hand, _card(Rank.SEVEN), shoe)
        assert ev == 0.0

    def test_ev_in_range(self):
        shoe = Shoe(n_decks=6)
        hand = _hand(Rank.TEN, Rank.SIX)
        ev = PE.ev_hit(hand, _card(Rank.SEVEN), shoe, n_sims=200)
        assert -1.5 <= ev <= 1.5
