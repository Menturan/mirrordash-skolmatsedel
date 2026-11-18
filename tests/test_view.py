from datetime import date

from mirrordash_skolmatsedel.day_header import day_header
from mirrordash_skolmatsedel.providers.base import Menu
from mirrordash_skolmatsedel.schedule import ShownDay
from mirrordash_skolmatsedel.view import SchoolMenu, build_days

WED, THU, FRI = date(2026, 11, 18), date(2026, 11, 19), date(2026, 11, 20)
SWEDISH = {"today": "Idag", "tomorrow": "Imorgon", "wednesday": "Onsdag", "thursday": "Torsdag", "friday": "Fredag"}


def translate(key, default):
    return SWEDISH.get(key, default)


def test_header_today_and_tomorrow_have_the_weekday_beside_them_and_later_days_only_the_weekday():
    assert day_header(WED, WED, translate) == ("Idag", "Onsdag")
    assert day_header(THU, WED, translate) == ("Imorgon", "Torsdag")
    assert day_header(FRI, WED, translate) == ("Fredag", "")


def test_header_falls_back_to_english_without_a_translation():
    assert day_header(WED, WED, lambda key, default: default) == ("Today", "Wednesday")


def test_header_after_a_weekend_names_monday_not_tomorrow_unless_it_is():
    monday = date(2026, 11, 23)
    assert day_header(monday, date(2026, 11, 20), translate)[1] == ""  # Friday: Monday is not tomorrow
    assert day_header(monday, date(2026, 11, 22), translate)[0] == "Imorgon"  # Sunday: it is


ALVA = SchoolMenu("Alva", Menu({WED: ["Fisk", "Soppa"], THU: ["Pasta"]}))
ELIS = SchoolMenu("Elis", Menu({WED: ["Bulle"], FRI: ["Pannkakor"]}))


def test_each_day_has_a_row_per_school_with_its_dishes():
    days = build_days([ShownDay(WED), ShownDay(THU)], [ALVA, ELIS], WED, translate)
    assert days[0] == {"label": "Idag", "sub": "Onsdag", "dimmed": False,
                       "schools": [{"name": "Alva", "dishes": ["Fisk", "Soppa"]},
                                   {"name": "Elis", "dishes": ["Bulle"]}]}


def test_a_school_without_a_menu_that_day_is_not_shown_that_day():
    days = build_days([ShownDay(WED), ShownDay(THU), ShownDay(FRI)], [ALVA, ELIS], WED, translate)
    assert [[s["name"] for s in d["schools"]] for d in days] == [["Alva", "Elis"], ["Alva"], ["Elis"]]


def test_a_day_without_any_menu_is_not_shown():
    days = build_days([ShownDay(WED), ShownDay(FRI)], [ALVA], WED, translate)
    assert [d["label"] for d in days] == ["Idag"]


def test_one_school_has_no_name():
    days = build_days([ShownDay(WED)], [ALVA], WED, translate)
    assert days[0]["schools"] == [{"name": "", "dishes": ["Fisk", "Soppa"]}]


def test_the_dimmed_flag_follows_the_shown_day():
    days = build_days([ShownDay(WED, dimmed=True), ShownDay(THU)], [ALVA], WED, translate)
    assert [d["dimmed"] for d in days] == [True, False]


def test_nothing_to_show_gives_no_days():
    assert build_days([ShownDay(WED)], [], WED, translate) == []
    assert build_days([ShownDay(WED)], [SchoolMenu("Alva", Menu(error="offline"))], WED, translate) == []
