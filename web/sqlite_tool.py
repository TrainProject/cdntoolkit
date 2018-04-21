# coding: utf-8

import json

from tornado.options import options

import web
import web.db
import web.log
import web.utils


class SQLite_table:
    def __init__(self) -> None:
        self.gf_id = 0
        self.gf_version = 0
        self.gf_slug = str()
        self.gf_title = str()
        self.gf_data = str()
        self.gf_org_id = 0
        self.gf_created = str()
        self.gf_updated = str()
        self.gf_updated_by = 0
        self.gf_created_by = 0
        self.gf_gnet_id = 0
        self.gf_plugin_id = str()


class SQLITE_DB:
    def __init__(self) -> None:
        try:
            self.the_db = web.db.DB_SQLITE()
            self.the_db.connect(web.db.DB_SQLITE_CONFIG.db_name)
        except Exception as e:
            options.config.logging.error(
                'sqlite_db.Init(),error=[%s],db_name=[%s]' % (
                    e, web.db.DB_SQLITE_CONFIG.db_name
                )
            )

    def get_last_id(self):
        try:
            sql = "select `id` from dashboard where 1=1 order by id DESC limit 1"
            result = self.the_db.execute(sql)
            s = self.the_db.fetchall()
            self.the_db.close()
            if len(s) > 0:
                return s[0][0]
            else:
                return 0
        except Exception as e:
            options.config.logging.error("get_last_id error=[%s],sql=[%s]" % (e, sql))

    def query_all_number(self):
        try:
            sql = "select count(id) from dashboard"
            result = self.the_db.execute(sql)
            s = self.the_db.fetchall()

            return s[0][0]
        except Exception as e:
            options.config.logging.error("query_all_number error=[%s],sql=[%s]" % (e, sql))

    def query_by_slug(self, slug):
        try:
            sql = "select `data` from dashboard where `slug`='%s'" % slug
            result = self.the_db.execute(sql)
            s = self.the_db.fetchall()
            #result = eval(str(s[0][0]).replace("false", "False").replace("true", "True").replace("null", "None"))
            result = json.loads(s[0][0])
            self.the_db.close()

        except Exception as e:
            options.config.logging.error("query_by_slug error=[%s],sql=[%s]" % (e, sql))
            result = False

        return result

    def check_slug(self, slug_md5):
        try:
            sql = "select count(id) from dashboard where `slug`='%s'" % slug_md5
            result = self.the_db.execute(sql)
            s = self.the_db.fetchall()
            self.the_db.close()

            return s[0][0]
        except Exception as e:
            options.config.logging.error("check_slug error=[%s],sql=[%s]" % (e, sql))

    def query_all(self, db_name):
        try:
            sqlite_list = []
            result = self.the_db.execute("select * from dashboard")
            data_list = self.the_db.fetchall()
            for one in data_list:
                temp = SQLite_table()
                temp.gf_id = one[0]
                temp.gf_version = one[1]
                temp.gf_slug = one[2]
                temp.gf_title = one[3]
                temp.gf_data = str(one[4])
                temp.gf_org_id = one[5]
                temp.gf_created = one[6]
                temp.gf_updated = one[7]
                temp.gf_updated_by = one[8]
                temp.gf_created_by = one[9]
                temp.gf_gnet_id = one[10]
                temp.gf_plugin_id = one[11]
                sqlite_list.append(temp)

        except Exception as e:
            options.config.logging.error("query_all error=[%s]" % e)

        return sqlite_list

    def query_table_records(self, start_num, finish_num):
        try:
            sqlite_list = []
            sql = "select `slug`,`title`,`data`,`created`,`updated` from dashboard limit %s, %s" % (start_num, finish_num)
            result = self.the_db.execute(sql)
            data_list = self.the_db.fetchall()
            for one in data_list:
                temp = dict()
                temp["slug"] = one[0]
                temp["title"] = one[1]
                temp["data"] = str(one[2])
                temp["created"] = one[3]
                temp["updated"] = one[4]
                sqlite_list.append(temp)

        except Exception as e:
            options.config.logging.error("query_table_records error=[%s],sql=[%s]" % (e, sql))

        return sqlite_list

    def query_table_page(self, page_num):
        try:
            if int(page_num) <= 0:
                page_num = 1

            start_num = (int(page_num)) * 20 - 20
            finish_num = (int(page_num)) * 20
            sqlite_list = []
            sql = "select `slug`,`title`,`data`,`created`,`updated` from dashboard order by `id` DESC limit 20 offset %s" % start_num
            result = self.the_db.execute(sql)
            data_list = self.the_db.fetchall()

            for one in data_list:
                temp = dict()
                temp["slug"] = one[0]
                temp["title"] = one[1]
                # temp["data"] = eval((str(one[2])).replace("false", "False").replace("true", "True").replace("null", "None"))
                temp["data"] = json.loads(one[2])
                temp["created"] = one[3]
                temp["updated"] = one[4]
                sqlite_list.append(temp)
            options.config.logging.info("query_table_page,num=[%s],sql=[%s]" % (page_num, sql))
        except Exception as e:
            options.config.logging.error("query_table_page error=[%s],sql=[%s]" % (e, sql))

        return sqlite_list

    def update_data(self, id, data):
        try:
            sql = "update dashboard set `data`='%s' where `id`=%s" % (data, id)
            self.the_db.execute(sql)
            self.the_db.commit()
            self.the_db.close()
            result = True

        except Exception as e:
            options.config.logging.error("update_data error=[%s],sql=[%s]" % (e, sql))
            result = False

        return result

    def del_by_slug(self, slug):
        try:
            sql = "delete from dashboard where `slug`='%s'" % slug
            self.the_db.execute(sql)
            self.the_db.commit()
            self.the_db.close()
            result = True

        except Exception as e:
            options.config.logging.error("del_by_slug error=[%s],aql=[%s]" % (e, sql))
            result = False

        return result

    def insert_item(self, _id, slug, version, title, data):
        try:
            creat_time = web.utils.get_datetime()
            update_time = web.utils.get_datetime()
            sql = "INSERT INTO dashboard (`id`,`version`,`slug`,`title`,`data`,`org_id`,`created`,`updated`," \
                  "`updated_by`,`created_by`,`gnet_id`,`plugin_id`) VALUES (%s, %s, '%s', '%s', '%s', %s, '%s', '%s', " \
                  "%s,%s,%s,'%s')" % (_id, version, slug, title, data, 1, creat_time, update_time, 1, 1, 0, '')
            self.the_db.execute(sql)
            self.the_db.commit()
            self.the_db.close()
            return True

        except Exception as e:
            options.config.logging.error("Insert_item error=[%s],sql=[%s]" % (e, sql))
            return False
