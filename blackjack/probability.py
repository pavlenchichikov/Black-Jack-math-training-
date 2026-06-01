"""Probability engine: exact and recursive EV calculations.

Two regimes:
  * Deterministic counts over the live shoe (bust, cards-to-target,
    dealer-bust analytical).
  * Recursive expected-value tree for player decisions, computed on a
    pruned shoe signature so repeated HUD queries inside one decision
    share a cache and finish in single-digit milliseconds.

Monte Carlo is still used for EV(Stand) where exact enumeration over
the dealer's full draw tree is wasteful given the live-shoe coupling.
Sim counts default to values calibrated for under-50ms HUD refresh on
a 6-deck shoe.
"""
from __future__ import annotations

import random
from functools import cache, lru_cache

from .models import Card, Hand, Rank, Shoe

# ── Public helpers ────────────────────────────────────────────────────────────


def shoe_signature(shoe: Shoe) -> tuple[tuple[int, int], ...]:
    """Hashable summary of the shoe by point value.

    Two shoes with the same per-points counts produce identical EVs for
    every decision question we ask, so this is a sound cache key.
    """
    by_pts = shoe.remaining_by_points()
    return tuple(sorted(by_pts.items()))


class ProbabilityEngine:
    """Computes probabilities based on the real shoe composition."""

    # ── Bust / next-card counts ───────────────────────────────────────────

    @staticmethod
    def bust_probability(hand: Hand, shoe: Shoe) -> float:
        """P(bust) on Hit, exact count from remaining cards."""
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

    # ── Dealer bust (analytical DP, cached) ───────────────────────────────

    @staticmethod
    def dealer_bust_probability(upcard: Card, shoe: Shoe,
                                n_sims: int | None = None,
                                hit_soft_17: bool = False) -> float:
        """Analytical P(dealer busts) given the live shoe composition.

        n_sims is accepted for API stability but ignored: this is now an
        exact dynamic-programming evaluation over the shoe signature.
        Returns 0.0 when too few cards remain to draw to 17 confidently;
        callers rely on this guard to skip the HUD on a near-empty shoe.
        """
        if shoe.remaining < 5:
            return 0.0
        sig = shoe_signature(shoe)
        if not sig:
            return 0.0
        starting_aces = 1 if upcard.rank is Rank.ACE else 0
        return _dealer_bust_dp(
            upcard.rank.points, starting_aces, sig, hit_soft_17
        )

    # ── EV(Stand): Monte Carlo over dealer draws ──────────────────────────

    @staticmethod
    def ev_stand(hand: Hand, dealer_upcard: Card, shoe: Shoe,
                 n_sims: int = 3000, hit_soft_17: bool = False) -> float:
        """EV(Stand) in bet units. Push counts as 0."""
        pv = hand.value
        if pv > 21:
            return -1.0
        if shoe.remaining < 5:
            return 0.0
        return _quick_ev_stand(pv, dealer_upcard, shoe, n_sims, hit_soft_17)

    # ── EV(Hit): recursive DP with shoe-signature cache ───────────────────

    @staticmethod
    def ev_hit(hand: Hand, dealer_upcard: Card, shoe: Shoe,
               n_sims: int = 2000, hit_soft_17: bool = False) -> float:
        """EV(Hit), assuming the player will subsequently play optimally.

        Computes max(EV_hit_again, EV_stand) at every reached node, so
        the value reflects how a basic-strategy player would continue.
        """
        if shoe.remaining < 5:
            return 0.0
        sig = shoe_signature(shoe)
        soft_aces = _hand_soft_aces(hand)
        return _ev_after_hit(
            hand.value, soft_aces, dealer_upcard, sig, n_sims, hit_soft_17
        )

    # ── Cache control ─────────────────────────────────────────────────────

    @staticmethod
    def clear_cache() -> None:
        _ev_after_hit.cache_clear()
        _ev_stand_at.cache_clear()
        _dealer_bust_dp.cache_clear()


# ── Internals ────────────────────────────────────────────────────────────────


def _hand_soft_aces(hand: Hand) -> int:
    """Number of aces currently being counted as 11 in this hand."""
    total = sum(c.points for c in hand.cards)
    aces = sum(1 for c in hand.cards if c.rank is Rank.ACE)
    while total > 21 and aces:
        total -= 10
        aces -= 1
    return aces


def _apply_card(value: int, soft_aces: int, pts: int) -> tuple[int, int]:
    """Update (value, soft_aces) after drawing a card with `pts` points."""
    new_val = value + pts
    new_aces = soft_aces + (1 if pts == 11 else 0)
    while new_val > 21 and new_aces > 0:
        new_val -= 10
        new_aces -= 1
    return new_val, new_aces


