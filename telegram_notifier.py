import asyncio
import logging
import re
from datetime import datetime

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError, TelegramAPIError
from dotenv import load_dotenv
import os

load_dotenv()

logger = logging.getLogger("telegram_notifier")

TELEGRAM_ENABLED = False
bot = None

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

STRONG_BULL_THRESHOLD = int(os.getenv("STRONG_BULL_THRESHOLD", 78))
STRONG_BEAR_THRESHOLD = int(os.getenv("STRONG_BEAR_THRESHOLD", 22))
VERY_STRONG_BULL = int(os.getenv("VERY_STRONG_BULL", 88))
VERY_STRONG_BEAR = int(os.getenv("VERY_STRONG_BEAR", 12))
TREND_CHANGE_THRESHOLD = int(os.getenv("TREND_CHANGE_THRESHOLD", 55))

ANTI_SPAM_STRONG_SEC = int(os.getenv("ANTI_SPAM_STRONG_SEC", 180))
ANTI_SPAM_CHANGE_SEC = int(os.getenv("ANTI_SPAM_CHANGE_SEC", 300))

last_strong_notify = {}
last_change_notify = {}

if BOT_TOKEN and CHAT_ID:
    try:
        bot = Bot(
            token=BOT_TOKEN,
            default=DefaultBotProperties(
                parse_mode="MarkdownV2",
                disable_web_page_preview=True
            )
        )
        TELEGRAM_ENABLED = True
        logger.info("Telegram notifier initialized")
    except Exception as e:
        logger.error(f"Telegram init failed: {e}")
else:
    logger.info("Telegram notifier disabled — missing BOT_TOKEN or CHAT_ID")


def escape_md_v2(text: str) -> str:
    return re.sub(r"([_*\[\]()~`>#+-=|{}.!])", r"\\\1", str(text))


async def send_message(text: str, silent: bool = True):
    if not TELEGRAM_ENABLED or not bot:
        return
    try:
        await bot.send_message(
            chat_id=CHAT_ID,
            text=text,
            disable_notification=silent,
        )
    except (TelegramBadRequest, TelegramForbiddenError, TelegramAPIError) as e:
        logger.error(f"Telegram send failed: {e}")
    except Exception as e:
        logger.exception("Unexpected error in telegram send")


async def send_strong_signal(symbol: str, timeframe: str, score: float, direction: str, extra: str = ""):
    if not TELEGRAM_ENABLED:
        return

    key = f"{symbol}_{timeframe}"
    now_ts = asyncio.get_event_loop().time()

    if key in last_strong_notify and now_ts - last_strong_notify[key] < ANTI_SPAM_STRONG_SEC:
        return

    last_strong_notify[key] = now_ts

    now = datetime.utcnow().strftime("%H:%M:%S UTC")

    if direction == "BULLISH":
        if score >= VERY_STRONG_BULL:
            emoji = "🔥🔥"
            strength = "VERY STRONG BULLISH"
        elif score >= STRONG_BULL_THRESHOLD:
            emoji = "🔥"
            strength = "STRONG BULLISH"
        else:
            return
    elif direction == "BEARISH":
        if score <= VERY_STRONG_BEAR:
            emoji = "🧊🧊"
            strength = "VERY STRONG BEARISH"
        elif score <= STRONG_BEAR_THRESHOLD:
            emoji = "🧊"
            strength = "STRONG BEARISH"
        else:
            return
    else:
        return

    text = (
        f"{emoji} *{escape_md_v2(symbol)} {escape_md_v2(timeframe)}* "
        f"→ {escape_md_v2(strength)} \${int(score)}\\/100\$\n"
        f"`{now}`\n\n"
    )

    if extra:
        text += escape_md_v2(extra) + "\n"

    silent = not (score >= VERY_STRONG_BULL or score <= VERY_STRONG_BEAR)
    await send_message(text, silent=silent)

    print(f"[TG strong] {symbol} {timeframe} {strength} ({score})")


async def send_trend_change(symbol: str, timeframe: str, old_direction: str, new_direction: str, score: float):
    if not TELEGRAM_ENABLED:
        return

    key = f"change_{symbol}_{timeframe}"
    now_ts = asyncio.get_event_loop().time()

    if key in last_change_notify and now_ts - last_change_notify[key] < ANTI_SPAM_CHANGE_SEC:
        return

    if abs(score - 50) < TREND_CHANGE_THRESHOLD:
        return

    last_change_notify[key] = now_ts

    now = datetime.utcnow().strftime("%H:%M:%S UTC")
    emoji = "⚡" if new_direction in ("BULLISH", "BEARISH") else "↔️"

    text = (
        f"{emoji} *{escape_md_v2(symbol)} {escape_md_v2(timeframe)}* trend changed: "
        f"*{escape_md_v2(old_direction)}* → *{escape_md_v2(new_direction)}* "
        f"\${int(score)}\\/100\$\n"
        f"`{now}`"
    )

    await send_message(text, silent=True)

    print(f"[TG change] {symbol} {timeframe} {old_direction} → {new_direction} ({score})")


async def shutdown_notifier():
    global bot
    if bot:
        try:
            await bot.session.close()
        except Exception:
            pass
        bot = None