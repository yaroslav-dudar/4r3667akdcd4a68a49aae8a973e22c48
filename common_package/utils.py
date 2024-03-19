import re
from dataclasses import dataclass
from datetime import datetime


TIME_LOCAL_FORMAT = "%d/%b/%Y:%H:%M:%S %z"


@dataclass(frozen=True)
class NginxLog:
    remote_addr: str
    remote_user: str
    time_local: int  # unix timestamp
    http_method: str
    request_url: str
    http_protocol: str
    status: int
    body_bytes_sent: int
    http_referer: str
    http_user_agent: str
    gzip_ratio: str

    def __post_init__(self):
        # frozen=True: require object.__setattr__()
        object.__setattr__(self, "status", int(self.status))
        object.__setattr__(self, "body_bytes_sent", int(self.body_bytes_sent))
        object.__setattr__(self, "time_local", self._time_local_to_timestamp())
        # escape `'` character to be able to push data to database
        object.__setattr__(
            self, "http_user_agent", self.http_user_agent.replace("'", r"\'")
        )
        object.__setattr__(self, "http_method", self.http_method.replace("'", r"\'"))
        object.__setattr__(self, "request_url", self.request_url.replace("'", r"\'"))
        object.__setattr__(
            self, "http_protocol", self.http_protocol.replace("'", r"\'")
        )

    def _time_local_to_timestamp(self) -> int:
        timestamp = datetime.strptime(self.time_local, TIME_LOCAL_FORMAT)
        return int(datetime.timestamp(timestamp))


def parse_nginx_log(log: str) -> NginxLog:
    """
    Parse nginx access log in such format
        '$remote_addr - $remote_user [$time_local] '
        '"$request" $status $body_bytes_sent '
        '"$http_referer" "$http_user_agent" "$gzip_ratio"';
    """
    pattern = (
        r"^(?P<remote_addr>[^\s]*) - (?P<remote_user>[^\s]*)\s{0,1}- \[(?P<time_local>[^\]]*)\] "
        r'"(?P<http_method>[^\s]*) (?P<request_url>[^\s]*) (?P<http_protocol>[^\s]*)" '
        r'(?P<status>[^\s]*) (?P<body_bytes_sent>[^\s]*) "(?P<http_referer>[^"]*)" '
        r'"(?P<http_user_agent>[^"]*)" "(?P<gzip_ratio>[^"]*)"$'
    )
    match = re.match(pattern, log)

    if not match:
        # "$request" may contain data that imposible to parse
        # when client try to connect via Https to Http server
        # example: "\x16\x03\x01\x00\xCA\x01\x00\x00\xC6\x03\x03\xD6\xB6c\xF6,G\x878\x17`\xFE" 400 157 "-" "-" "-"
        raise ValueError("Invalid nginx access log")

    groups = match.groupdict()
    return NginxLog(**groups)
