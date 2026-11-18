"""Skolmaten (skolmaten.se): one open RSS feed per school, with the current week only.

This is the only address the module calls on skolmaten.se. The municipalities and schools come from the
bundled list (schools.py), not from the network."""

import asyncio
import re
import xml.etree.ElementTree as ET
from datetime import date, datetime
from email.utils import parsedate_to_datetime
from html import unescape
from urllib.parse import quote

from mirrordash_skolmatsedel import schools
from mirrordash_skolmatsedel.providers.base import CACHE_SECONDS, Menu, Net, unique

RSS_URL = "https://skolmaten.se/api/4/rss/week/{slug}"
LINE_BREAK = re.compile(r"<br\s*/?>", re.IGNORECASE)
EDGE_JUNK = re.compile(r"^[\s,]+|[\s,]+$")  # spaces and commas around a dish


def split_dishes(description: str) -> list[str]:
    """'Soup, <br/>Pasta' -> ['Soup', 'Pasta']: one dish per line, trailing commas and spaces removed."""
    dishes = (EDGE_JUNK.sub("", unescape(part)) for part in LINE_BREAK.split(description))
    return unique([dish for dish in dishes if dish])


def parse_date(text: str) -> date | None:
    """An item's pubDate is the day itself ('Mon, 16 Nov 2026 00:00:00 GMT'); ISO dates work too."""
    try:
        return parsedate_to_datetime(text).date()
    except (TypeError, ValueError):
        pass
    try:
        return datetime.fromisoformat(text.strip().replace("Z", "+00:00")).date()
    except ValueError:
        return None


def parse_week(feed: bytes) -> dict[date, list[str]]:
    """The dishes per date of one RSS answer. Items without a date or without dishes are left out."""
    days: dict[date, list[str]] = {}
    for item in ET.fromstring(feed.strip()).iter("item"):
        day = parse_date(item.findtext("pubDate") or "")
        dishes = split_dishes(item.findtext("description") or "")
        if day and dishes:
            days[day] = dishes
    return days


async def list_municipalities(net: Net) -> list[dict]:
    return await asyncio.to_thread(schools.municipality_choices)


async def list_schools(net: Net, municipality_id: str) -> list[dict]:
    return await asyncio.to_thread(schools.school_choices, municipality_id)


async def fetch_menu(net: Net, school_id: str, first: date, last: date) -> Menu:
    """The school's week. The feed has no date range: first and last are not used."""
    data, error = await net.fetch(RSS_URL.format(slug=quote(school_id, safe="")), max_age=CACHE_SECONDS)
    if data is None:
        return Menu(error=error or "offline")
    try:
        return Menu(days=parse_week(data))
    except ET.ParseError:
        return Menu(error="invalid")
