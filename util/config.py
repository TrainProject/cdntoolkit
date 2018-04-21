# coding=utf-8

import json
import sqlite3
from typing import Dict, List, Any, Iterable

import tornado.web
import treq
from orderedattrdict import AttrDict
from tornado.options import options
from treq.response import _Response
from twisted.internet.defer import Deferred, DeferredList
from twisted.python.failure import Failure

from util.message import WampMessage
from . import GeneralException, parse_hostname, reactor
from .exception import print_frame
from .objects import object_manager
from .observer import Observer, signal
from .protocol import ConfigGetRequest, ConfigGetResponse


class ConfigData:
    def __init__(self) -> None:
        self.all: List[str, ConfigInfo] = list()
        self.host: Dict[str, ConfigInfo] = dict()
        self.hostname: Dict[str, ConfigInfo] = dict()
        self.source: Dict[str, List] = dict()


class ConfigInfo:
    def __init__(self) -> None:
        self.host: str = "FFFFFFFF-FFFF-FFFF-FFFF-FFFFFFFFFFFF"
        self.hostname: str = "__UNKNOWN__"
        self.source: int = 0

        self.addrs: str = str()
        self.country: str = str()
        self.area: str = str()
        self.host_id: int = str()
        self.isp: str = str()
        self.idc: str = str()
        self.meta: str = str()
        self.name: str = str()
        self.node_id: int = str()
        self.province: str = str()
        self.type: str = str()
        self.manager: str = str()

        """
        value = (
            _id, item['addrs'][0],
            item['area'], item['area_id'],
            item['country'], item['country_id'],
            int(item['enable']), item['host_id'],
            item['isp'], item['isp_id'],
            item['meta'], item['name'], item['node_id'],
            item['province'], item['province_id'],
            int(item['test']), item['type'], hostname
        )
        """

    def __iter__(self) -> Iterable[object]:
        # FIXME
        return iter(
            (
                self.host, self.hostname, self.source, self.addrs,
                self.country, self.area, self.host_id, self.isp,
                self.idc, self.meta, self.name, self.node_id,
                self.province, self.type, self.manager
            )
        )


class ConfigSource(Observer):
    def __init__(self) -> None:
        super().__init__()

    def proto(self) -> object:
        raise NotImplementedError

    def parse(self, data: object) -> List:
        raise NotImplementedError

    def fetch(self) -> None:
        _proto = self.proto()
        if isinstance(_proto, str):
            self.http_fetch(_proto)
        elif isinstance(_proto, list):
            self.wamp_fetch(_proto)
        else:
            assert 0

    def complete_header(self, r: _Response) -> None:
        if r is not None and r.code == 200:
            content: Deferred = r.content()
            content.addCallback(self.complete_body)

    def complete_body(self, data: bytes):
        self.on_fetch(data)

    def handle_error(self, error: Failure):
        print(error.getErrorMessage())

    def merge(self, data: ConfigData) -> None:
        raise NotImplementedError

    def http_fetch(self, url: str) -> None:
        try:
            d: Deferred = treq.get(url, timeout=5)
            d.addCallback(self.complete_header)
            d.addErrback(self.handle_error)
        except Exception as e:
            print_frame(e)

    def wamp_fetch(self, messages: List) -> None:
        dl = list()
        for message in messages:
            d = message.rpc("wamp.session.get.ex")
            d.addCallback(self.complete_wamp)
            dl.append(d)

        dfl = DeferredList(dl)
        dfl.addCallbacks(self.complet_wamp_all)

    @signal
    def on_fetch(self, data: object) -> None:
        pass

    def complete_wamp(self, data: List) -> None:
        result: List = list()
        try:
            for item in data:
                ci = ConfigInfo()
                ci.host = item['host_id']
                ci.hostname = item['host_name']
                result.append(ci)

        except Exception as e:
            print_frame(e)

        return result

    def complet_wamp_all(self, data):
        self.on_fetch(data)


class CdbConfigSource(ConfigSource):
    def __init__(self) -> None:
        super().__init__()

    def proto(self) -> object:
        return options.cdb_url

    def merge(self, data: ConfigData) -> None:
        source = data.source[str(type(self))]
        for item in source:
            if item.host:
                data.host[item.host] = item
            else:
                print("error: cdb host is empty  ", item)

            if item.hostname:
                data.hostname[item.hostname] = item
            else:
                print("error: cdb hostname is empty  ", item)

            data.all.append(item)

    def parse(self, data: object) -> List:
        _data: Dict = json.loads(data)
        source: List[ConfigSource] = list()

        for _id, group in _data.items():
            if _id == "unknown":
                continue

            hostname = group.get('hostname')
            if hostname is not None:
                del group['hostname']
            else:
                continue

            wan = group.get('wan')
            if wan is not None:
                del group['wan']

            lan = group.get('lan')
            if lan is not None:
                del group['lan']

            for _g, item in group.items():
                if _g == "unknown":
                    continue
                """
                enable = item['enable']
                if not enable:
                    continue
                """
                ci: ConfigInfo = ConfigInfo()
                try:
                    hostname = hostname.strip().upper()
                    ci.hostname = hostname
                    ci.host = _id
                    ci.source |= 1
                    ci.addrs = item['addrs'][0]
                    ci.area = item['area']
                    ci.country = item['country']
                    ci.host_id = item['host_id']
                    ci.meta = item['meta']
                    ci.name = item['name']
                    ci.node_id = item['node_id']
                    ci.province = item['province']
                    ci.type = item['type']

                    isp, idc = parse_hostname(hostname)

                    if isp:
                        ci.isp = isp

                    if idc:
                        ci.idc = idc

                    source.append(ci)

                except Exception as e:
                    print_frame(e)
                    print(ci, hostname)
                else:
                    break

        return source


