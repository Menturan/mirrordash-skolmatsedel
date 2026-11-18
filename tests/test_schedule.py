from datetime import date, datetime, time

from mirrordash_skolmatsedel.schedule import ALL_DAY, DIM, NEXT_DAY, ShownDay, parse_switch_time, shown_days

# November 2026: the 18th is a Wednesday, the 20th a Friday, the 21st and 22nd the weekend.
WED_MORNING = datetime(2026, 11, 18, 9, 0)
WED_AFTER_LUNCH = datetime(2026, 11, 18, 13, 0)
FRI_MORNING = datetime(2026, 11, 20, 8, 0)
FRI_AFTER_LUNCH = datetime(2026, 11, 20, 13, 30)
SATURDAY = datetime(2026, 11, 21, 10, 0)
SUNDAY_EVENING = datetime(2026, 11, 22, 20, 0)


def dates(shown):
    return [entry.day.day for entry in shown]


def test_before_lunch_today_is_the_first_day_in_every_mode():
    for mode in (NEXT_DAY, ALL_DAY, DIM):
        assert dates(shown_days(WED_MORNING, 3, mode)) == [18, 19, 20]


def test_after_lunch_the_default_mode_starts_from_the_next_school_day():
    assert dates(shown_days(WED_AFTER_LUNCH, 3, NEXT_DAY)) == [19, 20, 23]


def test_just_before_the_switch_time_today_still_counts():
    assert dates(shown_days(datetime(2026, 11, 18, 12, 59), 2, NEXT_DAY)) == [18, 19]


def test_friday_after_lunch_starts_on_monday():
    assert dates(shown_days(FRI_AFTER_LUNCH, 2, NEXT_DAY)) == [23, 24]


def test_friday_before_lunch_shows_friday_then_monday():
    assert dates(shown_days(FRI_MORNING, 2, NEXT_DAY)) == [20, 23]


def test_weekends_are_skipped_in_every_mode():
    for mode in (NEXT_DAY, ALL_DAY, DIM):
        assert dates(shown_days(SATURDAY, 2, mode)) == [23, 24]
        assert dates(shown_days(SUNDAY_EVENING, 1, mode)) == [23]


def test_all_day_keeps_today_after_lunch_and_nothing_is_dimmed():
    shown = shown_days(FRI_AFTER_LUNCH, 2, ALL_DAY)
    assert shown == [ShownDay(date(2026, 11, 20)), ShownDay(date(2026, 11, 23))]


def test_dim_keeps_today_after_lunch_but_dimmed():
    shown = shown_days(WED_AFTER_LUNCH, 2, DIM)
    assert shown == [ShownDay(date(2026, 11, 18), dimmed=True), ShownDay(date(2026, 11, 19))]


def test_dim_does_not_dim_before_lunch():
    assert not shown_days(WED_MORNING, 2, DIM)[0].dimmed


def test_one_day_at_least_is_always_asked_for():
    assert dates(shown_days(WED_MORNING, 0, NEXT_DAY)) == [18]


def test_another_switch_time():
    at_noon = time(12, 0)
    assert dates(shown_days(datetime(2026, 11, 18, 12, 0), 1, NEXT_DAY, at_noon)) == [19]
    assert dates(shown_days(datetime(2026, 11, 18, 11, 59), 1, NEXT_DAY, at_noon)) == [18]


def test_the_switch_time_setting_falls_back_to_13_00():
    assert parse_switch_time("12:30") == time(12, 30)
    for blank_or_bad in ("", None, "lunch", "25:00", "12"):
        assert parse_switch_time(blank_or_bad) == time(13, 0)
