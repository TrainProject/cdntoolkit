# coding=utf-8

import tornado.web
from tornado.options import options

from util import reactor
from .handler import PublishHandler
from .handler import PublishWorkingActivity


class PublishApp(tornado.web.Application):
    def __init__(self) -> None:
        import pymongo
        self.connection = pymongo.MongoClient(
            'mongodb://{db}/'.format(db=options.publish_db)
        )
        self.db = self.connection.get_database(options.publish_data_name)
        self.db.drop_collection("PublishWorking")

        self.wt = PublishWorkingActivity(self)
        reactor().callLater(1, self.wt.run)

        setting = dict(debug=False)
        handlers = [
            (r'/publish$',                      PublishHandler),
            (r'/publish/([0-9a-fA-F]{24}$)',    PublishHandler),
        ]

        tornado.web.Application.__init__(self, handlers, **setting)

