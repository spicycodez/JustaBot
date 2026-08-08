"""APScheduler-based task scheduler for periodic jobs."""

from __future__ import annotations

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler

logger = logging.getLogger(__name__)

_scheduler: AsyncIOScheduler | None = None


def init_scheduler() -> AsyncIOScheduler:
    """Create the scheduler and register all periodic jobs."""
    global _scheduler
    _scheduler = AsyncIOScheduler(timezone="UTC")

    # ── Daily quest reset – every day at midnight UTC ────────────────────
    _scheduler.add_job(
        _job_reset_daily_quests,
        trigger="cron",
        hour=0,
        minute=0,
        id="reset_daily_quests",
        replace_existing=True,
    )

    # ── Weekly quest reset – every Monday at midnight UTC ────────────────
    _scheduler.add_job(
        _job_reset_weekly_quests,
        trigger="cron",
        day_of_week="mon",
        hour=0,
        minute=0,
        id="reset_weekly_quests",
        replace_existing=True,
    )

    # ── Season reset check – daily at 00:05 UTC ─────────────────────────
    _scheduler.add_job(
        _job_check_season_reset,
        trigger="cron",
        hour=0,
        minute=5,
        id="check_season_reset",
        replace_existing=True,
    )

    # ── Stale-data cleanup – daily at 03:00 UTC ─────────────────────────
    _scheduler.add_job(
        _job_cleanup_stale_data,
        trigger="cron",
        hour=3,
        minute=0,
        id="cleanup_stale_data",
        replace_existing=True,
    )

    # ── Guild battle reward distribution – Sunday 20:00 UTC ─────────────
    _scheduler.add_job(
        _job_distribute_guild_battle_rewards,
        trigger="cron",
        day_of_week="sun",
        hour=20,
        minute=0,
        id="distribute_guild_battle_rewards",
        replace_existing=True,
    )

    return _scheduler


def start_scheduler() -> None:
    """Start the scheduler if it has been initialised."""
    if _scheduler is not None:
        _scheduler.start()
        logger.info("Scheduler started.")


def shutdown_scheduler() -> None:
    """Gracefully shut down the scheduler."""
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        logger.info("Scheduler shut down.")


# ── Job implementations (lazy imports for robustness) ─────────────────────


async def _job_reset_daily_quests() -> None:
    try:
        from bot.services.quest_service import reset_daily_quests  # noqa: F811

        await reset_daily_quests()
        logger.info("Daily quests reset completed.")
    except Exception as exc:
        logger.exception("Failed to reset daily quests: %s", exc)


async def _job_reset_weekly_quests() -> None:
    try:
        from bot.services.quest_service import reset_weekly_quests  # noqa: F811

        await reset_weekly_quests()
        logger.info("Weekly quests reset completed.")
    except Exception as exc:
        logger.exception("Failed to reset weekly quests: %s", exc)


async def _job_check_season_reset() -> None:
    try:
        from bot.services.season_service import check_season_reset

        await check_season_reset()
        logger.info("Season reset check completed.")
    except Exception as exc:
        logger.exception("Failed to check season reset: %s", exc)


async def _job_cleanup_stale_data() -> None:
    try:
        from bot.services.cleanup_service import cleanup_stale_data

        await cleanup_stale_data()
        logger.info("Stale data cleanup completed.")
    except Exception as exc:
        logger.exception("Failed to cleanup stale data: %s", exc)


async def _job_distribute_guild_battle_rewards() -> None:
    try:
        from bot.services.guild_service import distribute_guild_battle_rewards

        await distribute_guild_battle_rewards()
        logger.info("Guild battle reward distribution completed.")
    except Exception as exc:
        logger.exception("Failed to distribute guild battle rewards: %s", exc)
