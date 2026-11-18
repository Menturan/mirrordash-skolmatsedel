"""The bundled list of Skolmaten's municipalities and schools (data/schools.json).

The list is built by scripts/build_school_list.py and shipped with the module: it is never fetched while
the mirror runs."""

import json
from functools import lru_cache
from pathlib import Path

SCHOOLS_FILE = Path(__file__).parent / "data" / "schools.json"
HIDDEN_SCHOOLS = {"test"}  # Skolmaten's own test school


@lru_cache(maxsize=1)
def load_provinces() -> list[dict]:
    """The provinces of schools.json: each has districts (municipalities), each with its schools."""
    return json.loads(SCHOOLS_FILE.read_text(encoding="utf-8"))["provinces"]


def municipality_choices() -> list[dict]:
    """Every municipality that has at least one school, as {id, name, detail}. The province is the detail,
    so two municipalities with the same name can still be told apart."""
    choices = []
    for province in load_provinces():
        for district in province["districts"]:
            if visible_schools(district):
                choices.append({"id": district["slug"], "name": district["name"], "detail": province["name"]})
    return sorted(choices, key=lambda choice: choice["name"].casefold())


def school_choices(municipality_slug: str) -> list[dict]:
    """The schools of one municipality as {id, name}; the id is the school's slug on skolmaten.se."""
    for province in load_provinces():
        for district in province["districts"]:
            if district["slug"] == municipality_slug:
                return [{"id": school["slug"], "name": school["name"]} for school in visible_schools(district)]
    return []


def visible_schools(district: dict) -> list[dict]:
    """The district's schools without the ones that are not real schools."""
    return [school for school in district["schools"] if school["slug"] not in HIDDEN_SCHOOLS]
