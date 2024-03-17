import random
import unittest
from datetime import datetime

from common_package.utils import HH_MM_SS_FORMAT, YYYY_MM_DD_FORMAT, parse_file_name


class ParserTest(unittest.TestCase):

    n_runs = 100

    def time_until_end_of_day(self, dt: datetime) -> int:
        """
        Return seconds till the end of a day for given datetime obj
        """
        return (
            ((24 - dt.hour - 1) * 60 * 60)
            + ((60 - dt.minute - 1) * 60)
            + (60 - dt.second)
        )

    def get_timestamp_range(self) -> str:
        """
        Return seconds till the end of a day for given datetime obj
        """
        max_timestamp = int(datetime.now().timestamp())
        from_timestamp = random.randint(1, max_timestamp)

        # from date and to date should be within single day
        sec_until_end_of_day = self.time_until_end_of_day(
            datetime.fromtimestamp(from_timestamp)
        )

        from_to_range = random.randint(1, sec_until_end_of_day - 1)

        to_timestamp = from_timestamp + from_to_range
        return from_timestamp, to_timestamp

    def get_filename(self, from_timestamp: int, to_timestamp: int) -> str:
        """
        Take from and to timestamps and return nginx log filename based on that
        """
        from_date = datetime.fromtimestamp(from_timestamp)
        to_date = datetime.fromtimestamp(to_timestamp)

        yyyy_mm_dd = from_date.strftime(YYYY_MM_DD_FORMAT)
        hh_mm_ss_from = from_date.strftime(HH_MM_SS_FORMAT)
        hh_mm_ss_to = to_date.strftime(HH_MM_SS_FORMAT)
        return f"stdout/{yyyy_mm_dd}/{hh_mm_ss_from}_{hh_mm_ss_to}_.json"

    def test_success(self):
        for _ in range(self.n_runs):
            from_origin, to_origin = self.get_timestamp_range()
            filename = self.get_filename(from_origin, to_origin)
            from_parsed, to_parsed = parse_file_name(filename)

            assert from_parsed == from_origin
            assert to_parsed == to_origin

    def test_failed(self):
        with self.assertRaises(ValueError):
            parse_file_name("stdout/20/03/16/10:00:00_10:59:59_S0.json")

        with self.assertRaises(ValueError):
            parse_file_name("stdout/2024/03/1/10:00:00_10:59:59_S0.json")

        with self.assertRaises(ValueError):
            parse_file_name("stdout/2024/03/16/10:00:00_10-59-59-S0.json")


if __name__ == "__main__":
    unittest.main()
