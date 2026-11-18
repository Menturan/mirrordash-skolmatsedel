import json
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from mirrordash_skolmatsedel import plugin
from mirrordash_skolmatsedel.plugin import DEFAULT_DAYS_AHEAD, SkolmatsedelModule
from tests.conftest import fixture_bytes, fixture_json

SCHEMA = json.loads((Path(plugin.__file__).parent / "config_schema.json").read_text())
DEFAULTS = {key: prop["default"] for key, prop in SCHEMA["properties"].items() if "default" in prop}

WED_MORNING = datetime(2026, 11, 18, 9, 0)  # the saved real answers are for this week
FRIDHEM = {"provider": "mateo", "municipality": {"id": "gavle", "name": "Gävle"},
           "school": {"id": "913", "name": "Fridhemsskolan"}}
BORGAR = {"provider": "skolmaten", "municipality": {"id": "gavle-kommun", "name": "Gävle kommun"},
          "school": {"id": "borgarskolan", "name": "Borgarskolan"}}


def make_module(now=WED_MORNING, mateo=(None, "offline"), skolmaten=(None, "offline"), **settings):
    """The module as the mirror sets it up, with the mirror's helpers replaced by fakes and a fixed clock."""
    module = SkolmatsedelModule({**DEFAULTS, "globals": {"timezone": "Europe/Stockholm"}, **settings})
    module.now = lambda: now.replace(tzinfo=module.tz)
    module.render_template = MagicMock(side_effect=lambda name, **context: context)  # returns what the template gets
    module.translate = lambda key, default=None: default
    module.fetch_json = AsyncMock(return_value=mateo)
    module.fetch = AsyncMock(return_value=skolmaten)
    return module


def test_the_defaults_in_the_code_are_the_schemas():
    assert DEFAULT_DAYS_AHEAD == DEFAULTS["days_ahead"]
    assert SkolmatsedelModule({}).after_lunch == DEFAULTS["after_lunch"] == "next_day"
    assert SkolmatsedelModule({}).switch_time.strftime("%H:%M") == DEFAULTS["switch_time"] == "13:00"


@pytest.mark.asyncio
async def test_two_schools_from_two_providers_are_shown_day_by_day():
    module = make_module(schools=[FRIDHEM, {**BORGAR, "short_name": "Alva"}], days_ahead=2,
                         mateo=(fixture_json("mateo_days_913.json"), None),
                         skolmaten=(fixture_bytes("skolmaten_week.xml"), None))
    shown = await module.render()
    assert [d["label"] for d in shown["days"]] == ["Today", "Tomorrow"]
    today = shown["days"][0]["schools"]
    assert [s["name"] for s in today] == ["Fridhemsskolan", "Alva"]  # the short name replaces the school's name
    assert today[0]["dishes"][0].startswith("Pankopanerad fisk")
    assert today[1]["dishes"][0].startswith("Kikärtsgryta")
    assert shown["error"] is None and shown["show_header"] is True


@pytest.mark.asyncio
async def test_mateo_is_asked_for_exactly_the_days_shown():
    module = make_module(schools=[FRIDHEM], days_ahead=3, mateo=(fixture_json("mateo_days_913.json"), None))
    await module.render()
    assert module.fetch_json.call_args.kwargs["params"] == {"from": "2026-11-18", "to": "2026-11-20"}


@pytest.mark.asyncio
async def test_one_school_hides_its_name():
    module = make_module(schools=[FRIDHEM], mateo=(fixture_json("mateo_days_913.json"), None))
    shown = await module.render()
    assert all(s["name"] == "" for d in shown["days"] for s in d["schools"])


@pytest.mark.asyncio
async def test_friday_after_lunch_with_only_this_weeks_skolmaten_shows_nothing_and_hides_the_card():
    friday_after_lunch = datetime(2026, 11, 20, 13, 30)
    module = make_module(now=friday_after_lunch, schools=[BORGAR], skolmaten=(fixture_bytes("skolmaten_week.xml"), None))
    assert await module.render() == ""
    module.render_template.assert_not_called()


@pytest.mark.asyncio
async def test_a_weekend_with_only_this_weeks_skolmaten_hides_the_card():
    module = make_module(now=datetime(2026, 11, 21, 10, 0), schools=[BORGAR],
                         skolmaten=(fixture_bytes("skolmaten_week.xml"), None))
    assert await module.render() == ""


@pytest.mark.asyncio
async def test_dim_keeps_today_after_lunch_dimmed():
    module = make_module(now=datetime(2026, 11, 18, 14, 0), schools=[FRIDHEM], after_lunch="dim", days_ahead=2,
                         mateo=(fixture_json("mateo_days_913.json"), None))
    shown = await module.render()
    assert [(d["label"], d["dimmed"]) for d in shown["days"]] == [("Today", True), ("Tomorrow", False)]


@pytest.mark.asyncio
async def test_a_failing_school_does_not_hide_the_working_one():
    module = make_module(schools=[FRIDHEM, BORGAR], skolmaten=(fixture_bytes("skolmaten_week.xml"), None))
    shown = await module.render()  # Mateo is offline, Skolmaten works
    assert shown["days"] and shown["error"] is None


@pytest.mark.asyncio
async def test_without_any_menu_because_everything_failed_the_card_says_so():
    shown = await make_module(schools=[FRIDHEM, BORGAR]).render()
    assert shown["days"] == [] and shown["error"] == "Couldn't load the lunch menus"


@pytest.mark.asyncio
async def test_without_schools_the_card_is_hidden():
    module = make_module(schools=[])
    assert await module.render() == ""
    module.fetch.assert_not_called()
    module.fetch_json.assert_not_called()


@pytest.mark.asyncio
async def test_a_half_filled_row_is_ignored():
    module = make_module(schools=[{"provider": "mateo", "municipality": {}, "school": {}}])
    assert await module.render() == ""
    module.fetch_json.assert_not_called()


def test_an_unknown_time_zone_falls_back_to_stockholm():
    assert str(SkolmatsedelModule({"globals": {"timezone": "Nowhere/Land"}}).tz) == "Europe/Stockholm"
