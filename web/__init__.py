# coding: utf-8
import json
import math
import os
import time
from datetime import timedelta
from typing import List, Dict, Tuple

import requests
import tornado.httpserver
import tornado.ioloop
import tornado.web
from tornado.options import options

import util
import web.log
import web.sqlite_api
import web.sqlite_tool
import web.utils
from util import reactor
from util.exception import print_frame


class MainHandler(tornado.web.RequestHandler):
    def get(self):
        self.render("view.html")


class QueryMetricName(tornado.web.RequestHandler):
    def get(self):
        self.handle()

    def post(self):
        self.handle()

    def filter_metric_name(self, metric_list, metric_name):
        try:
            result = []
            for temp in metric_list:
                if temp.startswith(metric_name):
                    result.append(temp)

        except Exception as e:
            options.config.logging.error("filter_metricName error=[%s]" % e)

        return result

    def handle(self):
        try:
            param_metric_name = self.get_argument("metric_name")
            options.config.logging.info("QueryMetricName accept param_metric_name=[%s]"%(param_metric_name))
            result = web.utils.get_all_metric()
            if param_metric_name != '':
                result = self.filter_metric_name(result, str(param_metric_name))
            result = {"code":result,"metric_name": param_metric_name}

        except Exception as e:
            options.config.logging.error("QueryMetricName error=[%s]" % e)
            result = {"code": [], "metric_name": param_metric_name}
        result = "jsonpCallback(" + json.dumps(result) + ")"
        return self.write(result)


class QueryTagName(tornado.web.RequestHandler):
    def get(self):
        self.handle()

    def post(self):
        self.handle()

    def filter_tags_name(self, tags_list, tag_name):
        try:
            result = []
            if tag_name.split(',')[-1] != '':
                item = web.utils.find_symbol(tag_name.split(',')[-1])
                if item != '':
                    tags_b = tag_name.split(',')[-1].split('%s' % item)[-1]
                else:
                    tags_b = tag_name.split(',')[-1]
            else:
                tags_b = ''
            for temp in tags_list:
                if temp.startswith(tags_b):
                    result.append(temp)

        except Exception as e:
            options.config.logging.error("filter_tags_name error=[%s]" % e)

        return result

    def choice_func(self, influxdb_server, metric_name, range_tags):
        try:
            result: List = []
            tags_b = range_tags.split(',')[-1]
            if len(tags_b.split("=")) > 1:
                # if len(tags_b.split("=~")) > 1 or len(tags_b.split("=")) > 1:
                result = web.utils.get_tag_value(influxdb_server, metric_name, range_tags)
            else:
                result = web.utils.get_all_tags(influxdb_server, metric_name)

        except Exception as e:
            options.config.logging.error("choice_func error=[%s]" % e)

        return result

    def handle(self):
        try:
            result: Dict = list()
            param_metric_name = self.get_argument("metric_name")
            param_tags_name = self.get_argument("tags_name")

            if param_metric_name in ('', None) or param_tags_name is None:
                result = ['error']
            else:
                influxdb_server = web.utils.get_influxdb_server(param_metric_name)
                result = self.choice_func(influxdb_server, param_metric_name, param_tags_name)
                options.config.logging.info(
                    "QueryTagsName,param_metric_name=[%s],param_tags_name=[%s],influxdb_server=[%s]" % (
                        param_metric_name, param_tags_name, influxdb_server
                    )
                )
                if len(result) > 0:
                    result = self.filter_tags_name(result, str(param_tags_name))
                else:
                    result = ['error']
            result = {"code": result, "metric_name": param_metric_name, "tags_name": param_tags_name}

        except Exception as e:
            options.config.logging.error("QueryTagsName error=[%s]" % e)
            result = {"code": [], "metric_name": param_metric_name, "tags_name": param_tags_name}

        result = "jsonpCallback(" + json.dumps(result) + ")"
        return self.write(result)


class QueryGrafana(tornado.web.RequestHandler):
    def get(self):
        self.handle()

    def post(self):
        self.handle()

    def handle(self):
        try:
            self.param_metric_name = self.get_argument("metric_name")
            self.param_tags = self.get_argument("tags_name")
            self.param_aggregate = self.get_argument("aggregate")
            self.param_group = self.get_argument("group")

            if self.param_metric_name not in ('', None) and self.param_tags not in (None, ):
                self.influxdb_server = web.utils.get_influxdb_server(self.param_metric_name)

                url = web.sqlite_api.mk_dashboard_url(self)
                result = {"code": url, "metric_name": self.param_metric_name, "tags_name": self.param_tags}
                options.config.logging.info("QueryGrafana result=[%s]" % result)

        except Exception as e:
            options.config.logging.error(
                "QueryGrafana error=[%s],metric=[%s],tags=[%s]" % (
                    e, self.param_metric_name, self.param_tags
                )
            )
            result = {"error": "%s" % options.config.error}

        result = "jsonpCallback(" + json.dumps(result) + ")"
        return self.write(result)


