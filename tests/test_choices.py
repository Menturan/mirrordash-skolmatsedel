"""The choices of the settings' list fields, as the admin page asks for them (provider -> municipality -> school)."""

import pytest

from mirrordash_skolmatsedel import schools
from mirrordash_skolmatsedel.plugin import SkolmatsedelModule
from tests.conftest import fixture_json

GAVLE_MATEO = {"id": "gavle", "name": "Gävle"}


@pytest.fixture
def module(make_net):
    def build(**answers):
        net = make_net(**answers)
        m = SkolmatsedelModule({})
        m.fetch_json, m.fetch = net.fetch_json, net.fetch
        return m
    return build


@pytest.mark.asyncio
async def test_skolmaten_municipalities_come_from_the_bundled_list_and_hide_empty_ones(module):
    choices = await module().settings_list_municipality({"provider": "skolmaten"})
    ids = [c["id"] for c in choices]
    assert "gavle-kommun" in ids
    assert "karlshamns-kommun" not in ids  # a municipality with 0 schools
    assert all(schools.school_choices(i) for i in ids[:20])
    assert {"id": "gavle-kommun", "name": "Gävle kommun", "detail": "Gävleborgs län"} in choices


@pytest.mark.asyncio
async def test_a_row_without_a_provider_chosen_yet_means_skolmaten(module):
    assert await module().settings_list_municipality({}) == await module().settings_list_municipality({"provider": "skolmaten"})


@pytest.mark.asyncio
async def test_skolmaten_schools_follow_the_municipality_and_never_include_the_test_school(module):
    row = {"provider": "skolmaten", "municipality": {"id": "gavle-kommun", "name": "Gävle kommun"}}
    choices = await module().settings_list_school(row)
    assert {"id": "borgarskolan", "name": "Borgarskolan"} in choices
    assert all(c["id"] != "test" for c in choices)
    slugs = [s["id"] for m in schools.municipality_choices() for s in schools.school_choices(m["id"])]
    assert "test" not in slugs


def test_the_two_municipalities_with_the_same_name_are_told_apart_by_province_or_one_is_hidden():
    names = [(c["name"], c["detail"]) for c in schools.municipality_choices()]
    assert len(names) == len(set(names))  # the same name never appears twice in the same province
    assert sum(1 for name, _ in names if name == "Järfälla kommun") == 1  # the empty duplicate is hidden


@pytest.mark.asyncio
async def test_mateo_municipalities_are_fetched_from_mateo(module):
    m = module(json=(fixture_json("mateo_organizations.json"), None))
    assert (await m.settings_list_municipality({"provider": "mateo"}))[0] == GAVLE_MATEO
    assert m.fetch_json.call_args.args == ("https://meny-api.mateo.se/api/v1/organizations",)


@pytest.mark.asyncio
async def test_mateo_schools_follow_the_municipality(module):
    m = module(json=(fixture_json("mateo_organization_gavle.json"), None))
    row = {"provider": "mateo", "municipality": GAVLE_MATEO}
    assert [c["name"] for c in await m.settings_list_school(row)] == [
        "Fridhemsskolan", "Hemlingborg Skola", "Hemlingborgs Förskola"]
    assert m.fetch_json.call_args.args == ("https://meny-api.mateo.se/api/v1/organizations/gavle",)


@pytest.mark.asyncio
async def test_schools_need_a_municipality_first(module):
    for row in ({"provider": "mateo"}, {"provider": "mateo", "municipality": {}}):
        with pytest.raises(ValueError, match="Choose a municipality first"):
            await module().settings_list_school(row)


@pytest.mark.asyncio
async def test_an_unknown_provider_is_refused_with_words_for_the_owner(module):
    with pytest.raises(ValueError, match="Choose a provider first"):
        await module().settings_list_municipality({"provider": "nope"})


@pytest.mark.asyncio
async def test_mateo_being_down_is_said_under_the_field(module):
    with pytest.raises(ValueError, match="Mateo"):
        await module(json=(None, "offline")).settings_list_municipality({"provider": "mateo"})


def test_the_schema_marks_the_fields_the_core_asks_the_module_about():
    """The core asks settings_list_<key> for each list field of a row, so each needs a method and the format."""
    import json
    from pathlib import Path

    from mirrordash_skolmatsedel import plugin
    schema = json.loads((Path(plugin.__file__).parent / "config_schema.json").read_text())
    row = schema["properties"]["schools"]["items"]["properties"]
    lists = [key for key, prop in row.items() if prop.get("format") == "list"]
    assert lists == ["municipality", "school"]
    for key in lists:
        assert row[key]["type"] == "object"
        assert callable(getattr(SkolmatsedelModule, f"settings_list_{key}"))
    assert row["provider"]["enum"] == ["skolmaten", "mateo"]
