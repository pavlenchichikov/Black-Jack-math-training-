"""Tests for domain models: Card, Rank, Suit, Hand, Shoe."""

import pytest
from blackjack.models import Card, Hand, HandState, Rank, Shoe, Suit


# ── Rank ─────────────────────────────────────────────────────────────────

class TestRank:
    def test_points_number_cards(self):
        assert Rank.TWO.points == 2
        assert Rank.NINE.points == 9

    def test_points_face_cards(self):
        assert Rank.TEN.points == 10
        assert Rank.JACK.points == 10
        assert Rank.QUEEN.points == 10
        assert Rank.KING.points == 10

    def test_points_ace(self):
        assert Rank.ACE.points == 11

    def test_label(self):
        assert Rank.ACE.label == "A"
        assert Rank.JACK.label == "J"
        assert Rank.QUEEN.label == "Q"
        assert Rank.KING.label == "K"
        assert Rank.TWO.label == "2"

    def test_hilo_low(self):
        for r in (Rank.TWO, Rank.THREE, Rank.FOUR, Rank.FIVE, Rank.SIX):
            assert r.hilo_value == +1

    def test_hilo_neutral(self):
        for r in (Rank.SEVEN, Rank.EIGHT, Rank.NINE):
            assert r.hilo_value == 0

    def test_hilo_high(self):
        for r in (Rank.TEN, Rank.JACK, Rank.QUEEN, Rank.KING, Rank.ACE):
            assert r.hilo_value == -1


# ── Suit ─────────────────────────────────────────────────────────────────

class TestSuit:
    def test_is_red(self):
        assert Suit.HEARTS.is_red is True
        assert Suit.DIAMONDS.is_red is True
        assert Suit.CLUBS.is_red is False
        assert Suit.SPADES.is_red is False

    def test_symbols(self):
        assert Suit.HEARTS.symbol == "♥"
        assert Suit.SPADES.symbol == "♠"


# ── Card ─────────────────────────────────────────────────────────────────

class TestCard:
    def test_str(self):
        c = Card(Rank.ACE, Suit.SPADES)
        assert str(c) == "A♠"

    def test_frozen(self):
        c = Card(Rank.TWO, Suit.HEARTS)
        with pytest.raises(AttributeError):
            c.rank = Rank.THREE


# ── Hand ─────────────────────────────────────────────────────────────────

class TestHand:
    def _card(self, rank):
        return Card(rank, Suit.HEARTS)

    def test_value_simple(self):
        h = Hand(cards=[self._card(Rank.TEN), self._card(Rank.SEVEN)])
        assert h.value == 17

    def test_value_soft_ace(self):
        h = Hand(cards=[self._card(Rank.ACE), self._card(Rank.SIX)])
        assert h.value == 17
        assert h.is_soft is True

    def test_value_ace_downgrade(self):
        h = Hand(cards=[self._card(Rank.ACE), self._card(Rank.NINE), self._card(Rank.FIVE)])
        assert h.value == 15  # 11+9+5=25 -> 1+9+5=15
        assert h.is_soft is False

    def test_two_aces(self):
        h = Hand(cards=[self._card(Rank.ACE), self._card(Rank.ACE)])
        assert h.value == 12  # 11+1

    def test_blackjack(self):
        h = Hand(cards=[self._card(Rank.ACE), self._card(Rank.KING)])
        assert h.is_blackjack is True
        assert h.value == 21

    def test_not_blackjack_after_split(self):
        h = Hand(cards=[self._card(Rank.ACE), self._card(Rank.KING)], is_split=True)
        assert h.is_blackjack is False

    def test_bust(self):
        h = Hand(cards=[self._card(Rank.TEN), self._card(Rank.EIGHT), self._card(Rank.FIVE)])
        assert h.is_bust is True
        assert h.value == 23

    def test_can_split(self):
        h = Hand(cards=[self._card(Rank.EIGHT), self._card(Rank.EIGHT)])
        assert h.can_split is True

    def test_cannot_split_different(self):
        h = Hand(cards=[self._card(Rank.EIGHT), self._card(Rank.NINE)])
        assert h.can_split is False

    def test_can_double(self):
        h = Hand(cards=[self._card(Rank.FIVE), self._card(Rank.SIX)])
        assert h.can_double is True

    def test_cannot_double_three_cards(self):
        h = Hand(cards=[self._card(Rank.TWO), self._card(Rank.THREE), self._card(Rank.FOUR)])
        assert h.can_double is False

    def test_add_triggers_bust(self):
        h = Hand(cards=[self._card(Rank.TEN), self._card(Rank.EIGHT)])
        h.add(self._card(Rank.FIVE))
        assert h.state is HandState.BUST

    def test_stand(self):
        h = Hand(cards=[self._card(Rank.TEN), self._card(Rank.EIGHT)])
        h.stand()
        assert h.state is HandState.STAND

    def test_surrender(self):
        h = Hand()
        h.surrender()
        assert h.state is HandState.SURRENDER


# ── Shoe ─────────────────────────────────────────────────────────────────

class TestShoe:
    def test_initial_count(self):
        shoe = Shoe(n_decks=2)
        assert shoe.remaining == 2 * 52

    def test_draw_reduces_count(self):
        shoe = Shoe(n_decks=1)
        shoe.draw()
        assert shoe.remaining == 51

    def test_dealt_cards_tracked(self):
        shoe = Shoe(n_decks=1)
        c = shoe.draw()
        assert c in shoe.dealt_cards

    def test_remaining_by_points(self):
        shoe = Shoe(n_decks=1)
        by_pts = shoe.remaining_by_points()
        # Fresh deck: 4 aces (11 pts), 4 each of 2-9, 16 ten-value (10 pts)
        assert by_pts[11] == 4   # aces
        assert by_pts[10] == 16  # 10, J, Q, K
        assert by_pts[2] == 4

    def test_count_remaining(self):
        shoe = Shoe(n_decks=1)
        assert shoe.count_remaining(Rank.ACE) == 4

    def test_remaining_decks(self):
        shoe = Shoe(n_decks=2)
        assert shoe.remaining_decks == pytest.approx(2.0)

    def test_reshuffle_callback(self):
        called = []
        shoe = Shoe(n_decks=1, reshuffle_at=52)
        shoe.on_reshuffle(lambda: called.append(True))
        # First draw: 52 cards, not < 52, no reshuffle
        shoe.draw()
        assert len(called) == 0
        # Second draw: 51 cards < 52, triggers reshuffle
        shoe.draw()
        assert len(called) == 1

    def test_cards_snapshot_is_copy(self):
        shoe = Shoe(n_decks=1)
        snap = shoe.cards_snapshot
        snap.clear()
        assert shoe.remaining == 52  # original unaffected