class CtkConfigSource(ConfigSource):
    def __init__(self) -> None:
        self.messages: List = list()

        for port in range(
            options.router_port_start,
            options.router_port_end,
            options.router_port_step
        ):
            message: WampMessage = WampMessage()
            message.start(
                options.router_url.format(port=port),
                options.router_domain
            )
            self.messages.append(message)

        super().__init__()

    def proto(self) -> object:
        return self.messages

    def merge(self, data: ConfigData) -> None:
        source = data.source[str(type(self))]
        # print(source)
        try:
            for items in source:
                if not items[0]:
                    continue

                for item in items[1]:
                    item.hostname = item.hostname.strip().upper()
                    if item.host:
                        ci = data.host.get(item.host)
                        if ci is not None:
                            ci.source |= 2
                            if item.hostname != ci.hostname:
                                print("warning:", ci.host,
                                      ci.hostname, item.hostname)

                        else:
                            data.host[item.host] = item
                            data.all.append(item)

                    else:
                        print("error: ctk host is empty  ", item)
                        if item.hostname:
                            ci = data.hostname.get(item.hostname)
                            if ci is not None:
                                ci.source |= 2

                            else:
                                data.hostname[item.hostname] = item
                                data.all.append(item)
        except Exception as e:
            print_frame(e)

    def parse(self, data: object) -> List:
        return data


class OssConfigSource(ConfigSource):
    def __init__(self) -> None:
        super().__init__()

    def proto(self) -> object:
        return "http://asset.example.com/v1/servers"

    def parse(self, data: object) -> None:
        _data: Dict = json.loads(data)
        source: List[ConfigSource] = list()

        for server in _data['servers']:
            ci: ConfigInfo = ConfigInfo()
            try:
                hostname = server['hostName'].strip().upper()
                manager = server['managerIP']
                ci.hostname = hostname
                ci.manager = manager
                source.append(ci)

            except Exception as e:
                print_frame(e)
                print(ci)

        return source

    def merge(self, data: ConfigData) -> None:
        source = data.source[str(type(self))]
        for item in source:
            if item.hostname:
                ci = data.hostname.get(item.hostname)
                if ci is not None:
                    ci.source |= 4
                    ci.manager = item.manager
                else:
                    data.hostname[item.hostname] = item
                    data.all.append(item)


