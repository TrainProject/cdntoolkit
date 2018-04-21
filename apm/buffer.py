# coding=utf-8

from typing import Dict

import numpy as np

from util import polyhash
from .mr import factory

class ApmLinkedList(object):
    def __init__(self) -> None:
        self.index = None
        self.head = None
        self.size = 0

    def append(self, point):
        if self.head is None:
            point.prev = point
            point.next = point
            self.head = point

        else:
            last = self.head.prev
            last.next = point
            point.prev = last
            point.next = self.head
            self.head.prev = point

        self.size += 1

    def remove(self, point):
        if self.size == 1:
            self.head = self.index = None

        else:
            if self.head is point:
                self.head = point.next
                self.index = None
            else:
                self.index = point.prev

            point.prev.next = point.next
            point.next.prev = point.prev

        self.size -= 1

    def __iter__(self):
        return self

    def __next__(self):
        if self.index is None:
            self.index = self.head
            if self.index is None:
                raise StopIteration

        else:
            # self.index = self.index.next
            self.index = self.index.prev
            if self.index is self.head:
                self.index = None
                raise StopIteration

        return self.index


class ApmBuffer:
    def __init__(self) -> None:
        self.buffer: Dict = dict()
        self.metrics: Dict = dict()
        self.metric_cache: Dict = dict()
        self.tags_cache: Dict = dict()

    def make_key_by_tags(self, tags, mod):
        shard = self.tags_cache.get(tags)
        if shard is None:
            shard = polyhash(tags, m=mod)
            """
            shard = int(
                hashlib.md5(
                    tags.encode()
                ).hexdigest()[:2],
                16)
            """
            self.tags_cache[tags] = shard
        return shard

    def make_key(self, metric, mod):
        shard = self.metric_cache.get(metric)
        if shard is None:
            shard = polyhash(metric, m=mod)
            """
            shard = int(
                hashlib.md5(
                    metric.encode()
                ).hexdigest()[:2],
                16)
            """
            self.metric_cache[metric] = shard
        return shard

    def add_list(self, item) -> bool:
        try:
            point = factory(item)
            metric = self.metrics.get(point.metric, None) #metric as key
            if metric is None:
                metric = dict()
                self.metrics[point.metric] = metric

            buffer = metric.get(point.key, None) # idc as key
            if buffer is None:
                #buffer = (list(), list())   # buffer[0]:value, buffer[1]:ts
                buffer = ([0, 0, 0, 0, 0], [0, 0, 0, 0, 0])   # buffer[0]:value, buffer[1]:ts
                metric[point.key] = buffer

            point_ts = int(point.ts/10) * 10
            point_value = point.value

            if point_ts in buffer[1]:
                ts_index = buffer[1].index(point_ts)  # ts_index is the same as value_index
                buffer[0][ts_index] += point_value
            else:
                if point_ts > buffer[1][-1]:  # cur_time is newer than the last timestamp
                    buffer[0].append(point_value)
                    buffer[1].append(point_ts)
                    result, offset = self.std_3(buffer, point)
                    #if result:  #remove alert point
                        #buffer[0].pop(offset)
                        #buffer[1].pop(offset)

            if len(buffer[0]) >= 9:
                buffer[0].pop(0)
                buffer[1].pop(0)
        except Exception as e:
            print("add_list():", e)
        return True

    def std_3(self, buffer, point):
        values = buffer[0]
        ts = buffer[1]
        offset = -3
        warn = False
        try:
            cur_value = values[offset]
            cur_ts = ts[offset]
            avg = np.mean(values[:offset])
            std = np.std(values[:offset]) + 0.1 #correct zero misinformation
            if abs(cur_value - avg) > 10*std:
                print("warning::", avg, std, values, ts, point.metric, point.key)
                point.write_es(cur_value, avg, std, cur_ts, buffer)
                warn = True
        except Exception as e:
            print("calc_std_3:", e)
        return warn, offset

    def add_link(self, item) -> bool:
        point = factory(item)

        metric = self.metrics.get(point.metric)
        if metric is None:
            metric = dict()
            self.metrics[point.metric] = metric

        buffer: ApmLinkedList = metric.get(point.key)
        if buffer is None:
            buffer = ApmLinkedList()
            metric[point.key] = buffer

        for build in point.build():
            if build is None:
                break
            for _point in buffer:  # type : ignore
                if build(_point):
                    break

        for alert in point.check():
            if alert is None:
                break
            for _point in buffer:  # type : ignore
                if alert(_point):
                    break

        buffer.append(point)

        while buffer.size > 30:
            buffer.remove(buffer.head)

        return True
