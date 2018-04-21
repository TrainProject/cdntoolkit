# coding=utf-8

from typing import Dict


class CollectApp:
    def __init__(self) -> None:
        from .collector import Collector
        self.meta: Dict[str, Collector] = dict()

        from util.message import WsClientMessage
        self.message = WsClientMessage()

        from tornado.options import options
        self.message.run(options.config.unix_sock)
        Collector.loop_send(self.message)

        from .netstat import NetstatCollector
        from .ifstat import IfstatCollector
        from .iostat import IostatCollector
        from .procstats import ProcstatsCollector
        from .nginx import NginxCollector
        from .ats import AtsCollector
        from .accesslog import NgxLogCollector

        collect_map: Dict[str, type] = {
            'net': NetstatCollector,
            'if': IfstatCollector,
            'io': IostatCollector,
            'proc': ProcstatsCollector,
            'ngx': NginxCollector,
            'log': NgxLogCollector,
            'ats': AtsCollector,
        }

        for name, meta in collect_map.items():
            if name in options.config.collectors:
                collector: Collector = meta()
                self.meta[collector.name()] = collector
                collector.run()
