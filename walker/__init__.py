# coding=utf-8

from datetime import datetime
from typing import Dict, Any

from orderedattrdict import AttrDict
from tornado.options import options
from twisted.internet.defer import Deferred, CancelledError
from twisted.python.failure import Failure

import util
from util import reactor
from util.exception import print_frame
from util.message import WampMessage
from util.protocol import ConfigGetRequest


class WalkerApp:
    def __init__(self) -> None:
        self.defer: Deferred = None

        util.set_uuid(options.uuid)

        self.uuid = util.get_uuid()
        self.message: WampMessage = WampMessage()

        headers: Dict[str, str] = dict()
        headers["Host-Id"] = util.get_uuid()
        headers["Time-Created"] = str(int(datetime.utcnow().timestamp()))
        headers["Walker-Version"] = (
            "{major}.{minor}.{release}".format(
                major=options.major_version,
                minor=options.minor_version,
                release=options.release_version
            )
        )
        headers["Host-Address"] = util.get_address()
        headers["Host-Uptime"] = util.get_uptime()
        headers["Host-Kernel"] = util.get_kernel()
        headers["Host-Name"] = util.get_hostname()

        if not options.router and options.router_url:
            options.router = options.router_url.format(
                port=(
                    options.router_port_start +
                    int(self.uuid.split("-")[0][7], 16)
                )
            )

        self.message.start(options.router, options.router_domain, headers)

        from .handler import WalkerHandler
        self.handler: WalkerHandler = WalkerHandler(self.message)

        from .handler import NullHandler
        self.null: NullHandler = NullHandler(self.message)
        self.handler.add(self.null)

        from .publish import PublishHandler
        self.ph: PublishHandler = PublishHandler(self.message)
        self.handler.add(self.ph)

        from .command import CommandHandler
        self.ch: CommandHandler = CommandHandler(self.message)
        self.handler.add(self.ch)

        from .apm import ApmHandler
        self.apm: ApmHandler = ApmHandler(self.message)
        self.apm.offset = int(self.uuid[0:2], 16) / 25
        self.handler.add(self.apm)

        from .config import ConfigHandler
        self.config: ConfigHandler = ConfigHandler(self.message)
        self.handler.add(self.config)

        from .internal import InternalHandler
        self.internal: InternalHandler = InternalHandler(self.message)
        self.internal.add_slot(
            InternalHandler.config_changed,
            self.apm.set_config
        )

        self.internal.major_version = int(options.major_version)
        self.internal.minor_version = int(options.minor_version)
        self.internal.release_version = int(options.release_version)
        self.handler.add(self.internal)

        self.message.add_register(
            util.get_uuid(),
            self.handler.dispatch
        )

        self.message.add_signal(
            'onjoined',
            self.run_set_config
        )

        from util.message import WsServerMessage
        self.collect = WsServerMessage()
        self.collect.add_slot(WsServerMessage.recv_message, self.apm.data)
        self.collect.run(options.config.unix_sock)

    def check_config(self) -> None:
        if self.defer is not None:
            self.defer.cancel()
            self.defer = None

    def run_set_config(self) -> None:
        reactor().callLater(20, self.check_config)

        if self.defer is not None:
            self.defer.cancel()
            self.defer = None
            return

        data = AttrDict()
        data.host = self.uuid
        param: ConfigGetRequest = ConfigGetRequest(data)

        self.defer = self.message.rpc(
            options.topic_config_get, str(param)
        )

        self.defer.addCallback(self.set_config)
        self.defer.addErrback(self.set_error)

    def set_config(self, data: str) -> None:
        self.defer = None
        try:
            self.apm.set_config(data)
        except Exception as e:
            print_frame(e)
            reactor().callLater(20 * 60, self.run_set_config)

    def set_error(self, error: Failure) -> None:
        self.defer = None
        print(error.getErrorMessage())
        if not isinstance(error.value, CancelledError):
            reactor().callLater(20 * 60, self.run_set_config)
