"""Mateo (meny-api.mateo.se): an open JSON API, no key.

    /organizations              the municipalities
    /organizations/<slug>       one municipality, with its units (schools, preschools, ...)
    /days/<unit>?from=&to=      the days of one unit, each with its meals"""

from datetime import date
from urllib.parse import quote

from mirrordash_skolmatsedel.providers.base import Menu, Net, unique

BASE_URL = "https://meny-api.mateo.se/api/v1"
UNIT_TYPES = {"school": None, "preschool": "Preschool"}  # the units to pick from, and their dimmed detail
LUNCH_PREFIX = "lunch"  # "Lunch", "Lunch vegetarisk", "Lunch alternativ"; not "Tillbehör lunch" (sides)


def parse_organizations(data) -> list[dict]:
    """The /organizations answer -> choices {id: slug, name}, sorted by name."""
    choices = [{"id": org["slug"], "name": org["name"]} for org in data]
    return sorted(choices, key=lambda choice: choice["name"].casefold())


def parse_units(data: dict) -> list[dict]:
    """The /organizations/<slug> answer -> choices for its schools and preschools, sorted by name."""
    choices = [{"id": str(unit["id"]), "name": unit["name"], "detail": UNIT_TYPES[unit["type"]] or ""}
               for unit in data.get("units", []) if unit.get("type") in UNIT_TYPES]
    return sorted(choices, key=lambda choice: choice["name"].casefold())


def parse_days(data: list) -> dict[date, list[str]]:
    """The /days answer -> the lunch dishes per date. A day without lunch dishes is left out."""
    days: dict[date, list[str]] = {}
    for day in data:
        dishes = [meal["name"].strip() for meal in day.get("meals", [])
                  if meal.get("type", "").lower().startswith(LUNCH_PREFIX) and meal.get("name", "").strip()]
        if dishes:
            days[date.fromisoformat(day["date"][:10])] = unique(dishes)
    return days


async def list_municipalities(net: Net) -> list[dict]:
    data, error = await net.fetch_json(f"{BASE_URL}/organizations")
    if data is None:
        raise ValueError(f"Couldn't load the municipalities from Mateo ({error})")
    return parse_organizations(data)


async def list_schools(net: Net, municipality_id: str) -> list[dict]:
    data, error = await net.fetch_json(f"{BASE_URL}/organizations/{quote(municipality_id, safe='')}")
    if data is None:
        raise ValueError(f"Couldn't load the schools from Mateo ({error})")
    return parse_units(data)


async def fetch_menu(net: Net, school_id: str, first: date, last: date, max_age: float) -> Menu:
    params = {"from": first.isoformat(), "to": last.isoformat()}
    data, error = await net.fetch_json(f"{BASE_URL}/days/{quote(school_id, safe='')}", params=params, max_age=max_age)
    if not isinstance(data, list):
        return Menu(error=error or "invalid")
    return Menu(days=parse_days(data), stale=error is not None)
