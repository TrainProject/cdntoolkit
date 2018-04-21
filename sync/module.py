# coding=utf-8

from datetime import datetime
from typing import List, Dict, Any, no_type_check

from bson.objectid import ObjectId
from orderedattrdict import AttrDict
from pymongo.collection import Collection
from pymongo.database import Database
from pymongo.results import UpdateResult

from util import FrozenClass
from util.state import Status


class TransactionTransfer(Status, FrozenClass):
    def __init__(self) -> None:
        self.__hosts: List[AttrDict] = list()
        self.__retry: int = -1
        self.__timeout: int = -1
        self.__transfer_id: ObjectId = ObjectId(24 * '0')
        self.__shard: int = -1

        Status.__init__(self)
        FrozenClass.__init__(self)

    @property
    def hosts(self) -> List[AttrDict]:
        return self.__hosts

    @hosts.setter
    def hosts(self, value: List[AttrDict]) -> None:
        self.__hosts = value

    @property
    def retry(self) -> int:
        return self.__retry

    @retry.setter
    def retry(self, value: int) -> None:
        self.__retry = value

    @property
    def timeout(self) -> int:
        return self.__timeout

    @timeout.setter
    def timeout(self, value: int) -> None:
        self.__timeout = value

    @property
    def transfer_id(self) -> ObjectId:
        return self.__transfer_id

    @transfer_id.setter
    def transfer_id(self, value: ObjectId) -> None:
        self.__transfer_id = value

    @property
    def shard(self) -> int:
        return self.__shard

    @shard.setter
    def shard(self, value: int) -> None:
        self.__shard = value


class TransactionWorking(Status, FrozenClass):
    def __init__(self) -> None:
        self.___id: ObjectId = ObjectId(24 * '0')
        self.__create_time: datetime = datetime.utcfromtimestamp(0)
        self.__last_time: datetime = datetime.utcfromtimestamp(0)
        self.__retry: int = -1
        self.__timeout: int = -1
        self.__dst: object = None
        self.__application: AttrDict = AttrDict()
        self.__transfers: Dict[str, TransactionTransfer] = dict()

        Status.__init__(self)
        FrozenClass.__init__(self)

    @no_type_check
    def __eq__(self, *args, **kwargs) -> bool:
        other: TransactionWorking = args[0]
        return (
            self.__dst == other.dst and
            self.__application == other.application and
            self.__retry == other.retry and
            self.__timeout == other.timeout
        )

    @property
    def key(self) -> ObjectId:
        return self.___id

    @key.setter
    def key(self, value: ObjectId) -> None:
        self.___id = value

    @property
    def create_time(self) -> datetime:
        return self.__create_time

    @create_time.setter
    def create_time(self, value: datetime) -> None:
        self.__create_time = value

    @property
    def last_time(self) -> datetime:
        return self.__last_time

    @last_time.setter
    def last_time(self, value: datetime) -> None:
        self.__last_time = value

    @property
    def retry(self) -> int:
        return self.__retry

    @retry.setter
    def retry(self, value: int) -> None:
        self.__retry = value

    @property
    def timeout(self) -> int:
        return self.__timeout

    @timeout.setter
    def timeout(self, value: int) -> None:
        self.__timeout = value

    @property
    def dst(self) -> object:
        return self.__dst

    @dst.setter
    def dst(self, value: object) -> None:
        self.__dst = value

    @property
    def application(self) -> AttrDict:
        return self.__application

    @application.setter
    def application(self, value: AttrDict) -> None:
        self.__application = value

    @property
    def transfers(self) -> Dict[str, TransactionTransfer]:
        return self.__transfers

    @transfers.setter
    def transfers(self, value: Dict[str, TransactionTransfer]) -> None:
        self.__transfers = value


class TransactionModule:
    def __init__(self) -> None:
        self._database: Database = None
        self._transaction_working: Collection = None

    @property
    def database(self) -> Database:
        return self._database

    @database.setter
    def database(self, value: Database) -> None:
        self._database = value
        self._transaction_working = value.TransactionWorking

    def create_transaction(self, transaction: TransactionWorking) -> None:
        query = AttrDict()
        query.application = transaction.application

        transaction.create_time = datetime.utcnow()
        transaction.last_time = transaction.create_time
        transaction.code = Status.TransactionCreated.code
        transaction.message = Status.TransactionCreated.message

        update = AttrDict()
        insert = AttrDict(transaction)
        del insert._id
        update["$setOnInsert"] = insert

        created_transaction = self._transaction_working.find_and_modify(
            query=query, update=update, new=True, upsert=True
        )

        # result = self.db.TransactionWorking.update_one(query, update, True)
        # result = self.db.TranscationWorking.find_one(query)
        # self.create_transfer(transaction)

        if created_transaction is not None:
            transaction.key = created_transaction["_id"]
        else:
            raise Exception("upsert transaction error")

    def update_transfer_id(self, working: TransactionTransfer,
                           transaction_id: ObjectId,
                           transfer_id: ObjectId) -> bool:
        query = AttrDict()
        query._id = transaction_id
        query['transfers.hosts'] = working.hosts

        update_transfer = AttrDict()
        update_transfer['transfers.$.transfer_id'] = transfer_id

        update = AttrDict()
        update['$set'] = update_transfer
        print("###########", query, working.hosts, update_transfer)

        result: UpdateResult = self._transaction_working.update_one(
            query, update, False
        )

        return result.modified_count == 1

    def update_transfer_status(self, working: TransactionWorking,
                               transfer_id: ObjectId,
                               status: AttrDict) -> bool:
        query = AttrDict()
        query._id = working.key
        query['transfers.transfer_id'] = transfer_id

        update_transfer = AttrDict()
        update_transfer['transfers.$.code'] = status.code
        update_transfer['transfers.$.message'] = status.message

        update = AttrDict()
        update['$set'] = update_transfer

        result: UpdateResult = self._transaction_working.update_one(
            query, update, False
        )

        ret = result.modified_count == 1
        if ret:
            for _id, transfer in working.transfers.items():
                if transfer.transfer_id == transfer_id:
                    transfer.code = status.code
                    transfer.message = status.message
                    break
            return True

        return False

    def update_transaction_status(self, working: TransactionWorking,
                                  status: AttrDict) -> bool:
        query = AttrDict()
        query._id = working.key

        update_transaction = AttrDict()
        update_transaction.code = status.code
        update_transaction.message = status.message

        update = AttrDict()
        update['$set'] = update_transaction

        result: UpdateResult = self._transaction_working.update_one(
            query, update, False
        )

        ret = result.modified_count == 1
        if ret:
            working.code = status.code
            working.message = status.message
            return True

        return False

    def query_transfer_by_code(self, code: int) -> Any:
        query = AttrDict()
        query.code = code
        result = self._transaction_working.find(query)
        # .limit(128)
        return result

    def query_transaction_by_code(self, code: int) -> Any:
        query = AttrDict()
        query.code = code
        result = self._transaction_working.find(query)
        return result

    def update_transfer(self, _id: str, transfer_id: str) -> None:
        query = AttrDict()
        query._id = _id

        tid = AttrDict()
        tid.transfer_id = transfer_id

        update = AttrDict()
        update["$set"] = tid

        self._transaction_working.update_one(
            query, update, False
        )

    def update_trace(self, data: Any) -> None:
        self._transaction_working.update(data)

    def query_finish(self) -> None:
        pass

    def query_transfer(self) -> None:
        pass
