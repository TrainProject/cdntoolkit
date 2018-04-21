# coding=utf-8

from typing import Dict, List

from tornado.options import options

from util.message import WampMessage


class ApmApp:
    def __init__(self) -> None:
        from .buffer import ApmBuffer
        self.buffer = ApmBuffer()

        from .proxy import ApmProxy

        if options.role == "master":
            self.connections: Dict = dict()
            self.proxy = ApmProxy(self.buffer, self.connections)
            self.messages: List = list()

            for port in range(
                options.router_port_start,
                options.router_port_end,
                options.router_port_step
            ):

                message = WampMessage()

                message.add_subscribe(
                    options.topic_apm_collector,
                    self.proxy.handle_master
                )

                message.start(
                    options.router_url.format(port=port),
                    options.router_domain
                )

                self.messages.append(message)

            from util.message import WsClientMessage

            for index in range(options.shard * options.apm_multiple):
                client = WsClientMessage()
                client.run(options.apm_client.format(port=index))
                self.connections[index] = (client, list(), list())

        else:
            self.proxy = ApmProxy(self.buffer)

            from util.message import WsServerMessage
            server = WsServerMessage()
            server.add_slot(
                WsServerMessage.recv_message,
                self.proxy.handle_slave
            )
            server.run(options.apm_server.format(port=options.shard))
