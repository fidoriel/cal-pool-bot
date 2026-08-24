from dataclasses import dataclass
from datetime import date, datetime
import re
from typing import Iterable

import requests
from bs4 import BeautifulSoup


SCHEDULE_URL = "https://recwell.berkeley.edu/schedules-reservations/lap-swim/"


@dataclass(frozen=True)
class PoolOpening:
    """One pool's opening period."""

    date: date
    day: str
    pool: str
    opening: str | None = None
    closing: str | None = None


class PoolHoursScraper:
    _time_range = re.compile(
        r"(?P<opening>\d{1,2}:?\d{2}\s*[ap]m)\s*[-\u2013\u2014]\s*"
        r"(?P<closing>\d{1,2}:?\d{2}\s*[ap]m)",
        re.IGNORECASE,
    )

    def __init__(self, url: str = SCHEDULE_URL, timeout: int = 30) -> None:
        self.url = url
        self.timeout = timeout

    def fetch(self) -> str:
        """Return the schedule page HTML, raising for HTTP errors."""
        response = requests.get(
            self.url,
            timeout=self.timeout,
            headers={"User-Agent": "pool-hours-scraper/1.0"},
        )
        response.raise_for_status()
        return response.text

    def scrape(self) -> list[PoolOpening]:
        """Fetch the page and return its date-specific pool openings."""
        return self.parse(self.fetch())

    @classmethod
    def parse(cls, html: str) -> list[PoolOpening]:
        """Parse schedule HTML without making a network request."""
        soup = BeautifulSoup(html, "html.parser")
        openings: list[PoolOpening] = []

        for row in soup.select("table.table tbody > tr"):
            cells = row.find_all("td", recursive=False)
            if len(cells) < 4:
                continue

            schedule_date = cls._parse_date(cells[0].get_text(" ", strip=True))
            if schedule_date is None:
                continue

            day = cells[1].get_text(" ", strip=True)
            times = cls._cell_values(cells[2])
            pools = cls._cell_values(cells[3])

            for raw_time, pool in zip(times, pools):
                match = cls._time_range.search(raw_time)
                if not match:
                    # A non-time value means the pool is closed or unavailable.
                    continue

                openings.append(
                    PoolOpening(
                        date=schedule_date,
                        day=day,
                        pool=pool,
                        opening=cls._to_24_hour(match.group("opening")),
                        closing=cls._to_24_hour(match.group("closing")),
                    )
                )

        return openings

    @staticmethod
    def _cell_values(cell) -> list[str]:
        paragraphs = cell.find_all("p")
        values = [p.get_text(" ", strip=True) for p in paragraphs]
        return values or [cell.get_text(" ", strip=True)]

    @staticmethod
    def _parse_date(value: str) -> date | None:
        for format_string in ("%m/%d/%Y", "%m/%d/%y"):
            try:
                return datetime.strptime(value, format_string).date()
            except ValueError:
                pass
        return None

    @staticmethod
    def _to_24_hour(value: str) -> str:
        normalized = re.sub(r"\s+", "", value).lower()
        if ":" not in normalized:
            normalized = normalized[:-2] + ":00" + normalized[-2:]
        return datetime.strptime(normalized, "%I:%M%p").strftime("%H:%M")


def print_pool_hours(openings: Iterable[PoolOpening]) -> None:
    """Print scraped openings in a compact, human-readable format."""
    for opening in openings:
        day = opening.date.strftime("%Y-%m-%d")
        print(
            f"{day} ({opening.day}) | {opening.pool}: "
            f"{opening.opening}-{opening.closing}"
        )


if __name__ == "__main__":
    print_pool_hours(PoolHoursScraper().scrape())
