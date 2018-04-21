# coding=utf-8

from typing import List, Tuple

from util import reactor
from util.message import WampMessage
from util.objects import object_manager
from util.protocol import TransferPutRequest
from util.state import State, Status, StateManager, Activity, Context


class TaskCreatedState(State):
    def __init__(self, manager: StateManager) -> None:
        self.manager: StateManager = manager

        message: object = object_manager.find_type(str(WampMessage))
        assert isinstance(message, WampMessage)
        self._message = message

        from .module import TransferModule
        module: object = object_manager.find_type(str(TransferModule))
        assert isinstance(module, TransferModule)
        self._module = module

        super().__init__()

    def set(self, status: Status, context: Context=None) -> bool:
        from .task import Task
        task: Task = Task()
        task.index = context.index
        task.transfer_id = context.attachment
        task.status = status
        task.message = self._message
        task.module = self._module

        task.add_slot(Activity.on_create, self.complete)
        reactor().callLater(0, self._set, status)

        # task.add_slot(Task.on_create, self.complete_task_create)
        # task.add_slot(Task.on_error, self.complete_task_error)

        status.activity = task
        status.state = self
        return True

    def _set(self, status: Status) -> None:
        status.activity.create()
        # self.schedule(status)

    def schedule(self, status: Status) -> None:
        reactor().callLater(0, self.__start, status)

    def __start(self, status: Status) -> None:
        state = self.manager.state(Status.TransferTaskSending.code)
        state.set(status)


class TaskSendingState(State):
    def __init__(self, manager: StateManager) -> None:
        self.manager: StateManager = manager
        super().__init__()

    def set(self, status: Status, context: Context=None) -> bool:
        """
        activity.retry = reactor().callLater(
            5, self.__sending, status
        )
        """
        status.state = self
        ret = status.activity.send()
        if ret:
            self.schedule(status)
        return ret

    def __sending(self, status: Status) -> None:
        state = self.manager.state(Status.TransferTaskSending.code)
        state.set(status)

    """
    def schedule(self, status: Status):
        reactor().callLater(0, self.__sended, status)

    def __sended(self, status: Status):
        state = self.manager.state(Status.TransferTaskEnded.code)
        state.set(status)
    """

    def schedule(self, status: Status) -> None:
        pass


class TaskSendedState(State):
    def __init__(self, manager: StateManager) -> None:
        self.manager: StateManager = manager
        super().__init__()

    def set(self, status: Status, context: Context=None) -> bool:
        status.state = self
        # self.schedule(status)
        return status.activity.recv()

    def schedule(self, status: Status) -> None:
        reactor().callLater(600, self.__end, status)

    def __end(self, status: Status) -> None:
        state = self.manager.state(Status.TransferTaskEnded.code)
        put_param = TransferPutRequest()
        put_param.code = 522
        put_param.message = "Timeout"
        put_param.duration = 15
        context: Context = Context()
        context.data = put_param
        state.set(status, context)


class TaskEndedState(State):
    def __init__(self, manager: StateManager) -> None:
        self.manager: StateManager = manager
        super().__init__()

    def set(self, status: Status, context: Context=None) -> bool:
        status.state = self
        return status.activity.end(context)

    def schedule(self, status: Status) -> None:
        pass


class TransferCreatedState(State):
    def __init__(self, manager: StateManager) -> None:
        self.manager: StateManager = manager

        from .module import TransferModule
        module: object = object_manager.find_type(str(TransferModule))
        assert isinstance(module, TransferModule)
        self._module = module

        message: object = object_manager.find_type(str(WampMessage))
        assert isinstance(message, WampMessage)
        self._message = message

        super().__init__()

    def set(self, status: Status, context: Context=None) -> bool:
        # FIXME
        # exception, retry

        from .transfer import Transfer
        transfer: Transfer = Transfer()
        transfer.transaction_id = context.attachment
        transfer.status = status
        transfer.module = self._module
        transfer.message = self._message

        status.activity = transfer
        status.state = self

        ret = status.activity.create()
        if ret:
            self.schedule(status)
        return ret

    def schedule(self, status: Status) -> None:
        reactor().callLater(0, self.__start, status)

    def __start(self, status: Status) -> None:
        state = self.manager.state(Status.TransferStarted.code)
        state.set(status)

    def complete(self, context: Context) -> None:
        from .task import Task
        assert isinstance(context.sender, Task)
        task: Task = context.sender

        status = object_manager.object_by_id(task.transfer_id)
        if status is None:
            return

        from .transfer import Transfer
        assert isinstance(status.activity, Transfer)
        transfer: Transfer = status.activity
        transfer.complete_create(task)


