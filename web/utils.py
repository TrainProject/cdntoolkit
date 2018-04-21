# coding:utf-8

import json
import os
import time

import requests
from tornado.options import options

HTTP_TIMEOUT = 30


def get_datetime(timestamp=None):
    str_time = ''
    try:
        if timestamp is None:
            timestamp = int(time.time())
        elif len(str(int(timestamp))) == 13:
            timestamp = int(timestamp)/1000

        x = time.localtime(timestamp)
        str_time = time.strftime('%Y-%m-%d %H:%M:%S', x)

    except Exception as e:
        options.config.logging.error("get_datetime error=[%s]" % e)

    return str_time


def create_path(dst_path):
    try:
        os.mkdir(dst_path)
        options.config.logging.info("create_path path=[%s], success." % dst_path)
    except Exception as e:
        options.config.logging.error("create_path path=[%s], error=[%s]" % (dst_path, e))
        return False
    return True


def format_metric_json(metric_dict):
    try:
        m_list = metric_dict["results"][0]["series"][0]["values"]
        s = list()
        for temp in m_list:
            s.append(temp[0])
        # options.config.logging.info("format_metric_json s=[%s]"%s)
        return s
    except Exception as e:
        options.config.logging.error("format_metric_json error=[%s]" % e)


def format_tags_json(tags_dict):
    try:
        t_list = tags_dict["results"][0]["series"][0]["values"]
        s = list()
        for temp in t_list:
            s.append(temp[0])
        options.config.logging.info("format_tags_json tags_dict=[%s]" % tags_dict)
        return s
    except Exception as e:
        options.config.logging.error("format_tags_json error=[%s] tags_dict=[%s]" % (e, tags_dict))


def format_tags_value(tags_dict):
    try:
        t_list = tags_dict["results"][0]["series"][0]["values"]
        s = list()
        for temp in t_list:
            s.append(temp[1])
        # options.config.logging.info("format_tags_value tags_dict=[%s]"% tags_dict)
        return s
    except Exception as e:
        options.config.logging.error("format_tags_value error=[%s],tags_dict=[%s]" % (e, tags_dict))
        return []


def find_symbol(tag):
    result = ':'
    try:
        if tag.find("=~") >= 0:
            result = "=~"
        elif tag.find("<>") >= 0:
            result = "<>"
        elif tag.find("=") >= 0:
            result = "="
        elif tag.find("<") >= 0:
            result = "<"
        elif tag.find(">") >= 0:
            result = ">"
        elif tag.find("!=") >= 0:
            result = "!="
        options.config.logging.info("find_symbol result=[%s],tag=[%s]" % (result, tag))
    except Exception as e:
        options.config.logging.error("find_symbol error=[%s],tag=[%s]" % (e, tag))
    return result


def split_tag_name(tag_name):
    tag_dict = dict()
    group_by = dict()
    try:
        sign = find_symbol(tag_name)
        name_list = tag_name.split(sign)
        tag_dict["key"] = name_list[0]
        tag_dict["operator"] = sign
        if sign == ":":
            tag_dict["value"] = "error"
        else:
            tag_dict["value"] = name_list[-1]
        group_by["params"] = [name_list[0]]
        group_by["type"] = "tag"
        options.config.logging.info("split_tag_name tag_dict=[%s],group_by=[%s]" % (tag_dict, group_by))
    except Exception as e:
        options.config.logging.error("split_tagName error=[%s],tag_name=[%s]" % (e, tag_name))
    return tag_dict, group_by


def get_all_metric():
    try:
        all_metric = []
        for shard, influx_server in options.config.METRIC_URL.items():
            url = "http://" + influx_server + "/query?db=opentsdb&q=SHOW%20MEASUREMENTS"
            # f = urllib.urlopen(url)
            # metric = f.read()
            req = requests.get(url)
            metric = req.text
            metric = json.loads(metric)
            if "error" in metric.keys():
                return []
            metric = format_metric_json(metric)
            all_metric.extend(metric)

        all_metric = list(set(all_metric))
        all_metric.sort()
        options.config.logging.info("get_all_metric all_metric=[%s]" % all_metric)
        return all_metric
    except Exception as e:
        options.config.logging.error("get_all_metric error=[%s]" % e)
        return []


def polyhash(word, a=31, p=997, m=-1):
    _hash = 0
    for c in word:
        _hash = (_hash * a + ord(c)) % p
    if m == -1:
        return abs(_hash)
    else:
        return abs(_hash) % abs(m)


def get_influxdb_server(metric):
    try:
        shard = polyhash(metric, m=8)
        server = options.config.METRIC_URL[shard]
        options.config.logging.info("get_influxdb_server, metric=[%s], influxdb_server=[%s]" % (metric, server))
        return server
    except Exception as e:
        options.config.logging.error("get_influxdb_server error=[%s]" % e)


'''
def get_influxdb_server(metric):
    try:
        shard = int(hashlib.md5(metric.encode()).hexdigest()[:2], 16)
        shard %= 8
        print(metric,":",shard)
        server = options.config.METRIC_URL[shard]
        options.config.logging.info("get_influxdb_server,metric=[%s],influxdb_server=[%s]"%(metric, server))
        return server
    except Exception as e:
        options.config.logging.error("get_influxdb_server error=[%s], metric=[%s]"%(e, metric))
'''


def get_all_tags(influxdb_server, metric_name):
    try:
        url = 'http://' + influxdb_server + '/query?db=opentsdb&q=SHOW%20TAG%20KEYS%20FROM%20%22' + metric_name + '%22'
        url += "&epoch=ms"
        # req = urllib2.Request(url)
        # res_data = urllib2.urlopen(req)
        # data = res_data.read()
        req = requests.get(url)
        data = req.content
        data = json.loads(data)
        if 'error' in data:
            return []
        result = format_tags_json(data)
        options.config.logging.info("get_all_tags,url=[%s]" % url)
    except Exception as e:
        options.config.logging.error("get_all_tags error=[%s]" % e)
        result = []
    return result


def get_tag_value(influxdb_server, metric_name, tag_name):
    try:
        url = 'http://' + influxdb_server + '/query?db=opentsdb&q=SHOW%20TAG%20VALUES%20FROM%20%22' + \
              metric_name + '%22%20WITH%20KEY%20%3D%20%22'
        tags = tag_name.split(',')
        item = find_symbol(tags[-1])
        url += tags[-1].split("%s" % item)[0] + '%22'
        if len(tags) > 1:
            num = 0
            url += '%20WHERE%20'
            for i in range(0, len(tags)-1, 1):
                item = find_symbol(tags[i])
                if num == 0:
                    num += 1
                    url += '%22' + tags[i].split("%s" % item)[0] + '%22%20%3D%20%27' + tags[i].split("%s" % item)[1] + '%27'
                else:
                    url += '%20AND%20%22' + tags[i].split("%s" % item)[0] + '%22%20%3D%20%27' + tags[i].split("%s" % item)[1] + '%27'

        url += "&epoch=ms"
        # req = urllib2.Request(url)
        # res_data = urllib2.urlopen(req)
        # data = res_data.read()
        req = requests.get(url)
        data = req.text
        data = json.loads(data)
        if 'error' in data or len(data["results"][0]) == 0:
            options.config.logging.info("get_tag_value url error,url=[%s],url_result=[%s]" % (url, data))
            return []
        result = format_tags_value(data)

    except Exception as e:
        options.config.logging.error("get_tag_value error=[%s],url=[%s]" % (e, url))
        result = []

    return result
