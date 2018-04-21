# coding=utf-8

import json
import time

import requests
from tornado.options import options

from util import rfc3339_format


class Point:
    def __init__(self, item) -> None:
        self.item = item
        self.metric = item["metric"]
        self.value = item["value"]
        self.ts = item["ts"]
        self.key = item.get('idc', "unknown")
        #self.key = item.get('isp', "unknown") #1.9版本idc与isp反了
        self.country = item.get('country', 'unknown')
        self.province = item.get('province', 'unknown')
        self.area = item.get('area', 'area')

    def write_es(self, cur_value, avg, std, ts, buffer):
        try:
            meta = dict()
            datas = []
            meta["_index"] = "alert"
            meta["_type"] = "monitor"
            _meta = dict()
            _meta["index"] = meta
            __meta = json.dumps(_meta)
            __item = dict()
            __item["@timestamp"] = rfc3339_format(ts)
            __item["time_created"] = rfc3339_format(time.time())

            __item["metric"] = self.metric
            __item["country"] = self.country
            __item["province"] = self.province
            __item["area"] = self.area
            __item["idc"] = self.key
            __item["value"] = cur_value
            __item["avg"] = avg
            __item["3std"] = 3 * std
            __item["fall"] = int(cur_value - avg)

            __item["msg"] = '%s,%s'%(buffer[0], buffer[1])
            _d = json.dumps(__item)
            datas.append(__meta)
            datas.append(_d)
            _r = requests.post(
                "http://{address}/_bulk".format(
                    address=options.elasticsearch_offline
                ),
                data='\n'.join(datas) + '\n'
            )

            if _r.status_code != 200:
                print(_r.text)

        except Exception as e:
            print("write_es " + str(e))


def factory(item) -> Point:
    return Point(item)
