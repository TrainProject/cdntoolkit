# coding=utf-8

from typing import Callable

from orderedattrdict import AttrDict
from twisted.internet.defer import Deferred
from twisted.python.failure import Failure

from util import reactor
from util.message import WampMessage
from util.objects import object_manager
from util.protocol import TaskCommandRequest, TaskCommandResponse, TransferPutRequest
from util.state import Status, Activity, Context, StateManager
from .module import TransferTask, TransferModule


class Task(Activity):
    def __init__(self) -> None:
        self._key: str = 24 * '0'
        self._transfer_id: str = 24 * '0'
        self._index: int = -1
        self._retry: Deferred = None
        self._retry_count: int = 0
        self._duration: int = -1
        self._working: TransferTask = None
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
        if self._key == 24 * '0':
            return str(self._index)
        return self._key

    @key.setter
    def key(self, value: str) -> None:
        self._key = value

    @property
    def transfer_id(self) -> str:
        return self._transfer_id

    @transfer_id.setter
    def transfer_id(self, value: str) -> None:
        self._transfer_id = value

    @property
    def index(self) -> int:
        return self._index

    @index.setter
    def index(self, value: int) -> None:
        self._index = value

    @property
    def status(self) -> Status:
        return self._working

    @status.setter
    def status(self, status: Status) -> None:
        assert isinstance(status, TransferTask)
        self._working = status

    @property
    def module(self) -> TransferModule:
        return self._module

    @module.setter
    def module(self, module: TransferModule) -> None:
        self._module = module

    @property
    def message(self) -> WampMessage:
        return self._message

    @message.setter
    def message(self, message: WampMessage) -> None:
        self._message = message

    def create(self, context: Context=None) -> bool:
        self.module.create_task(self._working)
        self._key = str(self._working.key)
        self.add_slot(Task.on_error, self.error)
        context: Context = Context()
        self.on_create(context)
        return True

    def send(self, context: Context=None) -> bool:
        code = Status.TransferTaskSending.code
        message = Status.TransferTaskSending.message
        self._retry = None

        if self.module.update_task_status(self._working, code, message):
            def sending_callback(ret: str) -> None:
                tcr: TaskCommandResponse = TaskCommandResponse(ret)
                # self.code = tcr.code
                self.duration = tcr.duration
                # self.on_send()
            self.call(sending_callback)

        self._retry_count += 1
        return True

    def recv(self, context: Context=None) -> bool:
        # task = module.query_task_by_id(data._id)

        # task = AttrDict(task)
        if Status.TransferTaskSending.code == self._working.code:
            code = Status.TransferTaskSended.code
            message = Status.TransferTaskSended.message
            self.module.update_task_status(
                self._working, code, message, self._duration
            )
        # FIXME
        # self.on_recv()
        return True

    def end(self, context: Context=None) -> bool:
        assert isinstance(context.data, TransferPutRequest)
        data: TransferPutRequest = context.data
        ret = False

        # task = module.query_task_by_id(data._id)
        # task = module.query_task_by_id(data.transfer_id, data.host)
        # task = AttrDict(task)
        # print(self.working.code, code)
        if (self._working.code <= Status.TransferTaskSended.code and
                data.code >= Status.TransferTaskEnded.code):

            self.module.update_task_status(
                self._working, data.code, data.message, data.duration
            )
            ret = True

        """
        else:
            self.module.update_task_status(
                self.working, code, message, duration
            )
        """

        if self._retry is not None:
            # FIXME !!!!!!!
            #  self._retry.cancel()
            self._retry = None

        return ret

    def call(self, callback: Callable[[str], None]) -> None:
        data = AttrDict()
        data.task_id = self._key
        data.transfer_id = self.transfer_id
        data.application = self._working.application
        data.code = Status.TransferTaskSended.code
        data.timeout = self._working.timeout
        data.retry = self._working.retry
        tcr: TaskCommandRequest = TaskCommandRequest(data)
        # self.send_message(task.host.decode('ascii'), msg)
        session = self.message.session
        ret = session.call(self._working.host, str(tcr))
        ret.addCallback(callback)

        def st_error(error: Failure) -> None:
            print(error.getErrorMessage())
            if self._retry_count < self._working.retry:
                def redo() -> None:
                    _ret = session.call(self._working.host, str(tcr))
                    _ret.addErrback(st_error)
                    _ret.addCallback(callback)
                reactor().callLater(self._working.timeout, redo)
                self._retry_count += 1

            else:
                # FIXME!!!!
                """
                task_state_manager.set(
                    self.working,
                    code=522,
                    message="Call walker timeout",
                    duration=5
                )
                """
                # self.on_error(code=522, message="Call walker timeout", duration=5)

        ret.addErrback(st_error)

    def error(self, context: Context=None) -> None:
        # FIXME
        self._state_manager.set(self._working, context)
