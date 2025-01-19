import datetime

MONTH_TO_OBLIO_CALENDAR_TEXT = {
    1: "Ianuarie",
    2: "Februarie",
    3: "Martie",
    4: "Aprilie",
    5: "Mai",
    6: "Iunie",
    7: "Iulie",
    8: "August",
    9: "Septembrie",
    10: "Octombrie",
    11: "Noiembrie",
    12: "Decembrie",
}


def get_previous_month_as_date() -> datetime.date:
    now = datetime.datetime.now()
    year = now.year
    month = now.month - 1

    if month == 0:
        month = 12
        year -= 1

    return datetime.date(year, month, 1)
