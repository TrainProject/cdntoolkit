# coding: utf-8

import hashlib

from tornado.options import options

import web
import web.log
import web.sqlite_tool
import web.utils


class Sqlite_Json:
    def __init__(self) -> None:
        self.tags_json1 = {"key": "", "operator": "", "value": ""}
        self.tags_json2 = {"condition": "", "key": "", "operator": "", "value": ""}
        self.targets_json = {
            "alias": "",
            "dsType": "influxdb",
            "groupBy": [{"params": ["$interval"], "type": "time"}],
            "measurement": "temperature.cpu",
            "policy": "default",
            "query": "",
            "rawQuery": False,
            "refId": "A",
            "resultFormat": "time_series",
            "select": [[{"params": ["value"], "type": "field"}]],
            "tags": []
        }

        self.targets_root_json = [self.targets_json]
        self.legend_json = {
            "alignAsTable": True,
            "avg": False,
            "current": False,
            "max": False,
            "min": False,
            "rightSide": True,
            "show": True,
            "sideWidth": 20,
            "total": False,
            "values": False,
            "hideEmpty": False,
            "hideZero": False,
        }

        self.panels_json = {
            "aliasColors": {},
            "bars": False,
            # "datasource": "opentsdb",
            "datasource": None,
            "editable": True,
            "error": False,
            "fill": 0,
            "grid": {
                "threshold1": None,
                "threshold1Color": "rgba(216, 200, 27, 0.27)",
                "threshold2": None,
                "threshold2Color": "rgba(234, 112, 112, 0.22)",
                "thresholdLine": False
            },
            "hideTimeOverride": False,
            "id": 1,
            "isNew": True,
            "legend": self.legend_json,
            "lines": True,
            "linewidth": 2,
            "links": [],
            "nullPointMode": "connected",
            "percentage": False,
            "pointradius": 5,
            "points": False,
            "renderer": "flot",
            "seriesOverrides": [],
            "span": 12,
            "stack": False,
            "steppedLine": False,
            "targets": self.targets_root_json,
            "timeFrom": None,
            "timeShift": None,
            "title": "read/write requests",
            "tooltip": {"msResolution": True, "shared": False, "sort": 1, "value_type": "cumulative"},
            "transparent": False,
            "type": "graph",
            "xaxis": {"show": True},
            "yaxes": [
                {
                    "format": "short",
                    "label": None,
                    "logBase": 1,
                    "max": None,
                    "min": None,
                    "show": True
                },
                {
                    "format": "short",
                    "label": None,
                    "logBase": 1,
                    "max": None,
                    "min": None,
                    "show": True
                }
            ]
        }

        self.panels_root_json = [self.panels_json]
        self.rows_json = [{
            "collapse": False,
            "editable": True,
            "showTitle": False,
            "height": "250px",
            "panels": self.panels_root_json
            # "title": "Row"
        }]

        self.root_dict = {
            "annotations": {"list": []},
            "editable": True,
            "gnetId": None,
            "hideControls": False,
            "id": 1,
            "links": [],
            "refresh": False,
            "rows": self.rows_json,
            "schemaVersion": 12,
            "sharedCrosshair": False,
            "style": "dark",
            "tags": [],
            "templating": {"list": []},
            "time": {"from": "now-5m", "to": "now"},
            "timepicker": {
                "refresh_intervals": ["5s", "10s", "30s", "1m", "5m", "15m", "30m", "1h", "2h", "1d"],
                "time_options": ["5m", "15m", "1h", "6h", "12h", "24h", "2d", "7d", "30d"]
            },
            "timezone": "browser",
            "title": "disk",
            "version": 28
        }


def add_default_ptr(metric_name, note):
    try:
        sel_dict = {}
        gro_dict = {}

        if metric_name in options.config.SELECT:
            sel_dict["params"] = [options.config.SELECT[metric_name].split("(")[-1].split(")")[0]]
            sel_dict["type"] = [options.config.SELECT[metric_name].split("(")[0]]
            note.root_dict["rows"][0]["panels"][0]["targets"][0]["select"][0].append(sel_dict)

        if metric_name in options.config.GROUPBY:
            gro_dict["params"] = [options.config.GROUPBY[metric_name].split("(")[-1].split(")")[0]]
            gro_dict["type"] = [options.config.GROUPBY[metric_name].split("(")[0]]
            note.root_dict["rows"][0]["panels"][0]["targets"][0]["groupBy"].append(gro_dict)

        if metric_name in options.config.UNIT:
            note.root_dict["rows"][0]["panels"][0]["yaxes"][0]["format"] = options.config.UNIT[metric_name]

    except Exception as e:
        options.confing.logging.error(
            "add_default_ptr error=[%s],metric=[%s],note=[%s]" % (
                e, metric_name, note.root_dict
            )
        )

    return note


