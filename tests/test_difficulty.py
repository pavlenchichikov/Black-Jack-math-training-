"""Tests for difficulty presets."""

from blackjack.difficulty import DIFFICULTY_PRESETS, DifficultyLevel


class TestDifficultyPresets:
    def test_all_levels_present(self):
        for level in DifficultyLevel:
            assert level in DIFFICULTY_PRESETS

    def test_easy_is_generous(self):
        cfg = DIFFICULTY_PRESETS[DifficultyLevel.EASY]
        assert cfg.starting_balance >= 1000
        assert cfg.show_prob_hud is True
        assert cfg.show_optimal_hint is True

    def test_hard_is_punishing(self):
        cfg = DIFFICULTY_PRESETS[DifficultyLevel.HARD]
        assert cfg.starting_balance <= 500
        assert cfg.blackjack_payout < 1.5  # 6:5
        assert cfg.show_prob_hud is False

    def test_description_not_empty(self):
        for cfg in DIFFICULTY_PRESETS.values():
            assert len(cfg.description) > 0

    def test_challenge_levels_valid(self):
        for cfg in DIFFICULTY_PRESETS.values():
            for lvl in cfg.allowed_challenge_levels:
                assert lvl in (1, 2, 3)
