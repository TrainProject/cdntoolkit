# coding=utf-8

from typing import Callable, Any, no_type_check, Dict

from autobahn.twisted.wamp import Application
from autobahn.twisted.websocket import WebSocketClientFactory, WebSocketClientProtocol
from autobahn.twisted.websocket import WebSocketServerFactory, WebSocketServerProtocol
from autobahn.websocket.protocol import WebSocketProtocol
from twisted.application.internet import ClientService
from twisted.internet.defer import Deferred
from twisted.internet.endpoints import clientFromString
from twisted.internet.endpoints import serverFromString
from twisted.internet.interfaces import IStreamServerEndpoint

from util import reactor
from util.exception import print_frame
from util.observer import Observer
from util.observer import signal


class WampMessage(Application):
    def __init__(self) -> None:
        super().__init__()

        def on_open() -> None:
            print("onOpen")

        self.add_signal('onjoined', on_open)

    def add_signal(self, name: str, func: Callable[..., None]) -> None:
        self._signals.setdefault(name, []).append(func)

    def add_subscribe(self, uri: str, func: Callable[..., None]) -> None:
        self._handlers.append((uri, func))

    def add_register(self, uri: str, func: Callable[..., str]) -> None:
        self._procs.append((uri, func))

    def start(self, router: str, domain: str, headers: Dict[str, str]=None) -> Deferred:
        from autobahn.twisted.wamp import ApplicationRunner
        runner = ApplicationRunner(router, domain, headers=headers)
        return runner.run(self.__call__, False, True)

    @no_type_check
    def __call__(self, config):
        from autobahn.twisted.wamp import _ApplicationSession
        self.session = _ApplicationSession(config, self)
        return self.session

    def send(self, topic: str, data: str) -> bool:
        try:
            self.session.publish(topic, data)
            ret = True
        except Exception as e:
            ret = False
            print_frame(e)
        return ret

    def rpc(self, topic: str, data: str=None) -> Deferred:
        ret = None
        try:
            if self.session is not None:
                if data is None:
                    ret = self.session.call(topic)
                else:
                    ret = self.session.call(topic, data)
        except Exception as e:
            print_frame(e)

        return ret


class WsClientProtocol(WebSocketClientProtocol):
    def __init__(self) -> None:
        self.state: int = -1
        super().__init__()

    def onMessage(self, payload: bytes, is_binary: bool) -> None:
        if not is_binary:
            self.factory.message.recv_message(payload.decode())


class WsClientFactory(WebSocketClientFactory):
    def __init__(self, message: 'WsClientMessage') -> None:
        super().__init__()
        self.message: WsClientMessage = message

    @no_type_check
    def buildProtocol(self, addr):
        p = WebSocketClientFactory.buildProtocol(self, addr)
        self.message.session = p
        return p


class WsClientMessage(Observer):
    def __init__(self) -> None:
        self.session: WebSocketClientProtocol = None
        self.service: ClientService = None
        self.endpoint: IStreamServerEndpoint = None
        self.factory: WsClientFactory = None
        super().__init__()

    def run(self, sock: str) -> None:
        self.factory = WsClientFactory(self)
        self.factory.protocol = WsClientProtocol
        self.endpoint = clientFromString(reactor(), sock)
        self.service = ClientService(self.endpoint, self.factory)
        self.service.startService()

        def cleanup(proto: Any) -> Any:
            if hasattr(proto, '_session') and proto._session is not None:
                if proto._session.is_attached():
                    return proto._session.leave()
                elif proto._session.is_connected():
                    return proto._session.disconnect()

        def init_proto(proto: Any) -> Any:
            reactor().addSystemEventTrigger('before', 'shutdown', cleanup, proto)
            return proto

        d = self.service.whenConnected()
        d.addCallback(init_proto)

    def send_message(self, content: str) -> None:
        if (self.session and self.session.state ==
                WebSocketProtocol.STATE_OPEN):
            self.session.sendMessage(content.encode())
        else:
            print('self session is None')

    @signal
    def recv_message(self, data: str) -> None:
        pass


class WsServerProtocol(WebSocketServerProtocol):
    def __init__(self) -> None:
        self.state: int = -1
        super().__init__()

    def onMessage(self, payload: bytes, is_binary: bool) -> None:
        if not is_binary:
            self.factory.message.recv_message(payload.decode())


class WsServerFactory(WebSocketServerFactory):
    def __init__(self, message: 'WsServerMessage') -> None:
        super().__init__()
        self.message: WsServerMessage = message

    @no_type_check
    def buildProtocol(self, addr):
        p = WebSocketServerFactory.buildProtocol(self, addr)
        self.message.session = p
        return p


class WsServerMessage(Observer):
    def __init__(self) -> None:
        self.session: WebSocketProtocol = None
        self.factory: WsServerFactory = None
        self.server: IStreamServerEndpoint = None
        super().__init__()

    def run(self, sock: str) -> None:
        if sock.startswith("unix:"):
            try:
                import os
                os.unlink(sock.split(":")[1])
            except Exception as e:
                print(e)

        self.factory = WsServerFactory(self)
        self.factory.protocol = WsServerProtocol

        self.server = serverFromString(reactor(), sock)
        self.server.listen(self.factory)

    def send_message(self, content: str) -> None:
        if (self.session and self.session.state ==
                WebSocketProtocol.STATE_OPEN):
            try:
                self.session.sendMessage(content.encode())
            except Exception as e:
                print_frame(e)
        else:
            print('self session is None')

    @signal
    def recv_message(self, data: str) -> None:
        pass
