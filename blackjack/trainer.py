"""Math trainer: probability challenges during gameplay."""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from enum import Enum, auto

from .models import Hand, Rank, Shoe
from .counter import CardCounter
from .probability import ProbabilityEngine
from .renderer import Ansi


# ── Difficulty & Challenge ────────────────────────────────────────────────────

class Difficulty(Enum):
    EASY = 1
    MEDIUM = 2
    HARD = 3


@dataclass
class Challenge:
    question: str
    correct_answer: float
    tolerance: float
    explanation: str
    difficulty: Difficulty
    unit: str = ""
    answer_type: str = "float"   # "float" | "int" | "choice"
    choices: list[str] = field(default_factory=list)

    @property
    def points(self) -> int:
        return {Difficulty.EASY: 10, Difficulty.MEDIUM: 25, Difficulty.HARD: 50}[self.difficulty]


# ── MathTrainer ───────────────────────────────────────────────────────────────

class MathTrainer:

    def __init__(
        self,
        allowed_levels: tuple[int, ...] = (1, 2, 3),
        tolerance_mult: float = 1.0,
    ) -> None:
        self.score: int = 0
        self.streak: int = 0
        self.max_streak: int = 0
        self.total_asked: int = 0
        self.total_correct: int = 0
        self._allowed_levels = allowed_levels
        self._tolerance_mult = tolerance_mult

    # ── Public API ────────────────────────────────────────────────────────

    def generate(self, hand: Hand, dealer: Hand, shoe: Shoe,
                 counter: CardCounter) -> Challenge | None:
        generators = [
            self._challenge_bust_prob,
            self._challenge_cards_to_21,
            self._challenge_remaining_aces,
            self._challenge_hilo_count,
            self._challenge_best_action,
            self._challenge_dealer_bust,
            self._challenge_cards_seen,
            self._challenge_conditional_bj,
            # — NEW —
            self._challenge_draw_rank,
            self._challenge_complement,
            self._challenge_deck_composition,
            self._challenge_ratio_high_low,
            self._challenge_true_count,
            self._challenge_addition_rule,
            self._challenge_bj_combos,
            self._challenge_mean_card_value,
            self._challenge_expected_gain,
            self._challenge_kelly,
            self._challenge_two_tens,
            self._challenge_at_least_one_ace,
            self._challenge_std_dev,
            self._challenge_bernoulli,
            self._challenge_bayes,
            self._challenge_poisson,
        ]
        random.shuffle(generators)

        for gen in generators:
            ch = gen(hand, dealer, shoe, counter)
            if ch is not None:
                # Filter by allowed difficulty levels
                if ch.difficulty.value not in self._allowed_levels:
                    continue
                # Scale tolerance by difficulty multiplier
                ch.tolerance *= self._tolerance_mult
                return ch
        return None

    def check(self, challenge: Challenge, raw_answer: str) -> tuple[bool, str]:
        self.total_asked += 1

        cleaned = raw_answer.strip()
        if not cleaned:
            self.streak = 0
            return False, f"Пустой ввод. Правильный ответ: {self._fmt(challenge)}"

        try:
            if challenge.answer_type == "int":
                answer = float(int(cleaned))
            elif challenge.answer_type == "choice":
                answer = float(cleaned)
            else:
                answer = float(cleaned.replace(",", ".").rstrip("%").strip())
        except (ValueError, OverflowError):
            self.streak = 0
            return False, f"Некорректный ввод. Правильный ответ: {self._fmt(challenge)}"

        is_correct = abs(answer - challenge.correct_answer) <= challenge.tolerance

        if is_correct:
            self.total_correct += 1
            self.streak += 1
            self.max_streak = max(self.max_streak, self.streak)
            bonus = challenge.points * (1 + self.streak // 5)
            self.score += bonus
            feedback = (f"{Ansi.GREEN}Верно! +{bonus} очков"
                        f" (streak: {self.streak}){Ansi.RST}")
        else:
            self.streak = 0
            feedback = (f"{Ansi.RED}Неверно.{Ansi.RST} "
                        f"Ответ: {Ansi.BOLD}{self._fmt(challenge)}{Ansi.RST}")

        feedback += f"\n  {Ansi.DIM}{challenge.explanation}{Ansi.RST}"
        return is_correct, feedback

    @property
    def accuracy(self) -> float:
        return (self.total_correct / self.total_asked * 100) if self.total_asked else 0.0

    # ── Challenge generators ──────────────────────────────────────────────

    def _challenge_bust_prob(self, hand: Hand, dealer: Hand,
                             shoe: Shoe, counter: CardCounter) -> Challenge | None:
        if hand.value < 12 or hand.value > 20:
            return None

        p = ProbabilityEngine.bust_probability(hand, shoe) * 100
        max_safe = 21 - hand.value

        return Challenge(
            question=f"Твоя рука: {hand.value}. Какова P(bust) при Hit? (в %)",
            correct_answer=p,
            tolerance=3.0,
            explanation=(
                f"Формула: P(bust) = (карты > {max_safe} очков) / "
                f"{shoe.remaining} оставшихся.\n"
                f"  Точный ответ: {p:.1f}%"
            ),
            difficulty=Difficulty.MEDIUM,
            unit="%",
        )

    def _challenge_cards_to_21(self, hand: Hand, dealer: Hand,
                               shoe: Shoe, counter: CardCounter) -> Challenge | None:
        if hand.value < 11 or hand.value > 20:
            return None

        count, labels = ProbabilityEngine.cards_to_target(hand, 21, shoe)
        need = 21 - hand.value
        label_str = ", ".join(labels) if labels else "нет подходящих"

        return Challenge(
            question=(f"Рука: {hand.value}. Нужно {need} очков до 21.\n"
                      f"  Сколько карт в колоде дадут ровно 21?"),
            correct_answer=float(count),
            tolerance=0.0,
            explanation=(
                f"Нужны карты с {need} очками.\n"
                f"  В колоде: {label_str}. Итого: {count} шт."
            ),
            difficulty=Difficulty.EASY,
            unit="шт",
            answer_type="int",
        )

    def _challenge_remaining_aces(self, hand: Hand, dealer: Hand,
                                  shoe: Shoe, counter: CardCounter) -> Challenge | None:
        aces = shoe.count_remaining(Rank.ACE)
        total_initial = shoe.n_decks * 4
        dealt_aces = total_initial - aces

        return Challenge(
            question="Сколько тузов осталось в колоде?",
            correct_answer=float(aces),
            tolerance=0.0,
            explanation=(
                f"Всего в {shoe.n_decks}-колодной обуви: {total_initial} тузов.\n"
                f"  Уже вышло: {dealt_aces}. Осталось: {aces}."
            ),
            difficulty=Difficulty.EASY,
            unit="шт",
            answer_type="int",
        )

    def _challenge_hilo_count(self, hand: Hand, dealer: Hand,
                              shoe: Shoe, counter: CardCounter) -> Challenge | None:
        if counter.cards_seen < 6:
            return None

        return Challenge(
            question=(f"Hi-Lo: вышло {counter.cards_seen} карт.\n"
                      f"  Каков текущий Running Count?"),
            correct_answer=float(counter.running_count),
            tolerance=0.0,
            explanation=(
                f"Hi-Lo система: 2-6 = +1, 7-9 = 0, 10-A = -1.\n"
                f"  Running Count = {counter.running_count}.\n"
                f"  True Count = {counter.true_count(shoe.remaining_decks):.1f} "
                f"({counter.running_count} / {shoe.remaining_decks:.1f} колод)."
            ),
            difficulty=Difficulty.MEDIUM,
            answer_type="int",
        )

    def _challenge_best_action(self, hand: Hand, dealer: Hand,
                               shoe: Shoe, counter: CardCounter) -> Challenge | None:
        if hand.value < 8 or hand.value > 20:
            return None

        ev_s = ProbabilityEngine.ev_stand(hand, dealer.cards[1], shoe, n_sims=1000)
        ev_h = ProbabilityEngine.ev_hit(hand, dealer.cards[1], shoe, n_sims=1000)
        best = 1 if ev_h > ev_s else 2

        return Challenge(
            question=(f"Рука: {hand.value} vs Дилер: {dealer.cards[1]}.\n"
                      f"  Что выгоднее? (1 = Hit, 2 = Stand)"),
            correct_answer=float(best),
            tolerance=0.0,
            explanation=(
                f"EV(Hit)   = {ev_h:+.3f} ставки\n"
                f"  EV(Stand) = {ev_s:+.3f} ставки\n"
                f"  Лучше: {'Hit' if best == 1 else 'Stand'} "
                f"(разница: {abs(ev_h - ev_s):.3f})"
            ),
            difficulty=Difficulty.HARD,
            answer_type="int",
        )

    def _challenge_dealer_bust(self, hand: Hand, dealer: Hand,
                               shoe: Shoe, counter: CardCounter) -> Challenge | None:
        upcard = dealer.cards[1]
        std_bust = {2: 35, 3: 37, 4: 40, 5: 42, 6: 42, 7: 26,
                    8: 24, 9: 23, 10: 23, 11: 17}
        pts = upcard.rank.points
        approx = std_bust.get(pts, 25)

        actual = ProbabilityEngine.dealer_bust_probability(upcard, shoe, n_sims=3000) * 100

        return Challenge(
            question=(f"У дилера открыта {upcard}.\n"
                      f"  Какова примерная P(dealer bust)? (в %)"),
            correct_answer=actual,
            tolerance=5.0,
            explanation=(
                f"Стандартная таблица: ~{approx}% для карты {upcard.rank.label}.\n"
                f"  Точный расчёт из текущей колоды: {actual:.1f}%.\n"
                f"  Правило: дилер bust чаще с 4/5/6, реже с 7-A."
            ),
            difficulty=Difficulty.MEDIUM,
            unit="%",
        )

    def _challenge_cards_seen(self, hand: Hand, dealer: Hand,
                              shoe: Shoe, counter: CardCounter) -> Challenge | None:
        if counter.cards_seen < 4:
            return None

        return Challenge(
            question="Сколько карт уже вышло из колоды (включая текущую раздачу)?",
            correct_answer=float(counter.cards_seen),
            tolerance=0.0,
            explanation=(
                f"Вышло карт: {counter.cards_seen}.\n"
                f"  Осталось в колоде: {shoe.remaining}.\n"
                f"  Умение считать вышедшие карты — база card counting."
            ),
            difficulty=Difficulty.EASY,
            answer_type="int",
            unit="шт",
        )

    def _challenge_conditional_bj(self, hand: Hand, dealer: Hand,
                                  shoe: Shoe, counter: CardCounter) -> Challenge | None:
        upcard = dealer.cards[1]
        if upcard.rank not in (Rank.ACE, Rank.TEN, Rank.JACK, Rank.QUEEN, Rank.KING):
            return None

        total = shoe.remaining
        if total == 0:
            return None

        if upcard.rank is Rank.ACE:
            tens = sum(shoe.count_remaining(r) for r in
                       (Rank.TEN, Rank.JACK, Rank.QUEEN, Rank.KING))
            p = tens / total * 100
            need_str = "10/J/Q/K"
            need_count = tens
        else:
            aces = shoe.count_remaining(Rank.ACE)
            p = aces / total * 100
            need_str = "туз"
            need_count = aces

        return Challenge(
            question=(f"У дилера открыта {upcard}.\n"
                      f"  Какова P(Blackjack у дилера)? (в %)"),
            correct_answer=p,
            tolerance=2.0,
            explanation=(
                f"Нужна {need_str}. В колоде: {need_count} из {total} карт.\n"
                f"  P = {need_count}/{total} = {p:.1f}%.\n"
                f"  Это условная вероятность: P(BJ | видим {upcard.rank.label})."
            ),
            difficulty=Difficulty.HARD,
            unit="%",
        )

    # ── NEW challenge generators ─────────────────────────────────────────

    def _challenge_draw_rank(self, hand: Hand, dealer: Hand,
                             shoe: Shoe, counter: CardCounter) -> Challenge | None:
        """P(drawing specific rank) — Laplace formula P = m/n."""
        rank = random.choice([Rank.ACE, Rank.TWO, Rank.FIVE, Rank.SEVEN,
                              Rank.TEN, Rank.JACK, Rank.QUEEN, Rank.KING])
        count = shoe.count_remaining(rank)
        total = shoe.remaining
        if total == 0:
            return None
        p = count / total * 100

        return Challenge(
            question=(f"В колоде {total} карт, из них {count} шт. ранга {rank.label}.\n"
                      f"P(следующая карта = {rank.label}) = ? (в %)"),
            correct_answer=p,
            tolerance=2.0,
            explanation=(
                f"Формула Лапласа: P(A) = m / n = {count} / {total} = {p:.2f}%\n"
                f"  m = благоприятные исходы, n = все исходы."
            ),
            difficulty=Difficulty.EASY,
            unit="%",
        )

    def _challenge_complement(self, hand: Hand, dealer: Hand,
                              shoe: Shoe, counter: CardCounter) -> Challenge | None:
        """P(safe) = 1 − P(bust) — complement rule."""
        if hand.value < 12 or hand.value > 20:
            return None
        p_bust = ProbabilityEngine.bust_probability(hand, shoe) * 100
        p_safe = 100 - p_bust

        return Challenge(
            question=(f"Рука: {hand.value}. P(bust) = {p_bust:.1f}%.\n"
                      f"Какова P(НЕ перебрать при Hit)? (в %)"),
            correct_answer=p_safe,
            tolerance=1.0,
            explanation=(
                f"Правило дополнения: P(Ā) = 1 − P(A)\n"
                f"  P(safe) = 100% − {p_bust:.1f}% = {p_safe:.1f}%"
            ),
            difficulty=Difficulty.EASY,
            unit="%",
        )

    def _challenge_deck_composition(self, hand: Hand, dealer: Hand,
                                    shoe: Shoe, counter: CardCounter) -> Challenge | None:
        """Count 10-value cards remaining."""
        tens = sum(shoe.count_remaining(r)
                   for r in (Rank.TEN, Rank.JACK, Rank.QUEEN, Rank.KING))
        total_initial = shoe.n_decks * 16
        dealt = total_initial - tens

        return Challenge(
            question=(f"Сколько карт стоимостью 10 (10/J/Q/K)\n"
                      f"осталось в колоде из {shoe.remaining}?"),
            correct_answer=float(tens),
            tolerance=0.0,
            explanation=(
                f"10-value: 10, J, Q, K — 4 ранга × {shoe.n_decks} колод = "
                f"{total_initial} всего.\n"
                f"  Вышло: {dealt}. Осталось: {tens}."
            ),
            difficulty=Difficulty.EASY,
            unit="шт",
            answer_type="int",
        )

    def _challenge_ratio_high_low(self, hand: Hand, dealer: Hand,
                                  shoe: Shoe, counter: CardCounter) -> Challenge | None:
        """Ratio high/low cards — card counting insight."""
        by_pts = shoe.remaining_by_points()
        high = by_pts.get(10, 0) + by_pts.get(11, 0)   # 10-value + aces
        low = sum(by_pts.get(p, 0) for p in range(2, 7))  # 2-6
        if low == 0 or high == 0:
            return None
        total = shoe.remaining
        p_high = high / total * 100

        return Challenge(
            question=(f"В колоде {high} «высоких» (10/J/Q/K/A) и {low} «низких» (2-6).\n"
                      f"Какой % карт — высокие? (в %)"),
            correct_answer=p_high,
            tolerance=3.0,
            explanation=(
                f"P(high) = {high} / {total} = {p_high:.1f}%\n"
                f"  Ratio high:low = {high}:{low} = {high / low:.2f}\n"
                f"  Ratio > 1 → выгодно игроку (больше BJ и bust дилера)."
            ),
            difficulty=Difficulty.EASY,
            unit="%",
        )

    def _challenge_true_count(self, hand: Hand, dealer: Hand,
                              shoe: Shoe, counter: CardCounter) -> Challenge | None:
        """True Count = RC / remaining decks."""
        if counter.cards_seen < 10:
            return None
        rc = counter.running_count
        rd = shoe.remaining_decks
        if rd < 0.5:
            return None
        tc = rc / rd

        return Challenge(
            question=(f"Running Count = {rc}, осталось {rd:.1f} колод.\n"
                      f"Каков True Count? (округли до 0.1)"),
            correct_answer=round(tc, 1),
            tolerance=0.5,
            explanation=(
                f"TC = RC / remaining_decks = {rc} / {rd:.1f} = {tc:.1f}\n"
                f"  TC > +2: преимущество игрока, увеличивай ставку.\n"
                f"  TC < −2: преимущество казино, минимальная ставка."
            ),
            difficulty=Difficulty.MEDIUM,
        )

    def _challenge_addition_rule(self, hand: Hand, dealer: Hand,
                                 shoe: Shoe, counter: CardCounter) -> Challenge | None:
        """P(A∪B) = P(A) + P(B) − P(A∩B)."""
        remaining = shoe.cards_snapshot
        total = len(remaining)
        if total < 20:
            return None

        reds = sum(1 for c in remaining if c.suit.is_red)
        faces = sum(1 for c in remaining
                    if c.rank in (Rank.JACK, Rank.QUEEN, Rank.KING))
        red_faces = sum(1 for c in remaining
                        if c.suit.is_red
                        and c.rank in (Rank.JACK, Rank.QUEEN, Rank.KING))
        p = (reds + faces - red_faces) / total * 100

        return Challenge(
            question=(f"Из {total} карт: {reds} красных, {faces} картинок (J/Q/K),\n"
                      f"{red_faces} красных картинок.\n"
                      f"P(красная ИЛИ картинка) = ? (в %)"),
            correct_answer=p,
            tolerance=3.0,
            explanation=(
                f"Формула сложения: P(A∪B) = P(A) + P(B) − P(A∩B)\n"
                f"  = {reds}/{total} + {faces}/{total} − {red_faces}/{total}\n"
                f"  = ({reds} + {faces} − {red_faces}) / {total} = {p:.1f}%"
            ),
            difficulty=Difficulty.MEDIUM,
            unit="%",
        )

    def _challenge_bj_combos(self, hand: Hand, dealer: Hand,
                             shoe: Shoe, counter: CardCounter) -> Challenge | None:
        """Counting BJ combinations — multiplication rule."""
        aces = shoe.count_remaining(Rank.ACE)
        tens = sum(shoe.count_remaining(r)
                   for r in (Rank.TEN, Rank.JACK, Rank.QUEEN, Rank.KING))
        if aces == 0 or tens == 0:
            return None
        combos = aces * tens

        return Challenge(
            question=(f"В колоде {aces} тузов и {tens} десяток (10/J/Q/K).\n"
                      f"Сколько уникальных комбинаций 'Blackjack' (A + 10)?"),
            correct_answer=float(combos),
            tolerance=0.0,
            explanation=(
                f"Правило умножения: m × n = {aces} × {tens} = {combos}\n"
                f"  Каждый туз сочетается с каждой 10-value картой."
            ),
            difficulty=Difficulty.MEDIUM,
            answer_type="int",
        )

    def _challenge_mean_card_value(self, hand: Hand, dealer: Hand,
                                   shoe: Shoe, counter: CardCounter) -> Challenge | None:
        """E(X) — expected value of next card."""
        by_pts = shoe.remaining_by_points()
        total = shoe.remaining
        if total == 0:
            return None
        mean = sum(pts * cnt for pts, cnt in by_pts.items()) / total

        return Challenge(
            question=(f"Какова средняя стоимость карты в колоде?\n"
                      f"(мат. ожидание E(X), округли до 0.1)"),
            correct_answer=round(mean, 1),
            tolerance=0.5,
            explanation=(
                f"E(X) = Σ xᵢ × P(xᵢ) = Σ (pts × count) / total\n"
                f"  = {sum(pts * cnt for pts, cnt in by_pts.items())} / {total} = {mean:.2f}\n"
                f"  E(X) > 7 → в колоде больше крупных карт."
            ),
            difficulty=Difficulty.MEDIUM,
        )

    def _challenge_expected_gain(self, hand: Hand, dealer: Hand,
                                 shoe: Shoe, counter: CardCounter) -> Challenge | None:
        """Expected $ gain = EV × bet."""
        if hand.value < 8 or hand.value > 20 or hand.bet == 0:
            return None

        ev_s = ProbabilityEngine.ev_stand(hand, dealer.cards[1], shoe, n_sims=800)
        ev_h = ProbabilityEngine.ev_hit(hand, dealer.cards[1], shoe, n_sims=800)
        best_ev = max(ev_s, ev_h)
        best_name = "Hit" if ev_h > ev_s else "Stand"
        bet = hand.bet
        expected = best_ev * bet

        return Challenge(
            question=(f"Лучший ход: {best_name}, EV = {best_ev:+.2f} ставки.\n"
                      f"Ставка = ${bet}. Ожидаемый выигрыш/проигрыш в $?"),
            correct_answer=round(expected, 1),
            tolerance=max(abs(expected) * 0.15, 3.0),
            explanation=(
                f"Ожидаемый выигрыш = EV × Bet = {best_ev:+.2f} × ${bet} "
                f"= ${expected:+.1f}\n"
                f"  EV > 0 → в среднем профит. EV < 0 → в среднем убыток."
            ),
            difficulty=Difficulty.MEDIUM,
        )

    def _challenge_kelly(self, hand: Hand, dealer: Hand,
                         shoe: Shoe, counter: CardCounter) -> Challenge | None:
        """Kelly criterion: f* = (bp − q) / b."""
        if hand.value < 8 or hand.value > 20:
            return None

        ev_s = ProbabilityEngine.ev_stand(hand, dealer.cards[1], shoe, n_sims=800)
        # approximate P(win) from EV for even-money bet
        p_win = max(0.05, min(0.95, (ev_s + 1) / 2))
        p_lose = 1 - p_win
        b = 1.0  # even money
        kelly = (b * p_win - p_lose) / b * 100

        p_pct = p_win * 100
        q_pct = p_lose * 100

        return Challenge(
            question=(f"P(win) ≈ {p_pct:.0f}%, P(lose) ≈ {q_pct:.0f}%.\n"
                      f"Выплата 1:1. Критерий Келли f* = ? (в % от банка)"),
            correct_answer=round(kelly, 1),
            tolerance=5.0,
            explanation=(
                f"f* = (b×p − q) / b = (1×{p_win:.2f} − {p_lose:.2f}) / 1 "
                f"= {kelly:+.1f}%\n"
                f"  f* < 0 → не ставить (edge у казино).\n"
                f"  f* > 0 → ставить f*% банка для максимального роста."
            ),
            difficulty=Difficulty.HARD,
            unit="%",
        )

    def _challenge_two_tens(self, hand: Hand, dealer: Hand,
                            shoe: Shoe, counter: CardCounter) -> Challenge | None:
        """P(A∩B) for dependent events: two 10-value cards in a row."""
        tens = sum(shoe.count_remaining(r)
                   for r in (Rank.TEN, Rank.JACK, Rank.QUEEN, Rank.KING))
        total = shoe.remaining
        if total < 2 or tens < 2:
            return None
        p = tens / total * (tens - 1) / (total - 1) * 100

        return Challenge(
            question=(f"В колоде {tens} десяток из {total} карт.\n"
                      f"P(две десятки подряд) = ? (в %)"),
            correct_answer=p,
            tolerance=2.0,
            explanation=(
                f"Умножение зависимых событий:\n"
                f"  P(A∩B) = P(A) × P(B|A) = {tens}/{total} × "
                f"{tens - 1}/{total - 1} = {p:.2f}%\n"
                f"  Второе событие зависит от первого (карта не возвращается)."
            ),
            difficulty=Difficulty.HARD,
            unit="%",
        )

    def _challenge_at_least_one_ace(self, hand: Hand, dealer: Hand,
                                    shoe: Shoe, counter: CardCounter) -> Challenge | None:
        """P(≥1 ace in 3 draws) = 1 − P(no aces in 3 draws)."""
        aces = shoe.count_remaining(Rank.ACE)
        total = shoe.remaining
        if total < 3 or aces == 0:
            return None

        n_a = total - aces
        p_no = (n_a / total) * ((n_a - 1) / (total - 1)) * ((n_a - 2) / (total - 2))
        p = (1 - p_no) * 100

        return Challenge(
            question=(f"В колоде {total} карт, из них {aces} тузов.\n"
                      f"P(хотя бы 1 туз за 3 карты) = ? (в %)"),
            correct_answer=p,
            tolerance=3.0,
            explanation=(
                f"Дополнение + умножение зависимых:\n"
                f"  P(≥1) = 1 − P(0 тузов за 3 карты)\n"
                f"  P(0) = {n_a}/{total} × {n_a - 1}/{total - 1} × "
                f"{n_a - 2}/{total - 2} = {p_no:.4f}\n"
                f"  P(≥1) = 1 − {p_no:.4f} = {p:.1f}%"
            ),
            difficulty=Difficulty.HARD,
            unit="%",
        )

    def _challenge_std_dev(self, hand: Hand, dealer: Hand,
                           shoe: Shoe, counter: CardCounter) -> Challenge | None:
        """σ = √D(X) — standard deviation from variance."""
        by_pts = shoe.remaining_by_points()
        total = shoe.remaining
        if total == 0:
            return None
        mean = sum(pts * cnt for pts, cnt in by_pts.items()) / total
        var = sum(cnt * (pts - mean) ** 2 for pts, cnt in by_pts.items()) / total
        std = math.sqrt(var)

        return Challenge(
            question=(f"Дисперсия стоимости карт D(X) = {var:.1f}.\n"
                      f"Чему равно стандартное отклонение σ? (округли до 0.1)"),
            correct_answer=round(std, 1),
            tolerance=0.5,
            explanation=(
                f"σ = √D(X) = √{var:.1f} = {std:.2f}\n"
                f"  Средняя стоимость E(X) = {mean:.1f}\n"
                f"  Типичное значение: {mean:.1f} ± {std:.1f}"
            ),
            difficulty=Difficulty.HARD,
        )

    def _challenge_bernoulli(self, hand: Hand, dealer: Hand,
                             shoe: Shoe, counter: CardCounter) -> Challenge | None:
        """Bernoulli trials: P(X=k) = C(n,k) × p^k × (1−p)^(n−k)."""
        if hand.value < 12 or hand.value > 19:
            return None

        p = ProbabilityEngine.bust_probability(hand, shoe)
        q = 1 - p
        n = random.choice([3, 4, 5])
        k = random.randint(0, min(2, n))
        nk = n - k

        c_nk = math.comb(n, k)
        prob = c_nk * (p ** k) * (q ** nk) * 100

        return Challenge(
            question=(f"P(bust) = {p * 100:.1f}% для руки {hand.value}.\n"
                      f"Сыграв {n} таких рук (Hit), P(bust ровно {k} раз) = ?\n"
                      f"Формула Бернулли (в %)"),
            correct_answer=prob,
            tolerance=3.0,
            explanation=(
                f"Формула Бернулли: P(X=k) = C(n,k) × p^k × q^(n−k)\n"
                f"  C({n},{k}) = {c_nk},  p = {p:.3f},  q = {q:.3f}\n"
                f"  P = {c_nk} × {p:.3f}^{k} × {q:.3f}^{nk} = {prob:.2f}%"
            ),
            difficulty=Difficulty.HARD,
            unit="%",
        )

    def _challenge_bayes(self, hand: Hand, dealer: Hand,
                         shoe: Shoe, counter: CardCounter) -> Challenge | None:
        """Bayes' theorem: P(A|B) = P(B|A) × P(A) / P(B)."""
        remaining = shoe.cards_snapshot
        total = len(remaining)
        if total < 20:
            return None

        aces = sum(1 for c in remaining if c.rank is Rank.ACE)
        reds = sum(1 for c in remaining if c.suit.is_red)
        red_aces = sum(1 for c in remaining
                       if c.rank is Rank.ACE and c.suit.is_red)
        if reds == 0 or aces == 0:
            return None

        p_red_given_ace = red_aces / aces
        p_ace = aces / total
        p_red = reds / total
        # P(Ace|Red) = P(Red|Ace) × P(Ace) / P(Red)
        p_ace_given_red = red_aces / reds * 100

        return Challenge(
            question=(f"Из {total} карт: {aces} тузов, {reds} красных,\n"
                      f"{red_aces} красных тузов.\n"
                      f"Карта красная. P(это туз) = ? (Байес, в %)"),
            correct_answer=p_ace_given_red,
            tolerance=2.0,
            explanation=(
                f"Формула Байеса: P(A|B) = P(B|A) × P(A) / P(B)\n"
                f"  P(Red|Ace) = {red_aces}/{aces} = {p_red_given_ace:.3f}\n"
                f"  P(Ace) = {aces}/{total} = {p_ace:.4f}\n"
                f"  P(Red) = {reds}/{total} = {p_red:.3f}\n"
                f"  P(Ace|Red) = {p_red_given_ace:.3f} × {p_ace:.4f} / "
                f"{p_red:.3f} = {p_ace_given_red:.2f}%"
            ),
            difficulty=Difficulty.HARD,
            unit="%",
        )

    def _challenge_poisson(self, hand: Hand, dealer: Hand,
                           shoe: Shoe, counter: CardCounter) -> Challenge | None:
        """Poisson distribution: P(X=k) = (λ^k × e^(−λ)) / k!"""
        total = shoe.remaining
        if total < 20:
            return None
        aces = shoe.count_remaining(Rank.ACE)
        tens = sum(shoe.count_remaining(r)
                   for r in (Rank.TEN, Rank.JACK, Rank.QUEEN, Rank.KING))
        if aces == 0 or tens == 0:
            return None

        # P(BJ) = 2 × P(first=A)×P(second=10) (order matters)
        p_bj = 2 * (aces / total) * (tens / (total - 1))

        n = random.choice([20, 30, 50])
        lam = n * p_bj
        k = random.choice([0, 1, 2])

        prob = (lam ** k * math.exp(-lam)) / math.factorial(k) * 100
        lam_k = lam ** k
        e_neg = math.exp(-lam)
        k_fact = math.factorial(k)

        return Challenge(
            question=(f"P(Blackjack) ≈ {p_bj * 100:.2f}% за раздачу.\n"
                      f"λ = n×p = {n}×{p_bj:.4f} = {lam:.2f}\n"
                      f"P(ровно {k} BJ за {n} раздач) = ? (Пуассон, в %)"),
            correct_answer=prob,
            tolerance=3.0,
            explanation=(
                f"Формула Пуассона: P(X=k) = (λ^k × e^(−λ)) / k!\n"
                f"  λ = {lam:.2f}, k = {k}\n"
                f"  P = ({lam:.2f}^{k} × e^(−{lam:.2f})) / {k}!\n"
                f"  = {lam_k:.4f} × {e_neg:.4f} / {k_fact} = {prob:.2f}%"
            ),
            difficulty=Difficulty.HARD,
            unit="%",
        )

    @staticmethod
    def _fmt(ch: Challenge) -> str:
        if ch.answer_type == "int":
            return f"{int(ch.correct_answer)} {ch.unit}".strip()
        return f"{ch.correct_answer:.1f}{ch.unit}"