def mk_record_targets(influxdb_server, metric_name, tags_name, aggregate, group):
    try:
        notes = Sqlite_Json()
        notes = add_default_ptr(metric_name, notes)
        notes.targets_json["measurement"] = "%s" % metric_name
        notes.panels_json["datasource"] = influxdb_server
        tags = tags_name.split(',')
        num = 0
        for item in tags:
            tag_dict = {}
            group_by = {}
            if item:
                tag_dict, group_by = web.utils.split_tag_name(item)
                num += 1
                if num > 1:
                    tag_dict["condition"] = "AND"
                notes.targets_json["tags"].append(tag_dict)

        if not aggregate:
            aggregate = "max"

        notes.targets_json["select"][0].append({"params": [], "type": aggregate})

        if group:
            notes.targets_json["groupBy"].append({"params": [group], "type": "tag"})

        notes.targets_json["groupBy"].append({"type": "fill", "params": ["null"]})
        options.config.logging.info("mk_record_targets,record_detail=[%s]" % notes.root_dict)
    except Exception as e:
        options.config.logging.error(
            "mk_record_targets error=[%s],metric_name=[%s],tags_name=[%s]" % (
                e, metric_name, tags_name
            )
        )
        return False

    return notes


def get_query(notes):
    try:
        tags = notes.targets_json["tags"]
        gro_by = ''
        querys = "SELECT derivative(max(\"value\"), 1s) FROM \"" + notes.targets_json["measurement"] + "\" WHERE 1=1"
        for item in tags:
            querys = querys + " AND \"" + item["key"] + "\"" + item["operator"] + item["value"]
            gro_by = ", " + "\"" + item["value"] + "\""
        querys += " AND $timeFilter GROUP BY time($interval)" + gro_by + " fill(null)"
        notes.targets_json["query"] = querys
        options.config.logging.info("get_query querys =[%s]" % querys)
    except Exception as e:
        options.config.logging.error("get_query error=[%s],notes=[%s]" % (e, notes.root_dict))
        querys = ''

    return notes


def mk_record(influxdb_server, metric_name, tags_name, aggregate, group):
    try:
        note = mk_record_targets(influxdb_server, metric_name, tags_name, aggregate, group)
        if not note:
            return False

        notes = get_query(note)
        sqlite = web.sqlite_tool.SQLITE_DB()
        _id = sqlite.get_last_id() + 1

        notes.root_dict["version"] = _id
        notes.root_dict["id"] = _id
        notes.root_dict["rows"][0]["panels"][0]["id"] = 1
        notes.root_dict["rows"][0]["panels"][0]["title"] = metric_name
        options.config.logging.info("mk_record notes=[%s]" % notes.root_dict)
    except Exception as e:
        options.config.logging.error(
            "mk_record error=[%s],influx=[%s],metric=[%s],tags=[%s]" % (
                e, influxdb_server, metric_name, tags_name
            )
        )
        notes = None
    return notes


def check_md5(slug_md5):
    try:
        sqlite = web.sqlite_tool.SQLITE_DB()
        result = sqlite.check_slug(slug_md5)

        if result != 0:
            return True
        else:
            return False

    except Exception as e:
        options.config.logging.error("check_md5 error=[%s],slug_md5=[%s]" % (e, slug_md5))
        print(e)


def mk_dashboard_url(influxdb_server, metric_name, tags_name):
    try:
        d = mk_record(influxdb_server, metric_name, tags_name)
        if not d:
            return 'error'

        sqlite = web.sqlite_tool.SQLITE_DB()
        m2 = hashlib.md5()
        m2.update(str(d.root_dict["rows"]).encode())
        slug = m2.hexdigest()
        result = check_md5(slug)

        if result:
            return options.config.DASHBOARD_URL + slug

        d.root_dict["title"] = slug
        url = options.config.DASHBOARD_URL + slug
        title = slug + "||" + metric_name + "||" + tags_name

        s = str(d.root_dict)
        w = s.replace('"', '\\"').replace("'", '"')
        data = w.replace("False", "false").replace("True", "true").replace("None", "null")
        result = False
        if data:
            result = sqlite.insert_item(d.root_dict["id"], slug, d.root_dict["version"], title, data.replace("'", '"'))

        if not result:
            url = ''

    except Exception as e:
        options.config.logging.error(
            "mk_dashboard_url error=[%s],metric_name=[%s],tags_name=[%s]" % (
                e, metric_name, tags_name
            )
        )

    return url


