# coding=utf-8

import tornado.web
from pymongo import MongoClient
from pymongo.database import Database
from tornado.options import options

from util.config import config_manager
from util.message import WampMessage
from util.objects import object_manager


class TunnelApp(tornado.web.Application):
    def __init__(self) -> None:
        if "for host config data":
            config_manager.run()

        if "for module":
            connection = MongoClient(
                'mongodb://{db}/'.format(db=options.tunnel_db)
            )
            database: Database = connection.get_database(options.tunnel_data_name)

            from .module import TransferModule
            module: TransferModule = TransferModule()
            module.database = database
            object_manager.add_type(str(TransferModule), module)

        message: WampMessage = None
        if "for wamp session":
            message = WampMessage()
            object_manager.add_type(str(WampMessage), message)

        if "for state manager":
            from .state import init
            init()

        if "for handler":
            from .handler import TransferHandler
            handler: TransferHandler = TransferHandler()

            message.add_register(
                options.topic_transfer_post,
                handler.post
            )
            message.add_register(
                options.topic_transfer_get,
                handler.get
            )
            message.add_register(
                options.topic_transfer_put,
                handler.put
            )

            message.add_register(
                options.topic_config_get,
                config_manager.query_config_by_id
            )

            message.start(
                options.router_url.format(
                    port=options.router_port_start + options.shard
                ),
                options.router_domain
            )

            object_manager.add_type(str(TransferHandler), handler)

        if "for http service":
            from .handler import TransferWebHandler
            handlers = [
                (
                    r'/tunnel/transfer$',
                    TransferWebHandler
                ),
                (
                    r'/tunnel/transfer/([0-9a-fA-F]{24}$)',
                    TransferWebHandler
                ),
            ]

            settings = dict(debug=False)
            tornado.web.Application.__init__(self, handlers, **settings)
