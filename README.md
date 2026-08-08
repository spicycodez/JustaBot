# JustaBot — ChatQuest: Telegram RPG Community Bot

> **"Level up your community."**

ChatQuest transforms any Telegram group into an RPG game. Instead of simply counting messages, the bot rewards **meaningful participation** — members gain XP by chatting, inviting members, helping others, hosting events, completing quests, winning team battles, and staying active.

## Features

### Core Systems
- **XP System** — Intelligent scoring based on message length, replies, reactions, files, and more
- **Level System** — Progressive leveling (`100 × Level^1.5`) with rank titles (Newcomer → Mythic)
- **Coins & Economy** — Separate currency from quests, events, battles, and daily rewards
- **Anti-Spam** — Cooldowns, duplicate detection, emoji/link/sticker filtering, escalating XP freezes

### Engagement Systems
- **Daily & Weekly Quests** — 3 Easy + 2 Medium + 1 Hard daily, plus weekly missions
- **Streak System** — Daily activity tracking with escalating bonuses (1d 🔥 → 100d 🌟)
- **Achievements** — 20+ badges for milestones (First Message, Night Owl, Champion, Legend, etc.)
- **Reputation** — `/thanks @user` with daily limits and tiered rewards

### Community Systems
- **Guild System** — Create/join guilds (Blue Dragons, Shadow Wolves, Phoenix, Storm Knights, etc.)
- **Guild Battles** — Weekly team competitions with score tracking and exclusive rewards
- **Events** — Admin-created trivia, quizzes, movie nights, gaming, AMA, voice chat events
- **Seasons** — Monthly leaderboard resets with permanent history and tiered rewards
- **Referral System** — Unique invite links with join/active/level-up bonuses

### Fun & Rewards
- **Mini Games** — Dice, Rock-Paper-Scissors, Trivia, Math Challenge, Number Guess, Word Scramble, Hangman
- **Loot Boxes** — 5 rarities (Common → Mythic) with weighted random rewards
- **Lucky Wheel** — Daily spin for coins, XP, boosts, chests, and badges
- **Shop** — Titles, role colors, XP boosts, loot boxes, guild buffs, name effects, chat decorations
- **Temporary Powers** — 2x XP, Double Coins, Lucky Boost, Quest Skip, Streak Freeze

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Language | Python 3.12+ |
| Telegram Library | Aiogram 3.x |
| Database | MongoDB Atlas (Motor + Beanie ODM) |
| Cache | Redis (async) |
| Scheduler | APScheduler |
| Config | python-dotenv + pydantic-settings |

## Project Structure

```
├── .env.example
├── .gitignore
├── Dockerfile
├── docker-compose.yml
├── Procfile
├── requirements.txt
├── runtime.txt
├── bot/
│   ├── __init__.py
│   ├── main.py
│   ├── config.py
│   ├── database.py
│   ├── cache.py
│   ├── scheduler.py
│   ├── models/
│   │   ├── user.py
│   │   ├── guild.py
│   │   ├── quest.py
│   │   ├── achievement.py
│   │   ├── event.py
│   │   ├── battle.py
│   │   ├── season.py
│   │   ├── economy.py
│   │   ├── referral.py
│   │   └── settings.py
│   ├── services/
│   │   ├── xp_service.py
│   │   ├── level_service.py
│   │   ├── coins_service.py
│   │   ├── streak_service.py
│   │   ├── reputation_service.py
│   │   ├── anti_spam.py
│   │   ├── guild_service.py
│   │   ├── quest_service.py
│   │   ├── achievement_service.py
│   │   ├── leaderboard_service.py
│   │   ├── event_service.py
│   │   ├── battle_service.py
│   │   ├── economy_service.py
│   │   ├── referral_service.py
│   │   ├── season_service.py
│   │   └── minigames_service.py
│   ├── handlers/
│   │   ├── message_handler.py
│   │   ├── command_handlers.py
│   │   ├── admin_handlers.py
│   │   ├── callback_handlers.py
│   │   └── game_handlers.py
│   ├── utils/
│   │   ├── helpers.py
│   │   └── formatters.py
│   └── keyboards/
│       ├── inline.py
│       └── reply.py
├── data/
│   ├── quests.json
│   ├── achievements.json
│   ├── shop_items.json
│   ├── minigames.json
│   └── guild_templates.json
└── tests/
    └── test_xp.py
```

## Setup

### 1. Clone & Install

```bash
git clone https://github.com/spicycodez/JustaBot.git
cd JustaBot
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure

```bash
cp .env.example .env
# Edit .env with your BOT_TOKEN, MONGODB_URI, ADMIN_IDS
```

### 3. Run

**With Docker (recommended):**
```bash
docker-compose up -d
```

**Locally:**
```bash
python -m bot.main
```

### 4. Deploy

Push to Heroku, Railway, Render, or any VPS. A `Procfile` and `runtime.txt` are included.

## Commands

### User Commands
| Command | Description |
|---------|-------------|
| `/start` | Start bot, check referral |
| `/help` | All commands |
| `/profile` | RPG profile |
| `/rank` | Rank & level progress |
| `/leaderboard` | XP leaderboard |
| `/coins` | Coin balance |
| `/streak` | Streak info |
| `/quests` | Daily & weekly quests |
| `/daily` | Claim daily reward |
| `/shop` | Item shop |
| `/inventory` | Your items |
| `/guild` | Guild info |
| `/battle` | Guild battles |
| `/achievements` | Badges |
| `/stats` | Statistics |
| `/invite` | Referral link |
| `/tophelpers` | Reputation leaderboard |
| `/topinvites` | Invite leaderboard |
| `/guilds` | Guild leaderboard |

### Mini Games
`/dice` `/rps` `/trivia` `/math` `/guess` `/word` `/hangman`

### Admin Commands
`/settings` `/addxp` `/removexp` `/addcoins` `/createquest` `/createevent` `/endevent` `/resetseason` `/createguild` `/givebadge` `/banxp` `/unbanxp` `/setxp` `/setlevel` `/givereward`

## XP Table

| Action | XP |
|--------|-----|
| Short message (10-40 chars) | +2 |
| Long message (40+ chars) | +5 |
| Helpful reply | +8 |
| Heart reaction | +6 |
| Message pinned | +15 |
| File shared | +10 |
| Voice chat | +20 |
| Event hosted | +40 |
| Member invited | +50 |
| Referral 7-day active | +150 |
| Quest completed | +100 |
| Battle win | +300 |

## License

MIT License
