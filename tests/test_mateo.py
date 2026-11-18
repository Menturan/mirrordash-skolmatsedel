from datetime import date

import pytest

from mirrordash_skolmatsedel.providers import mateo
from tests.conftest import fixture_json


def test_the_real_organizations_are_sorted_choices_with_their_slug_as_id():
    assert mateo.parse_organizations(fixture_json("mateo_organizations.json")) == [
        {"id": "gavle", "name": "Gävle"}, {"id": "karlshamn", "name": "Karlshamn"}, {"id": "leksand", "name": "Leksand"}]


def test_gavle_has_two_schools_and_a_preschool_but_no_care_home():
    units = mateo.parse_units(fixture_json("mateo_organization_gavle.json"))
    assert units == [{"id": "913", "name": "Fridhemsskolan", "detail": ""},
                     {"id": "914", "name": "Hemlingborg Skola", "detail": ""},
                     {"id": "966", "name": "Hemlingborgs Förskola", "detail": "Preschool"}]


def test_a_real_week_gives_the_lunch_dishes_per_date():
    days = mateo.parse_days(fixture_json("mateo_days_913.json"))
    assert sorted(days) == [date(2026, 11, d) for d in (16, 17, 18, 19, 20)]
    assert days[date(2026, 11, 16)] == ["Chili con carne serveras med gräddfil och ris",
                                        "Chili sin carne serveras med gräddfil och ris"]


def test_the_same_dish_for_both_diets_is_shown_once():
    days = mateo.parse_days(fixture_json("mateo_days_913.json"))
    assert days[date(2026, 11, 20)] == ["Quornbugare med dressing, bröd, picklad lök, grönsaker och potatisklyftor"]


def test_sides_are_not_dishes_but_alternative_lunches_are():
    days = mateo.parse_days(fixture_json("mateo_days_395_with_sides.json"))
    assert days[date(2026, 11, 16)] == ["Kyckling (svensk) i currysås samt ris/bulgur (eko)",
                                        "Quorn med röd curry, kokosmjölk samt bulgur/ris (eko)"]


def test_a_day_without_meals_is_left_out():
    assert mateo.parse_days([{"date": "2026-11-16T00:00:00.000Z", "deviation": "Stängt", "meals": []}]) == {}


@pytest.mark.asyncio
async def test_fetch_menu_asks_for_the_dates_wanted(make_net):
    net = make_net(json=(fixture_json("mateo_days_913.json"), None))
    menu = await mateo.fetch_menu(net, "913", date(2026, 11, 16), date(2026, 11, 20), 3600)
    assert len(menu.days) == 5 and menu.error is None
    assert net.fetch_json.call_args.args == ("https://meny-api.mateo.se/api/v1/days/913",)
    assert net.fetch_json.call_args.kwargs["params"] == {"from": "2026-11-16", "to": "2026-11-20"}


@pytest.mark.asyncio
async def test_fetch_menu_reports_an_error_without_data(make_net):
    menu = await mateo.fetch_menu(make_net(json=(None, "http 500")), "913", date(2026, 11, 16), date(2026, 11, 16), 3600)
    assert menu.days == {} and menu.error == "http 500"


@pytest.mark.asyncio
async def test_the_lists_ask_mateo(make_net):
    net = make_net(json=(fixture_json("mateo_organization_gavle.json"), None))
    assert [s["id"] for s in await mateo.list_schools(net, "gavle")] == ["913", "914", "966"]
    assert net.fetch_json.call_args.args == ("https://meny-api.mateo.se/api/v1/organizations/gavle",)
    net = make_net(json=(fixture_json("mateo_organizations.json"), None))
    assert (await mateo.list_municipalities(net))[0]["id"] == "gavle"


@pytest.mark.asyncio
async def test_a_list_that_cannot_load_says_so_to_the_owner(make_net):
    with pytest.raises(ValueError, match="Couldn't load the schools from Mateo \\(offline\\)"):
        await mateo.list_schools(make_net(json=(None, "offline")), "gavle")


@pytest.mark.asyncio
async def test_an_old_answer_after_a_failed_call_is_marked_stale(make_net):
    menu = await mateo.fetch_menu(make_net(json=(fixture_json("mateo_days_913.json"), "offline")), "913",
                                  date(2026, 11, 16), date(2026, 11, 20), 0)
    assert menu.days and menu.stale
