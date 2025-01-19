import datetime
import sys

from loglib import logger
from timelib import get_previous_month_as_date


def get_login_code() -> str:
    code = input("what is the 6 digits code? >")
    if len(code) != 6:
        logger.debug("using ok as code")
        return "ok"
    if not code.isnumeric():
        logger.debug("using ok as code")
        return "ok"
    return code


def ask_for_period() -> datetime.date:
    try:
        period = get_previous_month_as_date()
        cyear = period.year
        cmonth = period.month
        year = input(f"what is the year of the bill? ({period.year}) > ")
        if year != "":
            cyear = int(year)
        month = input(f"what is the month of the bill? ({period.month}) > ")
        if month != "":
            cmonth = int(month)

        return datetime.date(cyear, cmonth, 1)
    except ValueError:
        logger.error("failed to supply a proper value for year or month")
        sys.exit()
