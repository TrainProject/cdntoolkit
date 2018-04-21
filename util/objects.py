# coding=utf-8

from typing import Dict

from orderedattrdict import AttrDict

from . import reactor
from .state import Status, Activity


class ObjectManager:
    def __init__(self) -> None:
        self._objects: Dict[str, Status] = dict()
        self._cache_objects: Dict[str, Status] = dict()
        self._activity: Activity = None
        self._type_objects: Dict[str, Dict[str, object]] = dict()

    @property
    def activity(self) -> Activity:
        return self._activity

    @activity.setter
    def activity(self, value: Activity) -> None:
        self._activity = value

    def add_object(self, _id: str, status: Status) -> None:
        self._objects[_id] = status

    def object_by_id(self, _id: str) -> Status:
        _object = None

        for _ in [0]:
            _object = self._objects.get(_id)
            if _object is not None:
                break

            _object = self._cache_objects.get(_id)
            if _object is not None:
                break

            # FIXME
            """
            _object = self.activity.query(id=_id)
            if _object is not None:
                self.__add_cache(_id, _object)
            """

            query = AttrDict()
            query.clear()

            query._id = _id
            # result = self.transfer_task.find_one(query)
            # return result

        return _object

    def find_object(self, status: Status) -> Status:
        for _id, _object in self._objects.items():
            if status == _object:
                return status
        return None

    def delete_object(self, _id: str) -> bool:
        _object = self._objects.get(_id)

        if _object is not None:
            del self._objects[_id]
            self.__add_cache(_id, _object)
            return True

        return False

    def __add_cache(self, _id: str, status: Status) -> None:
        if _id not in self._cache_objects:
            self._cache_objects[_id] = status
            reactor().callLater(3600, self.__clean_cache, _id)

    def __clean_cache(self, _id: str) -> None:
        if _id in self._cache_objects:
            del self._cache_objects[_id]

    def add_type(self, type_name: str, _object: object,
                 name: str='default') -> None:
        _type: Dict[str, object] = self._type_objects.get(type_name)
        if _type is None:
            _type = dict()
            self._type_objects[type_name] = _type
        _type[name] = _object

    def find_type(self, type_name: str,
                  name: str='default') -> object:
        ret: object = None
        _type: Dict[str, object] = self._type_objects.get(type_name)
        if _type is not None:
            ret = _type.get(name)
        return ret

    def foreach_type(self, type_name: str) -> object:
        _type: Dict[str, object] = self._type_objects.get(type_name)
        if _type is not None:
            for name, _object in _type.items():
                yield _object


object_manager = ObjectManager()
