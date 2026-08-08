from __future__ import annotations

from bot.handlers.message_handler import router as message_router
from bot.handlers.command_handlers import router as command_router
from bot.handlers.admin_handlers import router as admin_router
from bot.handlers.callback_handlers import router as callback_router
from bot.handlers.game_handlers import router as game_router

__all__ = [
    "message_router",
    "command_router",
    "admin_router",
    "callback_router",
    "game_router",
]
