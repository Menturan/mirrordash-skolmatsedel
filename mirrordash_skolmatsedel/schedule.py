"""Which school days the card shows, from the time of day and the after-lunch setting."""

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

NEXT_DAY = "next_day"  # after lunch, start from the next school day
ALL_DAY = "all_day"  # today stays until midnight
DIM = "dim"  # after lunch, today is still shown, but dimmed
MODES = (NEXT_DAY, ALL_DAY, DIM)

DEFAULT_SWITCH = time(13, 0)  # when lunch is over, unless the owner sets another time
SATURDAY = 5  # date.weekday(): Monday is 0


@dataclass(frozen=True)
class ShownDay:
    day: date
    dimmed: bool = False


def parse_switch_time(text) -> time:
    """'13:00' -> time(13, 0). Blank or invalid text means the default (13:00)."""
    try:
        hours, minutes = str(text).strip().split(":")
        return time(int(hours), int(minutes))
    except (TypeError, ValueError):
        return DEFAULT_SWITCH


def school_days(start: date, count: int) -> list[date]:
    """The first `count` weekdays from `start` (inclusive); Saturdays and Sundays are skipped."""
    days = []
    day = start
    while len(days) < count:
        if day.weekday() < SATURDAY:
            days.append(day)
        day += timedelta(days=1)
    return days


def shown_days(now: datetime, days_ahead: int, mode: str, switch: time = DEFAULT_SWITCH) -> list[ShownDay]:
    """The days to show at `now`, `days_ahead` school days counted from the first one shown.

    After the switch time: NEXT_DAY starts from tomorrow (on a Friday that is the next Monday), DIM keeps
    today but dimmed, ALL_DAY changes nothing. A weekend never shows: the first day is the next weekday."""
    today = now.date()
    after_lunch = now.time() >= switch
    start = today + timedelta(days=1) if mode == NEXT_DAY and after_lunch else today
    return [ShownDay(day, dimmed=mode == DIM and after_lunch and day == today)
            for day in school_days(start, max(days_ahead, 1))]
