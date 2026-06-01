"""Cross-session player profile stored in ~/.blackjack_edu/profile.json.

Captured fields:
  * Lifetime hand stats: rounds, wins, losses, pushes, surrenders,
    blackjacks, profit. Updated at end of each session.
  * Trainer stats: total asked, total correct, per-topic correct/asked
    counters used by the adaptive selector.
  * Session log: short list of last N session summaries (date, profit,
    accuracy) for the profile screen.

The format is plain JSON; old files are migrated leniently (missing
keys default to zero).
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

PROFILE_DIR = Path.home() / ".blackjack_edu"
PROFILE_PATH = PROFILE_DIR / "profile.json"
SESSION_LOG_LIMIT = 30


@dataclass
class TopicStats:
    asked: int = 0
    correct: int = 0

    @property
    def accuracy(self) -> float:
        return self.correct / self.asked if self.asked else 0.0


@dataclass
class Profile:
    rounds: int = 0
    wins: int = 0
    losses: int = 0
    pushes: int = 0
    surrenders: int = 0
    blackjacks: int = 0
    profit: int = 0
    trainer_asked: int = 0
    trainer_correct: int = 0
    max_streak: int = 0
    topic_stats: dict[str, TopicStats] = field(default_factory=dict)
    session_log: list[dict[str, Any]] = field(default_factory=list)

    @property
    def trainer_accuracy(self) -> float:
        return (self.trainer_correct / self.trainer_asked
                if self.trainer_asked else 0.0)

    def topic(self, name: str) -> TopicStats:
        ts = self.topic_stats.get(name)
        if ts is None:
            ts = TopicStats()
            self.topic_stats[name] = ts
        return ts

    def weakest_topics(self, min_asked: int = 5, k: int = 3) -> list[str]:
        ranked = [
            (name, ts.accuracy)
            for name, ts in self.topic_stats.items()
            if ts.asked >= min_asked
        ]
        ranked.sort(key=lambda x: x[1])
        return [name for name, _ in ranked[:k]]

    # ── Serialization ────────────────────────────────────────────────────

    def to_dict(self) -> dict[str, Any]:
        return {
            "rounds": self.rounds,
            "wins": self.wins,
            "losses": self.losses,
            "pushes": self.pushes,
            "surrenders": self.surrenders,
            "blackjacks": self.blackjacks,
            "profit": self.profit,
            "trainer_asked": self.trainer_asked,
            "trainer_correct": self.trainer_correct,
            "max_streak": self.max_streak,
            "topic_stats": {
                name: {"asked": ts.asked, "correct": ts.correct}
                for name, ts in self.topic_stats.items()
            },
            "session_log": self.session_log[-SESSION_LOG_LIMIT:],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Profile:
        p = cls(
            rounds=int(data.get("rounds", 0)),
            wins=int(data.get("wins", 0)),
            losses=int(data.get("losses", 0)),
            pushes=int(data.get("pushes", 0)),
            surrenders=int(data.get("surrenders", 0)),
            blackjacks=int(data.get("blackjacks", 0)),
            profit=int(data.get("profit", 0)),
            trainer_asked=int(data.get("trainer_asked", 0)),
            trainer_correct=int(data.get("trainer_correct", 0)),
            max_streak=int(data.get("max_streak", 0)),
        )
        for name, ts_data in (data.get("topic_stats") or {}).items():
            p.topic_stats[name] = TopicStats(
                asked=int(ts_data.get("asked", 0)),
                correct=int(ts_data.get("correct", 0)),
            )
        p.session_log = list(data.get("session_log") or [])
        return p

    # ── Mutators called from game/trainer at session end ────────────────

    def record_session(
        self,
        *,
        rounds: int,
        wins: int,
        losses: int,
        pushes: int,
        surrenders: int,
        blackjacks: int,
        profit_delta: int,
        trainer_asked: int,
        trainer_correct: int,
        max_streak: int,
        per_topic: dict[str, tuple[int, int]] | None = None,
    ) -> None:
        self.rounds += rounds
        self.wins += wins
        self.losses += losses
        self.pushes += pushes
        self.surrenders += surrenders
        self.blackjacks += blackjacks
        self.profit += profit_delta
        self.trainer_asked += trainer_asked
        self.trainer_correct += trainer_correct
        self.max_streak = max(self.max_streak, max_streak)

        for topic, (asked, correct) in (per_topic or {}).items():
            ts = self.topic(topic)
            ts.asked += asked
            ts.correct += correct

        self.session_log.append({
            "date": datetime.now(UTC).isoformat(timespec="seconds"),
            "rounds": rounds,
            "profit_delta": profit_delta,
            "trainer_accuracy": (
                trainer_correct / trainer_asked if trainer_asked else 0.0
            ),
        })
        if len(self.session_log) > SESSION_LOG_LIMIT:
            self.session_log = self.session_log[-SESSION_LOG_LIMIT:]


def load_profile(path: Path = PROFILE_PATH) -> Profile:
    if not path.exists():
        return Profile()
    try:
        with path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, json.JSONDecodeError):
        return Profile()
    return Profile.from_dict(data)


def save_profile(profile: Profile, path: Path = PROFILE_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as fh:
        json.dump(profile.to_dict(), fh, indent=2, ensure_ascii=False)
    os.replace(tmp, path)