class ConfigManager(Observer):
    # _id:0, addr:1, area:2, area_id:3, country:4, country_id:5,
    # enable:6, host_id:7, isp:8, isp_id:9, meta:10, name:11, node_id:12,
    # province:13, province_id:14, test:15, type:16

    def __init__(self) -> None:
        self.alive_data: set = None
        self.hostname2host: Dict[str, str] = dict()
        self.conn = sqlite3.connect(":memory:")
        self.cur = self.conn.cursor()
        self.cur.execute(
            "CREATE TABLE config ("
            "host GUID,"                # 0
            "hostname VARCHAR(32),"     # 1
            "source INTEGER,"           # 2
            "addr VARCHAR(16), "        # 3
            "country VARCHAR(16),"      # 4
            "area VARCHAR(16),"         # 5
            "host_id INTEGER,"          # 6
            "isp VARCHAR(16),"          # 7
            "idc VARCHAR(16),"          # 8
            "meta VARCHAR(16),"         # 9
            "name VARCHAR(16),"         # 10
            "node_id INTEGER,"          # 11
            "province VARCHAR(16),"     # 12
            "type VARCHAR(16),"         # 13
            "manager VARCHAR(16)"       # 14
            ")"
        )

        self.cur.execute(
            "CREATE UNIQUE INDEX host ON config (host)"
        )

        self.cur.execute(
            "CREATE INDEX hostname ON config (hostname)"
        )

        self.source_count: int = 0
        self.working: bool = False
        self.config_data: ConfigData = ConfigData()
        super().__init__()

    def complete_fetch(self, data: object) -> None:
        source: ConfigSource = self.sender
        self.config_data.source[str(type(source))] = source.parse(data)
        self.source_count -= 1
        if not self.source_count:
            try:
                self.merge()
                self.save()
            except Exception as e:
                print_frame(e)

    def run1(self) -> None:
        if self.working:
            return

        self.working = True
        self.source_count = 0

        for source in object_manager.foreach_type(
            str(ConfigSource)
        ):
            source.add_slot(
                ConfigSource.on_fetch,
                self.complete_fetch
            )
            source.fetch()
            self.source_count += 1

    def merge(self) -> None:
        for source in object_manager.foreach_type(
            str(ConfigSource)
        ):
            source.merge(self.config_data)

    def save(self) -> None:
        for item in self.config_data.all:
            try:
                self.cur.execute(
                    "insert into config values "
                    "(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    tuple(item)
                )

                # self.hostname2host[hostname] = _id
                self.cur.execute("select count(1) from config")

            except Exception as e:
                print_frame(e)

        print("load %s" % self.cur.fetchall(), len(self.config_data.all))
        self.working = False

    def query1(self, where: str) -> Any:
        self.cur.execute(
            "select * from config where {cond}".format(cond=where)
        )
        return self.cur.fetchall()

    @signal
    def on_config(self) -> None:
        pass

    def run(self) -> None:
        object_manager.add_type(
            str(ConfigSource), CdbConfigSource(), "cdb"
        )

        object_manager.add_type(
            str(ConfigSource), CtkConfigSource(), "ctk"
        )

        object_manager.add_type(
            str(ConfigSource), OssConfigSource(), "oss"
        )

        reactor().callLater(3, self.run1)

        """
        if options.cdb_data:
            self.load_data()

        if options.cdb_url:
            if options.monitor_address and options.moniotr_port:
                r = requests.get(
                    "http://{address}:{port}/alive".format(
                        address=options.monitor_address,
                        port=options.monitor_port
                    )
                )
                alive = json.loads(r.text)
                self.alive_data = set(alive["alive"])
            self.load()
        """

        """
        request: TransactionPostRequest = TransactionPostRequest()
        request.application = AttrDict()

        self.area_id = config.area_id
        self.country_id = config.country_id
        self.host_id = config.host_id
        self.isp_id = config.isp_id
        self.node_meta = config.node_meta
        self.node_id = config.node_id
        self.province_id = config.province_id
        self.node_type = config.node_type
        self.apm = "on"
        reactor().callLater(10, self.run)
        """

    def send(self) -> None:
        pass

    def keepalive(self) -> None:
        pass

    def config(self) -> None:
        pass

    def query_by_where(self, dst: str) -> List:
        where: str = dst
        hosts: List = list()

        try:
            sql = "select _id as uuid from config {where} limit 8000".format(
                where=("where " + where) if where else where
            )
            self.cur.execute(sql)
            # return self.cur.fetchall()

            column_names = [d[0] for d in self.cur.description]
            hosts = [AttrDict(zip(column_names, row)) for row in self.cur]
        except Exception as e:
            print_frame(e)
            raise GeneralException(400, str(e))

        return hosts

    def query_by_dst(self, dst: list) -> List:
        hosts: List = list()
        try:
            for item in dst:
                context = item.context
                for hostname in item.hostname:
                    host = AttrDict()
                    host.hostname = hostname
                    host.host = self.hostname2host[hostname.strip().upper()]
                    for name, value in context.items():
                        host[name] = value
                    hosts.append(host)
        except Exception as e:
            print_frame(e)
            raise GeneralException(400, str(e))

        return hosts

    def query(self, where: str) -> Dict:
        # import pdb; pdb.set_trace()
        sql = "select * from config where {cond}".format(cond=where)
        print(where, sql)
        self.cur.execute(sql)
        return self.cur.fetchall()

    def query_ids(self) -> Any:
        self.cur.execute("select _id from config group by _id")
        return self.cur.fetchall()

    def query_by_id(self, _id: str) -> Any:
        # self.cur.execute("select * from config where _id = '%s' group by _id" % _id)
        sql = "select * from config where _id = '{key}'".format(key=_id)
        self.cur.execute(sql)
        return self.cur.fetchall()

    def query_config_by_id(self, data: str) -> str:
        ret = ConfigGetResponse()

        try:
            config = self.query_by_id(ConfigGetRequest(data).host)

            if len(config) == 1:
                hostname: str = config[0][17]
                isp, idc = parse_hostname(hostname)
                if isp:
                    ret.isp = isp
                if idc:
                    ret.idc = idc
                ret.area = config[0][2]
                ret.country = config[0][5]
                ret.province = config[0][13]
                ret.role = config[0][16]

        except Exception as e:
            print_frame(e)

        return str(ret)


class ConfigWebHandler(tornado.web.RequestHandler):
    def get(self) -> None:
        where = self.get_argument('q')
        data = config_manager.query(where)
        # import pdb; pdb.set_trace()
        self.set_status(200)
        self.write(json.dumps(data))


config_manager: ConfigManager = ConfigManager()
