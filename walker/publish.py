# coding=utf-8

from util.exception import print_frame
from util.message import WampMessage
from .handler import WalkerHandler
from .module import Task


class PublishHandler(WalkerHandler):
    def __init__(self, message: WampMessage) -> None:
        super().__init__(message)

    def name(self) -> str:
        return "publish"

    def run(self, task: Task) -> None:
        try:
            task.code = 501
            task.message = "Not Implemented"
        except Exception as e:
            print_frame(e)

        self.finish(task)
