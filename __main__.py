# coding=utf-8

import os
import sys
from ctypes import CDLL
from typing import Callable, Dict, Any
from typing import List

from tornado.options import options

import util.exception
from util import monkey_patch
from util import reactor
from util.exception import ExceptionHook
from util.exception import trace


def command() -> object:
    from application.command import CommandApp
    application = CommandApp()
    return application


def config() -> object:
    from application.config import ConfigApp
    application = ConfigApp()
    return application


def publish() -> object:
    from publish import PublishApp
    application = PublishApp()
    application.listen(options.publish_port)
    return application


def sync() -> object:
    from sync import SyncApp
    application = SyncApp()
    application.listen(options.sync_port)
    return application


def tunnel() -> object:
    from tunnel import TunnelApp
    application = TunnelApp()
    application.listen(options.tunnel_port + options.shard)
    return application


def walker() -> object:
    from walker import WalkerApp
    application = WalkerApp()

    from util.proxy import AuthProxyFactory
    tcp = reactor().listenTCP(
        0, factory=AuthProxyFactory(), interface="localhost"
    )
    port = tcp._realPortNumber
    os.environ["http_proxy"] = "http://localhost:{port}".format(port=port)

    return application


def collect() -> object:
    from collect import CollectApp
    application = CollectApp()
    return application


def apm() -> object:
    from apm import ApmApp
    application = ApmApp()
    return application


def web() -> object:
    from web import WebApp
    application = WebApp()
    application.listen(options.web_port)
    return application


def monitor() -> object:
    from web import MonitorApp
    application = MonitorApp()
    application.listen(options.monitor_port)
    return application


apps: Dict[str, Callable[[], object]] = {
    "command": command,
    "config": config,
    "publish": publish,
    "sync": sync,
    "tunnel": tunnel,
    "walker": walker,
    "collect": collect,
    "apm": apm,
    "web": web,
    "monitor": monitor,
}


def start_app() -> object:
    func = apps.get(options.app)
    if func is not None:
        return func()
    return None


def load_depend() -> CDLL:
    run_path: str = sys.executable

    run_path_list: List = run_path.split('/')
    run_path_list[-1] = 'libsqlite3.so'

    lib_path = '/'.join(run_path_list)
    return CDLL(lib_path)


def start_log() -> None:
    count = len(options.debug)

    if 'p' in options.debug:
        count -= 1

        import txaio
        txaio.use_twisted()
        txaio.start_logging(level=options.log_level)

        from twisted.python import log
        log.startLogging(sys.stdout)

        from tornado.log import enable_pretty_logging
        enable_pretty_logging()

    if count:
        sys.excepthook: Any = ExceptionHook()
        sys.settrace(trace)

    if 's' in options.debug:
        util.exception.print_frame = util.exception.print_frame_debug


def start_dns() -> None:
    if options.dns_port:
        monkey_patch()
        from twisted.names import client
        resolver = client.Resolver(
            servers=[("127.0.0.1", options.dns_port)]
        )
        reactor().installResolver(resolver)


def main() -> None:
    lib = load_depend()
    _ = lib

    # FIXME
    # add runtime config
    import options as current_options
    current_options.load_options()

    from util import runtime
    runtime.load_options()

    if not options.major_version:
        options.major_version = 1

    if not options.minor_version:
        options.minor_version = 1

    if not options.release_version:
        options.release_version = 12

    start_dns()
    start_log()

    from tornado.platform.twisted import TwistedIOLoop
    TwistedIOLoop().install()

    app: object = start_app()
    _ = app

    import tornado.ioloop
    tornado.ioloop.IOLoop.instance().start()


if __name__ == "__main__":
    main()

    """
    site-packages/crossbar/router/service.py
    (u'wamp.session.get.ex', self.session_get_ex),

    @wamp.register(u'wamp.session.get.ex')
    def session_get_ex(self, details=None):
        sessions = list()
        for session_id, session in self._router._session_id_to_session.items():
            sd = session._session_details
            if sd is None:
                continue

            tp = sd.get("transport")
            if tp is None:
                continue

            headers = tp.get("http_headser_received")
            if headers is None:
                continue

            host_id = headers.get("host-id")
            if host_id is None:
                continue

            info = dict()
            info["peer"] = tp.get("peer", "")
            info["host_id"] = host_id
            info["real_ip"] = headers.get("x-real-ip", "")
            info["time_created"] = headers.get("time-created", "")
            info["walker_version"] = headers.get("walker-version", "")
            info["host_address"] = headers.get("host-address", "")
            info["host_uptime"] = headers.get("host-uptime", "")
            info["host_kernel"] = headers.get("host-kernel", "")
            info["host_name"] = headers.get("host-name", "")

            sessions.append(info)
    """