class TransferStartedState(State):
    def __init__(self, manager: StateManager) -> None:
        self.manager: StateManager = manager
        super().__init__()

    def set(self, status: Status, context: Context=None) -> bool:
        status.state = self
        self.schedule(status)
        return status.activity.start()

    def schedule(self, status: Status) -> None:
        reactor().callLater(600, self.__end, status)

    def __end(self, status: Status) -> None:
        state = self.manager.state(Status.TransferEnded.code)
        from .transfer import Transfer
        transfer: Transfer = None
        if isinstance(status.activity, Transfer):
            transfer = status.activity

        for _id, task in transfer.tasks.items():
            print("end by transfer", _id)
            put_param: TransferPutRequest = TransferPutRequest()
            put_param.code = 522
            put_param.message = "Timeout"
            put_param.duration = 15
            put_param.task_id = _id
            put_param.transfer_id = transfer.key

            context: Context = Context()
            context.attachment = transfer.key
            context.key = _id
            context.data = put_param

            state.set(status, context)


class TransferEndedState(State):
    def __init__(self, manager: StateManager) -> None:
        self.manager: StateManager = manager
        super().__init__()

    def set(self, status: Status, context: Context=None) -> bool:
        status.state = self
        ret = status.activity.end(context)
        if ret:
            self.schedule(status)
        return ret

    def schedule(self, status: Status) -> None:
        reactor().callLater(0, self.__finish, status)

    def __finish(self, status: Status) -> None:
        state = self.manager.state(Status.TransferFinished.code)
        state.set(status)


class TransferFinishedState(State):
    def __init__(self, manager: StateManager) -> None:
        self.manager: StateManager = manager
        super().__init__()

    def set(self, status: Status, context: Context=None) -> bool:
        status.state = self
        ret = status.activity.finish()
        if ret:
            self.schedule(status)
        return ret

    def schedule(self, status: Status) -> None:
        reactor().callLater(0, self.__delete, status)

    def __delete(self, status: Status) -> None:
        state = self.manager.state(Status.TransferDeleted.code)
        state.set(status)


class TransferDeletedState(State):
    def __init__(self, manager: StateManager) -> None:
        self.manager: StateManager = manager
        super().__init__()

    def set(self, status: Status, context: Context=None) -> bool:
        status.state = self
        return status.activity.delete()

    def schedule(self, status: Status) -> None:
        pass


class TaskStateManager(StateManager):
    def __init__(self) -> None:
        super().__init__()

        self.add_state(Status.TransferTaskCreated.code, TaskCreatedState(self))
        self.add_state(Status.TransferTaskSending.code, TaskSendingState(self))
        self.add_state(Status.TransferTaskSended.code, TaskSendedState(self))
        self.add_state(Status.TransferTaskEnded.code, TaskEndedState(self))


class TransferStateManager(StateManager):
    def __init__(self) -> None:
        super().__init__()

        self.add_state(Status.TransferCreated.code, TransferCreatedState(self))
        self.add_state(Status.TransferStarted.code, TransferStartedState(self))
        self.add_state(Status.TransferEnded.code, TransferEndedState(self))
        self.add_state(Status.TransferFinished.code, TransferFinishedState(self))
        self.add_state(Status.TransferDeleted.code, TransferDeletedState(self))


def init() -> None:
    task_state_manager: StateManager = TaskStateManager()
    transfer_state_manager: StateManager = TransferStateManager()

    codes: List[Tuple[int, int]] = [
        (Status.TransferTaskCreated.code, Status.TransferCreated.code),
    ]

    for code in codes:
        task_state: State = task_state_manager.states[code[0]]
        transfer_state: State = transfer_state_manager.states[code[1]]
        task_state.add_slot(State.on, transfer_state.complete)

    object_manager.add_type(
        str(StateManager), task_state_manager, 'task'
    )

    object_manager.add_type(
        str(StateManager), transfer_state_manager, 'transfer'
    )
