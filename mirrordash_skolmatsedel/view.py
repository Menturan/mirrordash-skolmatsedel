"""From the menus to what the template shows: days, each with the schools that have a menu that day."""

from dataclasses import dataclass
from datetime import date

from mirrordash_skolmatsedel.day_header import day_header
from mirrordash_skolmatsedel.providers.base import Menu
from mirrordash_skolmatsedel.schedule import ShownDay


@dataclass(frozen=True)
class SchoolMenu:
    """One configured school (a row of the settings) and its menu."""
    name: str  # the short name if the owner gave one, else the school's name
    menu: Menu


def build_days(shown: list[ShownDay], schools: list[SchoolMenu], today: date, translate) -> list[dict]:
    """One entry per shown day that has at least one menu. A school without a menu that day is left out.

    The school's name is left empty when only one school is set up: then the label is not needed."""
    show_names = len(schools) > 1
    days = []
    for entry in shown:
        rows = [{"name": school.name if show_names else "", "dishes": school.menu.days[entry.day]}
                for school in schools if school.menu.days.get(entry.day)]
        if rows:
            label, sub = day_header(entry.day, today, translate)
            days.append({"label": label, "sub": sub, "dimmed": entry.dimmed, "schools": rows})
    return days
