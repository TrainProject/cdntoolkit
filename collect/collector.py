# coding=utf-8

import hashlib
from typing import Dict, List

from orderedattrdict import AttrDict
from tornado.options import options

from util import loop_timer, get_hostname, round_looper
from util.exception import print_frame
from util.json import AttrJson
from util.message import WsClientMessage


class Collector:
    message: WsClientMessage = None
    count: int = 0
    data: Dict[str, List[str]] = dict()
    sending: Dict[str, List[str]] = dict()
    host: str = str()

    def __init__(self) -> None:
        self.offset = int(
            int(hashlib.md5(self.name().encode()).hexdigest()[-1],
                16) * 100 * options.collect_interval / 16.0
        )
        Collector.host = get_hostname()
        Collector.data[self.name()] = list()
        Collector.sending[self.name()] = list()

    def name(self) -> str:
        return "Collector"

    def collect(self, ts: int) -> None:
        pass

    def swap(self, timestamp: int) -> None:
        self.collect(timestamp)
        self.sending[self.name()] = self.data[self.name()]
        self.data[self.name()] = list()

    def run(self) -> None:
        loop_timer(round_looper(options.collect_interval, self.offset, self.swap))

    def send_message(self, data: AttrDict) -> None:
        data.host = self.host
        data_json: str = AttrJson.dumps(data)
        Collector.data[self.name()].append(data_json)

    @classmethod
    def do_send(cls, content: str) -> bool:
        ret = False
        try:
            cls.message.send_message(content)
            ret = True
        except Exception as e:
            print_frame(e)

        return ret

    @classmethod
    def send(cls, _: int) -> None:
        sending = cls.sending
        for name, data in sending.items():
            content = "\n".join([d for d in data])
            # print(name, len(data))
            cls.do_send(content)

    @classmethod
    def loop_send(cls, message: WsClientMessage) -> None:
        cls.message = message
        loop_timer(round_looper(options.collect_interval, 0, cls.send))
