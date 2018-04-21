# coding=utf-8
import sqlite3


class DB_SQLITE_CONFIG:
    # db_name = '/var/lib/grafana/grafana.db'
    db_name = '/usr/local/grafana-4.1.0-1484127817/data/grafana.db'


class DB_SQLITE:
    def __init__(self) -> None:
        self.cx = None
        self.cu = None

    def connect(self, db_name):
        try:
            self.cx = sqlite3.connect(db_name)
            self.cu = self.cx.cursor()

        except Exception as e:
            print(e)

        return True

    def execute(self, sql):
        return self.cu.execute(sql)

    def commit(self):
        return self.cx.commit()

    def fetchall(self):
        return self.cu.fetchall()

    def close(self):
        self.cu.close()
        self.cx.close()
