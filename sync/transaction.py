# coding=utf-8

from typing import List, Dict, Any

import treq
from bson.objectid import ObjectId
from tornado.options import options
from treq.response import _Response
from twisted.internet.defer import Deferred
from twisted.python.failure import Failure

from util.config import config_manager
from util.exception import print_frame
from util.objects import object_manager
from util.protocol import \
    TransferGetResponse, TransactionGetResponse
from util.state import Status, Activity, Context, StateManager
from .module import TransactionModule
from .module import TransactionWorking, TransactionTransfer
from .transfer import Transfer


class Transaction(Activity):
    def __init__(self) -> None:
        self._key: str = 24 * '0'
        self._transfer_count: int = 0
        self._finished_count: int = 0
        self._query_response: List[TransferGetResponse] = list()
        self._working: TransactionWorking = None
        self._module: TransactionModule = None

        transfer_state_manager: object = object_manager.find_type(
            str(StateManager), 'transfer'
        )
        assert isinstance(transfer_state_manager, StateManager)
        self._state_manager: StateManager = transfer_state_manager

        super().__init__()

    @property
    def key(self) -> str:
        return self._key

    @key.setter
    def key(self, value: str) -> None:
        self._key = value

    @property
    def module(self) -> TransactionModule:
        return self._module

    @module.setter
    def module(self, value: TransactionModule) -> None:
        self._module = value

    @property
    def status(self) -> Status:
        return self._working

    @status.setter
    def status(self, status: Status) -> None:
        assert isinstance(status, TransactionWorking)
        self._working = status

    def query(self) -> None:
        for _id, working in self._working.transfers.items():
            assert isinstance(working.activity, Transfer)
            transfer: Transfer = working.activity
            transfer.add_slot(
                Transfer.on_query, self.complete_query
            )
            transfer.query()

    def dispatch(self) -> None:
        dst = self._working.dst
        transfers: Dict[str, TransactionTransfer] = self._working.transfers

        if isinstance(dst, str):
            hosts = config_manager.query_by_where(dst)
        elif isinstance(dst, list):
            hosts = config_manager.query_by_dst(dst)
        else:
            return

        transfer_shard: Dict[int, TransactionTransfer] = dict()

        for host in hosts:
            uuid = host.host
            shard = int(uuid.split("-")[0][7], 16)
            transfer: TransactionTransfer = transfer_shard.get(shard)

            if transfer is None:
                transfer = TransactionTransfer()
                transfer.retry = self._working.retry
                transfer.timeout = self._working.timeout
                transfer.shard = shard
                transfer_shard[shard] = transfer
                transfers[str(self._transfer_count)] = transfer
                self._transfer_count += 1

            transfer.hosts.append(host)

            if len(transfer.hosts) == 128:
                del transfer_shard[shard]

    def create(self, context: Context=None) -> bool:
        self.dispatch()
        self.module.create_transaction(self._working)
        self.key = str(self._working.key)

        context: Context = Context()
        context.attachment = self.key
        context.data = self._working.application

        for _id, working in self._working.transfers.items():
            context.index = int(_id)
            self._state_manager.set(working, context=context)
            """
            transfer_state_manager.set(
                working, index=_id, transaction_id=str(self._working.key),
                application=self._working.application,
                message=self.messages[working.shard]
            )
            """

        return True

    def start(self, context: Context=None) -> bool:
        shard = context.index
        if shard == -1:
            batch = set(range(16))
        else:
            batch = {shard}

        for key, working in self._working.transfers.items():
            if len(key) != 24:
                shard = working.shard
                if shard in batch:
                    batch.remove(shard)
                    self._state_manager.schedule(working)
                    # transfer.start()
                    # print("transfer start:", transfer.index, shard)
                    if not batch:
                        break

        return True

    def complete_start(self, transfer_id: str, transfer: Transfer) -> bool:
        if (transfer_id is not None and
                transfer_id not in self._working.transfers):

            assert isinstance(transfer.status, TransactionTransfer)
            working: TransactionTransfer = transfer.status

            ret = self.module.update_transfer_id(
                working, self._working.key,
                ObjectId(transfer_id)
            )
            if ret:
                working.transfer_id = ObjectId(transfer_id)
                transfer.key = transfer_id
                del self._working.transfers[str(transfer.index)]
                self._working.transfers[transfer.key] = working

                print("finish transfer:", transfer.index, working.shard)

            else:
                print("db post error: ", transfer_id)
        else:
            print("post retry")

        # reactor().callLater(0, self.start_transfer, transfer.working.shard)
        return True

    def complete_query(self, context: Context=None) -> None:
        assert isinstance(context.data, TransferGetResponse)
        data: TransferGetResponse = context.data
        self._query_response.append(data)

        if len(self._query_response) == self._transfer_count:
            get_return = TransactionGetResponse()
            get_return.transaction_id = self.key
            get_return.create_time = self._working.create_time
            get_return.last_time = self._working.last_time
            # get_return.dst = transaction.working.dst
            get_return.application = self._working.application
            get_return.transfers = self._query_response
            get_return.code = self._working.code
            get_return.message = self._working.message

            context.data = get_return
            self.on_query(context)
            self._query_response: List[TransferGetResponse] = list()

    def end(self, context: Context=None) -> bool:
        # FIXME
        # complete end transfer

        transfer_id: str = context.key
        working: TransactionTransfer = self._working.transfers[transfer_id]
        working.activity.end()

        ret = self.module.update_transfer_status(
            self._working, working.transfer_id, Status.TransferFinished
        )

        if ret:
            print(self._finished_count, self._transfer_count, "end transfer")
            self._finished_count += 1
            if self._finished_count == self._transfer_count:
                return True
        return False

    def finish(self, context: Context=None) -> bool:
        return self.module.update_transaction_status(
            self._working, Status.TransactionFinished
        )

    def archive(self, context: Context=None) -> bool:
        d: Deferred = treq.get(
            "http://{address}:{port}/sync/transaction/{key}".format(
                address=options.sync_address, port=options.sync_port, key=self.key
            ),
            timeout=30
        )
        d.addCallback(self.complete_header)
        d.addErrback(self.print_error)

        # for debug cdb data
        # print_frame()
        # reactor().callLater(300, self.load)
        return True

    def complete(self, context: Context=None) -> None:
        pass
        # transaction_state_manager.schedule(self.working)

    def print_error(self, error: Failure) -> None:
        print(error.getErrorMessage())
        # FIXME
        # self.on_archive()

    def complete_header(self, r: _Response) -> None:
        if r is not None and r.code == 200:
            content: Deferred = r.content()
            content.addCallback(self.complete_body)
            content.addErrback(self.print_error)

    def complete_body(self, data: bytes) -> None:
        try:
            d: Deferred = treq.post(
                self._working.application.notify,
                data=data,
                headers={b'Content-Type': [b'application/json']}
            )
            d.addCallback(self.post_result)
            d.addErrback(self.print_error)
        except Exception as e:
            print_frame(e)

    def post_result(self, r: _Response) -> None:
        pass
        # FIXME
        # self.on_archive()
