import re
from datetime import datetime
from typing import Tuple

YYYY_MM_DD_FORMAT = "%Y/%m/%d"
HH_MM_SS_FORMAT = "%H:%M:%S"


def get_timestamp(
    year: str, month: str, day: str, hours: str, minutes: str, seconds: str
) -> int:
    """
    Return unix timestamp from {year,month,day hour,minutes,seconds}
    """
    date = datetime.strptime(
        f"{year}/{month}/{day} {hours}:{minutes}:{seconds}",
        f"{YYYY_MM_DD_FORMAT} {HH_MM_SS_FORMAT}",
    )
    return int(datetime.timestamp(date))


def parse_file_name(file_name: str) -> Tuple[int, int]:
    """
    Input nginx log file name and return from_timestamp, to_timestamp pair
    """
    match = re.match(
        (
            r".*/(?P<year>[0-9]{4})/(?P<month>[0-9]{2})/(?P<day>[0-9]{2})/"
            r"(?P<hour_from>[0-9]{2}):(?P<min_from>[0-9]{2}):(?P<sec_from>[0-9]{2})_"
            r"(?P<hour_to>[0-9]{2}):(?P<min_to>[0-9]{2}):(?P<sec_to>[0-9]{2})_.*"
        ),
        file_name,
    )
    if not match:
        raise ValueError("Incorrect filename pattern")

    groups = match.groupdict()

    from_timestamp = get_timestamp(
        groups["year"],
        groups["month"],
        groups["day"],
        groups["hour_from"],
        groups["min_from"],
        groups["sec_from"],
    )
    to_timestamp = get_timestamp(
        groups["year"],
        groups["month"],
        groups["day"],
        groups["hour_to"],
        groups["min_to"],
        groups["sec_to"],
    )
    return from_timestamp, to_timestamp
