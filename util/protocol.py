# coding=utf-8

from datetime import datetime
from typing import List, Union

from orderedattrdict import AttrDict
from tornado.options import options

from . import FrozenClass
from .json import AttrJson


class TransactionPostRequest(FrozenClass):
    def __init__(self, _data: Union[str, AttrDict]=None) -> None:
        timeout: int = -1
        retry: int = -1
        dst: object = None
        application: AttrDict = AttrDict()

        if _data is not None:
            if isinstance(_data, str):
                data: AttrDict = AttrJson.loads(_data)
            else:
                data = _data

            timeout = data.get('timeout', -1)
            if timeout == -1:
                timeout = options.default_timeout

            retry = data.get('retry', -1)
            if retry == -1:
                retry = options.default_retry

            dst = data.dst
            application = data.application

        self.__dst: object = dst
        self.__timeout: int = timeout
        self.__retry: int = retry
        self.__application: AttrDict = application
        super().__init__()

    @property
    def dst(self) -> object:
        return self.__dst

    @dst.setter
    def dst(self, value: object) -> None:
        self.__dst = value

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
    def application(self) -> AttrDict:
        return self.__application

    @application.setter
    def application(self, value: AttrDict) -> None:
        self.__application = value


class TransactionPostResponse(FrozenClass):
    def __init__(self, _data: Union[str, AttrDict]=None) -> None:
        transaction_id: str = 24 * '0'
        code: int = -1
        message: str = str()

        if _data is not None:
            if isinstance(_data, str):
                data: AttrDict = AttrJson.loads(_data)
            else:
                data = _data

            transaction_id = str(data.transfer_id)
            code = data.code
            message = data.message

        self.__transaction_id: str = transaction_id
        self.__code: int = code
        self.__message: str = message
        super().__init__()

    @property
    def transaction_id(self) -> str:
        return self.__transaction_id

    @transaction_id.setter
    def transaction_id(self, value: str) -> None:
        self.__transaction_id = value

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


class TransactionGetRequest(FrozenClass):
    def __init__(self, _data: Union[str, AttrDict]=None) -> None:
        transaction_id: str = 24 * '0'

        if _data is not None:
            if isinstance(_data, str):
                data: AttrDict = AttrJson.loads(_data)
            else:
                data = _data

            transaction_id = str(data.transaction_id)

        self.__transaction_id: str = transaction_id
        super().__init__()

    @property
    def transaction_id(self) -> str:
        return self.__transaction_id

    @transaction_id.setter
    def transaction_id(self, value: str) -> None:
        self.__transaction_id = value


class TransactionGetResponse(FrozenClass):
    def __init__(self, _data: Union[str, AttrDict]=None) -> None:
        transaction_id: str = 24 * '0'
        create_time: datetime = datetime.utcfromtimestamp(0)
        last_time: datetime = datetime.utcfromtimestamp(0)
        dst = None
        application: AttrDict = AttrDict()
        transfers: List[TransferGetResponse] = list()
        code: int = -1
        message: str = str()

        if _data is not None:
            if isinstance(_data, str):
                data: AttrDict = AttrJson.loads(_data)
            else:
                data = _data

            transaction_id = str(data.transaction_id)
            create_time = data.create_time
            last_time = data.last_time
            dst = data.dst
            application = data.application
            transfers = data.transfers
            code = data.code
            message = data.message

        self.__transaction_id: str = transaction_id
        self.__create_time: datetime = create_time
        self.__last_time: datetime = last_time
        self.__dst: object = dst
        self.__application: AttrDict = application
        self.__transfers: List[TransferGetResponse] = transfers
        self.__code: int = code
        self.__message: str = message
        super().__init__()

    @property
    def transaction_id(self) -> str:
        return self.__transaction_id

    @transaction_id.setter
    def transaction_id(self, value: str) -> None:
        self.__transaction_id = value

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
    def transfers(self) -> List['TransferGetResponse']:
        return self.__transfers

    @transfers.setter
    def transfers(self, value: List['TransferGetResponse']) -> None:
        self.__transfers = value

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


