# coding=utf-8

from datetime import datetime
from typing import List, Any, no_type_check

from bson.objectid import ObjectId
from orderedattrdict import AttrDict
from pymongo.collection import Collection
from pymongo.database import Database
from pymongo.results import UpdateResult

from util import FrozenClass, trace_to_attrdict
from util.state import Status


class TaskTrace(FrozenClass):
    def __init__(self) -> None:
        self.__code: int = -1
        self.__start_time: datetime = datetime.utcfromtimestamp(0)
        self.__end_time: datetime = datetime.utcfromtimestamp(0)
        self.__duration: int = -1
        super().__init__()

    @property
    def code(self) -> int:
        return self.__code

    @code.setter
    def code(self, value: int) -> None:
        self.__code = value

    @property
    def start_time(self) -> datetime:
        return self.__start_time

    @start_time.setter
    def start_time(self, value: datetime) -> None:
        self.__start_time = value

    @property
    def end_time(self) -> datetime:
        return self.__end_time

    @end_time.setter
    def end_time(self, value: datetime) -> None:
        self.__end_time = value

    @property
    def duration(self) -> int:
        return self.__duration

    @duration.setter
    def duration(self, value: int) -> None:
        self.__duration = value


class TransferResult(FrozenClass):
    def __init__(self) -> None:
        self.__host: str = str()
        self.__trace: List[TaskTrace] = list()
        self.__code: int = -1
        self.__message: str = str()
        super().__init__()

    @property
    def host(self) -> str:
        return self.__host

    @property
    def trace(self) -> List[TaskTrace]:
        return self.__trace

    @property
    def code(self) -> int:
        return self.__code

    @property
    def message(self) -> str:
        return self.__message


class TransferTask(Status, FrozenClass):
    def __init__(self) -> None:
        # FIXME _id is id why?
        self.___id: ObjectId = ObjectId(24 * '0')
        self.__transfer_id: ObjectId = ObjectId(24 * '0')
        self.__timeout: int = -1
        self.__retry: int = -1
        self.__host: str = str()
        self.__hostname: str = str()
        self.__application: AttrDict = AttrDict()
        self.__timestamp: datetime = datetime.utcfromtimestamp(0)
        self.__duration: int = -1
        self.__trace: List[TaskTrace] = list()

        Status.__init__(self)
        FrozenClass.__init__(self)

    @property
    def key(self) -> ObjectId:
        return self.___id

    @key.setter
    def key(self, value: ObjectId) -> None:
        self.___id = value

    @property
    def transfer_id(self) -> ObjectId:
        return self.__transfer_id

    @transfer_id.setter
    def transfer_id(self, value: ObjectId) -> None:
        self.__transfer_id = value

    @property
    def timeout(self) -> int:
        return self.__timeout

    @timeout.setter
    def timeout(self, value: int) -> None:
        self.__timeout = value

    @property
    def retry(self) -> int:
        return self.__retry

    @retry.setter
    def retry(self, value: int) -> None:
        self.__retry = value

    @property
    def host(self) -> str:
        return self.__host

    @host.setter
    def host(self, value: str) -> None:
        self.__host = value

    @property
    def hostname(self) -> str:
        return self.__hostname

    @hostname.setter
    def hostname(self, value: str) -> None:
        self.__hostname = value

    @property
    def application(self) -> AttrDict:
        return self.__application

    @application.setter
    def application(self, value: AttrDict) -> None:
        self.__application = value

    @property
    def timestamp(self) -> datetime:
        return self.__timestamp

    @timestamp.setter
    def timestamp(self, value: datetime) -> None:
        self.__timestamp = value

    @property
    def duration(self) -> int:
        return self.__duration

    @duration.setter
    def duration(self, value: int) -> None:
        self.__duration = value

    @property
    def trace(self) -> List[TaskTrace]:
        return self.__trace

    @trace.setter
    def trace(self, value: List[TaskTrace]) -> None:
        self.__trace = value


