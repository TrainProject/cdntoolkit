# coding=utf-8

from orderedattrdict import AttrDict

from util import FrozenClass


class Task(FrozenClass):
    def __init__(self) -> None:
        self._task_id: str = 24 * '0'
        self._transfer_id: str = 24 * '0'
        self._application: AttrDict = None
        self._retry: int = -1
        self._code: int = -1
        self._message: str = str()
        self._timeout: int = -1

        self._ts: int = -1
        self._stage: int = 0
        self._context: AttrDict = AttrDict()
        self._duration: int = 1

        super().__init__()

    @property
    def task_id(self) -> str:
        return self._task_id

    @task_id.setter
    def task_id(self, value: str) -> None:
        self._task_id = value

    @property
    def transfer_id(self) -> str:
        return self._transfer_id

    @transfer_id.setter
    def transfer_id(self, value: str) -> None:
        self._transfer_id = value

    @property
    def application(self) -> AttrDict:
        return self._application

    @application.setter
    def application(self, value: AttrDict) -> None:
        self._application = value

    @property
    def retry(self) -> int:
        return self._retry

    @retry.setter
    def retry(self, value: int) -> None:
        self._retry = value

    @property
    def code(self) -> int:
        return self._code

    @code.setter
    def code(self, value: int) -> None:
        self._code = value

    @property
    def message(self) -> str:
        return self._message

    @message.setter
    def message(self, value: str) -> None:
        self._message = value

    @property
    def timeout(self) -> int:
        return self._timeout

    @timeout.setter
    def timeout(self, value: int) -> None:
        self._timeout = value

    @property
    def ts(self) -> int:
        return self._ts

    @ts.setter
    def ts(self, value: int) -> None:
        self._ts = value

    @property
    def stage(self) -> int:
        return self._stage

    @stage.setter
    def stage(self, value: int) -> None:
        self._stage = value

    @property
    def context(self) -> AttrDict:
        return self._context

    @context.setter
    def context(self, value: AttrDict) -> None:
        self._context = value

    @property
    def duration(self) -> int:
        return self._duration

    @duration.setter
    def duration(self, value: int) -> None:
        self._duration = value