class QueryQuickGrafana(tornado.web.RequestHandler):
    def get(self):
        self.handle()

    def post(self):
        self.handle()

    def handle(self):
        try:
            param_slug = self.get_argument("slug")
            if param_slug not in ('', None):
                url = options.config.DASHBOARD_URL + param_slug
                result = url
            else:
                result = 'error'

            result = {"code": result, "slug": param_slug}
            options.config.logging.info("QueryQuickGrafana result=[%s]" % result)
        except Exception as e:
            options.config.logging.error("QueryQuickGrafana error=[%s],slug=[%s]" % (e, param_slug))
            result = {"error": "%s" % result}
        result = "jsonpCallback(" + json.dumps(result) + ")"
        return self.write(result)


class QueryTable_bak(tornado.web.RequestHandler):
    def get(self):
        self.handle()

    def post(self):
        self.handle()

    def handle(self):
        try:
            param_start_num = self.get_argument("start_num")
            param_finish_num = self.get_argument("finish_num")
            options.config.logging.info(
                "QueryTable_bak param_start_num=[%s],param_finish_num=[%s]" % (
                    param_start_num, param_finish_num
                )
            )

            result = web.sqlite_api.get_records(param_start_num, param_finish_num)
            result = {"code": result}

        except Exception as e:
            options.config.logging.error("QueryTable_bak error=[%s]" % e)
            result = {"error": e}

        result = "jsonpCallback(" + json.dumps(result) + ")"
        return self.write(result)


class QueryTable(tornado.web.RequestHandler):
    def get(self):
        self.handle()

    def post(self):
        self.handle()

    def handle(self):
        try:
            param_page_num = int(self.get_argument("page_num"))
            num = web.sqlite_api.get_all_records()
            if param_page_num >= math.ceil(num/20.0):
                param_page_num = math.ceil(num/20.0)
            result = web.sqlite_api.get_page_records(param_page_num)
            result = {"code": result, "count": num, "page_num": param_page_num}

        except Exception as e:
            options.config.logging.error("QueryTable error=[%s],slug=[%s]" % (e, param_page_num))
            result = {"error": e}

        result = "jsonpCallback(" + json.dumps(result) + ")"
        return self.write(result)


class CocatGrafana(tornado.web.RequestHandler):
    def get(self):
        self.handle()

    def post(self):
        self.handle()

    def handle(self):
        try:
            param_cocat_graph = self.get_argument("code")
            cocat_list = param_cocat_graph.split(",")
            result = web.sqlite_api.cocat_records(cocat_list)
            result = {"code": result, "cocat_graph": param_cocat_graph}
            options.config.logging.info("CocatGrafana url=[%s],param_cocat_graph=[%s]" % (result, param_cocat_graph))

        except Exception as e:
            options.config.logging.error("CocatGrafana error=[%s],graph=[%s]" % (e, param_cocat_graph))
            result = {"error": "%s" % e}

        result = "jsonpCallback(" + json.dumps(result) + ")"
        return self.write(result)


class ViewGraphDetail(tornado.web.RequestHandler):
    def get(self):
        self.handle()

    def post(self):
        self.handle()

    def handle(self):
        try:
            param_slug = self.get_argument("slug")
            result = web.sqlite_api.view_detail(param_slug)
            result = {"code": result, "slug": param_slug}
            options.config.logging.info("ViewGraphDetail result=[%s]" % result)
        except Exception as e:
            options.config.logging.error("ViewGraphDetail error=[%s],detail=[%s]" % (e, param_slug))
            result = {"error": "%s" % e}
        result = "jsonpCallback(" + json.dumps(result) + ")"
        return self.write(result)


class DeleteBySlug(tornado.web.RequestHandler):
    def get(self):
        self.handle()

    def post(self):
        self.handle()

    def handle(self):
        try:
            param_slug = self.get_argument("slug")
            result = web.sqlite_api.del_item(param_slug)
            result = {"code": result, "slug": param_slug}
            options.config.logging.info("DeleteBySlug result=[%s]" % result)
        except Exception as e:
            options.config.logging.error("DeleteBySlug error=[%s],detail=[%s]" % (e, param_slug))
            result = {"error": "%s" % e}

        result = "jsonpCallback(" + json.dumps(result) + ")"
        return self.write(result)