class TransferWorking(Status, FrozenClass):
    def __init__(self) -> None:
        self.___id: ObjectId = ObjectId(24 * '0')
        self.__transaction_id: ObjectId = ObjectId(24 * '0')
        self.__timeout: int = -1
        self.__retry: int = -1
        self.__hosts: List[AttrDict] = list()
        self.__application: AttrDict = AttrDict()
        self.__create_time: datetime = datetime.utcfromtimestamp(0)
        self.__last_time: datetime = datetime.utcfromtimestamp(0)
        self.__results: List[TransferResult] = list()

        Status.__init__(self)
        FrozenClass.__init__(self)

    @no_type_check
    def __eq__(self, *args, **kwargs) -> bool:
        other: TransferWorking = args[0]
        return (
            self.__transaction_id == other.transaction_id and
            self.__hosts == other.hosts and
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
    def transaction_id(self) -> ObjectId:
        return self.__transaction_id

    @transaction_id.setter
    def transaction_id(self, value: ObjectId) -> None:
        self.__transaction_id = value

    @property
    def timeout(self) -> int:
        return self.__timeout

    @timeout.setter
    def timeout(self, value: int) -> None:
        self.__timeout = value

    @property
    def retry(self) -> int:
        return self.__retry

    @retry.setter
    def retry(self, value: int) -> None:
        self.__retry = value

    @property
    def hosts(self) -> List[AttrDict]:
        return self.__hosts

    @hosts.setter
    def hosts(self, value: List[AttrDict]) -> None:
        self.__hosts = value

    @property
    def application(self) -> AttrDict:
        return self.__application

    @application.setter
    def application(self, value: AttrDict) -> None:
        self.__application = value

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
    def results(self) -> List[TransferResult]:
        return self.__results

    @results.setter
    def results(self, value: List[TransferResult]) -> None:
        self.__results = value


class TransferModule:
    def __init__(self) -> None:
        self._database: Database = None
        self._transfer_task: Collection = None
        self._transfer_working: Collection = None

    @property
    def database(self) -> Database:
        return self._database

    @database.setter
    def database(self, value: Database) -> None:
        self._database = value
        self._transfer_task = value.TransferTask
        self._transfer_working = value.TransferWorking

    def check_task(self) -> None:
        pass

    def create_task(self, task: TransferTask) -> TransferTask:
        query = AttrDict()
        query.host = task.host
        query.application = task.application

        task.code = Status.TransferTaskCreated.code
        task.message = Status.TransferTaskCreated.message
        task.timestamp = datetime.utcnow()

        update = AttrDict()
        insert = AttrDict(task)
        del insert._id

        update["$setOnInsert"] = insert

        created_task = self._transfer_task.find_one_and_update(
            query, update, new=True, upsert=True
        )

        if created_task is not None:
            task.key = created_task["_id"]
        return task

    def create_transfer(self, transfer: TransferWorking) -> TransferWorking:
        transfer.create_time = datetime.utcnow()
        transfer.last_time = transfer.create_time
        transfer.code = Status.TransferCreated.code
        transfer.message = Status.TransferCreated.message

        query = AttrDict()
        query.transaction_id = transfer.transaction_id
        query.hosts = transfer.hosts

        update = AttrDict()
        insert = AttrDict(transfer)
        del insert._id

        update["$setOnInsert"] = insert

        created_transfer = self._transfer_working.find_one_and_update(
            query, update, new=True, upsert=True
        )

        # json_transfer: str = AttrJson.dumps(transfer)
        # transfer: AttrDict = AttrJson.loads(json_transfer)
        if created_transfer is not None:
            transfer.key = created_transfer["_id"]
        return transfer
        # self.create_task(transfer)
        # return str(transfer._id)

    def query_task_by_id(self, _id: Any) -> Any:
        query = AttrDict()
        query._id = _id
        result = self._transfer_task.find_one(query)
        return result

    def query_task_by_transfer_id(self, transfer_id: ObjectId) -> Any:
        query = AttrDict()
        query.transfer_id = transfer_id
        result = self._transfer_task.find_one(query)
        return result

    def query_task_by_code(self, code: int) -> Any:
        query = AttrDict()
        if code == Status.TransferTaskEnded.code:
            query.code = AttrDict()
            query.code["$gte"] = code
        else:
            query.code = code
        result = self._transfer_task.find(query)
        # .limit(128)
        return result

    def query_transfer_by_code(self, code: Any) -> Any:
        query = AttrDict()
        query.code = code
        result = self._transfer_working.find(query)
        return result

    def is_task_end(self, _id: str) -> bool:
        query = AttrDict()
        query.transfer_id = _id
        query.code = AttrDict()
        query.code["$lt"] = Status.TransferTaskEnded.code

        return self._transfer_task.find_one(query).count() == 0

    def update_task(self, task: Any) -> None:
        pass

    def end_task(self, _id: Any) -> bool:
        query = AttrDict()
        query._id = _id

        transfer = AttrDict()
        transfer.code = Status.TransferEnded.code

        update = AttrDict()
        update["$set"] = transfer

        result = self._transfer_task.update_one(query, update)
        return result.modified_count == 1

    def update_transfer(self, working: TransferWorking,
                        code: int, message: str,
                        results: AttrDict) -> bool:
        # FIXME update timestamp
        query = AttrDict()
        query._id = working.key

        transfer = AttrDict()
        transfer.code = code
        transfer.message = message
        if results is not None:
            transfer.results = results

        update = AttrDict()
        update["$set"] = transfer

        result = self._transfer_working.update_one(query, update)
        ret = result.modified_count == 1
        if ret:
            working.code = code
            working.message = message
            if results is not None:
                working.results = results
            return True

        return False

    def update_task_status(self, task: TransferTask,
                           code: int, message: str,
                           duration: int=0) -> bool:
        print(code, message, duration, "update task status")
        query = AttrDict()
        query._id = task.key

        now = datetime.utcnow()
        if duration == 0:
            duration = (now - task.timestamp).seconds

        trace = task.trace.copy()

        find = False
        for item in trace:
            if item.code == code:
                item.code = task.code
                item.start_time = task.timestamp
                item.end_time = now
                item.duration = duration
                find = True
                break

        if not find:
            # trace_item = AttrDict()
            trace_item = TaskTrace()
            trace_item.code = task.code
            trace_item.start_time = task.timestamp
            trace_item.end_time = now
            trace_item.duration = duration
            trace.append(trace_item)

        _task = AttrDict()
        _task.code = code
        _task.message = message
        _task.duration = duration
        _task.timestamp = now
        _task.trace = trace_to_attrdict(trace)

        update = AttrDict()
        update["$set"] = _task

        result: UpdateResult = self._transfer_task.update_one(query, update)

        ret = result.modified_count == 1
        if ret:
            task.code = code
            task.message = message
            task.duration = duration
            task.timestamp = now
            task.trace = trace
            return True

        return False
