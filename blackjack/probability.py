"""Probability engine: exact calculations from remaining shoe state."""

from __future__ import annotations

import random

from .models import Card, Hand, Rank, Shoe


class ProbabilityEngine:
    """Computes probabilities based on the real shoe composition."""

    @staticmethod
    def bust_probability(hand: Hand, shoe: Shoe) -> float:
        """P(bust) on Hit — exact count from remaining cards."""
        current = hand.value
        if current >= 21:
            return 1.0
        max_safe = 21 - current

        by_pts = shoe.remaining_by_points()
        total = shoe.remaining
        if total == 0:
            return 0.0

        safe = 0
        for pts, count in by_pts.items():
            effective = pts
            if pts == 11 and current + pts > 21:
                effective = 1
            if effective <= max_safe:
                safe += count

        return 1.0 - safe / total

    @staticmethod
    def cards_to_target(hand: Hand, target: int, shoe: Shoe) -> tuple[int, list[str]]:
        """How many cards in shoe give exactly *target* points?"""
        need = target - hand.value
        if need <= 0 or need > 11:
            return 0, []

        by_pts = shoe.remaining_by_points()
        count = 0
        labels: list[str] = []

        if need == 11:
            c = by_pts.get(11, 0)
            if c:
                count += c
                labels.append(f"A({c})")
        elif need == 1:
            if not hand.is_soft:
                c = by_pts.get(11, 0)
                if c:
                    count += c
                    labels.append(f"A({c})")
        elif 2 <= need <= 9:
            c = by_pts.get(need, 0)
            if c:
                count += c
                labels.append(f"{need}({c})")
        elif need == 10:
            c = by_pts.get(10, 0)
            if c:
                count += c
                labels.append(f"10/J/Q/K({c})")

        return count, labels

    @staticmethod
    def dealer_bust_probability(upcard: Card, shoe: Shoe,
                                n_sims: int = 5000) -> float:
        """P(dealer bust) — Monte-Carlo with real shoe."""
        remaining = shoe.cards_snapshot
        if len(remaining) < 5:
            return 0.0

        busts = 0
        for _ in range(n_sims):
            deck = remaining.copy()
            random.shuffle(deck)
            total = upcard.points
            aces = 1 if upcard.rank is Rank.ACE else 0

            while True:
                val, a = total, aces
                while val > 21 and a:
                    val -= 10
                    a -= 1
                if val >= 17:
                    break
                if not deck:
                    break
                c = deck.pop()
                total += c.points
                if c.rank is Rank.ACE:
                    aces += 1

            val, a = total, aces
            while val > 21 and a:
                val -= 10
                a -= 1
            if val > 21:
                busts += 1

        return busts / n_sims

    @staticmethod
    def ev_stand(hand: Hand, dealer_upcard: Card, shoe: Shoe,
                 n_sims: int = 3000) -> float:
        """EV(Stand) — expected payout in bet units."""
        pv = hand.value
        if pv > 21:
            return -1.0

        remaining = shoe.cards_snapshot
        if len(remaining) < 5:
            return 0.0

        return ProbabilityEngine._quick_ev_stand(
            pv, dealer_upcard, remaining, n_sims
        )

    @staticmethod
    def ev_hit(hand: Hand, dealer_upcard: Card, shoe: Shoe,
               n_sims: int = 2000) -> float:
        """EV(Hit) — approximate: hit 1 card, then stand."""
        remaining = shoe.cards_snapshot
        if len(remaining) < 5:
            return 0.0

        pv = hand.value
        by_pts = shoe.remaining_by_points()

        total_ev = 0.0
        weight = 0

        for pts, cnt in by_pts.items():
            new_val = pv + pts
            if new_val > 21 and (hand.is_soft or pts == 11):
                new_val -= 10
            if new_val > 21:
                total_ev -= cnt
            else:
                ev_after = ProbabilityEngine._quick_ev_stand(
                    new_val, dealer_upcard, remaining, min(200, n_sims // 10)
                )
                total_ev += cnt * ev_after
            weight += cnt

        return total_ev / weight if weight else 0.0

    @staticmethod
    def _quick_ev_stand(player_val: int, dealer_upcard: Card,
                        remaining: list[Card], n_sims: int) -> float:
        total = 0.0
        for _ in range(n_sims):
            deck = remaining.copy()
            random.shuffle(deck)
            dtotal = dealer_upcard.points
            daces = 1 if dealer_upcard.rank is Rank.ACE else 0
            while True:
                val, a = dtotal, daces
                while val > 21 and a:
                    val -= 10
                    a -= 1
                if val >= 17:
                    break
                if not deck:
                    break
                c = deck.pop()
                dtotal += c.points
                if c.rank is Rank.ACE:
                    daces += 1
            dv, a = dtotal, daces
            while dv > 21 and a:
                dv -= 10
                a -= 1
            if dv > 21 or player_val > dv:
                total += 1.0
            elif player_val < dv:
                total -= 1.0
        return total / n_sims if n_sims else 0.0