def get_records(start_num, finish_num):
    try:
        sqlite = web.sqlite_tool.SQLITE_DB()
        result = sqlite.query_table_records(start_num, finish_num)
        options.config.logging.info("get_records start_num=[%s], finish_num=[%s]" % (start_num, finish_num))
    except Exception as e:
        options.config.logging.error(
            "get_records error=[%s],start_num=[%s],finish_num=[%s]" % (
                e, start_num, finish_num
            )
        )
        result = []

    return result


def get_page_records(page_num=1):
    try:
        table_list = []
        sqlite = web.sqlite_tool.SQLITE_DB()
        result = sqlite.query_table_page(page_num)
        for item in result:
            temp = dict()
            temp["metric_name"] = ''
            temp["tags"] = ''
            for panel in item["data"]["rows"][0]["panels"]:
                if panel["targets"][0]["measurement"] not in temp["metric_name"]:
                    if temp["metric_name"] == '':
                        temp["metric_name"] = temp["metric_name"] + (panel["targets"][0]["measurement"]).replace("||", '')
                    else:
                        temp["metric_name"] = temp["metric_name"] + " || " + (panel["targets"][0]["measurement"]).replace("||", '')
                tags = panel["targets"][0]["tags"]
                if temp["tags"] == '':
                    for tag in tags:
                        if len(tag) > 0:
                            temp["tags"] = temp["tags"] + tag["key"] + tag["operator"] + tag["value"] + ","
                else:
                    temp["tags"] = temp["tags"][: -1] + " || "
                    for tag in tags:
                        if len(tag) > 0:
                            temp["tags"] = temp["tags"] + tag["key"] + tag["operator"] + tag["value"] + ","

            temp["tags"] = temp["tags"][:-1]
            temp["slug"] = item["slug"]
            temp["created"] = item["created"]
            temp["updated"] = item["updated"]
            table_list.append(temp)
        options.config.logging.info("get_page_records table_list=[%s]" % (table_list))
    except Exception as e:
        options.config.logging.error(
            "get_page_records error=[%s],table_list=[%s]" % (e, table_list)
        )
        result = []

    return table_list


def get_all_records():
    try:
        result = None
        sqlite = web.sqlite_tool.SQLITE_DB()
        result = sqlite.query_all_number()

    except Exception as e:
        options.config.logging.error(
            "get_all_records error=[%s],result=[%s]" % (
                e, result
            )
        )

    return result


def cocat_records(param_json):
    try:
        slug_list = param_json
        notes = Sqlite_Json()
        notes.panels_root_json = []
        id = 1
        for item in slug_list:
            sqlite = web.sqlite_tool.SQLITE_DB()
            result = sqlite.query_by_slug(item)
            for temp in result["rows"][0]["panels"]:
                if temp not in notes.panels_root_json:
                    temp["id"] = id
                    notes.panels_root_json.append(temp)
                    id += 1

        notes.root_dict["rows"][0]["panels"] = notes.panels_root_json
        m2 = hashlib.md5()
        m2.update(str(notes.root_dict["rows"]).encode())
        slug = m2.hexdigest()
        notes.root_dict["title"] = slug
        sqlite = web.sqlite_tool.SQLITE_DB()
        notes.root_dict["id"] = sqlite.Get_LastId() + 1

        re = check_md5(slug)
        if re:
            return options.config.DASHBOARD_URL + slug

        title = slug
        s = str(notes.root_dict)
        w = s.replace('"', '\\"').replace("'", '"')
        data = w.replace("False", "false").replace("True", "true").replace("None", "null")
        result = False

        if data is not None:
            sqlite = web.sqlite_tool.SQLITE_DB()
            result = sqlite.insert_item(
                notes.root_dict["id"], slug,
                notes.root_dict["version"], title,
                data.replace("'", '"')
            )

        if not result:
            url = ''
        url = options.config.DASHBOARD_URL + slug
        options.config.logging.info("cocat_records url=[%s],param_json=[%s]" % (url, param_json))
    except Exception as e:
        options.config.logging.error("cocat_records error=[%s],param_json=[%s]" % (e, param_json))
        url = 'error'

    return url


def view_detail(slug):
    try:
        result = None
        sqlite = web.sqlite_tool.SQLITE_DB()
        result = sqlite.query_by_slug(slug)
        options.config.logging.info("view_detail slug=[%s], result=[%s]"% (slug, result))
    except Exception as e:
        options.config.logging.error(
            "view_detail=[%s],slug=[%s],result=[%s]" % (
                e, slug, result
            )
        )
    return result


def del_item(slug):
    try:
        result = None
        sqlite = web.sqlite_tool.SQLITE_DB()
        result = sqlite.del_by_slug(slug)
        if result:
            result = "delete OK"
        else:
            result = "delete fail"
        options.config.logging.info("del_item slug=[%s], result=[%s]"% (slug, result))
    except Exception as e:
        options.config.logging.error("del_item error=[%s],slug=[%s]" % (e, slug))

    return result
