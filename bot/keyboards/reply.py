from aiogram.types import ReplyKeyboardMarkup, KeyboardButton


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="👤 Profile"), KeyboardButton(text="📜 Quests")],
            [KeyboardButton(text="🏪 Shop"), KeyboardButton(text="🏰 Guild")],
            [KeyboardButton(text="🎮 Games"), KeyboardButton(text="❓ Help")],
        ],
        resize_keyboard=True,
    )
    return kb


def admin_keyboard() -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="⚙️ Settings"), KeyboardButton(text="📊 Stats")],
            [KeyboardButton(text="👑 Manage Users"), KeyboardButton(text="📢 Announce")],
            [KeyboardButton(text="🛡️ Anti-Spam"), KeyboardButton(text="🔄 Reset User")],
            [KeyboardButton(text="🔙 Back to Menu")],
        ],
        resize_keyboard=True,
    )
    return kb
