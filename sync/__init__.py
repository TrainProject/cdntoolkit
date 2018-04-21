# coding=utf-8

from typing import List

import tornado.web
from pymongo import MongoClient
from pymongo.database import Database
from tornado.options import options
from twisted.internet.defer import Deferred

from util.message import WampMessage
from util.objects import object_manager


class SyncApp(tornado.web.Application):
    def __init__(self) -> None:
        if "for host config data":
            from util.config import config_manager
            config_manager.run()

        if "for module":
            connection: MongoClient = MongoClient(
                'mongodb://{db}/'.format(db=options.sync_db)
            )

            database: Database = connection.get_database(
                options.sync_data_name
            )
            database.drop_collection("TransactionWorking")

            tunnel_db: Database = connection.get_database(
                options.tunnel_data_name
            )
            tunnel_db.drop_collection("TransferWorking")
            tunnel_db.drop_collection("TransferTask")

            from .module import TransactionModule
            module: TransactionModule = TransactionModule()
            module.database = database

            object_manager.add_type(str(TransactionModule), module)

        messages: List[WampMessage] = list()
        if "for wamp session":
            index: int = 0
            for port in range(
                    options.router_port_start,
                    options.router_port_end,
                    options.router_port_step
            ):
                message: WampMessage = WampMessage()
                defer: Deferred = message.start(
                    options.router_url.format(port=port),
                    options.router_domain
                )
                _ = defer  # TODO when connected

                object_manager.add_type(
                    str(WampMessage), message, str(index)
                )

                index += 1

        if "for state manager":
            from .state import init
            init()

        if "for handler":
            from .handler import TransactionHandler
            handler: TransactionHandler = TransactionHandler()

            for message in messages:
                message.add_register(
                    options.topic_transaction_post,
                    handler.post
                )

                message.add_register(
                    options.topic_transaction_get,
                    handler.get
                )

                message.add_register(
                    options.topic_transaction_put,
                    handler.put
                )

                """
                message.register(
                    options.topic_config_get,
                    config_manager.query_config_by_id
                )
                """

            object_manager.add_type(str(TransactionHandler), handler)

        if "for http service":
            from .handler import TransactionWebHandler
            from util.config import ConfigWebHandler

            handlers = [
                (
                    r'/sync/transaction$',
                    TransactionWebHandler
                ),
                (
                    r'/sync/transaction/([0-9a-fA-F]{24}$)',
                    TransactionWebHandler
                ),
                (
                    r'/sync/transaction/([0-9a-fA-F]{24}$)/transfer/([0-9a-fA-F]{24}$)',
                    TransactionWebHandler
                ),
                (
                    r'/sync/config',
                    ConfigWebHandler
                ),
            ]
            settings = dict(debug=False)  # self.config.debug != 0)
            tornado.web.Application.__init__(self, handlers, **settings)