class WebApp(tornado.web.Application):
    def __init__(self) -> None:
        if not os.path.exists(options.config.log_dir):
            os.mkdir(options.config.log_dir)

        logging = web.log.Logger(
            logname=os.path.join(options.config.log_dir, options.config.log_name),
            loglevel=1,
            logger="grafana_tool_main"
        ).getlog()

        options.config.logging = logging

        handlers = [
            (r"/admin.do",                  MainHandler),
            (r"/QueryMetricName.do",        QueryMetricName),
            (r"/QueryTagName.do",           QueryTagName),
            (r"/QueryGrafana.do",           QueryGrafana),
            (r"/QueryQuickGrafana.do",      QueryQuickGrafana),
            (r"/QueryTable.do",             QueryTable),
            (r"/CocatGrafana.do",           CocatGrafana),
            (r"/ViewGraphDetail.do",        ViewGraphDetail),
            (r"/DeleteBySlug.do",           DeleteBySlug)
        ]

        settings = dict(
            template_path=os.path.join(os.path.dirname(__file__), "template"),
            static_path=os.path.join(os.path.dirname(__file__), "static"),
            Debug=True,
        )

        tornado.web.Application.__init__(self, handlers, **settings)


alive: List = list()


class AliveHandler(tornado.web.RequestHandler):
    def get(self):
        d = dict()
        d["alive"] = alive
        self.write(json.dumps(d))
        self.set_status(200)


