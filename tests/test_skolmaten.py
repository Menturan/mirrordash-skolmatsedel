from datetime import date

import pytest

from mirrordash_skolmatsedel.providers import skolmaten
from tests.conftest import fixture_bytes

WEEK = date(2026, 11, 16)  # the Monday of the saved feed


def test_a_real_feed_gives_the_dishes_per_date():
    days = skolmaten.parse_week(fixture_bytes("skolmaten_week.xml"))
    assert sorted(days) == [date(2026, 11, d) for d in (16, 17, 18, 19, 20)]
    assert days[date(2026, 11, 16)] == ["Broccoli- och ostsås med pasta", "Bolognese på sojafärs med pasta"]
    assert days[date(2026, 11, 20)][0] == "Morotsbiff med mango- currydressing och bulgur"


def test_dishes_lose_trailing_commas_and_spaces():
    assert skolmaten.split_dishes("Soppa, <br/>Pasta,  <br />  Pannkakor ,") == ["Soppa", "Pasta", "Pannkakor"]


def test_empty_lines_and_repeated_dishes_are_dropped():
    assert skolmaten.split_dishes("<br/>Fisk<br/>, <br/>Fisk") == ["Fisk"]
    assert skolmaten.split_dishes("") == []


def test_html_entities_are_decoded():
    assert skolmaten.split_dishes("Mac &amp; cheese") == ["Mac & cheese"]


def test_the_date_is_the_pubdate_in_either_format():
    assert skolmaten.parse_date("Mon, 16 Nov 2026 00:00:00 GMT") == WEEK
    assert skolmaten.parse_date("2026-11-16T00:00:00Z") == WEEK
    assert skolmaten.parse_date("not a date") is None


def test_an_item_without_dishes_or_date_is_left_out():
    feed = (b"<rss><channel>"
            b"<item><description>Soup</description><pubDate>nonsense</pubDate></item>"
            b"<item><description><![CDATA[ , ]]></description><pubDate>Tue, 17 Nov 2026 00:00:00 GMT</pubDate></item>"
            b"</channel></rss>")
    assert skolmaten.parse_week(feed) == {}


@pytest.mark.asyncio
async def test_fetch_menu_asks_only_for_the_schools_rss(make_net):
    net = make_net(raw=(fixture_bytes("skolmaten_week.xml"), None))
    menu = await skolmaten.fetch_menu(net, "borgarskolan", WEEK, WEEK, 3600)
    assert menu.error is None and len(menu.days) == 5
    assert net.fetch.call_args.args == ("https://skolmaten.se/api/4/rss/week/borgarskolan",)
    net.fetch_json.assert_not_called()


@pytest.mark.asyncio
async def test_fetch_menu_reports_an_error_without_data(make_net):
    menu = await skolmaten.fetch_menu(make_net(raw=(None, "offline")), "x", WEEK, WEEK, 3600)
    assert menu.days == {} and menu.error == "offline"
    menu = await skolmaten.fetch_menu(make_net(raw=(b"<rss", None)), "x", WEEK, WEEK, 3600)
    assert menu.error == "invalid"


@pytest.mark.asyncio
async def test_the_lists_come_from_the_bundled_file_without_the_network(make_net):
    net = make_net()
    assert any(m["id"] == "gavle-kommun" for m in await skolmaten.list_municipalities(net))
    assert {"id": "borgarskolan", "name": "Borgarskolan"} in await skolmaten.list_schools(net, "gavle-kommun")
    net.fetch.assert_not_called()
    net.fetch_json.assert_not_called()
