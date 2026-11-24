"""Fetch each school's menu once per calendar day, and retry a failure only now and then.

The mirror's fetch helper already saves every answer on disk, so a restart does not lose data. What it
cannot say is "once per calendar day" or "wait a while after a failure", so this small class keeps that
bookkeeping in memory. The rules:

    - A good answer is reused until the date changes (a calendar day, not 24 hours).
    - No answer yet, or a new school: fetch at once.
    - After a failure the last good menu stays on the screen and the fetch is tried again after RETRY_SECONDS.
    - A Monday-Friday menu without today in it is "incomplete": it is shown, but fetched again after
      RECHECK_SECONDS. The feed switches to the new week at about 00:00 UTC on Monday (01:00 or 02:00 Swedish
      time, measured 2026-11-23), so a fetch just after local midnight still gets last week.
"""

from datetime import datetime, timedelta
from typing import Awaitable, Callable

from mirrordash_skolmatsedel.providers.base import Menu

RETRY_SECONDS = 15 * 60  # the least time between two fetches of a school that keeps failing
RECHECK_SECONDS = 60 * 60  # the least time between two fetches while the menu lacks today


def seconds_since_midnight(now: datetime) -> float:
    """How old a saved answer may be to count as fetched today: the mirror's fetch takes this as max_age,
    so after a restart an answer saved today is reused, and an older one is fetched again."""
    return (now - now.replace(hour=0, minute=0, second=0, microsecond=0)).total_seconds()


class DailyMenus:
    def __init__(self):
        # school -> (when it was fetched, its menu, whether the menu is complete for that day)
        self.good: dict[tuple, tuple[datetime, Menu, bool]] = {}
        self.failed_at: dict[tuple, datetime] = {}  # school -> when the last fetch failed

    async def get(self, key: tuple, now: datetime, fetch: Callable[[float], Awaitable[Menu]]) -> Menu:
        """The menu of the school `key` (provider, school id). `fetch(max_age)` really asks for it."""
        saved = self.good.get(key)
        max_age = seconds_since_midnight(now)
        if saved and saved[0].date() == now.date():
            fetched_at, menu, complete = saved
            if complete or now - fetched_at < timedelta(seconds=RECHECK_SECONDS):
                return menu  # fetched today already (or an incomplete one that is too soon to check again)
            max_age = min(max_age, RECHECK_SECONDS)  # do not reuse the saved answer from before the switch
        failed_at = self.failed_at.get(key)
        if failed_at and now - failed_at < timedelta(seconds=RETRY_SECONDS):
            return saved[1] if saved else Menu(error="offline")  # too soon to try again
        menu = await fetch(max_age)
        if menu.error or menu.stale:  # nothing at all, or only an old answer
            self.failed_at[key] = now
            return menu if menu.days or not saved else saved[1]
        self.failed_at.pop(key, None)
        self.good[key] = (now, menu, has_today(menu, now))
        return menu


def has_today(menu: Menu, now: datetime) -> bool:
    """A week feed never has weekend days, so only Monday-Friday can be missing today."""
    return now.weekday() >= 5 or now.date() in menu.days
