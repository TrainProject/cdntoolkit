# coding=utf-8

from orderedattrdict import AttrDict

from util.exception import print_frame
from util.message import WampMessage
from .handler import WalkerHandler
from .module import Task


class CommandHandler(WalkerHandler):
    def __init__(self, message: WampMessage) -> None:
        super().__init__(message)

    def name(self) -> str:
        return "command"

    def run(self, task: Task) -> None:
        try:
            import sh
            application: AttrDict = task.application
            message = str(eval(application.command))

            task.code = 200
            task.message = message

        except ImportError as e:
            task.code = 500
            task.message = str(e)
            sh = None
            _ = sh

        except Exception as e:
            task.code = 400
            task.message = str(e)
            print_frame(e)

        self.finish(task)
