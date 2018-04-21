# coding=utf-8

import json
import time
from typing import Dict, Any

import requests
from orderedattrdict import AttrDict
from tornado.options import options

import util
from util.json import AttrJson


class CommandApp:
    def __init__(self) -> None:
        if options.param == "init":
            self.init_es()

        elif options.param == "post":
            data = AttrDict()
            # data.dst = "addr = '119.167.147.190'"
            # data.dst = "province_id = 7"  # "addr = '119.167.147.190'"
            data.dst = ""
            data.retry = 3
            data.timeout = 3

            application = AttrDict()
            # application.name = "command"
            application.name = "config"
            # application.command = "sh.grep(sh.ls('./', '-1'), 'count')"
            # application.command = "sh.ls('./', '-all')"
            application.command = "sh.hostname()"
            application.ts = int(time.time())
            application.path = "example.com"
            # application.command = "sh.cat('/proc/cpuinfo')"
            # application.command = "sh.cat('/proc/meminfo')"
            data.application = application

            # print("post test", AttrJson.dumps(data))

            r: Any = requests.post(
                "http://{address}:{port}/sync/transaction".format(
                    address=options.sync_address,
                    port=options.sync_port
                ),
                data=AttrJson.dumps(data)
            )

            if r is not None and r.status_code == 200:
                d = AttrJson.loads(r.text)
                print(d)

        elif len(options.param) == 24:
            self.uuid2host: Dict = dict()
            self.get_uuid_body()

            url = "http://{address}:{port}/sync/transaction/{key}".format(
                address=options.sync_address, port=options.sync_port, key=options.param
            )
            print(url)

            r = requests.get(url)

            if r is not None and r.status_code == 200:
                print(r.status_code)
                tmp = json.loads(r.text)
                # print(json.dumps(tmp, indent=4, sort_keys=True))
                self.sync_es(AttrJson.loads(r.text))
                # print(AttrJson.dumps(tmp))
            print(r)
            print(r.status_code)

    def get_uuid_body(self):
        with open(options.cdb_uuid_file) as f:
            test = f.read()

        data = json.loads(test)
        for _id, item in data.items():
            if _id == "unknown":
                continue
            hostname = item.get('hostname')
            if hostname is not None:
                self.uuid2host[_id] = hostname.upper()

    def init_es(self):
        mapping: Any = """
        {
            "response": {
                "dynamic": "strict",
                "properties": {
                    "@timestamp": {
                        "type": "date",
                        "format": "dateOptionalTime",
                        "index": "analyzed"
                    },
                    "sync_id": {
                        "type": "string",
                        "index": "analyzed"
                    },
                    "host_id": {
                        "type": "string",
                        "index": "analyzed"
                    },
                    "host_name": {
                        "type": "string",
                        "index": "analyzed"
                    },
                    "code": {
                        "type": "long",
                        "index": "analyzed"
                    },
                    "message": {
                        "type": "string",
                        "index": "analyzed"
                    }
                }
            }
        }
        """

        # @timestamp, sync_id, host_id, host_name, code, message

        _r: requests.Response = requests.delete("http://127.0.0.1:9000/sync")
        r: requests.Response = requests.post("http://127.0.0.1:9000/sync/response", data='{}')
        if r.status_code == 201:
            r = requests.put("http://127.0.0.1:9000/sync/response/_mapping", data=mapping)
            print(r.text)

    def sync_es(self, data):
        datas = list()
        meta = dict()
        meta["_index"] = "sync"
        meta["_type"] = "response"
        _meta = dict()
        _meta["index"] = meta
        __meta = json.dumps(_meta)

        items = list()
        sync_id = data.transaction_id
        for transfer in data.transfers:
            for result in transfer.results:
                item = AttrDict()
                item.sync_id = str(sync_id)
                item.host_id = str(result.host)
                item.code = result.code
                item.message = result.message.strip()
                item["@timestamp"] = util.rfc3339_format(result.trace[-1].end_time)
                item.host_name = self.uuid2host.get(result.host, result.host)
                items.append(item)

        for ___item in items:
            _d = json.dumps(___item)
            datas.append(__meta)
            datas.append(_d)

        datas.append(str())
        print(len(items))

        _r: requests.Response = requests.post(
            "http://127.0.0.1:9000/_bulk",
            data='\n'.join(datas)
        )

        if _r.status_code == 200:
            print(_r.status_code)
