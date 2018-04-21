# coding=utf-8

from typing import Dict

from orderedattrdict import AttrDict

from .observer import Observer, signal


class Context:
    def __init__(self) -> None:
        self._key: str = 24 * '0'
        self._attachment: str = 24 * '0'
        self._index: int = -1
        self._data: object = None
        self._sender: 'Status' = None

    @property
    def key(self) -> str:
        return self._key

    @key.setter
    def key(self, value: str) -> None:
        self._key = value

    @property
    def attachment(self) -> str:
        return self._attachment

    @attachment.setter
    def attachment(self, value: str) -> None:
        self._attachment = value

    @property
    def index(self) -> int:
        return self._index

    @index.setter
    def index(self, value: int) -> None:
        self._index = value

    @property
    def data(self) -> object:
        return self._data

    @data.setter
    def data(self, value: object) -> None:
        self._data = value

    @property
    def sender(self) -> 'Status':
        return self._sender

    @sender.setter
    def sender(self, value: 'Status') -> None:
        self._sender = value


class Activity(Observer):
    def __init__(self) -> None:
        if type(self) is Activity:
            raise NotImplementedError

        self._retry = None
        super().__init__()

    @property
    def key(self) -> str:
        raise NotImplementedError

    @key.setter
    def key(self, value: str) -> None:
        raise NotImplementedError

    @property
    def status(self) -> 'Status':
        raise NotImplementedError

    @status.setter
    def status(self, value: 'Status') -> None:
        raise NotImplementedError

    def query(self) -> None:
        pass

    @signal
    def on_query(self, context: Context=None) -> None:
        pass

    def create(self, context: Context=None) -> bool:
        raise RuntimeError

    @signal
    def on_create(self, context: Context=None) -> None:
        pass

    def start(self, context: Context=None) -> bool:
        raise RuntimeError

    @signal
    def on_start(self, context: Context=None) -> None:
        pass

    def send(self, context: Context=None) -> bool:
        raise RuntimeError

    @signal
    def on_send(self, context: Context=None) -> None:
        pass

    def recv(self, context: Context=None) -> bool:
        raise RuntimeError

    @signal
    def on_recv(self, context: Context=None) -> None:
        pass

    def end(self, context: Context=None) -> bool:
        raise RuntimeError

    @signal
    def on_end(self, context: Context=None) -> None:
        pass

    def finish(self, context: Context=None) -> bool:
        raise RuntimeError

    @signal
    def on_finish(self, context: Context=None) -> None:
        pass

    def archive(self, context: Context=None) -> bool:
        raise RuntimeError

    @signal
    def on_archive(self, context: Context=None) -> None:
        pass

    def delete(self, context: Context=None) -> bool:
        raise RuntimeError

    @signal
    def on_delete(self, context: Context=None) -> None:
        pass

    @signal
    def on_error(self, context: Context=None) -> None:
        pass


class Status:
    TransactionCreated = AttrDict()
    TransactionCreated.code = 0
    TransactionCreated.message = "TransactionCreated"

    TransactionStarted = AttrDict()
    TransactionStarted.code = 1
    TransactionStarted.message = "TransactionStarted"

    TransactionEnded = AttrDict()
    TransactionEnded.code = 2
    TransactionEnded.message = "TransactionEnded"

    TransactionFinished = AttrDict()
    TransactionFinished.code = 3
    TransactionFinished.message = "TransactionFinished"

    TransactionArchived = AttrDict()
    TransactionArchived.code = 4
    TransactionArchived.message = "TransactionArchived"

    TransactionDeleted = AttrDict()
    TransactionDeleted.code = 5
    TransactionDeleted.message = "TransactionDeleted"

    TransferCreated = AttrDict()
    TransferCreated.code = 10
    TransferCreated.message = "TransferCreated"

    TransferStarted = AttrDict()
    TransferStarted.code = 11
    TransferStarted.message = "TransferStarted"

    TransferEnded = AttrDict()
    TransferEnded.code = 12
    TransferEnded.message = "TransferEnded"

    TransferFinished = AttrDict()
    TransferFinished.code = 13
    TransferFinished.message = "TransferFinished"

    TransferDeleted = AttrDict()
    TransferDeleted.code = 14
    TransferDeleted.message = "TransactionDeleted"

    TransferTaskCreated = AttrDict()
    TransferTaskCreated.code = 20
    TransferTaskCreated.message = "TransferTaskCreated"

    TransferTaskSending = AttrDict()
    TransferTaskSending.code = 21
    TransferTaskSending.message = "TransferTaskSending"

    TransferTaskSended = AttrDict()
    TransferTaskSended.code = 22
    TransferTaskSended.message = "TransferTaskSended"

    TransferTaskEnded = AttrDict()
    TransferTaskEnded.code = 23
    TransferTaskEnded.message = "TransferTaskEnded"

    TransferTaskDeleted = AttrDict()
    TransferTaskDeleted.code = 23
    TransferTaskDeleted.message = "TransferTaskDeleted"

    def __init__(self) -> None:
        self.__code: int = -1
        self.__message: str = str()
        self._state: State = None
        self._activity: Activity = None

    @property
    def code(self) -> int:
        return self.__code

    @code.setter
    def code(self, value: int) -> None:
        self.__code = value

    @property
    def message(self) -> str:
        return self.__message

    @message.setter
    def message(self, value: str) -> None:
        self.__message = value

    @property
    def state(self) -> 'State':
        return self._state

    @state.setter
    def state(self, value: 'State') -> None:
        self._state = value

    @property
    def activity(self) -> Activity:
        return self._activity

    @activity.setter
    def activity(self, value: Activity) -> None:
        self._activity = value


class State(Observer):
    def __init__(self) -> None:
        if type(self) is State:
            raise NotImplementedError
        super().__init__()

    def schedule(self, status: Status) -> None:
        raise NotImplementedError

    def set(self, status: Status, context: Context=None) -> bool:
        raise NotImplementedError

    @signal
    def on(self, context: Context=None) -> None:
        pass

    def complete(self, context: Context) -> None:
        sender: Observer = self.sender
        assert isinstance(sender, Activity)
        context.sender = sender
        self.on(context)


class StateManager:
    def __init__(self) -> None:
        self.states: Dict[int, State] = dict()

    def add_state(self, code: int, state: State) -> None:
        self.states[code] = state

    def state(self, code: int) -> State:
        return self.states[code]

    def default(self) -> State:
        first = next(iter(self.states))
        state = self.states[first]
        return state

    def set(self, status: Status,
            state: State=None,
            context: Context=None) -> bool:

        if state is None:
            state = status.state

        if state is None:
            state = self.default()

        return state.set(status, context)

    def schedule(self, status: Status) -> None:
        status.state.schedule(status)
