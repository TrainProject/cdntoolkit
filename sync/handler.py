# coding=utf-8

from typing import Union, List, Callable, Dict

import tornado.web
from tornado.concurrent import Future

from util import GeneralException
from util.exception import print_frame
from util.objects import object_manager
from util.observer import Observer
from util.protocol import \
    TransactionPostRequest, TransactionPostResponse,\
    TransactionGetRequest, TransactionGetResponse,\
    TransactionPutRequest, TransactionPutResponse,\
    TransactionDeleteRequest, TransactionDeleteResponse
from util.state import Status, Activity, Context, StateManager
from .module import TransactionWorking


class TransactionHandler(Observer):
    def __init__(self) -> None:
        self._query_requests: Dict[
            str, List[
                Callable[[TransactionGetResponse], None]
            ]
        ] = dict()

        transaction_state_manager: object = object_manager.find_type(
            str(StateManager), 'transaction'
        )
        assert isinstance(transaction_state_manager, StateManager)
        self._state_manager: StateManager = transaction_state_manager

        super().__init__()

    def post(self, data: Union[str, TransactionPostRequest],
             ret: TransactionPostResponse=None) -> str:

        post_param: TransactionPostRequest = None
        has_return = False

        if ret is None:
            ret = TransactionPostResponse()
            has_return = True

        if isinstance(data, TransactionPostRequest):
            post_param = data

        try:
            if post_param is None:
                post_param = TransactionPostRequest(data)

            working: TransactionWorking = TransactionWorking()
            working.dst = post_param.dst
            working.retry = post_param.retry
            working.timeout = post_param.timeout
            working.application = post_param.application

            status = object_manager.find_object(working)
            if status is None:
                if self._state_manager.set(status=working):
                    activity = working.activity
                    object_manager.add_object(
                        activity.key, activity.status
                    )

                else:
                    raise GeneralException(
                        500, "create transaction error"
                    )

            else:
                activity = status.activity

            ret.transaction_id = activity.key
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

    def complete(self, context: Context) -> None:
        # FIXME timeout transaction deleted
        assert isinstance(self.sender, Activity)
        activity: Activity = self.sender

        assert isinstance(context.data, TransactionGetResponse)
        data: TransactionGetResponse = context.data

        key: str = activity.key
        completes = self._query_requests.get(key)
        if completes:
            for complete_request in completes:
                complete_request(data)
            self._query_requests[key].clear()

    def get(self, data: Union[str, TransactionGetRequest],
            ret: TransactionGetResponse=None,
            complete_request: Callable[[TransactionGetResponse], None]=None
            ) -> str:

        get_param: TransactionGetRequest = None
        has_return = False

        if ret is None:
            ret = TransactionGetResponse()
            has_return = True

        if isinstance(data, TransactionGetRequest):
            get_param = data

        try:
            if get_param is None:
                get_param = TransactionGetRequest(data)

            if complete_request is None:
                # FIXME!
                # WAMP request is None, HTTP request give complete_request
                pass

            status = object_manager.object_by_id(
                get_param.transaction_id
            )

            if status is not None:
                key: str = status.activity.key

                if key not in self._query_requests:
                    status.activity.add_slot(
                        Activity.on_query, self.complete
                    )
                    status.activity.query()
                    self._query_requests[key] = list()

                self._query_requests[key].append(complete_request)

                ret.code = -1

            else:
                ret.code = 404
                ret.message = "invalid transaction id {key}".format(
                    key=get_param.transaction_id
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

    def put(self, data: Union[str, TransactionPutRequest],
            ret: TransactionPutResponse=None) -> str:

        put_param: TransactionPutRequest = None
        has_return = False

        if ret is None:
            ret = TransactionPutResponse()
            has_return = True

        if isinstance(data, TransactionPutRequest):
            put_param = data

        try:
            if put_param is None:
                put_param = TransactionPutRequest(data)

            status = object_manager.object_by_id(put_param.transaction_id)

            if status is not None:
                state = self._state_manager.state(
                    Status.TransactionEnded.code
                )

                context = Context()
                context.key = put_param.transfer_id
                context.data = put_param

                self._state_manager.set(
                    status=status, state=state, context=context
                )

                ret.code = 200
                ret.message = "success"

            else:
                ret.code = 404
                ret.message = "invalid transacion id {key}".format(
                    key=put_param.transaction_id
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

    def delete(self, data: Union[str, TransactionDeleteRequest],
               ret: TransactionDeleteResponse=None) -> str:

        delete_param: TransactionDeleteRequest = None
        has_return = False

        if ret is None:
            ret = TransactionDeleteResponse()
            has_return = True

        if isinstance(data, TransactionDeleteRequest):
            delete_param = data

        try:
            if delete_param is None:
                delete_param = TransactionDeleteRequest(data)
                _ = delete_param
            # print(self, delete_param)
            ret.code = 400
            ret.message = "unsupport"

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


class TransactionWebHandler(tornado.web.RequestHandler):
    def post(self) -> None:
        ret: TransactionPostResponse = TransactionPostResponse()
        try:
            body: bytes = self.request.body
            post_param: TransactionPostRequest = (
                TransactionPostRequest(body.decode())
            )
            handler: object = object_manager.find_type(str(TransactionHandler))
            assert isinstance(handler, TransactionHandler)
            handler.post(post_param, ret)

        except Exception as e:
            print_frame(e)
            ret.code = 400
            ret.message = str(e)

        self.set_status(200)
        self.write(str(ret))

    @tornado.web.asynchronous
    def get(self, transaction_id: str) -> None:
        ret: TransactionGetResponse = TransactionGetResponse()
        try:
            get_param: TransactionGetRequest = TransactionGetRequest()
            get_param.transaction_id = transaction_id

            def complete_request(data: TransactionGetResponse) -> None:
                self.set_status(200)
                self.write(str(data))
                self.finish()

            handler: object = object_manager.find_type(str(TransactionHandler))
            assert isinstance(handler, TransactionHandler)
            handler.get(get_param, ret, complete_request)

        except Exception as e:
            print_frame(e)
            ret.code = 400
            ret.message = str(e)

        if ret.code != -1:
            self.set_status(200)
            self.write(str(ret))
            self.finish()

    def put(self, transaction_id: str, transfer_id: str) -> None:
        ret: TransactionPutResponse = TransactionPutResponse()
        try:
            put_param: TransactionPutRequest = TransactionPutRequest()
            put_param.transaction_id = transaction_id
            put_param.transfer_id = transfer_id
            handler: object = object_manager.find_type(str(TransactionHandler))
            assert isinstance(handler, TransactionHandler)
            handler.put(put_param, ret)

        except Exception as e:
            print_frame(e)
            ret.code = 400
            ret.message = str(e)

        self.set_status(200)
        self.write(str(ret))

    def delete(self, transaction_id: str) -> None:
        ret: TransactionDeleteResponse = TransactionDeleteResponse()
        try:
            delete_param: TransactionDeleteRequest = TransactionDeleteRequest()
            delete_param.transaction_id = transaction_id
            handler: object = object_manager.find_type(str(TransactionHandler))
            assert isinstance(handler, TransactionHandler)
            handler.delete(delete_param, ret)

        except Exception as e:
            print_frame(e)
            ret.code = 400
            ret.message = str(e)

        self.set_status(200)
        self.write(str(ret))

    def data_received(self, chunk: object) -> Future:
        return super().data_received(chunk)
