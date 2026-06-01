"""Headless backtester: simulate strategies over thousands of hands.

Usage:
    python -m blackjack.backtest --hands 10000
    python -m blackjack.backtest --hands 50000 --counting hi-lo --seed 42
    python -m blackjack.backtest --hands 100000 --bankroll 10000 --decks 6

Output:
    summary table with PnL, ROI, win rate, sigma, P(bankruptcy at N).

Limitations:
    * Uses basic strategy (optionally with Hi-Lo Index Plays) for player
      decisions. No splits in the backtester (treated as Hit) to keep
      the simulator simple; splits are rare enough that their impact on
      the headline ROI is small.
    * Bet sizing: flat min_bet by default, or TC-ramped when --counting
      hi-lo is passed.
"""
from __future__ import annotations

import argparse
import math
import random
import statistics
import sys

from .actions import Action
from .basic_strategy import optimal_action
from .counter import CardCounter
from .dealer import StandardDealer
from .models import Hand, HandState, Rank, Shoe
from .strategy_deviations import (
    index_decision,
    recommend_bet,
    should_take_insurance,
)


def simulate(
    hands: int,
    *,
    bankroll: int = 10_000,
    min_bet: int = 10,
    n_decks: int = 6,
    blackjack_payout: float = 1.5,
    hit_soft_17: bool = False,
    use_counting: bool = False,
    seed: int | None = None,
) -> dict[str, float | int]:
    """Run `hands` rounds and return aggregate statistics.

    Tracks balance after every hand to compute sigma and bankruptcy rate.
    """
    rng = random.Random(seed)
    shoe = Shoe(n_decks=n_decks, rng=rng)
    dealer_strategy = StandardDealer(hit_soft_17=hit_soft_17)
    counter = CardCounter()
    shoe.on_reshuffle(counter.reset)

    balance = bankroll
    rounds_played = 0
    wins = losses = pushes = surrenders = blackjacks_done = 0
    bankruptcy_hand: int | None = None
    balance_curve = [balance]

    while rounds_played < hands and balance >= min_bet:
        tc = counter.true_count(shoe.remaining_decks) if use_counting else 0.0

        # Bet sizing
        bet = recommend_bet(tc, min_bet) if use_counting else min_bet
        if bet > balance:
            bet = (balance // min_bet) * min_bet
        if bet < min_bet:
            break

        balance -= bet

        # Deal
        player = Hand(bet=bet)
        dealer = Hand()
        player.add(_draw(shoe, counter))
        dealer.add(_draw(shoe, counter))
        player.add(_draw(shoe, counter))
        dealer.add(_draw(shoe, counter))

        # Insurance side bet (only if dealer shows Ace and counting on)
        insurance_paid = 0
        if (use_counting
                and dealer.cards[1].rank is Rank.ACE
                and should_take_insurance(tc)):
            ins = bet // 2
            if ins <= balance:
                balance -= ins
                if dealer.is_blackjack:
                    balance += ins * 3
                else:
                    insurance_paid = -ins

        # Naturals
        if dealer.is_blackjack and player.is_blackjack:
            balance += bet
            pushes += 1
            rounds_played += 1
            balance_curve.append(balance)
            continue
        if player.is_blackjack:
            balance += int(bet + bet * blackjack_payout)
            wins += 1
            blackjacks_done += 1
            rounds_played += 1
            balance_curve.append(balance)
            continue
        if dealer.is_blackjack:
            losses += 1
            balance += insurance_paid
            rounds_played += 1
            balance_curve.append(balance)
            continue

        # Player decisions (no splits in the backtester; treat as Hit)
        while player.state is HandState.ACTIVE:
            action: Action | None = None
            if use_counting:
                action = index_decision(player, dealer.cards[1], tc,
                                        allow_surrender=True)
            if action is None:
                action = optimal_action(
                    player, dealer.cards[1],
                    allow_double=(len(player.cards) == 2 and balance >= bet),
                    allow_split=False,
                    allow_surrender=(len(player.cards) == 2),
                )

            if action is Action.HIT:
                player.add(_draw(shoe, counter))
            elif action is Action.STAND:
                player.stand()
            elif action is Action.DOUBLE:
                if balance >= bet and len(player.cards) == 2:
                    balance -= bet
                    player.bet *= 2
                    player.is_doubled = True
                    player.add(_draw(shoe, counter))
                    if player.state is HandState.ACTIVE:
                        player.stand()
                else:
                    player.add(_draw(shoe, counter))
            elif action is Action.SURRENDER:
                player.surrender()
                balance += player.bet // 2
            elif action is Action.SPLIT:
                # Backtester treats pair-as-hit; encode as Hit.
                player.add(_draw(shoe, counter))

        if player.state is HandState.SURRENDER:
            surrenders += 1
            rounds_played += 1
            balance_curve.append(balance)
            continue

        if player.state is HandState.BUST:
            losses += 1
            rounds_played += 1
            balance_curve.append(balance)
            continue

        # Dealer turn
        while dealer_strategy.should_hit(dealer):
            dealer.add(_draw(shoe, counter))

        pv = player.value
        dv = dealer.value
        if dv > 21 or pv > dv:
            balance += player.bet * 2
            wins += 1
        elif pv == dv:
            balance += player.bet
            pushes += 1
        else:
            losses += 1

        rounds_played += 1
        balance_curve.append(balance)

        if balance < min_bet and bankruptcy_hand is None:
            bankruptcy_hand = rounds_played

    decided = wins + losses + pushes + surrenders
    win_rate = wins / decided if decided else 0.0
    profit = balance - bankroll
    roi = profit / (rounds_played * min_bet) if rounds_played else 0.0

    diffs = [balance_curve[i + 1] - balance_curve[i]
             for i in range(len(balance_curve) - 1)]
    sigma_per_hand = statistics.pstdev(diffs) if len(diffs) > 1 else 0.0
    sharpe_like = (statistics.mean(diffs) / sigma_per_hand
                   * math.sqrt(rounds_played)
                   if sigma_per_hand and rounds_played else 0.0)

    return {
        "hands_played": rounds_played,
        "starting_bankroll": bankroll,
        "final_balance": balance,
        "profit": profit,
        "roi_per_unit": roi,
        "win_rate": win_rate,
        "wins": wins,
        "losses": losses,
        "pushes": pushes,
        "surrenders": surrenders,
        "blackjacks": blackjacks_done,
        "sigma_per_hand": sigma_per_hand,
        "sharpe_like": sharpe_like,
        "bankrupt_at_hand": bankruptcy_hand,
    }


def _draw(shoe: Shoe, counter: CardCounter):
    card = shoe.draw()
    counter.update(card)
    return card


# ── CLI ──────────────────────────────────────────────────────────────────────


def _format_report(stats: dict[str, float | int]) -> str:
    lines = [
        "==========================================",
        "  BLACKJACK BACKTEST REPORT",
        "==========================================",
        f"  Hands played:    {stats['hands_played']:,}",
        f"  Starting:        ${stats['starting_bankroll']:,}",
        f"  Final balance:   ${stats['final_balance']:,}",
        f"  Profit:          ${stats['profit']:+,}",
        f"  ROI per unit:    {stats['roi_per_unit'] * 100:+.3f}%",
        "  ----- Outcomes -----",
        f"  Wins:            {stats['wins']:,}",
        f"  Losses:          {stats['losses']:,}",
        f"  Pushes:          {stats['pushes']:,}",
        f"  Surrenders:      {stats['surrenders']:,}",
        f"  Blackjacks:      {stats['blackjacks']:,}",
        f"  Win rate:        {stats['win_rate'] * 100:.2f}%",
        "  ----- Risk -----",
        f"  Sigma / hand:    ${stats['sigma_per_hand']:,.2f}",
        f"  Sharpe-like:     {stats['sharpe_like']:+.3f}",
        f"  Bankrupt at:     {stats['bankrupt_at_hand'] or 'never'}",
        "==========================================",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="blackjack-backtest",
        description=("Run a headless Blackjack simulation and report PnL, "
                     "win rate, sigma, and bankruptcy."),
    )
    parser.add_argument("--hands", type=int, default=10_000,
                        help="Number of rounds to simulate (default 10000).")
    parser.add_argument("--bankroll", type=int, default=10_000,
                        help="Starting bankroll in units (default 10000).")
    parser.add_argument("--min-bet", type=int, default=10,
                        help="Minimum bet per hand (default 10).")
    parser.add_argument("--decks", type=int, default=6,
                        help="Decks in the shoe (default 6).")
    parser.add_argument("--bj-payout", type=float, default=1.5,
                        help="Blackjack payout multiplier (default 1.5 = 3:2).")
    parser.add_argument("--hit-soft-17", action="store_true",
                        help="Dealer hits soft 17 (default Stand).")
    parser.add_argument("--counting", choices=["off", "hi-lo"], default="off",
                        help=("Use Hi-Lo counting with Index Plays and a "
                              "TC-based bet ramp (default off)."))
    parser.add_argument("--seed", type=int, default=None,
                        help="Optional RNG seed for reproducibility.")
    args = parser.parse_args(argv)

    stats = simulate(
        hands=args.hands,
        bankroll=args.bankroll,
        min_bet=args.min_bet,
        n_decks=args.decks,
        blackjack_payout=args.bj_payout,
        hit_soft_17=args.hit_soft_17,
        use_counting=(args.counting == "hi-lo"),
        seed=args.seed,
    )
    print(_format_report(stats))
    return 0


if __name__ == "__main__":
    sys.exit(main())
