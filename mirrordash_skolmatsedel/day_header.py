"""The words in a day's header: 'Idag' + weekday, 'Imorgon' + weekday, or the weekday alone."""

from datetime import date, timedelta

WEEKDAY_KEYS = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")
DEFAULT_WEEKDAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")


def day_header(day: date, today: date, translate) -> tuple[str, str]:
    """(label, dimmed sub label) of a day. translate(key, default) gives the texts in the mirror's language."""
    weekday = translate(WEEKDAY_KEYS[day.weekday()], DEFAULT_WEEKDAYS[day.weekday()])
    if day == today:
        return translate("today", "Today"), weekday
    if day == today + timedelta(days=1):
        return translate("tomorrow", "Tomorrow"), weekday
    return weekday, ""
