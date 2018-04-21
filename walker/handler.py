# coding=utf-8

import threading
import time
from collections import OrderedDict
from typing import Dict

from orderedattrdict import AttrDict
from tornado.options import options
from twisted.internet.defer import Deferred
from twisted.python.failure import Failure

from util import reactor
from util.exception import print_frame
from util.message import WampMessage
from util.observer import Observer
from util.protocol import TaskCommandRequest, TaskCommandResponse
from util.protocol import TransferPutRequest, TransferPutResponse
from .module import Task


class WalkerHandler(Observer):
    def __init__(self, message: WampMessage) -> None:
        self.names: Dict[str, 'WalkerHandler'] = dict()
        self.message: WampMessage = message
        self.tasks: OrderedDict = OrderedDict()
        self.event = threading.Event()
        self.worker_thread = threading.Thread(target=self.worker_handler)
        self.worker_thread.start()
        self.wakeup_count = 0
        super().__init__()

    def wakeup_worker(self) -> None:
        self.event.set()
        self.wakeup_count += 1

    def worker_handler(self) -> None:
        while 1:
            self.event.wait()
            self.event.clear()

            while self.wakeup_count:
                keys = list(self.tasks.keys())

                self.run_start()
                for key in keys:
                    task = self.tasks.get(key)
                    if task is not None and task.stage != -1:
                        self.run(task)
                self.run_end()

                self.wakeup_count -= 1

    def run(self, task: Task) -> None:
        pass

    def run_start(self) -> None:
        pass

    def run_end(self) -> None:
        pass

    def name(self) -> str:
        return "walker"

    def handle(self, command: TaskCommandRequest) -> TaskCommandResponse:
        ret = AttrDict()
        # FIXME
        ret.code = command.code
        ret.duration = 1

        if command.task_id not in self.tasks:

            if len(self.tasks) < 10:
                task: Task = Task()
                task.ts = int(time.time())
                task.application = command.application
                task.task_id = command.task_id
                task.transfer_id = command.transfer_id
                task.application = command.application
                task.code = command.code
                task.timeout = command.timeout
                task.retry = command.retry

                self.tasks[task.task_id] = task
                self.wakeup_worker()

                ret.message = '{name} handler acked'.format(name=self.name())

            else:
                ret.code = 429
                ret.message = "Too Many Requests"

        else:
            # task = self.tasks[command.task_id]
            ret.code = 208
            ret.message = "Already Reported"

        return TaskCommandResponse(ret)

    def dispatch(self, data: str) -> str:
        request: TaskCommandRequest = TaskCommandRequest(data)
        handler = self.match(request.application.name)
        return str(handler.handle(request))

    def add(self, handler: 'WalkerHandler') -> None:
        self.names[handler.name()] = handler

    def match(self, name: str) -> 'WalkerHandler':
        h = self.names.get(name)
        if h is None:
            h = self.names.get('null')
        return h

    def finish(self, task: Task) -> None:
        task.stage = -1
        reactor().callFromThread(self.put)

    def put(self) -> None:
        keys = list(self.tasks.keys())
        for key in keys:
            task: Task = self.tasks.get(key)
            if task is not None and task.stage == -1:
                task.retry -= 1
                task.ts = int(time.time())

                put_param: TransferPutRequest = TransferPutRequest()
                put_param.task_id = task.task_id
                put_param.transfer_id = task.transfer_id
                put_param.code = task.code
                put_param.message = task.message
                put_param.duration = task.duration
                print("%%%%%%%%%s", put_param)

                defer: Deferred = self.message.rpc(
                    options.topic_transfer_put, str(put_param)
                )
                defer.addCallback(self.put_complete, task)
                defer.addErrback(self.put_error, task)

    def put_complete(self, _put_ret: str, task: Task) -> None:
        try:
            put_ret: TransferPutResponse = TransferPutResponse(_put_ret)

            if put_ret.code == 503:
                task.ts = int(time.time())
                reactor().callLater(0, self.put)

            else:
                del self.tasks[task.task_id]

        except Exception as e:
            print_frame(e)

    def put_error(self, error: Failure, task: Task) -> None:
        print(error.getErrorMessage())

        if not task.retry:
            del self.tasks[task.task_id]
        else:
            reactor().callLater(0, self.put)


class NullHandler(WalkerHandler):
    def __init__(self, message: WampMessage) -> None:
        super().__init__(message)

    def name(self) -> str:
        return "null"

    def handle(self, command: TaskCommandRequest) -> TaskCommandResponse:
        tcr: TaskCommandResponse = TaskCommandResponse()
        tcr.message = "walker match nothing."
        tcr.code = 404
        tcr.duration = 0
        return tcr