class TransactionPutRequest(FrozenClass):
    def __init__(self, _data: Union[str, AttrDict]=None) -> None:
        transaction_id: str = str()
        transfer_id: str = str()

        if _data is not None:
            if isinstance(_data, str):
                data: AttrDict = AttrJson.loads(_data)
            else:
                data = _data

            transaction_id = str(data.transaction_id)
            transfer_id = str(data.transfer_id)

        self.__transaction_id: str = transaction_id
        self.__transfer_id: str = transfer_id
        super().__init__()

    @property
    def transaction_id(self) -> str:
        return self.__transaction_id

    @transaction_id.setter
    def transaction_id(self, value: str) -> None:
        self.__transaction_id = value

    @property
    def transfer_id(self) -> str:
        return self.__transfer_id

    @transfer_id.setter
    def transfer_id(self, value: str) -> None:
        self.__transfer_id = value


class TransactionPutResponse(FrozenClass):
    def __init__(self, _data: Union[str, AttrDict]=None) -> None:
        code: int = -1
        message: str = str()

        if _data is not None:
            if isinstance(_data, str):
                data: AttrDict = AttrJson.loads(_data)
            else:
                data = _data

            code = data.code
            message = data.message

        self.__code: int = code
        self.__message: str = message
        super().__init__()

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


class TransactionDeleteRequest(FrozenClass):
    def __init__(self, _data: Union[str, AttrDict]=None) -> None:
        transaction_id: str = 24 * '0'

        if _data is not None:
            if isinstance(_data, str):
                data: AttrDict = AttrJson.loads(_data)
            else:
                data = _data

            transaction_id = str(data.transaction_id)

        self.__transaction_id: str = transaction_id
        super().__init__()

    @property
    def transaction_id(self) -> str:
        return self.__transaction_id

    @transaction_id.setter
    def transaction_id(self, value: str) -> None:
        self.__transaction_id = value


class TransactionDeleteResponse(FrozenClass):
    def __init__(self, _data: Union[str, AttrDict]=None) -> None:
        code: int = -1
        message: str = str()

        if _data is not None:
            if isinstance(_data, str):
                data: AttrDict = AttrJson.loads(_data)
            else:
                data = _data

            code = data.code
            message = data.message

        self.__code: int = code
        self.__message: str = message
        super().__init__()

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


class TransferPostRequest(FrozenClass):
    def __init__(self, _data: Union[str, AttrDict]=None) -> None:
        transaction_id: str = 24 * '0'
        hosts: List[AttrDict] = list()
        timeout: int = -1
        retry: int = -1
        application: AttrDict = AttrDict()

        if _data is not None:
            if isinstance(_data, str):
                data: AttrDict = AttrJson.loads(_data)
            else:
                data = _data

            transaction_id = str(data.transaction_id)
            hosts = data.hosts

            timeout = data.get('timeout', -1)
            if timeout == -1:
                timeout = options.default_timeout

            retry = data.get('retry', -1)
            if retry == -1:
                retry = options.default_retry

            application = data.application

        self.__transaction_id: str = transaction_id
        self.__hosts: List[AttrDict] = hosts
        self.__timeout: int = timeout
        self.__retry: int = retry
        self.__application: AttrDict = application
        super().__init__()

    @property
    def transaction_id(self) -> str:
        return self.__transaction_id

    @transaction_id.setter
    def transaction_id(self, value: str) -> None:
        self.__transaction_id = value

    @property
    def hosts(self) -> List[AttrDict]:
        return self.__hosts

    @hosts.setter
    def hosts(self, value: List[AttrDict]) -> None:
        self.__hosts = value

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
    def application(self) -> AttrDict:
        return self.__application

    @application.setter
    def application(self, value: AttrDict) -> None:
        self.__application = value


class TransferPostResponse(FrozenClass):
    def __init__(self, _data: Union[str, AttrDict]=None) -> None:
        transfer_id: str = 24 * '0'
        code: int = -1
        message: str = str()

        if _data is not None:
            if isinstance(_data, str):
                data: AttrDict = AttrJson.loads(_data)
            else:
                data = _data

            transfer_id = str(data.transfer_id)
            code = data.code
            message = data.message

        self.__transfer_id: str = transfer_id
        self.__code: int = code
        self.__message: str = message
        super().__init__()

    @property
    def transfer_id(self) -> str:
        return self.__transfer_id

    @transfer_id.setter
    def transfer_id(self, value: str) -> None:
        self.__transfer_id = value

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


class TransferGetRequest(FrozenClass):
    def __init__(self, _data: Union[str, AttrDict]=None) -> None:
        transfer_id: str = 24 * '0'

        if _data is not None:
            if isinstance(_data, str):
                data: AttrDict = AttrJson.loads(_data)
            else:
                data = _data

            transfer_id = str(data.transfer_id)

        self.__transfer_id: str = transfer_id
        super().__init__()

    @property
    def transfer_id(self) -> str:
        return self.__transfer_id

    @transfer_id.setter
    def transfer_id(self, value: str) -> None:
        self.__transfer_id = value


