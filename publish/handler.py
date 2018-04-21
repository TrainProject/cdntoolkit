# coding=utf-8

import datetime

import tornado.web
import treq
from orderedattrdict import AttrDict
from tornado.options import options
from treq.response import _Response
from twisted.internet.defer import Deferred

from util import reactor
from util.exception import print_frame
from util.json import AttrJson


class PublishHandler(tornado.web.RequestHandler):
    def transaction_id(self):
        # call sync
        return 1

    def dst(self, domain: str) -> str:
        return "hostId = test"

    def post(self):
        ret = AttrDict()
        try:
            db = self.application.db
            ret = AttrDict()
            raw_body: bytes = self.request.body
            body: AttrDict = AttrJson.loads(raw_body.decode())

            for _ in [0]:
                # result = db.PublishWorking.insert_one(json.dumps(insert))
                # result = db.PublishWorking.insert_one(insert)
                query = AttrDict()
                query.user = body.user
                query.gslb_domain = body.gslb_domain
                query.publish_url = body.publish_url

                publish = AttrDict()
                """
                publish.user = body.user
                publish.publish_url = body.publish_url
                publish.gslb_domain = body.gslb_domain
                """
                publish.md5 = body.md5
                publish.version = body.version
                publish.prop = body.prop
                publish.bussid = body.bussid
                publish.action = body.action
                publish.callback = body.callback
                publish.item_id = body.item_id
                publish.transaction_id = 24 * "0"

                publish.create_time = datetime.datetime.utcnow()
                publish.dst = self.dst(body.gslb_domain)

                update = dict()
                update["$setOnInsert"] = publish

                publish = db.PublishWorking.find_and_modify(
                    query=query, update=update, new=True, upsert=True
                )
                publish = AttrDict(publish)
                ret.message = "OK"
                ret.publish_id = str(publish._id)

        except Exception as e:
            print_frame(e)

        self.write(ret)
        self.set_status(200)

    def get(self, publish_id: str):
        db = self.application.db
        status = None
        ret = AttrDict()

        try:
            for _ in [0]:
                if not publish_id:
                    break

                query = AttrDict()
                query._id = publish_id
                result = db.PublishWorking.find_one(query)
                if result is not None:
                    result = AttrDict(result)
                    ret.publish_id = str(result._id)
                    ret.create_time = str(result.create_time)
                    ret.code = -1
                    ret.message = "Working."

                # if not result:
                #    result = self.db.PublishWorking.query()
                # transaction_id

                """
                if state == "started":
                    self.db.PublishWorking.query()
                    break

                if state == "finished":
                    self.db.PublishArchive.query()
                    break
                """

        except Exception as e:
            print_frame(e)

        self.write(ret)
        self.set_status(200)

    def put(self, publish_id: str):
        db = self.application.db
        result = db.PublishWorking.query()
        result = db.PublishWorking.update()

    def delete(self, publish_id):
        pass


class PublishWorkingActivity:
    def __init__(self, _application) -> None:
        self.application = _application
        """@type: PublishApp"""
        self.db = _application.db

    def check_finish(self):
        data = self.db.query() # .limit(64)
        for d in data:
            pass
            # self.db.PublishArchive.insert()
            # self.db.PublishWorking.delete()

    def check_transaction(self):
        def check_transaction_ret_header(r):
            if r.code == 200:
                content: Deferred = r.content()
                content.addCallback(check_transaction_ret_body)

        def check_transaction_ret_body(content: bytes):
            try:
                ret = AttrJson.loads(content.decode())

                _query = AttrDict()
                _query._id = transaction._id

                tid = AttrDict()
                tid.transaction_id = ret.transaction_id

                update = AttrDict()
                update["$set"] = tid
            except Exception as _e:
                print_frame(_e)

        query = AttrDict()
        query.transaction_id = 24 * "0"
        transactions = self.db.PublishWorking.find(query)

        for transaction in transactions:
            try:
                transaction = AttrDict(transaction)

                data = AttrDict()
                data.dst = "host"
                data.notify = "http://{address}:{port}/publish".format(
                    address=options.publish_address, port=options.publish_port
                )
                data.application = AttrDict()
                data.application.name = "publish"
                data.application.user = transaction.user
                data.application.publish_url = transaction.publish_url
                data.application.md5 = transaction.md5
                data.application.version = transaction.version
                data.application.gslb_domain = transaction.gslb_domain
                data.application.prop = transaction.prop
                data.application.bussid = transaction.bussid
                data.application.action = transaction.action

                post_url = "http://{address}:{port}/sync/transaction".format(
                    address=options.sync_address, port=options.sync_port
                )
                d: Deferred = treq.post(
                    post_url, data=AttrJson.dumps(data).encode(), timeout=1
                )
                d.addCallback(check_transaction_ret_header)

            except Exception as e:
                print_frame(e)
                # self.db.TransferWorking.update_one(query, update)

    def test(self):
        self.test_post()

    def test_get(self, publish_id: str):
        def test_get_ret_body(content: bytes):
            try:
                query_result = AttrJson.loads(content.decode())
                print(query_result)
            except Exception as _e:
                print_frame(_e)

        def test_get_ret_header(r: _Response):
            if r.code == 200:
                content: Deferred = r.content()
                content.addCallback(test_get_ret_body)

        try:
            query_url = "http://{address}:{port}/publish/{key}".format(
                address=options.publish_address,
                port=options.publish_port,
                key=publish_id
            )

            d: Deferred = treq.get(query_url, timeout=1)
            d.addCallback(test_get_ret_header)
        except Exception as e:
            print_frame(e)

    def test_post(self):
        def test_post_ret_body(content: bytes):
            try:
                ret: AttrDict = AttrJson.loads(content.decode())
                self.test_get(ret.publish_id)
            except Exception as _e:
                print_frame(_e)

        def test_post_ret_header(r: _Response):
            if r.code == 200:
                content: Deferred = r.content()
                content.addCallback(test_post_ret_body)

        data = AttrDict()
        data.user = "user"
        data.publish_url = "http://abc.com"
        data.md5 = "ae5800d3fa505e92e244023a02bd9735"
        data.version = "ae5800d3fa505e92e244023a02bd9735"
        data.gslb_domain = "http://www.example.com"
        data.prop = 9
        data.bussid = 1
        data.action = "ATDADD"
        data.callback = "http://notify.example.com"
        data.item_id = 5734

        try:
            post_url = "http://{address}:{port}/publish".format(
                address=options.publish_address, port=options.publish_port
            )
            d: Deferred = treq.post(post_url, data=AttrJson.dumps(data).encode(), timeout=1)
            d.addCallback(test_post_ret_header)
            # r = requests.post(post_url, data=AttrJson.dumps(data), timeout=(3, 3))
            # print(r.content)

        except Exception as e:
            print_frame(e)

    def run(self):
        self.test()
        self.check_transaction()
        # self.check_finish()
        reactor().callLater(10, self.run)
