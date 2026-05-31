"""Tests for the JSON profile persistence layer."""
from __future__ import annotations

import json

from blackjack.persistence import Profile, load_profile, save_profile


def test_round_trip(tmp_path):
    path = tmp_path / "profile.json"
    p = Profile()
    p.record_session(
        rounds=10, wins=5, losses=3, pushes=1, surrenders=1,
        blackjacks=1, profit_delta=120,
        trainer_asked=8, trainer_correct=6, max_streak=4,
        per_topic={"bust_prob": (3, 2), "bayes": (2, 1)},
    )
    save_profile(p, path)
    loaded = load_profile(path)
    assert loaded.rounds == 10
    assert loaded.wins == 5
    assert loaded.profit == 120
    assert loaded.trainer_accuracy == 6 / 8
    assert loaded.topic_stats["bust_prob"].asked == 3
    assert loaded.topic_stats["bust_prob"].correct == 2
    assert loaded.topic_stats["bayes"].accuracy == 0.5
    assert len(loaded.session_log) == 1


def test_load_missing_file_returns_empty_profile(tmp_path):
    path = tmp_path / "does_not_exist.json"
    p = load_profile(path)
    assert p.rounds == 0
    assert p.trainer_asked == 0
    assert p.topic_stats == {}


def test_load_corrupt_file_returns_empty_profile(tmp_path):
    path = tmp_path / "broken.json"
    path.write_text("{not: valid json", encoding="utf-8")
    p = load_profile(path)
    assert p.rounds == 0


def test_two_sessions_accumulate(tmp_path):
    path = tmp_path / "profile.json"
    p = load_profile(path)
    p.record_session(
        rounds=5, wins=2, losses=2, pushes=1, surrenders=0,
        blackjacks=0, profit_delta=-30,
        trainer_asked=4, trainer_correct=2, max_streak=2,
        per_topic={"bust_prob": (2, 1)},
    )
    save_profile(p, path)

    p2 = load_profile(path)
    p2.record_session(
        rounds=3, wins=2, losses=1, pushes=0, surrenders=0,
        blackjacks=1, profit_delta=70,
        trainer_asked=2, trainer_correct=2, max_streak=3,
        per_topic={"bust_prob": (1, 1), "bayes": (1, 0)},
    )
    save_profile(p2, path)

    final = load_profile(path)
    assert final.rounds == 8
    assert final.wins == 4
    assert final.profit == 40
    assert final.max_streak == 3
    assert final.topic_stats["bust_prob"].asked == 3
    assert final.topic_stats["bust_prob"].correct == 2
    assert final.topic_stats["bayes"].asked == 1
    assert len(final.session_log) == 2


def test_weakest_topics_ranking(tmp_path):
    p = Profile()
    p.topic("hard").asked = 10
    p.topic("hard").correct = 2
    p.topic("medium").asked = 10
    p.topic("medium").correct = 5
    p.topic("easy").asked = 10
    p.topic("easy").correct = 9
    p.topic("brand_new").asked = 1  # below min_asked threshold
    p.topic("brand_new").correct = 1
    weakest = p.weakest_topics(min_asked=5, k=3)
    assert weakest[0] == "hard"
    assert weakest[1] == "medium"
    assert weakest[2] == "easy"
    assert "brand_new" not in weakest


def test_session_log_capped(tmp_path):
    p = Profile()
    for _ in range(50):
        p.record_session(
            rounds=1, wins=1, losses=0, pushes=0, surrenders=0,
            blackjacks=0, profit_delta=1,
            trainer_asked=0, trainer_correct=0, max_streak=0,
        )
    assert len(p.session_log) <= 30
