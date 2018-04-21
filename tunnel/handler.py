# coding=utf-8

from typing import Union

import tornado.web
from bson.objectid import ObjectId
from tornado.concurrent import Future

from util import GeneralException
from util.exception import print_frame
from util.objects import object_manager
from util.protocol import \
    TransferPostRequest, TransferPostResponse, \
    TransferGetRequest, TransferGetResponse, \
    TransferPutRequest, TransferPutResponse, \
    TransferDeleteRequest, TransferDeleteResponse, \
    TransferGetResponseResult
from util.state import Status, Context, StateManager
from .module import TransferWorking


class TransferHandler:
    def __init__(self) -> None:
        transfer_state_manager: object = object_manager.find_type(
            str(StateManager), 'transfer'
        )
        assert isinstance(transfer_state_manager, StateManager)
        self._state_manager: StateManager = transfer_state_manager

    def post(self, data: Union[str, TransferPostRequest],
             ret: TransferPostResponse=None) -> str:

        post_param: TransferPostRequest = None
        has_return = False

        if ret is None:
            ret = TransferPostResponse()
            has_return = True

        if isinstance(data, TransferPostRequest):
            post_param = data

        try:
            if post_param is None:
                post_param = TransferPostRequest(data)

            working: TransferWorking = TransferWorking()
            working.transaction_id = ObjectId(post_param.transaction_id)
            working.hosts = post_param.hosts
            working.retry = post_param.retry
            working.timeout = post_param.timeout
            working.application = post_param.application

            status = object_manager.find_object(working)
            if status is None:
                context: Context = Context()
                context.attachment = str(working.transaction_id)

                if self._state_manager.set(status=working, context=context):
                    activity = working.activity
                    object_manager.add_object(
                        activity.key, activity.status
                    )

                else:
                    raise GeneralException(
                        500, "create transfer error"
                    )

            else:
                activity = status.activity

            ret.transfer_id = activity.key
            ret.message = "success"
            ret.code = 200

        except GeneralException as e:
            print_frame(e)
            ret.code = e.code
            ret.message = e.message

        except Exception as e:
            print_frame(e)
            ret.code = 400
            ret.message = str(e)

        if has_return:
            return str(ret)

        return None

    def get(self, data: Union[str, TransferGetRequest],
            ret: TransferGetResponse=None) -> str:

        get_param: TransferGetRequest = None
        has_return = False

        if ret is None:
            ret = TransferGetResponse()
            has_return = True

        if isinstance(data, TransferGetRequest):
            get_param = data

        try:
            if get_param is None:
                get_param = TransferGetRequest(data)

            status = object_manager.object_by_id(get_param.transfer_id)

            if status is not None:
                assert isinstance(status, TransferWorking)

                ret.code = status.code
                ret.message = status.message
                ret.create_time = status.create_time
                ret.last_time = status.last_time

                for result in status.results:
                    _result = TransferGetResponseResult()
                    _result.host = result.host
                    _result.code = result.code
                    _result.message = result.message
                    ret.results.append(_result)

                # host -> uuid
                # ret.results = working.results
                # FIXME API completion
                # ret.hosts = working.hosts
                # self.tst.query_transfer(get_param.transfer_id, ret)
                ret.code = 200
                ret.message = "success"

            else:
                ret.code = 404
                ret.message = "invalid transfer id {key}".format(
                    key=get_param.transfer_id
                )

        except GeneralException as e:
            print_frame(e)
            ret.code = e.code
            ret.message = e.message

        except Exception as e:
            print_frame(e)
            ret.message = str(e)
            ret.code = 400

        if has_return:
            return str(ret)

        return None

    def put(self, data: Union[str, TransferPutRequest],
            ret: TransferPutResponse=None) -> str:

        put_param: TransferPutRequest = None
        has_return = False

        if ret is None:
            ret = TransferPutResponse()
            has_return = True

        if isinstance(data, TransferPutRequest):
            put_param = data

        try:
            if put_param is None:
                put_param = TransferPutRequest(data)

            status = object_manager.object_by_id(put_param.transfer_id)

            if status is not None:
                state = self._state_manager.state(
                    Status.TransferEnded.code
                )

                context: Context = Context()
                context.attachment = put_param.transfer_id
                context.key = put_param.task_id
                context.data = put_param

                self._state_manager.set(
                    status=status, state=state, context=context
                )

                ret.code = 200
                ret.message = "success"

            else:
                ret.code = 404
                ret.message = "invalid transfer id {key}".format(
                    key=put_param.transfer_id
                )

        except GeneralException as e:
            print_frame(e)
            ret.code = e.code
            ret.message = e.message

        except Exception as e:
            print_frame(e)
            ret.code = 400
            ret.message = str(e)

        if has_return:
            return str(ret)

        return None

    def delete(self, data: Union[str, TransferDeleteRequest],
               ret: TransferDeleteResponse=None) -> str:

        delete_param: TransferDeleteRequest = None
        has_return = False

        if ret is None:
            ret = TransferDeleteResponse()
            has_return = True

        if isinstance(data, TransferDeleteRequest):
            delete_param = data

        try:
            if delete_param is None:
                delete_param = TransferDeleteRequest(data)
                _ = delete_param

            ret.code = 200
            ret.message = "success."

        except GeneralException as e:
            print_frame(e)
            ret.code = e.code
            ret.message = e.message

        except Exception as e:
            print_frame(e)
            ret.code = 400
            ret.message = str(e)

        if has_return:
            return str(ret)

        return None


class TransferWebHandler(tornado.web.RequestHandler):
    def post(self) -> None:
        ret: TransferPostResponse = TransferPostResponse()
        try:
            body: bytes = self.request.body
            post_param = TransferPostRequest(body.decode())
            handler: object = object_manager.find_type(str(TransferHandler))
            assert isinstance(handler, TransferHandler)
            handler.post(post_param, ret)

        except Exception as e:
            print_frame(e)
            ret.code = 400
            ret.message = str(e)

        self.set_status(200)
        self.write(str(ret))

    def get(self, transfer_id: str) -> None:
        ret: TransferGetResponse = TransferGetResponse()
        try:
            get_param: TransferGetRequest = TransferGetRequest()
            get_param.transfer_id = transfer_id
            handler: object = object_manager.find_type(str(TransferHandler))
            assert isinstance(handler, TransferHandler)
            handler.get(get_param, ret)

        except Exception as e:
            print_frame(e)
            ret.code = 400
            ret.message = str(e)

        self.set_status(200)
        self.write(str(ret))

    def put(self, transfer_id: str) -> None:
        ret: TransferPutResponse = TransferPutResponse()
        try:
            put_param: TransferPutRequest = TransferPutRequest()
            put_param.transfer_id = transfer_id
            handler: object = object_manager.find_type(str(TransferHandler))
            assert isinstance(handler, TransferHandler)
            handler.put(put_param, ret)

        except Exception as e:
            print_frame(e)
            ret.code = 400
            ret.message = str(e)

        self.set_status(200)
        self.write(str(ret))

    def delete(self, transfer_id: str) -> None:
        ret: TransferDeleteResponse = TransferDeleteResponse()
        try:
            delete_param: TransferDeleteRequest = TransferDeleteRequest()
            delete_param.transfer_id = transfer_id
            handler: object = object_manager.find_type(str(TransferHandler))
            assert isinstance(handler, TransferHandler)
            handler.delete(delete_param, ret)

        except Exception as e:
            print_frame(e)
            ret.code = 400
            ret.message = str(e)

        self.set_status(200)
        self.write(str(ret))

    def data_received(self, chunk: object) -> Future:
        return super().data_received(chunk)