class TransferGetResponseResult(FrozenClass):
    def __init__(self, _data: AttrDict=None) -> None:
        host: str = str()
        code: int = -1
        message: str = str()

        if _data is not None:
            data: AttrDict = _data
            host = data.host
            code = data.code
            message = data.message

        self.__host: str = host
        self.__code: int = code
        self.__message: str = message

        super().__init__()

    @property
    def host(self) -> str:
        return self.__host

    @host.setter
    def host(self, value: str) -> None:
        self.__host = value

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


class TransferGetResponse(FrozenClass):
    def __init__(self, _data: Union[str, AttrDict]=None) -> None:
        hosts: str = str()
        create_time: datetime = datetime.utcfromtimestamp(0)
        last_time: datetime = datetime.utcfromtimestamp(0)
        # FIXME
        # TransferResult
        results: List[TransferGetResponseResult] = list()
        code: int = -1
        message: str = str()

        if _data is not None:
            if isinstance(_data, str):
                data: AttrDict = AttrJson.loads(_data)
            else:
                data = _data

            hosts = data.hosts
            create_time = data.create_time
            last_time = data.last_time
            # results = data.results
            # FIXME
            for result in data.results:
                _result = TransferGetResponseResult(result)
                _result.code = result.code
                _result.message = result.message
                results.append(_result)
            code = data.code
            message = data.message

        self.__hosts: str = hosts
        self.__create_time: datetime = create_time
        self.__last_time: datetime = last_time
        self.__results: List[TransferGetResponseResult] = results
        self.__code: int = code
        self.__message: str = message
        super().__init__()

    @property
    def hosts(self) -> str:
        return self.__hosts

    @hosts.setter
    def hosts(self, value: str) -> None:
        self.__hosts = value

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
    def results(self) -> List[TransferGetResponseResult]:
        return self.__results

    @results.setter
    def results(self, value: List[TransferGetResponseResult]) -> None:
        self.__results = value

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


class TransferPutRequest(FrozenClass):
    def __init__(self, _data: Union[str, AttrDict]=None) -> None:
        task_id: str = str()
        transfer_id: str = str()
        code: int = -1
        message: str = str()
        duration: int = -1

        if _data is not None:
            if isinstance(_data, str):
                data: AttrDict = AttrJson.loads(_data)
            else:
                data = _data

            task_id = str(data.task_id)
            transfer_id = str(data.transfer_id)
            code = data.code
            message = data.message
            duration = data.duration

        self.__task_id: str = task_id
        self.__transfer_id: str = transfer_id
        self.__code: int = code
        self.__message: str = message
        self.__duration: int = duration
        super().__init__()

    @property
    def task_id(self) -> str:
        return self.__task_id

    @task_id.setter
    def task_id(self, value: str) -> None:
        self.__task_id = value

    @property
    def transfer_id(self) -> str:
        return self.__transfer_id

    @transfer_id.setter
    def transfer_id(self, value: str) -> None:
        self.__transfer_id = value

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
    def duration(self) -> int:
        return self.__duration

    @duration.setter
    def duration(self, value: int) -> None:
        self.__duration = value


class TransferPutResponse(FrozenClass):
    def __init__(self, _data: Union[str, AttrDict]=None) -> None:
        code: int = -1
        message: str = str()

        if _data is not None:
            if isinstance(_data, str):
                data: AttrDict = AttrJson.loads(_data)
            else:
                data = _data

            code = data.code
            message = data.message

        self.__code: int = code
        self.__message: str = message
        super().__init__()

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


class TransferDeleteRequest(FrozenClass):
    def __init__(self, _data: Union[str, AttrDict]=None) -> None:
        transfer_id: str = 24 * '0'

        if _data is not None:
            if isinstance(_data, str):
                data: AttrDict = AttrJson.loads(_data)
            else:
                data = _data
            transfer_id = str(data.transfer_id)

        self.__transfer_id: str = transfer_id
        super().__init__()

    @property
    def transfer_id(self) -> str:
        return self.__transfer_id

    @transfer_id.setter
    def transfer_id(self, value: str) -> None:
        self.__transfer_id = value


class TransferDeleteResponse(FrozenClass):
    def __init__(self, _data: Union[str, AttrDict]=None) -> None:
        code: int = -1
        message: str = str()

        if _data is not None:
            if isinstance(_data, str):
                data: AttrDict = AttrJson.loads(_data)
            else:
                data = _data

            code = data.code
            message = data.message

        self.__code: int = code
        self.__message: str = message
        super().__init__()

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


