"""Calendarul din România: sărbători legale, zile lucrătoare și termene mutate după weekend.

Un termen fiscal care pică într-o zi nelucrătoare se mută în prima zi lucrătoare următoare.
"""

import calendar
from datetime import date, timedelta
from functools import lru_cache

FIXED_HOLIDAYS = [(1, 1), (1, 2), (1, 6), (1, 7), (1, 24), (5, 1), (6, 1), (8, 15), (11, 30), (12, 1),
                  (12, 25), (12, 26)]


def orthodox_easter(year: int) -> date:
    """Paștele ortodox (algoritmul Meeus pentru calendarul iulian, plus 13 zile)."""
    a, b, c = year % 4, year % 7, year % 19
    d = (19 * c + 15) % 30
    e = (2 * a + 4 * b - d + 34) % 7
    month, day = divmod(d + e + 114, 31)
    return date(year, month, day + 1) + timedelta(days=13)


@lru_cache(maxsize=64)
def holidays(year: int) -> dict[date, str]:
    names = {(1, 1): "Anul Nou", (1, 2): "Anul Nou", (1, 6): "Boboteaza", (1, 7): "Sf. Ioan",
             (1, 24): "Unirea Principatelor", (5, 1): "Ziua Muncii", (6, 1): "Ziua Copilului",
             (8, 15): "Adormirea Maicii Domnului", (11, 30): "Sf. Andrei", (12, 1): "Ziua Națională",
             (12, 25): "Crăciunul", (12, 26): "Crăciunul"}
    result = {date(year, m, d): names[(m, d)] for m, d in FIXED_HOLIDAYS}
    easter = orthodox_easter(year)
    for offset, name in [(-2, "Vinerea Mare"), (0, "Paștele"), (1, "Paștele"), (49, "Rusaliile"),
                         (50, "Rusaliile")]:
        result[easter + timedelta(days=offset)] = name
    return result


def is_working_day(day: date) -> bool:
    return day.weekday() < 5 and day not in holidays(day.year)


def next_working_day(day: date) -> date:
    while not is_working_day(day):
        day += timedelta(days=1)
    return day


def working_days(ym: str) -> int:
    year, month = (int(part) for part in ym.split("-"))
    return sum(is_working_day(date(year, month, d)) for d in range(1, calendar.monthrange(year, month)[1] + 1))


def deadline(year: int, month: int, day: int = 25) -> date:
    """Termenul legal (de obicei pe 25), mutat dacă pică într-o zi nelucrătoare."""
    if month > 12:
        year, month = year + 1, month - 12
    return next_working_day(date(year, month, day))
