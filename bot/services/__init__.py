# ChatQuest Service Modules

from bot.services.guild_service import (
    create_guild,
    join_guild,
    leave_guild,
    get_guild_info,
    get_guild_leaderboard,
    add_guild_xp,
    update_guild_rankings,
    get_guild_members,
    disband_guild,
    transfer_ownership,
    set_guild_emblem,
)

from bot.services.quest_service import (
    generate_daily_quests,
    generate_weekly_quests,
    update_quest_progress,
    complete_quest,
    claim_quest_reward,
    get_user_quests,
    reset_all_daily_quests,
    reset_all_weekly_quests,
)

from bot.services.achievement_service import (
    check_achievements,
    award_achievement,
    get_user_achievements,
    get_all_achievements,
    get_achievement_progress,
)

from bot.services.leaderboard_service import (
    get_xp_leaderboard,
    get_coins_leaderboard,
    get_streak_leaderboard,
    get_helpers_leaderboard,
    get_invites_leaderboard,
    get_guild_leaderboard,
    update_leaderboard_cache,
    get_cached_leaderboard,
    get_user_rank,
)

from bot.services.event_service import (
    create_event,
    start_event,
    join_event,
    end_event,
    get_active_events,
    get_user_events,
    cancel_event,
)

from bot.services.battle_service import (
    create_battle,
    start_battle,
    update_battle_score,
    end_battle,
    get_active_battles,
    get_battle_info,
    auto_match_guilds,
)

from bot.services.economy_service import (
    get_shop_items,
    purchase_item,
    use_item,
    get_user_inventory,
    open_loot_box,
    spin_lucky_wheel,
    get_or_create_user,
)

from bot.services.referral_service import (
    generate_referral_link,
    process_referral_join,
    activate_referral,
    check_level5_bonus,
    get_referral_stats,
    cleanup_stale_referrals,
)

from bot.services.season_service import (
    get_current_season,
    create_new_season,
    reset_season,
    get_season_leaderboard,
    get_season_info,
)

from bot.services.minigames_service import (
    play_dice,
    play_rps,
    play_trivia,
    play_math,
    play_guess,
    play_word,
    play_hangman,
    check_minigame_cooldown,
    award_minigame_xp,
    verify_trivia_answer,
    verify_math_answer,
    verify_word_answer,
    check_guess,
    check_hangman_letter,
)

__all__ = [
    # Guild
    "create_guild", "join_guild", "leave_guild", "get_guild_info",
    "get_guild_leaderboard", "add_guild_xp", "update_guild_rankings",
    "get_guild_members", "disband_guild", "transfer_ownership", "set_guild_emblem",
    # Quests
    "generate_daily_quests", "generate_weekly_quests", "update_quest_progress",
    "complete_quest", "claim_quest_reward", "get_user_quests",
    "reset_all_daily_quests", "reset_all_weekly_quests",
    # Achievements
    "check_achievements", "award_achievement", "get_user_achievements",
    "get_all_achievements", "get_achievement_progress",
    # Leaderboard
    "get_xp_leaderboard", "get_coins_leaderboard", "get_streak_leaderboard",
    "get_helpers_leaderboard", "get_invites_leaderboard", "get_guild_leaderboard",
    "update_leaderboard_cache", "get_cached_leaderboard", "get_user_rank",
    # Events
    "create_event", "start_event", "join_event", "end_event",
    "get_active_events", "get_user_events", "cancel_event",
    # Battles
    "create_battle", "start_battle", "update_battle_score", "end_battle",
    "get_active_battles", "get_battle_info", "auto_match_guilds",
    # Economy
    "get_shop_items", "purchase_item", "use_item", "get_user_inventory",
    "open_loot_box", "spin_lucky_wheel", "get_or_create_user",
    # Referrals
    "generate_referral_link", "process_referral_join", "activate_referral",
    "check_level5_bonus", "get_referral_stats", "cleanup_stale_referrals",
    # Seasons
    "get_current_season", "create_new_season", "reset_season",
    "get_season_leaderboard", "get_season_info",
    # Minigames
    "play_dice", "play_rps", "play_trivia", "play_math", "play_guess",
    "play_word", "play_hangman", "check_minigame_cooldown", "award_minigame_xp",
    "verify_trivia_answer", "verify_math_answer", "verify_word_answer",
    "check_guess", "check_hangman_letter",
]