class MonitorApp(tornado.web.Application):
    """
    """
    mapping = """
    {
        "connections": {
            "dynamic": "strict",
            "properties": {
                "@timestamp": {
                    "type": "date",
                    "format": "dateOptionalTime",
                    "index": "analyzed"
                },
                "peer": {
                    "type": "string",
                    "index": "analyzed"
                },
                "real_ip": {
                    "type": "string",
                    "index": "analyzed"
                },
                "host_id": {
                    "type": "string",
                    "index": "analyzed"
                },
                "time_created": {
                    "type": "long",
                    "index": "analyzed"
                },
                "walker_version": {
                    "type": "string",
                    "index": "analyzed"
                },
                "crossbar_port": {
                    "type": "long",
                    "index": "analyzed"
                },
                "host_address": {
                    "type": "string",
                    "index": "analyzed",
                    "analyzer": "whitespace"
                },
                "host_uptime": {
                    "type": "long",
                    "index": "analyzed"
                },
                "host_kernel": {
                    "type": "string",
                    "index": "analyzed"
                },
                "host_name": {
                    "type": "string",
                    "index": "analyzed"
                },
                "host_alive": {
                    "type": "string",
                    "index": "analyzed"
                },
                "connection_alive": {
                    "type": "string",
                    "index": "analyzed"
                },
                "in_cdb": {
                    "type": "boolean",
                    "index": "analyzed"
                },
                "message": {
                    "type": "string",
                    "index": "analyzed",
                    "analyzer": "whitespace"
                }
            }
        }
    }
    """

    def __init__(self) -> None:
        from util.message import WampMessage

        self.messages: List[Tuple[WampMessage, int]] = list()
        self.cdb: Dict = dict()
        self._load()

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
            self.messages.append((message, port))

        start = int(time.time())
        end = start + 10 - start % 10
        diff = round(end - start, 3)
        reactor().callLater(diff, self.monitor, int(end))

        import threading
        self.t = threading.Thread(target=self.load)
        self.t.start()

        handlers = [
            (r"/alive", AliveHandler),
        ]

        settings = dict(
            template_path=os.path.join(os.path.dirname(__file__), "template"),
            Debug=False,
        )

        tornado.web.Application.__init__(self, handlers, **settings)

    def load(self):
        while True:
            time.sleep(600)
            self._load()

    def _load(self):
        self.cdb = dict()

        start = int(time.time())
        r = requests.get(options.cdb_url, timeout=100)

        if r.status_code == 200:
            try:
                data = json.loads(r.text)
                for _id, group in data.items():
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

                    __data = list()
                    enable = False

                    for _g, item in group.items():
                        if _g == "unknown":
                            continue

                        enable = item["enable"]
                        if not enable:
                            continue

                        __item = dict()
                        __item["addrs"] = item["addrs"][0]
                        __item["area"] = item["area"]
                        __item["country"] = item["country"]
                        __item["isp"] = item["isp"]
                        __item["meta"] = item["meta"]
                        __item["province"] = item["province"]
                        __item["name"] = item["name"]
                        __item["type"] = item["type"]
                        __data.append(__item)

                    if enable:
                        self.cdb[_id] = __data

            except Exception as e:
                print_frame(e)

        end = int(time.time())

        print("load cost time", end - start)

    def monitor(self, end):
        from twisted.internet.defer import DeferredList
        # d.addCallback(result)

        def write_result(all_list):
            datas = list()
            meta = dict()
            meta["_index"] = "crossbar"
            meta["_type"] = "connections"
            _meta = dict()
            _meta["index"] = meta
            __meta = json.dumps(_meta)
            items = dict()

            try:

                for ret, results in all_list:
                    if ret:
                        for _result in results:
                            items[_result["host_id"]] = _result
                            """
                            data = json.dumps(_result)
                            datas.append(__meta)
                            datas.append(data)
                            """
                        # print(r.status_code)
            except Exception as e:
                print_frame(e)

            try:
                for _id, group in self.cdb.items():
                    if _id == "unknown":
                        continue

                    __item = items.get(_id)
                    if __item is not None:
                        __item["in_cdb"] = True

                        msg = list()
                        try:
                            for _item in group:
                                msg.append(
                                    "area:%s;country:%s;isp:%s;province:%s;meta:%s;name:%s;address:%s;type:%s" % (
                                        _item['area'], _item['country'], _item['isp'], _item['province'],
                                        _item['meta'], _item['name'], _item["addrs"], _item['type']
                                    )
                                )
                        except Exception as e:
                            print_frame(e)

                        __item["message"] = " ".join(msg)

                    else:
                        __item = dict()
                        __item["@timestamp"] = util.rfc3339_format(end)
                        __item["peer"] = str()
                        __item["real_ip"] = str()
                        __item["host_id"] = _id
                        __item["time_created"] = -1
                        __item["walker_version"] = str()
                        __item["crossbar_port"] = -1
                        __item["host_address"] = str()
                        __item["host_uptime"] = str()
                        __item["host_kernel"] = str()
                        __item["host_name"] = str()
                        __item["connection_alive"] = -1
                        __item["host_alive"] = -1
                        __item["in_cdb"] = True

                        msg = list()
                        try:
                            for _item in group:
                                msg.append(
                                    "area:%s;country:%s;isp:%s;province:%s;meta:%s;name:%s;address:%s;type:%s" % (
                                        _item['area'], _item['country'], _item['isp'], _item['province'],
                                        _item['meta'], _item['name'], _item["addrs"], _item['type']
                                    )
                                )
                        except Exception as e:
                            print_frame(e)

                        __item["message"] = " ".join(msg)
                        items[_id] = __item

                __alive = list()
                for _id, ___item in items.items():
                    _d = json.dumps(___item)
                    datas.append(__meta)
                    datas.append(_d)
                    if ___item["time_created"] > 300:
                        __alive.append(___item["host_id"])
                    #   print(___item["host_id"])

                if len(__alive) > 1000:
                    global alive
                    alive = __alive
                datas.append(str())

            except Exception as e:
                print_frame(e)

            _r = requests.post(
                "http://%s/_bulk" % options.elasticsearch_online,
                data='\n'.join(datas)
            )
            print(_r.status_code)

            __t = """{
                "query": {
                    "range": {
                        "@timestamp": {
                            "gte": "%s",
                            "lte": "%s"
                        }
                    }
                }
            }"""

            __d = __t % (
                util.rfc3339_format(end - 30 - 3 * 24 * 3600),
                util.rfc3339_format(end - 3 * 24 * 3600)
            )
            __d = json.loads(__d)
            __r = requests.post(
                "http://%s/crossbar/connections/_delete_by_query" % options.elasticsearch_online,
                data=json.dumps(__d)
            )
            print(__r.status_code)

        def result(data_list, _port):
            try:
                for data in data_list:
                    tc = data["time_created"]

                    if not tc:
                        tc = -1
                        _tc = str(timedelta(seconds=0))
                    else:
                        tc = end - int(tc) - 28800
                        _tc = str(timedelta(seconds=tc))

                    hu = data["host_uptime"]
                    if not hu:
                        hu = -1
                        _hu = str(timedelta(seconds=0))
                    else:
                        hu = int(float(hu))
                        _hu = str(timedelta(seconds=hu))

                    data["@timestamp"] = util.rfc3339_format(end)
                    data["crossbar_port"] = _port
                    data["time_created"] = tc
                    data["host_uptime"] = hu
                    data["connection_alive"] = _tc
                    data["host_alive"] = _hu
                    data["in_cdb"] = False
                    data["message"] = str()

            except Exception as e:
                from util.exception import print_frame
                print_frame(e)

            print("result port", _port)
            return data_list

        try:
            dl = list()
            for message, port in self.messages:
                d = message.rpc("wamp.session.get.ex")
                d.addCallback(result, port)
                dl.append(d)

            dfl = DeferredList(dl)
            dfl.addCallbacks(write_result)

        except Exception as e:
            print_frame(e)

        _start = int(time.time())
        _end = _start + 10 - _start % 10
        _diff = round(_end - _start, 3)
        reactor().callLater(_diff, self.monitor, int(_end))
