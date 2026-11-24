from datetime import date, datetime

import pytest

from mirrordash_skolmatsedel.providers.base import Menu
from mirrordash_skolmatsedel.providers.daily_cache import DailyMenus

pytestmark = pytest.mark.asyncio

KEY = ("skolmaten", "borgarskolan")
MONDAY = date(2026, 11, 23)
LAST_WEEK = Menu(days={date(2026, 11, 20): ["Fisk"]})
THIS_WEEK = Menu(days={MONDAY: ["Pasta"]})


class FakeFetch:
    """Gives the answers in order (the last one repeats) and records the max_age of every call."""

    def __init__(self, *answers: Menu):
        self.answers = list(answers)
        self.max_ages: list[float] = []

    async def __call__(self, max_age: float) -> Menu:
        self.max_ages.append(max_age)
        return self.answers.pop(0) if len(self.answers) > 1 else self.answers[0]


def at(day: int, hour: int, minute: int = 0) -> datetime:
    return datetime(2026, 11, day, hour, minute)


async def test_monday_just_after_midnight_is_fetched_again_after_the_feed_switches():
    menus, fetch = DailyMenus(), FakeFetch(LAST_WEEK, THIS_WEEK)
    assert await menus.get(KEY, at(23, 0, 30), fetch) == LAST_WEEK
    assert fetch.max_ages == [30 * 60]
    assert await menus.get(KEY, at(23, 1, 0), fetch) == LAST_WEEK  # only 30 minutes later
    assert len(fetch.max_ages) == 1
    assert await menus.get(KEY, at(23, 1, 31), fetch) == THIS_WEEK
    assert len(fetch.max_ages) == 2 and fetch.max_ages[1] <= 3600
    assert await menus.get(KEY, at(23, 9, 0), fetch) == THIS_WEEK
    assert await menus.get(KEY, at(23, 20, 0), fetch) == THIS_WEEK
    assert len(fetch.max_ages) == 2


async def test_a_complete_menu_is_fetched_once_per_day():
    menus, fetch = DailyMenus(), FakeFetch(THIS_WEEK)
    await menus.get(KEY, at(23, 8, 0), fetch)
    await menus.get(KEY, at(23, 12, 0), fetch)
    await menus.get(KEY, at(23, 23, 0), fetch)
    assert fetch.max_ages == [8 * 3600]
    await menus.get(KEY, at(24, 8, 0), fetch)
    assert len(fetch.max_ages) == 2


async def test_saturday_needs_no_today_in_the_menu():
    menus, fetch = DailyMenus(), FakeFetch(LAST_WEEK)  # the menu has no Saturday
    for hour in (9, 11, 15, 22):
        assert await menus.get(KEY, at(21, hour), fetch) == LAST_WEEK
    assert len(fetch.max_ages) == 1


async def test_a_failed_recheck_keeps_the_incomplete_menu_and_follows_the_retry_rule():
    menus, fetch = DailyMenus(), FakeFetch(LAST_WEEK, Menu(error="offline"), THIS_WEEK)
    await menus.get(KEY, at(23, 0, 30), fetch)
    assert await menus.get(KEY, at(23, 1, 31), fetch) == LAST_WEEK  # the recheck fails
    assert len(fetch.max_ages) == 2
    assert await menus.get(KEY, at(23, 1, 40), fetch) == LAST_WEEK  # 9 minutes later: too soon
    assert len(fetch.max_ages) == 2
    assert await menus.get(KEY, at(23, 1, 47), fetch) == THIS_WEEK  # 16 minutes later: tries again
    assert len(fetch.max_ages) == 3
