# coding=utf-8

import math
import os
import queue
import random
import subprocess
import threading
import time
import traceback
import unittest
import util.pygtrie as pygtrie
from collections import defaultdict

import numpy as np
import pandas as pd
import regex


class DomainTree:
    def __init__(self, domains):
        self.tree = pygtrie.StringTrie(separator='.')
        for domain in domains:
            self.tree[domain[::-1]] = domain

    def match(self, domain):
        return self.tree.longest_prefix(domain[::-1])[1]


supported_domains = DomainTree(['www.example.com'])


def rewrite_domain(s):
    import socket
    from urllib import parse

    hostname = s

    try:
        hostname = parse.urlparse('http://' + hostname).hostname
        socket.inet_aton(hostname)
        return 'example.com'
    except:
        return supported_domains.match(hostname) or "unknown"


class NgxVar:
    """
     log_format cdn_log   '"$server_addr:$server_port" "$remote_addr" "$time_local" "$request" "$status" "$body_bytes_sent" "$bytes_sent
" "$sent_http_content_length" '
                         '"-" "$http_host" "$http_user_agent" "$http_referer" "$http_range" "-" "$request_time" "5" "$upstream_http_le_
status" "-" "-" "-" '
                         '"$upstream_connect_time" "$upstream_header_time" "$upstream_response_time" "$upstream_addr" "$http_x_forwarde
d_for" "$upstream_http_via" "$bill_status" "$connection"';
    """
    PATTERN = regex.compile(r'(?(DEFINE)(?P<item>"(?P<value>[^"]*)" *))(?&item)*')

    server_addr = None
    server_port = None
    remote_addr = None
    time_local = None
    request = None
    status = None
    body_bytes_sent = None
    bytes_sent = None
    sent_http_content_length = None
    padding1 = None
    http_host = None
    http_user_agent = None
    http_referer = None
    http_range = None
    padding2 = None
    request_time = None
    node_type = None
    upstream_http_le_status = None
    padding4 = None
    padding5 = None
    padding6 = None
    upstream_connect_time = None
    upstream_header_time = None
    upstream_response_time = None
    upstream_addr = None
    http_x_forwarded_for = None
    upstream_http_via = None
    bill_status = None
    connection = None

    def __init__(self, line):
        result = regex.match(self.PATTERN, line)
        values = result.captures('value')

        self.server_addr, self.server_port = values[0].split(':')
        self.server_port = self.parse_int(self.server_port)
        # self.remote_addr = self.parse_str(values[1])
        self.time_local = int(time.mktime(time.strptime(values[2], '%d/%b/%Y:%H:%M:%S %z')))
        # self.request = self.parse_str(values[3])
        self.status = self.parse_int(values[4])
        # self.body_bytes_sent = self.parse_int(values[5])
        self.bytes_sent = self.parse_int(values[6])
        self.sent_http_content_length = self.parse_int(values[7])
        # self.padding1 = values[8]
        self.http_host = self.parse_str(values[9])
        # self.http_user_agent = self.parse_str(values[10])
        # self.http_referer = self.parse_str(values[11])
        # self.http_range = self.parse_str(values[12])
        # self.padding2 = values[13]
        self.request_time = self.parse_float(values[14])
        # self.node_type = self.parse_int(values[15])
        self.upstream_response_time = None

        if len(values) > 22:
            value = values[22]
            for delim in [' : ', ', ']:
                try:
                    self.upstream_response_time = sum([self.parse_float(x) for x in value.split(delim)])
                    break
                except ValueError:
                    pass
            if self.upstream_response_time is None:
                self.upstream_response_time = self.parse_float(value)
        else:
            self.upstream_response_time = 0.0

    def non_trivial(self, value):
        return value and value != "-"

    def parse_int(self, value):
        return int(value) if self.non_trivial(value) else 0

    def parse_float(self, value):
        v = float(value) if self.non_trivial(value) else 1e-6
        if math.isclose(v, 0, abs_tol=1e-6):
            v = 1e-6
        return v

    def parse_str(self, value):
        return bytes(value, 'utf-8').decode('unicode_escape') if self.non_trivial(value) else ""


