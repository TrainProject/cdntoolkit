# coding=utf-8

from typing import no_type_check

from twisted.python.compat import urllib_parse
from twisted.web.http import HTTPFactory
from twisted.web.http import Request, _QUEUED_SENTINEL
from twisted.web.proxy import Proxy, ProxyClientFactory

from . import reactor


class AuthProxyRequest(Request):
    protocols = {b'http': ProxyClientFactory}
    ports = {b'http': 80}

    @no_type_check
    def __init__(self, channel, queued=_QUEUED_SENTINEL) -> None:
        Request.__init__(self, channel, queued)

    @no_type_check
    def process(self) -> None:
        parsed: urllib_parse.ParseResult = urllib_parse.urlparse(self.uri)
        protocol = parsed[0]
        host = parsed.hostname.decode()
        port = self.ports[protocol]

        rest = urllib_parse.urlunparse((b'', b'') + parsed[2:])

        if not rest:
            rest += b'/'

        class_ = self.protocols[protocol]
        headers = self.getAllHeaders().copy()

        if b'host' not in headers:
            headers[b'host'] = host.encode()

        self.content.seek(0, 0)
        s = self.content.read()
        client_factory = class_(
            self.method, rest, self.clientproto,
            headers, s, self
        )
        reactor().connectTCP(host, port, client_factory)


class AuthProxy(Proxy):
    requestFactory = AuthProxyRequest


class AuthProxyFactory(HTTPFactory):
    protocol: type = AuthProxy

    @no_type_check
    def __init__(self, log_path=None, timeout=60*60*12,
                 log_formatter=None) -> None:
        super().__init__(log_path, timeout, log_formatter, reactor())
