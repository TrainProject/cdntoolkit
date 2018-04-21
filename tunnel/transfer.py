# coding=utf-8

from typing import Dict

from orderedattrdict import AttrDict
from tornado.options import options
from twisted.python.failure import Failure

from util import trace_to_attrdict
from util.message import WampMessage
from util.objects import object_manager
from util.protocol import TransactionPutRequest, TransferPutRequest
from util.state import Status, Activity, Context, StateManager
from .module import TransferModule, TransferWorking, TransferTask
from .task import Task


class Transfer(Activity):
    def __init__(self) -> None:
        self._key: str = 24 * '0'
        self._transaction_id: str = 24 * '0'
        self._tasks: Dict[str, Status] = dict()
        self._task_count: int = 0
        self._finish_count: int = 0
        self._working: TransferWorking = None
        self._module: TransferModule = None
        self._message: WampMessage = None

        task_state_manager: object = object_manager.find_type(
            str(StateManager), 'task'
        )
        assert isinstance(task_state_manager, StateManager)
        self._state_manager: StateManager = task_state_manager

        super().__init__()

    @property
    def key(self) -> str:
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
    def tasks(self) -> Dict[str, Status]:
        return self._tasks

    @property
    def status(self) -> Status:
        return self._working

    @status.setter
    def status(self, status: Status) -> None:
        assert isinstance(status, TransferWorking)
        self._working = status

    @property
    def module(self) -> TransferModule:
        return self._module

    @module.setter
    def module(self, value: TransferModule) -> None:
        self._module = value

    @property
    def message(self) -> WampMessage:
        return self._message

    @message.setter
    def message(self, value: WampMessage) -> None:
        self._message = value

    def query(self) -> None:
        return

    def create(self, context: Context=None) -> bool:
        self.module.create_transfer(self._working)
        self._key = str(self._working.key)
        # self.add_slot(Transfer.on_error, self.error)

        for host in self._working.hosts:
            working: TransferTask = TransferTask()
            working.host = host.pop('host')
            working.hostname = host.pop('hostname')
            working.retry = self._working.retry
            working.timeout = self._working.timeout
            working.transfer_id = self._working.key
            working.application = self._working.application.copy()
            working.application.update(host)

            _context: Context = Context()
            _context.attachment = str(working.transfer_id)
            _context.index = self._task_count

            if self._state_manager.set(status=working, context=_context):
                activity = working.activity
                self._tasks[activity.key] = activity.status
                print(self._tasks)
                self._task_count += 1

            else:
                return False

        return True

    def complete_create(self, task: Task) -> None:
        print(self._tasks, task.key)
        if task.key not in self.tasks:
            del self._tasks[str(task._index)]
            self._tasks[task.key] = task._working

    """
    def complete_task_error(self, context: Context) -> None:
        code = kwargs['code']
        message = kwargs['message']
        duration = kwargs['duration']
        task: Task = self.sender
        self.on_error(task.key, code, message, duration)
    """

    def start(self, contex: Context=None) -> bool:
        for _id, status in self._tasks.items():
            self._state_manager.schedule(status)
            # reactor().callLater(0, task.create)
        return True

    def end(self, context: Context=None) -> bool:
        assert isinstance(context.data, TransferPutRequest)
        data: TransferPutRequest = context.data

        status = self._tasks[data.task_id]

        state = self._state_manager.state(
            Status.TransferTaskEnded.code
        )

        if self._state_manager.set(
            status=status, state=state, context=context
        ):

            self._finish_count += 1

            if self._task_count == self._finish_count:

                def end_callback() -> None:
                    # transfer = module.query_transfer_by_id(self.working._id)
                    # tasks = module.query_task_by_transfer_id(self.working._id)
                    results = list()
                    for _id, _status in self._tasks.items():
                        assert isinstance(_status, TransferTask)
                        working: TransferTask = _status
                        result = AttrDict()
                        # PS:
                        # result.hostname = working.hostname
                        # result.host = working.host
                        result.host = working.hostname
                        result.code = working.code
                        result.message = working.message
                        result.trace = trace_to_attrdict(working.trace)
                        results.append(result)

                    self.module.update_transfer(
                        self._working,
                        Status.TransferEnded.code,
                        Status.TransferEnded.message,
                        results
                    )

                    # self.on_end()

                # reactor().callLater(0, end_callback)
                end_callback()
                return True

        return False

    def finish(self, context: Context=None) -> bool:
        message = self._message
        put_param: TransactionPutRequest = TransactionPutRequest()
        put_param.transfer_id = self._key
        put_param.transaction_id = self.transaction_id
        ret = message.session.call(
            options.topic_transaction_put, str(put_param)
        )

        def finish_callback(data: str) -> None:
            del data
            self.module.update_transfer(
                self._working,
                Status.TransferFinished.code,
                Status.TransferFinished.message,
                None
            )
            # self.on_finish()

        ret.addCallback(finish_callback)

        def st_error(error: Failure) -> None:
            print(error.getErrorMessage())

        ret.addErrback(st_error)
        return True

    def delete(self, context: Context=None) -> bool:
        pass