class TaskCommandRequest(FrozenClass):
    def __init__(self, _data: Union[str, AttrDict]=None) -> None:
        task_id: str = str()
        transfer_id: str = str()
        application: AttrDict = AttrDict()
        code: int = -1
        timeout: int = -1
        retry: int = -1

        if _data is not None:
            if isinstance(_data, str):
                data: AttrDict = AttrJson.loads(_data)
            else:
                data = _data

            task_id = str(data.task_id)
            transfer_id = str(data.transfer_id)
            application = data.application
            code = data.code
            timeout = data.get('timeout', -1)
            if timeout == -1:
                timeout = options.default_timeout

            retry = data.get('retry', -1)
            if retry == -1:
                retry = options.default_retry

        self.__task_id: str = task_id
        self.__transfer_id: str = transfer_id
        self.__application: AttrDict = application
        self.__code: int = code
        self.__timeout: int = timeout
        self.__retry: int = retry
        super().__init__()

    @property
    def task_id(self) -> str:
        return self.__task_id

    @task_id.setter
    def task_id(self, value: str) -> None:
        self.__task_id = value

    @property
    def transfer_id(self) -> str:
        return self.__transfer_id

    @transfer_id.setter
    def transfer_id(self, value: str) -> None:
        self.__transfer_id = value

    @property
    def application(self) -> AttrDict:
        return self.__application

    @application.setter
    def application(self, value: AttrDict) -> None:
        self.__application = value

    @property
    def code(self) -> int:
        return self.__code

    @code.setter
    def code(self, value: int) -> None:
        self.__code = value

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


class TaskCommandResponse(FrozenClass):
    def __init__(self, _data: Union[str, AttrDict]=None) -> None:
        code: int = -1
        message: str = str()
        duration: int = -1

        if _data is not None:
            if isinstance(_data, str):
                data: AttrDict = AttrJson.loads(_data)
            else:
                data = _data
            code = data.code
            message = data.message
            duration = data.duration

        self.__code: int = code
        self.__message: str = message
        self.__duration: int = duration
        super().__init__()

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
    def duration(self) -> int:
        return self.__duration

    @duration.setter
    def duration(self, value: int) -> None:
        self.__duration = value


class ConfigGetRequest(FrozenClass):
    def __init__(self, _data: Union[str, AttrDict]=None) -> None:
        host: str = "FFFFFFFF-FFFF-FFFF-FFFF-FFFFFFFFFFFF"
        if _data is not None:
            if isinstance(_data, str):
                data: AttrDict = AttrJson.loads(_data)
            else:
                data = _data
            host = data.host

        self.__host: str = host
        super().__init__()

    @property
    def host(self) -> str:
        return self.__host

    @host.setter
    def host(self, value: str) -> None:
        self.__host = value


class ConfigGetResponse(FrozenClass):
    def __init__(self, _data: Union[str, AttrDict]=None) -> None:
        country: str = "unknown"
        province: str = "unknown"
        area: str = "unknown"
        idc: str = "unknown"
        isp: str = "unknown"
        role: str = "unknown"

        if _data is not None:
            if isinstance(_data, str):
                data: AttrDict = AttrJson.loads(_data)
            else:
                data = _data

            country = data.country
            province = data.province
            area = data.area
            idc = data.idc
            isp = data.isp
            role = data.role

        self.__country: str = country
        self.__province: str = province
        self.__area: str = area
        self.__idc: str = idc
        self.__isp: str = isp
        self.__role: str = role
        super().__init__()

    @property
    def country(self) -> str:
        return self.__country

    @country.setter
    def country(self, value: str) -> None:
        self.__country = value

    @property
    def province(self) -> str:
        return self.__province

    @province.setter
    def province(self, value: str) -> None:
        self.__province = value

    @property
    def area(self) -> str:
        return self.__area

    @area.setter
    def area(self, value: str) -> None:
        self.__area = value

    @property
    def idc(self) -> str:
        return self.__idc

    @idc.setter
    def idc(self, value: str) -> None:
        self.__idc = value

    @property
    def isp(self) -> str:
        return self.__isp

    @isp.setter
    def isp(self, value: str) -> None:
        self.__isp = value

    @property
    def role(self) -> str:
        return self.__role

    @role.setter
    def role(self, value: str) -> None:
        self.__role = value
