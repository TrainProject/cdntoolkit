# coding=utf-8

from typing import List, Tuple

from orderedattrdict import AttrDict

from util import reactor
from util.message import WampMessage
from util.objects import object_manager
from util.state import State, Status, StateManager, Activity, Context


class TransferCreatedState(State):
    def __init__(self, manager: StateManager) -> None:
        self.manager: StateManager = manager
        super().__init__()

    def set(self, status: Status, context: Context=None) -> bool:
        from .transfer import Transfer
        transfer: Transfer = Transfer()
        transfer.transaction_id = context.attachment
        transfer.index = context.index
        transfer.status = status

        message: object = object_manager.find_type(
            str(WampMessage), str(context.index % 16)
        )
        assert isinstance(message, WampMessage)
        transfer.message = message

        data: object = context.data
        assert isinstance(data, AttrDict)
        transfer.application = data

        status.activity = transfer
        status.state = self

        return status.activity.create()

    def schedule(self, status: Status) -> None:
        self.__start(status)

    def __start(self, status: Status) -> None:
        state = self.manager.state(Status.TransferStarted.code)
        state.set(status)


class TransferStartedState(State):
    def __init__(self, manager: StateManager) -> None:
        self.manager: StateManager = manager
        super().__init__()

    def set(self, status: Status, context: Context=None) -> bool:
        status.activity.add_slot(
            Activity.on_start, self.complete
        )
        status.state = self
        return status.activity.start(context)

    def schedule(self, status: Status) -> None:
        pass


class TransferEndedState(State):
    def __init__(self, manager: StateManager) -> None:
        self.manager: StateManager = manager
        super().__init__()

    def set(self, status: Status, context: Context=None) -> bool:
        pass

    def schedule(self, status: Status) -> None:
        pass


class TransactionCreatedState(State):
    def __init__(self, manager: StateManager) -> None:
        self.manager: StateManager = manager

        from .module import TransactionModule
        module: object = object_manager.find_type(
            str(TransactionModule)
        )
        assert isinstance(module, TransactionModule)
        self._module = module

        super().__init__()

    def set(self, status: Status, context: Context=None) -> bool:
        from .transaction import Transaction
        transaction = Transaction()
        transaction.status = status
        transaction.module = self._module

        status.activity = transaction
        status.state = self

        ret = status.activity.create()
        if ret:
            self.schedule(status)
        return ret

    def schedule(self, status: Status) -> None:
        # self.__start(status)
        reactor().callLater(0, self.__start, status)

    def __start(self, status: Status) -> None:
        state = self.manager.state(Status.TransactionStarted.code)
        state.set(status)


class TransactionStartedState(State):
    def __init__(self, manager: StateManager) -> None:
        self.manager: StateManager = manager
        super().__init__()

    def set(self, status: Status, context: Context=None) -> bool:
        status.state = self
        context: Context = Context()
        context.index = -1
        return status.activity.start(context)

    def schedule(self, status: Status) -> None:
        # FIXME
        pass

    def complete(self, context: Context=None) -> None:
        from .transfer import Transfer
        assert isinstance(context.sender, Transfer)
        transfer: Transfer = context.sender

        status = object_manager.object_by_id(
            transfer.transaction_id
        )
        if status is None:
            return

        from .transaction import Transaction
        assert isinstance(status.activity, Transaction)
        transaction: Transaction = status.activity

        transaction.complete_start(
            context.key, transfer
        )

        context.index = transfer.shard
        transaction.start(context)


class TransactionEndedState(State):
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
        self.__finish(status)
        # reactor().callLater(0, self.__finish, status)

    def __finish(self, status: Status) -> None:
        state = self.manager.state(Status.TransactionFinished.code)
        state.set(status)


class TransactionFinishedState(State):
    def __init__(self, manager: StateManager) -> None:
        self.manager: StateManager = manager
        super().__init__()

    def set(self, status: Status, context: Context=None) -> bool:
        status.state = self
        self.schedule(status)
        return status.activity.finish(context)

    def schedule(self, status: Status) -> None:
        self.__archive(status)
        # reactor().callLater(0, self.__archive, status)

    def __archive(self, status: Status) -> None:
        if status.code != Status.TransactionArchived.code:
            state = self.manager.state(Status.TransactionArchived.code)
            state.set(status)


class TransactionArchivedState(State):
    def __init__(self, manager: StateManager) -> None:
        self.manager: StateManager = manager
        super().__init__()

    def set(self, status: Status, context: Context=None) -> bool:
        status.state = self
        return status.activity.archive(context)

    def schedule(self, status: Status) -> None:
        pass


class TransferStateManager(StateManager):
    def __init__(self) -> None:
        super().__init__()

        self.add_state(Status.TransferCreated.code, TransferCreatedState(self))
        self.add_state(Status.TransferStarted.code, TransferStartedState(self))
        self.add_state(Status.TransferEnded.code, TransferEndedState(self))


class TransactionStateManager(StateManager):
    def __init__(self) -> None:
        super().__init__()

        self.add_state(Status.TransactionCreated.code, TransactionCreatedState(self))
        self.add_state(Status.TransactionStarted.code, TransactionStartedState(self))
        self.add_state(Status.TransactionEnded.code, TransactionEndedState(self))
        self.add_state(Status.TransactionFinished.code, TransactionFinishedState(self))
        self.add_state(Status.TransactionArchived.code, TransactionArchivedState(self))


def init() -> None:
    transfer_state_manager: StateManager = TransferStateManager()
    transaction_state_manager: StateManager = TransactionStateManager()

    codes: List[Tuple[int, int]] = [
        (Status.TransferCreated.code, Status.TransactionCreated.code),
        (Status.TransferStarted.code, Status.TransactionStarted.code),
        (Status.TransferEnded.code, Status.TransactionEnded.code),
    ]

    for code in codes:
        transfer_state: State = transfer_state_manager.states[code[0]]
        transaction_state: State = transaction_state_manager.states[code[1]]
        transfer_state.add_slot(State.on, transaction_state.complete)

    object_manager.add_type(
        str(StateManager), transfer_state_manager, 'transfer'
    )

    object_manager.add_type(
        str(StateManager), transaction_state_manager, 'transaction'
    )
