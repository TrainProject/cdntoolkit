# coding=utf-8

import json
import socket
import threading
import queue
import time
import re
from typing import List, Dict, Tuple
from tornado.options import options

from util import reactor, perf
from util.exception import print_frame
from util.observer import Observer


class ApmProxy(Observer):
    def __init__(self, buffer, connections=None) -> None:
        #perf()
        self.buffer = buffer
        self.connections = connections
        self.influx_connections: Dict[int, Tuple] = dict()
        self.count = 0
        # for count packages
        self.package_num = 0
        self.s_time = time.time()
       
        # for count_ts error
        self.hostname = list()
        # end
        # for count metric_num every 10s
        self.count_metric_by_idc = dict()
        self.one_metric_count = 0
        self.all_metric_count = 0
        self.start_time = time.time()
        self.start_time_count = time.time()
        self.flag = False
        # end
        # for thread_master
        self.connections2slave = dict()
        self.connections2influx = dict()
        for i in range(16):
            self.connections2slave[i] = queue.Queue(100000)
            self.connections2influx[i] = queue.Queue(100000)

        def send_slave(slave_client):
            
            while True:
                try:
                    _slave_client = slave_client.get(block=True)
                    _slave_client[0].send_message(_slave_client[1])
                except Exception as s_e:
                    # print("send_thread slave:", s_e, slave_client.qsize(), slave_shard)
                    pass
        def send_influx(influx_client):
            while True: 
                try:  
                    _influx_client = influx_client.get(block=True)
                    temp = _influx_client[1].encode()
                    result = _influx_client[0].sendall(temp)
                except Exception as e:
                    print("send_thread influxdb:", e, len(temp))
                    pass

        self.thread_items = queue.Queue()
        def calc_std_3(thread_items):
            while True:
                try:
                    if thread_items.qsize() <= 0:
                        time.sleep(1)
                        continue

                    _buffer = self.buffer
                    _buffer.add_list(thread_items.get(block=False))
                except Exception as e:
                    print("thread error calc_std_3():", e)
        for i in range(16):
            if options.role == "master":
                t_handle_slave = threading.Thread(target=send_slave, args=(self.connections2slave[i], ))
                t_handle_influx = threading.Thread(target=send_influx, args=(self.connections2influx[i], ))
                t_handle_slave.setDaemon(False)
                t_handle_influx.setDaemon(False)
                t_handle_slave.start()
                t_handle_influx.start()
            else:
                t_handle = threading.Thread(target=calc_std_3, args=(self.thread_items[i], ))
                t_handle.setDaemon(False)
                t_handle.start()
        # end

        if options.role == "master":
            try:
                i = 0
                for influx_ip in options.influx_addrs.split(":"):
                    for influx_port in options.influx_ports.split(":"):
                        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        s.settimeout(10)
                        s.connect((influx_ip, int(influx_port)))
                        self.influx_connections[i] = (s, list())
                        i += 1
            except Exception as e:
                print_frame(e)

        super().__init__()

    def handle_master(self, content: str):
        try:
            if 'd' in options.debug:
                print(content)
            self.package_num += 1
            e_time = time.time()
            _buffer = self.buffer
            lines: List[object] = content.split('\n')
            if e_time - self.s_time >= 10:
                ts = int(self.s_time/10) * 10
                self.s_time = e_time
                _line = '%s,apm.master.num,%s,%s;put apm.master.num %s %s master=%s'%(options.release_version,ts,self.package_num, ts,self.package_num,str(options.router_port_end)[-2:])
                self.package_num = 0
                lines.append(_line)
            cur_time = time.time()
            for line in lines:
                if line:
                    _data = line.split(';', 1)
                    if len(_data) < 2:
                        continue
                    prefix = _data[0]
                    put_data = _data[1]
                    vmtv = prefix.split(',')
                    metric = vmtv[1]
                    #influx_shard = _buffer.make_key(metric, 8)
                    influx_shard = options.config.metric_shard.get(metric, None)
                    if influx_shard is None:
                        influx_shard = 7
                    if metric in ('ngx.log.qps', 'ngx.log.speed.avg'):
                        province = re.findall("province=([^ ]*)", put_data)[0]
                        isp = re.findall("isp=([^ ]*)", put_data)[0]
                        if isp not in ("CNC", "CTC", "CMCC"):
                            isp = 'other'
                        shard = _buffer.make_key_by_tags(metric + "%s_%s"%(province, isp), 16)
                        server, buffer, buff = self.connections[shard]
                        buffer.append(line)
                    
                    influd_server, buff_put = self.influx_connections[influx_shard]
                    buff_put.append(put_data)
                    self.metric_count(metric, False) 

        except Exception as e:
            print_frame(e)
        end_time = time.time()
        check_time = end_time - self.start_time
        try:
            self.count += 1
            # if self.count == 256 or check_time >= 10:
            if  check_time >= 7:
                self.start_time = end_time
                self.count = 0
                _shard, __shard = 0, 0
                for _shard, _client in self.connections.items():
                    self.connections2slave[_shard].put([_client[0], "\n".join(_client[1])])
                    _client[1].clear()
                for __shard, __client in self.influx_connections.items():
                    if len(__client[1]) < 1:
                        continue
                    self.connections2influx[__shard].put([__client[0], "\n".join(__client[1]) + '\n']) 
                    __client[1].clear()
        except Exception as e:
            print("influx_connections%s:%s" % (__shard, e))

    def handle_slave(self, content: str):
        lines: List[object] = content.split('\n')
        try:
            for line in lines:
                if line:
                    item = json.loads(line)
                    self.thread_items.put(item)

        except Exception as e:
            print_frame(e)

    def run(self):
        return
        _buffer = self.buffer
        _buffer.handle()
        reactor().callLater(30, self.run)

    def metric_count_slave(self, metric_name):

        end_time = time.time()
        if metric_name == 'testing':
            self.one_metric_count += 1

        self.all_metric_count += 1

        if end_time - self.start_time_count >= 10:
            self.start_time_count = end_time

            file_name = '/usr/local/cdntoolkit/ctk/apm/' + '%s' % options.shard + '.txt'
            file_obj = open(file_name, 'w')
            try:
                file_obj.writelines(str(self.one_metric_count) + '_' + str(self.all_metric_count) + '_' + str(end_time) + '\n')
            finally:
                file_obj.close()
            self.one_metric_count = 0
            self.all_metric_count = 0

    def metric_count(self, metric, flag):
        # for verify data_num
        end_time = time.time()
        one_metric_count = self.count_metric_by_idc.get(metric, None)
        all_metric_count = self.count_metric_by_idc.get("all", None)
        if not flag and one_metric_count is None:
            self.count_metric_by_idc[metric] = 1
        else:
            self.count_metric_by_idc[metric] += 1
        if not flag and all_metric_count is None:
            self.count_metric_by_idc['all'] = 1
        else:
            self.count_metric_by_idc['all'] += 1

        if end_time - self.start_time_count >= 10:
            self.start_time_count = end_time

            file_name = '/usr/local/cdntoolkit/ctk/apm/' + '%s' % options.router_port_start + '.txt'
            file_obj = open(file_name, 'w')
            try:
                # file_obj.writelines(str(self.one_metric_count) + '_' + str(self.all_metric_count) + '\n')
                file_obj.writelines(json.dumps(self.count_metric_by_idc))
            finally:
                file_obj.close()
            self.count_metric_by_idc = dict()
        return True

    def calc_metric_by_idc(self, idc, metric_key):
        try:
            metrics = self.count_metric_by_idc.get(idc, None)
            if metrics is None:
                metrics = list()
                self.count_metric_by_idc[idc] = metrics

            if metric_key in metrics:
                pass
            else:
                metrics.append(metric_key)

            end_time = time.time()
            if end_time - self.start_time >= 300:
                self.start_time = end_time

                file_name = '/usr/local/cdntoolkit/ctk/apm/test/' + '%s' % options.router_port_start + '.txt'
                file_obj = open(file_name, 'w')
                try:
                    file_obj.writelines(json.dumps(self.count_metric_by_idc))
                finally:
                    file_obj.close()
                self.count_metric_by_idc.clear()
        except Exception as e:
            self.count_metric_by_idc.clear()
            print("calc_metric_by_idc", e)