class NgxSample:
    def __init__(self, stream, interval=10, ignore_fallback=True):
        self.stream = stream
        self.interval = interval
        self.last_time = 0
        self.stack = []
        self.ignore_fallback = ignore_fallback

    def sample(self):
        d = {
            'timestamp': [],
            'domain': [],
            'code': [],
            'speed': [],
            'req_time': [],
            'ups_time': [],
            'body_size': [],
        }

        for item in self.stack:
            d['timestamp'].append(item.time_local // 10 * 10)
            d['domain'].append(rewrite_domain(item.http_host))
            d['code'].append(int(item.status / 100))
            d['speed'].append(item.bytes_sent / item.request_time)
            d['req_time'].append(item.request_time)
            d['ups_time'].append(item.upstream_response_time)
            d['body_size'].append(item.sent_http_content_length)

        self.last_time = 0
        self.stack = []
        df = pd.DataFrame(d)
        group = df.groupby(['domain', 'code'])
        return pd.DataFrame({
            'ts': group['timestamp'].last(),
            'ngx.log.qps': group.size() / self.interval,
            'ngx.log.speed.avg': group['speed'].mean(),
            'ngx.log.speed.mid': group['speed'].median(),
            'ngx.log.speed.min': group['speed'].min(),
            'ngx.log.speed.max': group['speed'].max(),
            'ngx.log.req_time.avg': group['req_time'].mean(),
            'ngx.log.req_time.mid': group['req_time'].median(),
            'ngx.log.req_time.min': group['req_time'].min(),
            'ngx.log.req_time.max': group['req_time'].max(),
            'ngx.log.ups_time.avg': group['ups_time'].mean(),
            'ngx.log.ups_time.mid': group['ups_time'].median(),
            'ngx.log.ups_time.min': group['ups_time'].min(),
            'ngx.log.ups_time.max': group['ups_time'].max(),
            'ngx.log.body_size.avg': group['body_size'].mean(),
            'ngx.log.body_size.mid': group['body_size'].median(),
            'ngx.log.body_size.min': group['body_size'].min(),
            'ngx.log.body_size.max': group['body_size'].max(),
        }).reset_index()

    def ngx_var(self, x):
        return x

    def __iter__(self):
        for line in self.stream:
            try:
                ngx_var = self.ngx_var(NgxVar(line))
                if self.ignore_fallback and ngx_var.server_port == 16688:
                    continue
            except Exception:
                print(traceback.format_exc(), "line:", line)
                continue

            timestamp = ngx_var.time_local
            if self.last_time == 0:
                self.last_time = timestamp
            if timestamp - self.last_time < self.interval:
                self.stack.append(ngx_var)
            else:
                yield self.sample()

        yield self.sample()


class Tailer:
    def __init__(self, filename, buffer=0, lines=10, from_start=False):
        cmd = ['/usr/bin/tail', '-F', '-n']
        if from_start:
            cmd.append('+%d' % lines)
        else:
            cmd.append(str(lines))

        cmd.append(filename)

        self.fp = subprocess.Popen(cmd, stdout=subprocess.PIPE)
        self.queue = queue.Queue(buffer)
        self.thread = threading.Thread(target=self._target)
        self.thread.start()

    def _target(self):
        while True:
            try:
                line = self.fp.stdout.readline()
                if not line:
                    print('tailer eof')
                    return
                self.queue.put(line.decode('utf-8'))
            except ValueError:
                if self.fp.stdout.closed:
                    return
                raise

    def __iter__(self):
        while not self.fp.stdout.closed:
            try:
                yield self.queue.get(timeout=1)
            except queue.Empty:
                self.on_idle()

    @property
    def closed(self):
        return self.fp.stdout.closed

    def close(self):
        if self.fp.stdout.closed:
            return

        self.fp.kill()
        self.fp.stdout.close()
        self.thread.join()

    def on_idle(self):
        pass


class NgxLog:
    def __init__(self, stream, buffer_size=100000, collect_diff=10):
        self.stream = stream
        self.collect_diff = collect_diff
        self.done = False
        self.queue = queue.Queue(buffer_size)
        threading.Thread(target=self._target).start()

    def collect(self, ts):
        return self._get(ts)

    def _get(self, ts):
        metrics = []
        while not self.done:
            try:
                metrics.append(self.queue.get(timeout=1))
            except queue.Empty:
                break

        return metrics

    def _put(self, metric):
        try:
            self.queue.put(metric, timeout=0.1)
        except queue.Full:
            pass

    def _target(self):
        try:
            for df in self.stream:
                for metric in NgxLog.format_as_metrics(df):
                    self._put(metric)
        finally:
            self.done = True

    @classmethod
    def format_as_metrics(cls, df):
        names = [x for x in df]
        tuples = df.itertuples(index=False)
        metrics = []
        for values in tuples:
            d = {}
            metric_index = []
            values = list(values)
            for i in range(len(names)):
                value_type = type(values[i])
                if value_type is np.int64:
                    values[i] = int(values[i])
                elif value_type is np.float64:
                    values[i] = float(values[i])

                name, value = names[i], values[i]
                if name.startswith('ngx.log.'):
                    metric_index.append(i)
                else:
                    d[name] = value

            for i in metric_index:
                metric = d.copy()
                name = names[i]
                metric['metric'] = name
                value = values[i]
                if math.isclose(value, 0, abs_tol=1e-6):
                    value = 0

                metric['value'] = value
                metrics.append(metric)

        return metrics


class TestRewriteDomain(unittest.TestCase):
    def test_domain(self):
        self.assertEqual(supported_domains.match("y.com"), None)
        self.assertEqual(supported_domains.match("y.com.cn"), "y.com.cn")
        self.assertEqual(supported_domains.match("x.y.com.cn"), "y.com.cn")
        self.assertEqual(supported_domains.match("x.y.z.com.cn"), "z.com.cn")
        self.assertEqual(supported_domains.match("x.z.com"), None)
        self.assertEqual(supported_domains.match("xz.com.cn"), None)

    def test_hostname(self):
        self.assertEqual(rewrite_domain('127.0.0.1'), 'example.com')
        self.assertEqual(rewrite_domain('127.0.0.1:80'), 'example.com')
        self.assertEqual(rewrite_domain('x.y.com.cn'), 'y.com.cn')
        self.assertEqual(rewrite_domain('x.y.com.cn:80'), 'y.com.cn')
        self.assertEqual(rewrite_domain('x.com'), 'unknown')
        self.assertEqual(rewrite_domain('x.com:80'), 'unknown')


class TestNgxLog(unittest.TestCase):
    def setUp(self):
        def append(fname='access.log', total=6000, qps=100, rounds=3):
            pattern = '"{server_addr}:{server_port}" "{remote_addr}" "{time_local}" "{request}" "{status}" "{body_bytes_sent}" "{bytes_sent}" "{sent_http_content_length}" "-" "{http_host}" "{http_user_agent}" "{http_referer}" "{http_range}" "-" "{request_time}" "5" "{upstream_http_le_status}" "-" "-" "-" "{upstream_connect_time}" "{upstream_header_time}" "{upstream_response_time}" "{upstream_addr}" "{http_x_forwarded_for}" "{upstream_http_via}" "{bill_status}" "{connection}"'

            fp = open(fname, 'w')
            for i in range(rounds):
                for j in range(total):
                    start = time.time()
                    x = defaultdict(lambda: '-')
                    x['time_local'] = time.strftime('%d/%b/%Y:%H:%M:%S %z')
                    x['status'] = random.choice([101, 200, 302, 404, 500])
                    x['sent_http_content_length'] = random.randint(10000, 20000)
                    x['bytes_sent'] = x['sent_http_content_length'] + random.randint(50, 100)
                    x['http_host'] = random.choice(['localhost', 'example.com'])
                    x['request_time'] = x['bytes_sent'] / qps
                    fp.write(pattern.format_map(x) + '\n')
                    elapsed = time.time() - start
                    interval = 1 / qps
                    if interval > elapsed:
                        time.sleep((interval - elapsed) * 0.85)

                old_fname = '%s-%s' % (fname, time.time())
                os.rename(fname, old_fname)
                old = fp
                fp = open(fname, 'w')
                old.close()
                os.unlink(old_fname)

            fp.close()
            print('finished appending')

        class MyTailer(Tailer):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.idle_count = 0

            def on_idle(self):
                self.idle_count += 1
                if self.idle_count == 3:
                    self.close()

        self.fname = 'access.log'
        self.total = 6000
        self.qps = 100
        self.rounds = 3
        self.ngx_log = NgxLog(NgxSample(MyTailer(self.fname)))
        self.th = threading.Thread(target=append, kwargs={
            'fname': self.fname,
            'total': self.total,
            'qps': self.qps,
            'rounds': self.rounds,
        })
        self.th.start()

    def tearDown(self):
        self.th.join()

    def test_collect(self):
        while not self.ngx_log.done:
            self.ngx_log.collect(int(time.time()))


if __name__ == '__main__':
    import sys

    unittest.main()
    sys.exit()

from .collector import Collector
from orderedattrdict import AttrDict
from util.exception import print_frame


class NgxLogCollector(Collector):
    def __init__(self):
        self.ngx_log = NgxLog(NgxSample(Tailer('/usr/local/example/access.log')))
        super().__init__()

    def name(self):
        return "NginxLogCollector"

    def collect(self, ts):
        try:
            for metric in self.ngx_log.collect(ts):
                self.send_message(AttrDict(metric))
        except Exception as e:
            print_frame(e)
