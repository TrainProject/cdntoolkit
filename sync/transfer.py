# coding=utf-8

from orderedattrdict import AttrDict
from tornado.options import options
from twisted.internet.defer import Deferred
from twisted.python.failure import Failure

from util.exception import print_frame
from util.message import WampMessage
from util.protocol import \
    TransferGetRequest, TransferGetResponse,\
    TransferPostRequest, TransferPostResponse
from util.state import Activity, Status, Context
from .module import TransactionTransfer


class Transfer(Activity):
    def __init__(self) -> None:
        self._key: str = 24 * '0'
        self._transaction_id: str = 24 * '0'
        self._index: int = -1
        self._application: AttrDict = None
        self._working: TransactionTransfer = None
        self._message: WampMessage = None
        super().__init__()

    @property
    def key(self) -> str:
        if self._key == 24 * '0':
            return str(self.index)
        return self._key

    @key.setter
    def key(self, value: str) -> None:
        self._key = value

    @property
    def transaction_id(self) -> str:
        return self._transaction_id

    @transaction_id.setter
    def transaction_id(self, value: str) -> None:
        self._transaction_id = value

    @property
    def index(self) -> int:
        return self._index

    @index.setter
    def index(self, value: int) -> None:
        self._index = value

    @property
    def message(self) -> WampMessage:
        return self._message

    @message.setter
    def message(self, value: WampMessage) -> None:
        self._message = value

    @property
    def application(self) -> AttrDict:
        return self._application

    @application.setter
    def application(self, value: AttrDict) -> None:
        self._application = value

    @property
    def status(self) -> Status:
        return self._working

    @status.setter
    def status(self, status: Status) -> None:
        assert isinstance(status, TransactionTransfer)
        self._working = status

    @property
    def shard(self) -> int:
        return self._working.shard

    def query(self) -> None:
        get_param: TransferGetRequest = TransferGetRequest()
        get_param.transfer_id = self.key
        print(str(get_param))

        d: Deferred = self.message.session.call(
            options.topic_transfer_get, str(get_param)
        )

        def query_callback(data: str) -> None:
            get_return: TransferGetResponse = TransferGetResponse(data)
            context: Context = Context()
            context.data = get_return
            self.on_query(context)

        d.addCallback(query_callback)

        def st_error(error: Failure) -> None:
            print(error.getErrorMessage())

        d.addErrback(st_error)

    def create(self, context: Context=None) -> bool:
        self._working.code = Status.TransferTaskCreated.code
        self._working.message = Status.TransferTaskCreated.message
        return True

    def start(self, context: Context=None) -> bool:
        print(self.key, self.transaction_id)

        def st_error(error: Failure) -> None:
            print("post_transfer_error:", error.getErrorMessage())
            # reactor.callLater(5, self.start, callback)

        def st_callback(data: str) -> None:
            retry = True
            _context: Context = Context()
            try:
                ret: TransferPostResponse = TransferPostResponse(data)
                if ret is not None:
                    if ret.code == 200:
                        # FIXME!!!!!!!!!! not
                        _context.key = ret.transfer_id
                        print("!!!!!!", _context.key)
                        self.on_start(_context)
                        retry = False
                    else:
                        print("tunnel post error:", ret.code, ret.message)
                else:
                    print("transfer post return value error")
                    _context.key = None
                    self.on_start(_context)

            except Exception as e:
                print_frame(e)

            if retry:
                st_error("retry")

            """
            if ret and ret.status_code == 200:
                # d = json._loads(r.text, object_pairs_hook=AttrDict)
                self.module.update_transfer(
                    transfer._id, d.transfer_id
                )
            """

        post_param: TransferPostRequest = TransferPostRequest()
        post_param.hosts = self._working.hosts
        post_param.retry = self._working.retry
        post_param.timeout = self._working.timeout
        post_param.transaction_id = self.transaction_id
        post_param.application = self.application

        d: Deferred = self.message.session.call(
            options.topic_transfer_post, str(post_param)
        )

        d.addCallback(st_callback)
        d.addErrback(st_error)

        return True

    def end(self, context: Context=None) -> bool:
        pass
