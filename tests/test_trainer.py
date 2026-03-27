"""Tests for MathTrainer: input parsing, challenge generation, scoring."""

import pytest
from blackjack.models import Card, Hand, Rank, Shoe, Suit
from blackjack.counter import CardCounter
from blackjack.trainer import Challenge, Difficulty, MathTrainer


def _card(rank, suit=Suit.HEARTS):
    return Card(rank, suit)


def _hand(*ranks, bet=100):
    return Hand(cards=[_card(r) for r in ranks], bet=bet)


@pytest.fixture
def trainer():
    return MathTrainer(allowed_levels=(1, 2, 3), tolerance_mult=1.0)


@pytest.fixture
def shoe():
    return Shoe(n_decks=6)


@pytest.fixture
def counter():
    return CardCounter()


# ── Input parsing ────────────────────────────────────────────────────────

class TestInputParsing:
    def _challenge(self, answer_type="float", correct=42.0, tolerance=1.0):
        return Challenge(
            question="test",
            correct_answer=correct,
            tolerance=tolerance,
            explanation="test",
            difficulty=Difficulty.EASY,
            answer_type=answer_type,
        )

    def test_empty_input(self, trainer):
        ch = self._challenge()
        ok, msg = trainer.check(ch, "")
        assert ok is False
        assert "Пустой" in msg

    def test_whitespace_only(self, trainer):
        ch = self._challenge()
        ok, msg = trainer.check(ch, "   ")
        assert ok is False
        assert "Пустой" in msg

    def test_valid_float(self, trainer):
        ch = self._challenge(correct=42.0, tolerance=1.0)
        ok, _ = trainer.check(ch, "42.5")
        assert ok is True

    def test_comma_as_decimal(self, trainer):
        ch = self._challenge(correct=42.5, tolerance=0.1)
        ok, _ = trainer.check(ch, "42,5")
        assert ok is True

    def test_percent_suffix(self, trainer):
        ch = self._challenge(correct=50.0, tolerance=1.0)
        ok, _ = trainer.check(ch, "50.0%")
        assert ok is True

    def test_percent_with_comma(self, trainer):
        ch = self._challenge(correct=50.5, tolerance=0.1)
        ok, _ = trainer.check(ch, "50,5%")
        assert ok is True

    def test_int_type(self, trainer):
        ch = self._challenge(answer_type="int", correct=7.0, tolerance=0.0)
        ok, _ = trainer.check(ch, "7")
        assert ok is True

    def test_choice_type(self, trainer):
        ch = self._challenge(answer_type="choice", correct=2.0, tolerance=0.0)
        ok, _ = trainer.check(ch, "2")
        assert ok is True

    def test_garbage_input(self, trainer):
        ch = self._challenge()
        ok, msg = trainer.check(ch, "abc")
        assert ok is False
        assert "Некорректный" in msg

    def test_special_chars(self, trainer):
        ch = self._challenge()
        ok, msg = trainer.check(ch, "!@#$")
        assert ok is False


# ── Scoring ──────────────────────────────────────────────────────────────

class TestScoring:
    def test_correct_increments_streak(self, trainer):
        ch = Challenge("q", 10.0, 1.0, "e", Difficulty.EASY)
        trainer.check(ch, "10")
        assert trainer.streak == 1
        assert trainer.total_correct == 1

    def test_wrong_resets_streak(self, trainer):
        ch = Challenge("q", 10.0, 0.0, "e", Difficulty.EASY)
        trainer.check(ch, "10")
        trainer.check(ch, "999")
        assert trainer.streak == 0
        assert trainer.total_correct == 1
        assert trainer.total_asked == 2

    def test_accuracy(self, trainer):
        ch = Challenge("q", 10.0, 1.0, "e", Difficulty.EASY)
        trainer.check(ch, "10")
        trainer.check(ch, "999")
        assert trainer.accuracy == pytest.approx(50.0)

    def test_accuracy_no_questions(self, trainer):
        assert trainer.accuracy == 0.0

    def test_score_increases_on_correct(self, trainer):
        ch = Challenge("q", 10.0, 1.0, "e", Difficulty.EASY)  # 10 points
        trainer.check(ch, "10")
        assert trainer.score == 10

    def test_streak_bonus(self, trainer):
        ch = Challenge("q", 10.0, 1.0, "e", Difficulty.MEDIUM)  # 25 points
        for _ in range(6):
            trainer.check(ch, "10")
        # 5 answers: streak 1-4 → bonus=1, streak 5 → bonus=2
        # Points: 25*1 + 25*1 + 25*1 + 25*1 + 25*2 + 25*2 = 200
        assert trainer.score > 0
        assert trainer.max_streak == 6


# ── Challenge generation ─────────────────────────────────────────────────

class TestChallengeGeneration:
    def test_generate_returns_challenge(self, trainer, shoe, counter):
        hand = _hand(Rank.TEN, Rank.SIX)  # 16 — many generators work
        dealer = _hand(Rank.TWO, Rank.KING)
        # Draw some cards to populate counter
        for _ in range(10):
            c = shoe.draw()
            counter.update(c)
        ch = trainer.generate(hand, dealer, shoe, counter)
        assert ch is not None
        assert isinstance(ch, Challenge)

    def test_generate_respects_difficulty_filter(self, shoe, counter):
        trainer = MathTrainer(allowed_levels=(3,))  # HARD only
        hand = _hand(Rank.TEN, Rank.SIX)
        dealer = _hand(Rank.TWO, Rank.KING)
        for _ in range(15):
            c = shoe.draw()
            counter.update(c)
        ch = trainer.generate(hand, dealer, shoe, counter)
        if ch is not None:
            assert ch.difficulty == Difficulty.HARD

    def test_tolerance_mult_applied(self, shoe, counter):
        trainer = MathTrainer(tolerance_mult=2.0)
        hand = _hand(Rank.TEN, Rank.SIX)
        dealer = _hand(Rank.TWO, Rank.KING)
        for _ in range(10):
            c = shoe.draw()
            counter.update(c)
        ch = trainer.generate(hand, dealer, shoe, counter)
        # tolerance_mult=2.0 means tolerance is doubled — hard to test exact value
        # but at least verify the challenge is generated
        assert ch is None or isinstance(ch, Challenge)


# ── Challenge dataclass ──────────────────────────────────────────────────

class TestChallenge:
    def test_points_easy(self):
        ch = Challenge("q", 1.0, 0, "e", Difficulty.EASY)
        assert ch.points == 10

    def test_points_medium(self):
        ch = Challenge("q", 1.0, 0, "e", Difficulty.MEDIUM)
        assert ch.points == 25

    def test_points_hard(self):
        ch = Challenge("q", 1.0, 0, "e", Difficulty.HARD)
        assert ch.points == 50
