"""Basic tests for ChatQuest bot services."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestLevelService:
    def test_xp_required_level_1(self):
        from bot.services.level_service import xp_required
        assert xp_required(1) == 100

    def test_xp_required_level_5(self):
        from bot.services.level_service import xp_required
        assert 1100 <= xp_required(5) <= 1120

    def test_xp_required_level_10(self):
        from bot.services.level_service import xp_required
        assert 3150 <= xp_required(10) <= 3170

    def test_xp_required_level_20(self):
        from bot.services.level_service import xp_required
        assert 8900 <= xp_required(20) <= 9000

    def test_get_level_from_xp_0(self):
        from bot.services.level_service import get_level_from_xp
        assert get_level_from_xp(0) == 1

    def test_get_rank_title_newcomer(self):
        from bot.services.level_service import get_rank_title
        assert get_rank_title(1) == "Newcomer"
        assert get_rank_title(4) == "Newcomer"

    def test_get_rank_title_villager(self):
        from bot.services.level_service import get_rank_title
        assert get_rank_title(5) == "Villager"
        assert get_rank_title(9) == "Villager"

    def test_get_rank_title_mythic(self):
        from bot.services.level_service import get_rank_title
        assert get_rank_title(40) == "Mythic"


class TestHelpers:
    def test_format_number(self):
        from bot.utils.helpers import format_number
        assert format_number(19300) == "19,300"
        assert format_number(100) == "100"

    def test_generate_unique_id(self):
        from bot.utils.helpers import generate_unique_id
        id1 = generate_unique_id("test")
        assert id1.startswith("test")

    def test_format_xp_bar_full(self):
        from bot.utils.helpers import format_xp_bar
        assert "100%" in format_xp_bar(100, 100)

    def test_generate_referral_code(self):
        from bot.utils.helpers import generate_referral_code
        code = generate_referral_code(12345)
        assert "CQ" in code


class TestStreakService:
    def test_format_streak_1(self):
        from bot.services.streak_service import format_streak
        assert "\U0001f525" in format_streak(1)

    def test_format_streak_7(self):
        from bot.services.streak_service import format_streak
        assert "\U0001f525\U0001f525" in format_streak(7)

    def test_format_streak_30(self):
        from bot.services.streak_service import format_streak
        assert "\U0001f451" in format_streak(30)

    def test_format_streak_100(self):
        from bot.services.streak_service import format_streak
        assert "\U0001f31f" in format_streak(100)


class TestXPService:
    def test_calculate_xp_short(self):
        from bot.services.xp_service import calculate_message_xp
        assert calculate_message_xp("hi", False, False) == 0

    def test_calculate_xp_medium(self):
        from bot.services.xp_service import calculate_message_xp
        assert calculate_message_xp("This is a medium message", False, False) == 2

    def test_calculate_xp_long(self):
        from bot.services.xp_service import calculate_message_xp
        assert calculate_message_xp("This is a very long message that gives more XP", False, False) == 5

    def test_calculate_xp_reply(self):
        from bot.services.xp_service import calculate_message_xp
        assert calculate_message_xp("Reply text here", True, False) >= 10

    def test_calculate_xp_file(self):
        from bot.services.xp_service import calculate_message_xp
        assert calculate_message_xp("Check this", False, True) >= 12


class TestCoinsService:
    def test_daily_reward_day1(self):
        from bot.services.coins_service import get_daily_reward
        assert get_daily_reward(1)["coins"] == 100

    def test_daily_reward_day2(self):
        from bot.services.coins_service import get_daily_reward
        assert get_daily_reward(2)["coins"] == 150

    def test_daily_reward_day7(self):
        from bot.services.coins_service import get_daily_reward
        r = get_daily_reward(7)
        assert r.get("chest") or r.get("loot_box") is not None

    def test_daily_reward_day30(self):
        from bot.services.coins_service import get_daily_reward
        r = get_daily_reward(30)
        assert r.get("chest") or r.get("title") is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
