"""What every provider shares.

A provider is a module in this folder with the same three functions:

    async def list_municipalities(net) -> list[dict]          choices {id, name, detail}
    async def list_schools(net, municipality_id) -> list[dict]
    async def fetch_menu(net, school_id, first, last) -> Menu

`net` is a Net (the mirror's fetch helpers); first and last are the dates the module wants to show."""

from dataclasses import dataclass, field
from datetime import date
from typing import Awaitable, Callable

# Menus change rarely: ask again after this many seconds (a few times a day), reuse the answer before.
CACHE_SECONDS = 4 * 3600


@dataclass(frozen=True)
class Net:
    """The mirror's two fetch helpers, handed to the providers so tests can replace them."""
    fetch_json: Callable[..., Awaitable]  # await fetch_json(url, ...) -> (data, error)
    fetch: Callable[..., Awaitable]  # await fetch(url, ...) -> (bytes, error)


@dataclass
class Menu:
    """One school's dishes per date, or the error when there is nothing at all to show."""
    days: dict[date, list[str]] = field(default_factory=dict)
    error: str | None = None


def unique(dishes: list[str]) -> list[str]:
    """The dishes in their order, each only once (a school can list the same dish for two diets)."""
    return list(dict.fromkeys(dishes))
