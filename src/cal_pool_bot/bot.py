import logging
from datetime import date, datetime, time, timedelta
import asyncio
from zoneinfo import ZoneInfo

from aiogram import Bot, Dispatcher, Router
from aiogram.filters import Command
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from .config import get_settings
from .pool_scraper import PoolHoursScraper, PoolOpening


BERKELEY_TIMEZONE = ZoneInfo("America/Los_Angeles")
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


class PoolTelegramBot:
    BUTTONS = (
        ("Open now", "open_now"),
        ("Today", "today"),
        ("Tomorrow", "tomorrow"),
        ("This week", "this_week"),
    )
    GITHUB_URL = "https://github.com/fidoriel/cal-pool-bot"

    def __init__(self, scraper: PoolHoursScraper | None = None) -> None:
        self.scraper = scraper or PoolHoursScraper()

    def keyboard(self) -> InlineKeyboardMarkup:
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text=label, callback_data=key)
                    for label, key in self.BUTTONS[:1]
                ],
                [
                    InlineKeyboardButton(text=label, callback_data=key)
                    for label, key in self.BUTTONS[1:3]
                ],
                [
                    InlineKeyboardButton(text=label, callback_data=key)
                    for label, key in self.BUTTONS[3:]
                ],
                [InlineKeyboardButton(text="GitHub", url=self.GITHUB_URL)],
            ]
        )

    async def start(self, message: Message) -> None:
        await message.answer(
            "When would you like to swim?", reply_markup=self.keyboard()
        )

    async def button(self, query: CallbackQuery) -> None:
        await query.answer()
        try:
            # Keep the synchronous HTTP scraper from blocking other Telegram updates.
            openings = await asyncio.to_thread(self.scraper.scrape)
            if query.data == "open_now":
                text = self._format_open_now(openings)
            else:
                selected_dates = self._dates_for(query.data or "")
                text = self._format_openings(openings, selected_dates)
        except Exception:
            logger.exception("Could not retrieve pool hours")
            text = "The opening hours could not be retrieved right now."

        if query.message:
            await query.message.edit_text(text, reply_markup=self.keyboard())

    @staticmethod
    def _dates_for(selection: str) -> set[date]:
        today = datetime.now(BERKELEY_TIMEZONE).date()
        if selection == "today":
            return {today}
        if selection == "tomorrow":
            return {today + timedelta(days=1)}
        if selection == "this_week":
            monday = today - timedelta(days=today.weekday())
            return {monday + timedelta(days=offset) for offset in range(7)}
        return {today}

    @staticmethod
    def _format_openings(openings: list[PoolOpening], selected_dates: set[date]) -> str:
        matching = [opening for opening in openings if opening.date in selected_dates]
        if not matching:
            return "No opening hours are available for this period."

        lines: list[str] = []
        current_date: date | None = None
        for opening in matching:
            if opening.date != current_date:
                current_date = opening.date
                lines.append(f"\n{opening.date:%A, %d.%m.%Y}")
            lines.append(f"{opening.pool}: {opening.opening}-{opening.closing}")
        return "Opening hours:\n" + "\n".join(lines).strip()

    @staticmethod
    def _format_open_now(openings: list[PoolOpening]) -> str:
        now = datetime.now(BERKELEY_TIMEZONE).replace(second=0, microsecond=0)
        open_now = [
            opening
            for opening in openings
            if opening.date == now.date()
            and PoolTelegramBot._contains_time(opening, now.time())
        ]
        if not open_now:
            return "No pool is open right now."

        lines = [
            f"{opening.pool}: {opening.opening}-{opening.closing} "
            f"({PoolTelegramBot._remaining(opening, now)} remaining)"
            for opening in open_now
        ]
        return "Open now:\n" + "\n".join(lines)

    @staticmethod
    def _contains_time(opening: PoolOpening, current: time) -> bool:
        if opening.opening is None or opening.closing is None:
            return False
        opening_time = datetime.strptime(opening.opening, "%H:%M").time()
        closing_time = datetime.strptime(opening.closing, "%H:%M").time()
        if closing_time < opening_time:
            return current >= opening_time or current < closing_time
        return opening_time <= current < closing_time

    @staticmethod
    def _remaining(opening: PoolOpening, now: datetime) -> str:
        closing = datetime.strptime(opening.closing or "00:00", "%H:%M").time()
        closing_at = datetime.combine(now.date(), closing, tzinfo=now.tzinfo)
        if closing_at <= now:
            closing_at += timedelta(days=1)
        remaining_minutes = max(0, int((closing_at - now).total_seconds() // 60))
        return f"{remaining_minutes // 60:02d}:{remaining_minutes % 60:02d}"


def main() -> None:
    settings = get_settings()
    asyncio.run(run_bot(settings.telegram_bot_token.get_secret_value()))


async def run_bot(token: str) -> None:
    bot = Bot(token=token)
    dispatcher = Dispatcher()
    router = Router()
    handlers = PoolTelegramBot()

    router.message.register(handlers.start, Command(commands=["start", "help"]))
    router.callback_query.register(handlers.button)
    dispatcher.include_router(router)

    await dispatcher.start_polling(bot)


if __name__ == "__main__":
    main()
