"""Tests for Hi-Lo card counter."""

from blackjack.models import Card, Rank, Suit
from blackjack.counter import CardCounter


def _card(rank, suit=Suit.HEARTS):
    return Card(rank, suit)


class TestCardCounter:
    def test_initial_state(self):
        c = CardCounter()
        assert c.running_count == 0
        assert c.cards_seen == 0

    def test_low_card_increments(self):
        c = CardCounter()
        c.update(_card(Rank.TWO))
        assert c.running_count == 1
        assert c.cards_seen == 1

    def test_high_card_decrements(self):
        c = CardCounter()
        c.update(_card(Rank.ACE))
        assert c.running_count == -1

    def test_neutral_card(self):
        c = CardCounter()
        c.update(_card(Rank.SEVEN))
        assert c.running_count == 0
        assert c.cards_seen == 1

    def test_sequence(self):
        c = CardCounter()
        # +1, +1, 0, -1, -1 = 0
        for r in (Rank.TWO, Rank.FIVE, Rank.EIGHT, Rank.TEN, Rank.ACE):
            c.update(_card(r))
        assert c.running_count == 0
        assert c.cards_seen == 5

    def test_true_count(self):
        c = CardCounter()
        # RC = +4
        for _ in range(4):
            c.update(_card(Rank.TWO))
        # 2 decks remaining -> TC = 4/2 = 2.0
        assert c.true_count(2.0) == 2.0

    def test_true_count_small_decks(self):
        c = CardCounter()
        c.update(_card(Rank.TWO))
        # remaining_decks < 0.5 is clamped to 0.5
        tc = c.true_count(0.1)
        assert tc == 1 / 0.5  # 2.0

    def test_reset(self):
        c = CardCounter()
        c.update(_card(Rank.TWO))
        c.update(_card(Rank.ACE))
        c.reset()
        assert c.running_count == 0
        assert c.cards_seen == 0
