import asyncio
import logging
from datetime import datetime, time
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from mirrordash_skolmatsedel.providers import PROVIDERS
from mirrordash_skolmatsedel.providers.base import Menu, Net
from mirrordash_skolmatsedel.providers.daily_cache import DailyMenus
from mirrordash_skolmatsedel.schedule import NEXT_DAY, parse_switch_time, shown_days
from mirrordash_skolmatsedel.view import SchoolMenu, build_days

logger = logging.getLogger("mirrordash.modules.mirrordash_skolmatsedel")

DEFAULT_DAYS_AHEAD = 3  # the same as the schema's default (a test checks it)
REDRAW_SECONDS = 300  # the card is drawn again this often (after lunch and at midnight the days change)


class SkolmatsedelModule:
    # Keeps pytest from collecting this class as a test
    __test__ = False

    def __init__(self, config):
        # The mirror adds self.render_template, self.translate, self.fetch and self.fetch_json after __init__.
        self.config = config
        self.name = "mirrordash_skolmatsedel"
        # Drawing is cheap: DailyMenus keeps each school's menu for the whole calendar day, so the
        # network is asked about once a day while the days still change on time.
        self.menus = DailyMenus()
        self.interval = REDRAW_SECONDS
        self.schools = config.get("schools") or []
        self.days_ahead = config.get("days_ahead", DEFAULT_DAYS_AHEAD)
        self.after_lunch = config.get("after_lunch", NEXT_DAY)
        self.switch_time = parse_switch_time(config.get("switch_time"))  # blank or bad: 13:00
        self.tz = self.read_timezone(config.get("globals", {}).get("timezone", "Europe/Stockholm"))

    @staticmethod
    def read_timezone(name: str) -> ZoneInfo:
        try:
            return ZoneInfo(name)
        except (ZoneInfoNotFoundError, ValueError):
            logger.warning("Unknown time zone %r, using Europe/Stockholm", name)
            return ZoneInfo("Europe/Stockholm")

    def now(self) -> datetime:
        return datetime.now(self.tz)

    def net(self) -> Net:
        return Net(fetch_json=self.fetch_json, fetch=self.fetch)

    def configured_schools(self) -> list[dict]:
        """The settings rows that name a known provider and a school."""
        return [row for row in self.schools
                if row.get("provider") in PROVIDERS and (row.get("school") or {}).get("id")]

    async def menu_of(self, row: dict, now: datetime) -> Menu:
        """The school's menu: fetched once per day, whatever the card shows at the moment.

        The dates asked for are the same all day (today up to the last day the card can reach after the
        switch), so the 13:00 switch never needs another fetch."""
        provider, school = row["provider"], row["school"]["id"]
        last = shown_days(datetime.combine(now.date(), time(23, 59)), self.days_ahead, NEXT_DAY)[-1].day
        return await self.menus.get(
            (provider, school), now,
            lambda max_age: PROVIDERS[provider].fetch_menu(self.net(), school, now.date(), last, max_age))

    async def render(self) -> str:
        now = self.now()
        shown = shown_days(now, self.days_ahead, self.after_lunch, self.switch_time)
        rows = self.configured_schools()
        menus = await asyncio.gather(*(self.menu_of(row, now) for row in rows))
        schools = [SchoolMenu(row.get("short_name") or row["school"]["name"], menu)
                   for row, menu in zip(rows, menus)]
        days = build_days(shown, schools, now.date(), self.translate)
        if not days and schools and all(school.menu.error for school in schools):
            error = self.translate("error_fetching", "Couldn't load the lunch menus")
        elif not days:
            return ""  # nothing to show: an empty answer hides the whole card
        else:
            error = None
        return self.render_template("widget.html", days=days, error=error)

    # ── The choices of the settings' list fields (asked with the unsaved form, one row at a time) ──

    @staticmethod
    def provider_of(item: dict):
        provider = PROVIDERS.get(item.get("provider") or "skolmaten")
        if provider is None:
            raise ValueError("Choose a provider first")
        return provider

    async def settings_list_municipality(self, item):
        """The municipalities of the row's provider."""
        return await self.provider_of(item).list_municipalities(self.net())

    async def settings_list_school(self, item):
        """The schools of the row's municipality."""
        municipality = (item.get("municipality") or {}).get("id")
        if not municipality:
            raise ValueError("Choose a municipality first")
        return await self.provider_of(item).list_schools(self.net(), municipality)
