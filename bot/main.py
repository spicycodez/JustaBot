import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from aiogram.types import BotCommand

from bot.config import settings
from bot.database import init_db
from bot.cache import init_redis
from bot.scheduler import init_scheduler, start_scheduler, shutdown_scheduler
from bot.handlers.message_handler import router as message_router
from bot.handlers.command_handlers import router as command_router
from bot.handlers.admin_handlers import router as admin_router
from bot.handlers.callback_handlers import router as callback_router
from bot.handlers.game_handlers import router as game_router

logging.basicConfig(
    level=settings.LOG_LEVEL,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def main() -> None:
    bot = Bot(token=settings.BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    # Register routers – order matters: commands first, then callbacks,
    # then game callbacks, then catch-all message handler last.
    dp.include_router(command_router)
    dp.include_router(admin_router)
    dp.include_router(callback_router)
    dp.include_router(game_router)
    dp.include_router(message_router)

    # Initialise persistence & background tasks
    await init_db()
    await init_redis()
    init_scheduler()
    start_scheduler()

    # Set bot commands visible in the Telegram client menu
    await bot.set_my_commands([
        BotCommand(command="start", description="Start the bot"),
        BotCommand(command="help", description="Show all commands"),
        BotCommand(command="profile", description="View your RPG profile"),
        BotCommand(command="leaderboard", description="XP Leaderboard"),
        BotCommand(command="quests", description="Daily & weekly quests"),
        BotCommand(command="daily", description="Claim daily reward"),
        BotCommand(command="shop", description="Open shop"),
        BotCommand(command="guild", description="Guild info"),
        BotCommand(command="battle", description="Guild battles"),
        BotCommand(command="achievements", description="Your achievements"),
        BotCommand(command="stats", description="Detailed statistics"),
        BotCommand(command="invite", description="Get referral link"),
    ])

    logger.info("ChatQuest Bot starting...")
    try:
        await dp.start_polling(bot)
    finally:
        shutdown_scheduler()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
