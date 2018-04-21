# coding=utf-8

import re
from typing import Any, Tuple, Dict

import treq
from orderedattrdict import AttrDict
from treq.response import _Response
from twisted.internet.defer import Deferred
from twisted.python.failure import Failure

from util.exception import print_frame
from .collector import Collector


# Active connections: 291
# server accepts handled requests
#  16630948 16630948 31070465
# Reading: 6 Writing: 179 Waiting: 106


class NginxCollector(Collector):
    def __init__(self) -> None:
        self.ts: int = 0
        self.regexp: re.__Regex = re.compile(
            u"Active connections: (?P<actives>\d+).*\n"
            u"server accepts handled requests.*\n (?P<accepts>\d+) (?P<handled>\d+) (?P<requests>\d+).*\n"
            u"Reading: (?P<reading>\d+) Writing: (?P<writing>\d+) Waiting: (?P<waiting>\d+).*")

        self.last: Dict[str, Tuple] = dict([
            ('accepts', None),
            ('handled', None),
            ('requests', None),
        ])

        super().__init__()

    def name(self) -> str:
        return "NginxCollector"

    def collect(self, ts: int) -> None:
        self.ts = ts
        status_url = "http://127.0.0.1/NginxStatus/"

        try:
            d: Deferred = treq.get(status_url, timeout=1)
            d.addCallback(self.complete_header, ts)
            d.addErrback(self.response_error)
        except Exception as e:
            print_frame(e)

    def handler_error(self, error: Failure) -> None:
        print(error.getErrorMessage())

    def response_error(self, error: Failure) -> None:
        print(error.getErrorMessage())
        try:
            status_url = "http://127.0.0.1/NginxStatus/"
            d: Deferred = treq.get(status_url, timeout=1)
            d.addCallback(self.complete_header)
            d.addErrback(self.handler_error)
        except Exception as e:
            print_frame(e)

    def complete_header(self, r: _Response) -> None:
        if r is not None and r.code == 200:
            content: Deferred = r.content()
            content.addCallback(self.complete_body)
            content.addErrback(self.response_error)

    def complete_body(self, content: bytes) -> None:
        try:
            ts = self.ts
            text = content.decode()
            m = re.match(self.regexp, text)
            if m:
                self.print_ngx("actives", int(m.group("actives")), ts)
                self.print_ngx("accepts", int(m.group("accepts")), ts)
                self.print_ngx("handled", int(m.group("handled")), ts)
                self.print_ngx("requests", int(m.group("requests")), ts)
                self.print_ngx("reading", int(m.group("reading")), ts)
                self.print_ngx("writing", int(m.group("writing")), ts)
                self.print_ngx("waiting", int(m.group("waiting")), ts)

        except Exception as e:
            print_frame(e)

    def print_ngx(self, metric: str, value: int, ts: int) -> None:
        if metric in self.last:
            item = self.last[metric]
            if item is not None:
                timestamp = item[0]
                _value = item[1]
                if self.ts > timestamp and value > _value:
                    self.last[metric] = (self.ts, value)
                    value = (value - _value) // (self.ts - timestamp) + 1

                else:
                    return None

            else:
                self.last[metric] = (self.ts, value)
                return None

        data = AttrDict()
        data.metric = "ngx.status.%s" % metric
        data.ts = ts
        data.value = value
        self.send_message(data)
