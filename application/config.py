# coding=utf-8

import json
from typing import Dict, Any

import requests
from orderedattrdict import AttrDict
from tornado.options import options

from util.json import AttrJson


class ConfigApp:
    def __init__(self) -> None:
        if options.param == "init":
            pass

        elif options.param == "post":
            data = AttrDict()
            # data.dst = "addr = '119.167.147.190'"
            # data.dst = "province_id = 7"  # "addr = '119.167.147.190'"

            data.dst = list()
            dst = AttrDict()
            dst.hostname = options.config.hostname
            dst.context = options.config.context
            data.dst.append(dst)

            data.retry = 3
            data.timeout = 300
            data.notify = "localhost"

            application = AttrDict()
            application.name = "config"
            application.notify = "http://127.0.0.1:8080"
            data.application = application

            # print("post test", AttrJson.dumps(data))

            if options.sync_domain:
                url = "http://{sync_domain}/sync/transaction".format(
                     sync_domain=options.sync_domain
                )
            else:
                url = "http://{sync_address}:{sync_port}/sync/transaction".format(
                    sync_address=options.sync_address,
                    sync_port=options.sync_port
                )

            r: requests.Response = requests.post(url, data=AttrJson.dumps(data))

            print("data", AttrJson.dumps(data), r)

            if r is not None and r.status_code == 200:
                d = AttrJson.loads(r.text)
                print(d)

        elif len(options.param) == 24:
            self.uuid2host: Dict[str, str] = dict()
            # self.get_uuid_body()
            if options.sync_domain:
                url = "http://{sync_domain}/sync/transaction/{key}".format(
                    sync_domain=options.sync_domain,
                    key=options.param
                )
            else:
                url = "http://{sync_address}:{sync_port}/sync/transaction/{key}".format(
                    sync_address=options.sync_address, sync_port=options.sync_port,
                    key=options.param
                )

            print(url)
            r = requests.get(url)

            if r is not None and r.status_code == 200:
                print(r.status_code)
                print(r.text)
                print(json.loads(r.text))
                # print(json.dumps(tmp, indent=4, sort_keys=True))
                # self.sync_es(AttrJson.loads(r.text))
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