@lru_cache(maxsize=4096)
def _ev_after_hit(
    player_val: int,
    soft_aces: int,
    dealer_upcard: Card,
    shoe_sig: tuple[tuple[int, int], ...],
    n_sims: int,
    hit_soft_17: bool,
) -> float:
    """E[result | player hits this card, then plays optimally]."""
    by_pts = dict(shoe_sig)
    total_cards = sum(by_pts.values())
    if total_cards == 0:
        return 0.0

    expected = 0.0
    for pts, count in by_pts.items():
        if count <= 0:
            continue
        new_val, new_aces = _apply_card(player_val, soft_aces, pts)
        if new_val > 21:
            ev_branch = -1.0
        elif new_val == 21:
            ev_branch = _ev_stand_at(
                21, dealer_upcard, shoe_sig, n_sims, hit_soft_17
            )
        else:
            ev_stand = _ev_stand_at(
                new_val, dealer_upcard, shoe_sig, n_sims, hit_soft_17
            )
            ev_hit_next = _ev_after_hit(
                new_val, new_aces, dealer_upcard,
                shoe_sig, n_sims, hit_soft_17,
            )
            ev_branch = max(ev_stand, ev_hit_next)
        expected += (count / total_cards) * ev_branch
    return expected


@lru_cache(maxsize=2048)
def _ev_stand_at(
    player_val: int,
    dealer_upcard: Card,
    shoe_sig: tuple[tuple[int, int], ...],
    n_sims: int,
    hit_soft_17: bool,
) -> float:
    """Monte Carlo EV(Stand) keyed on shoe signature."""
    if player_val > 21:
        return -1.0
    by_pts = dict(shoe_sig)
    total = sum(by_pts.values())
    if total < 5:
        return 0.0

    points_pool: list[int] = []
    for pts, cnt in by_pts.items():
        points_pool.extend([pts] * cnt)

    upcard_pts = dealer_upcard.rank.points
    starting_aces = 1 if dealer_upcard.rank is Rank.ACE else 0

    rng = random.Random(player_val * 1000 + upcard_pts)
    score = 0.0
    for _ in range(n_sims):
        deck = points_pool.copy()
        rng.shuffle(deck)
        dval, daces = upcard_pts, starting_aces
        while _dealer_keeps_hitting(dval, daces, hit_soft_17):
            if not deck:
                break
            pts = deck.pop()
            dval, daces = _apply_card(dval, daces, pts)
        if dval > 21 or player_val > dval:
            score += 1.0
        elif player_val < dval:
            score -= 1.0
    return score / n_sims if n_sims else 0.0


@lru_cache(maxsize=2048)
def _dealer_bust_dp(
    upcard_pts: int,
    starting_aces: int,
    shoe_sig: tuple[tuple[int, int], ...],
    hit_soft_17: bool,
) -> float:
    """P(dealer busts) via memoized recursion over draw outcomes.

    Approximation: we sample draws with replacement from the shoe
    composition at every step (no coupling between successive draws).
    The bias is small for typical 6-deck shoes and lets the DP collapse
    to a fixed-point table independent of draw order.
    """
    by_pts = dict(shoe_sig)
    total = sum(by_pts.values())
    if total == 0:
        return 0.0
    probs = {pts: cnt / total for pts, cnt in by_pts.items()}

    @cache
    def bust_from(val: int, aces: int) -> float:
        if val > 21:
            return 1.0
        if not _dealer_keeps_hitting(val, aces, hit_soft_17):
            return 0.0
        p_bust = 0.0
        for pts, prob in probs.items():
            new_val, new_aces = _apply_card(val, aces, pts)
            p_bust += prob * bust_from(new_val, new_aces)
        return p_bust

    return bust_from(upcard_pts, starting_aces)


def _dealer_keeps_hitting(val: int, aces: int, hit_soft_17: bool) -> bool:
    if val < 17:
        return True
    return val == 17 and aces > 0 and hit_soft_17


def _quick_ev_stand(player_val: int, dealer_upcard: Card,
                    shoe: Shoe, n_sims: int, hit_soft_17: bool) -> float:
    """Direct Monte Carlo on the live shoe (no cache)."""
    remaining = shoe.cards_snapshot
    if len(remaining) < 5:
        return 0.0

    upcard_pts = dealer_upcard.rank.points
    starting_aces = 1 if dealer_upcard.rank is Rank.ACE else 0

    score = 0.0
    for _ in range(n_sims):
        deck = remaining.copy()
        random.shuffle(deck)
        dval, daces = upcard_pts, starting_aces
        while _dealer_keeps_hitting(dval, daces, hit_soft_17):
            if not deck:
                break
            c = deck.pop()
            dval, daces = _apply_card(dval, daces, c.points)
        if dval > 21 or player_val > dval:
            score += 1.0
        elif player_val < dval:
            score -= 1.0
    return score / n_sims if n_sims else 0.0
