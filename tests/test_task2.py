import datetime
import ipaddress
import random
import unittest

from common_package.utils import TIME_LOCAL_FORMAT, parse_nginx_log


class ParserTest(unittest.TestCase):

    n_runs = 10000
    user_agent = (
        "'Mozilla/5.0 (compatible; GenomeCrawlerd/1.0; "
        "+https://www.nokia.com/networks/ip-networks/deepfield/genome/)'"
    )

    def get_fake_access_log(
        self,
        log_time: datetime,
        ip_address: str,
        http_method: str,
        body_bytes_sent: int,
    ) -> str:
        time_local = log_time.strftime(TIME_LOCAL_FORMAT)

        return (
            f'{ip_address} - - [{time_local}] "{http_method} /favicon.ico HTTP/1.1" '
            f'200 {body_bytes_sent} "-" "{self.user_agent}" "-"'
        )

    def random_ipv4(self) -> str:
        return ipaddress.IPv4Address._string_from_ip_int(
            random.randint(0, ipaddress.IPv4Address._ALL_ONES)
        )

    def random_http_method(self) -> str:
        return random.choice(
            ["GET", "POST", "PATCH", "DELETE", "OPTIONS", "PUT", "HEAD"]
        )

    def test_success(self):
        log_time = datetime.datetime.now(datetime.timezone.utc)

        for _ in range(self.n_runs):
            delay_in_sec = random.randint(1, 1000)
            log_time = log_time + datetime.timedelta(seconds=delay_in_sec)
            ip_address = self.random_ipv4()
            http_method = self.random_http_method()
            body_bytes_sent = random.randint(1, 10000)

            raw_log = self.get_fake_access_log(
                log_time, ip_address, http_method, body_bytes_sent
            )

            parsed_log = parse_nginx_log(raw_log)
            assert parsed_log.time_local == int(log_time.timestamp())
            assert parsed_log.remote_addr == ip_address
            assert parsed_log.http_method == http_method
            assert parsed_log.body_bytes_sent == body_bytes_sent
            assert parsed_log.gzip_ratio == "-"
            assert parsed_log.http_user_agent.replace(r"\'", "'") == self.user_agent
            assert parsed_log.request_url == "/favicon.ico"

    def test_failed(self):
        with self.assertRaises(ValueError):
            parse_nginx_log("10.132.0.3 - -")

        with self.assertRaises(ValueError):
            incorect_time_local = (
                '10.132.0.3 - - [4554675 "GET /favicon.ico HTTP/1.1" '
                '404 153 "-" "\'Mozilla/5.0 (compatible; GenomeCrawlerd/1.0; '
                '+https://www.nokia.com/networks/ip-networks/deepfield/genome/)\'" "-"'
            )
            parse_nginx_log(incorect_time_local)

        with self.assertRaises(ValueError):
            https_log = (
                '10.132.0.4 - - [16/Mar/2024:16:11:03 +0000] "\\x16\\x03\\x01\\x00\\xB1'
                "\\x01\\x00\\x00\\xAD\\x03\\x03\\x11U\\xD1@\\xC9\\x99\\x96\\xCB\\xE0\\x12"
                "\\xD0\\xCE 5oDb\\x9B\\xB4\\xA2'\\xC2\\xB6\\xE3u[|\\xAC\\xE1j\\x09\\x87"
                "\\x00\\x00P\\xC0/\\xC0+\\xC0\\x11\\xC0\\x07\\xC0\\x13\\xC0\\x09\\xC0"
                '\\x14\\xC0" 400 157 "-" "-" "-"'
            )
            parse_nginx_log(https_log)


if __name__ == "__main__":
    unittest.main()
