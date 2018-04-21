# coding=utf-8

from typing import Dict, Callable, List


def signal(func: Callable[..., object]) -> Callable[..., object]:
    def slot(*args: List, **kwargs: Dict) -> object:
        ret = None
        _object = args[0]

        for _ in [0]:
            assert isinstance(_object, Observer)

            _slot: Callable[..., object] = _object.query_slot(func)
            if _slot is None:
                break

            recv = _slot.__self__
            assert isinstance(recv, Observer)

            recv.sender = _object
            ret = _slot(*args[1:], **kwargs)
            recv.sender = recv

        func(*args, **kwargs)
        return ret

    slot.__name__ = func.__name__
    slot.__qualname__ = func.__qualname__
    return slot


class Observer:
    def __init__(self) -> None:
        self._signal_handler: Dict[str, Callable[..., object]] = dict()
        self._sender: Observer = self

    @property
    def sender(self) -> 'Observer':
        return self._sender

    @sender.setter
    def sender(self, value: 'Observer') -> None:
        self._sender = value

    def add_slot(self, _signal: Callable[..., object], _slot: Callable[..., object]) -> None:
        # FIXME
        # if _signal.__qualname__.split('.')[0] == type(self).__name__:
        self._signal_handler[_signal.__qualname__] = _slot

    def del_slot(self, _signal: Callable[..., object]) -> None:
        del self._signal_handler[_signal.__qualname__]

    def query_slot(self, _signal: Callable[..., object]) -> Callable[..., object]:
        return self._signal_handler.get(
            _signal.__qualname__
        )
