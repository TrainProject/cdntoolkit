# coding=utf-8

from typing import List

from tornado.options import options
from twisted.internet.defer import Deferred

from util import reactor, get_isp_idc
from util.json import AttrJson
from util.message import WampMessage
from util.protocol import ConfigGetResponse
from .handler import WalkerHandler


class ApmHandler(WalkerHandler):
    def __init__(self, message: WampMessage) -> None:
        self.offset = 0.0
        self.config: ConfigGetResponse = ConfigGetResponse()
        super().__init__(message)

    def name(self) -> str:
        return "apm"

    def set_config(self, data: str) -> None:
        self.config = ConfigGetResponse(data)

    def data(self, content: str) -> None:
        if not content:
            return

        send_list: List[str] = list()

        for line in content.split('\n'):
            if not line:
                continue

            item = AttrJson.loads(line)

            item.area = self.config.area
            item.country = self.config.country
            item.province = self.config.province
            item.role = self.config.role
            item.isp = self.config.isp
            item.idc = self.config.idc

            if item.isp == 'unknown' or item.idc == 'unknown':
                isp, idc = get_isp_idc()
                if isp:
                    item.isp = isp
                if idc:
                    item.idc = idc

            send_list.append(AttrJson.dumps(item))

        if send_list:
            reactor().callLater(
                self.offset,
                self.send_apm,
                '\n'.join(send_list)
            )

        """
        ret = self.send_apm(content)
        if not ret and retry:
            reactor().callLater(5, self.data, content, False)
        """

    def call_config(self, data: str) -> Deferred:
        return self.message.rpc(
            options.topic_config_get, data
        )

    def send_apm(self, data: str) -> bool:
        return self.message.send(
            options.topic_apm_collector, data
        )
