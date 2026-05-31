"""Smoke tests for the headless backtester."""
from __future__ import annotations

from blackjack.backtest import simulate


def test_simulate_deterministic_with_seed():
    a = simulate(hands=200, seed=42)
    b = simulate(hands=200, seed=42)
    assert a["final_balance"] == b["final_balance"]
    assert a["wins"] == b["wins"]
    assert a["losses"] == b["losses"]


def test_simulate_returns_expected_keys():
    s = simulate(hands=100, seed=1)
    required = {
        "hands_played", "starting_bankroll", "final_balance", "profit",
        "roi_per_unit", "win_rate", "wins", "losses", "pushes",
        "surrenders", "blackjacks", "sigma_per_hand", "sharpe_like",
        "bankrupt_at_hand",
    }
    assert required <= set(s)


def test_simulate_hands_count_reasonable():
    """Either we finish all requested hands or we go bankrupt."""
    s = simulate(hands=500, bankroll=1000, min_bet=50, seed=7)
    assert s["hands_played"] <= 500
    assert s["wins"] + s["losses"] + s["pushes"] + s["surrenders"] == s["hands_played"]


def test_simulate_with_counting_runs():
    s = simulate(hands=300, use_counting=True, seed=11)
    assert s["hands_played"] > 0
    assert isinstance(s["sigma_per_hand"], float)


def test_house_edge_roughly_negative_without_counting():
    """Flat-bet basic strategy averages a small negative ROI over many
    hands. We allow generous bounds because variance over 5k hands is
    still wide, but the result should not be wildly positive."""
    s = simulate(hands=5000, bankroll=20000, min_bet=10, seed=2024)
    assert -0.06 < s["roi_per_unit"] < 0.04
