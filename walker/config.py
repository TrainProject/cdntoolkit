# coding=utf-8

from typing import Any

from orderedattrdict import AttrDict
from tornado.options import options

import util
from util.c3 import Target, Error,\
    checkout, update, snapshot, nginx_reload
from util.exception import print_frame
from util.message import WampMessage
from .handler import WalkerHandler
from .module import Task


class ConfigHandler(WalkerHandler):
    def __init__(self, message: WampMessage) -> None:
        self.trigger_code = -1
        self.trigger_message = str()
        self.timer_trigger: int = 0
        self.check_count = 0

        offset = int(util.get_uuid().split("-")[1][:3], 16)
        interval = offset * options.walker_interval / 4096.0
        looper = util.round_looper(
            options.walker_interval,
            int(interval),
            self.set_timer_trigger
        )
        util.loop_timer(looper)
        super().__init__(message)

    def set_timer_trigger(self, _: float) -> None:
        self.timer_trigger += 1
        self.wakeup_worker()

    def name(self) -> str:
        return "config"

    def run(self, task: Task) -> None:
        import beeprint
        beeprint.pp(task)

        if task.stage == 0:
            # http://127.0.0.1/example.com.git
            path = task.application.get("path")
            version = task.application.get("version")

            if isinstance(path, str) and isinstance(version, str):
                target = AttrDict()
                target.repo = "http://{address}/{path}.git".format(
                    address=options.git_server, path=path
                )
                target.git_dir = "{git_dir}/{path}/".format(
                    git_dir=options.git_dir, path=path
                )
                target.working_tree = options.git_work
                target.username = options.git_user
                target.password = options.git_password
                target.commit = None

                try:
                    c3tg = Target(
                        repo=target.repo,
                        git_dir=target.git_dir,
                        working_tree=target.working_tree,
                        username=target.username,
                        password=target.password,
                        commit=target.commit
                    )
                    _update: Any = update
                    _r: Any = _update([c3tg])
                    import typing

                    beeprint.pp(_r)

                except Error as e:
                    print_frame(e)
                    task.code = Error.code
                    task.message = str(e)
                    self.finish(task)

                else:
                    target.commit = version
                    task.context.target = target
                    task.stage = 1

            else:
                task.code = 400
                task.message = "missing version field"
                self.finish(task)

        elif task.stage == 1:
            if self.timer_trigger:
                try:
                    target = task.context.target
                    c3tg = Target(
                        repo=target.repo,
                        git_dir=target.git_dir,
                        working_tree=target.working_tree,
                        username=target.username,
                        password=target.password,
                        commit=target.commit
                    )
                    _checkout: Any = checkout
                    _r = _checkout([c3tg])
                    beeprint.pp(_r)

                except Error as _e:
                    print_frame(_e)
                    task.code = Error.code
                    task.message = str(_e)
                    self.finish(task)

                else:
                    self.check_count += 1
                    task.stage = 2

        elif task.stage == 2:
            task.code = self.trigger_code
            task.message = self.trigger_message
            self.finish(task)
            # FIXME time

    def run_end(self) -> None:
        # reload
        # FIXME check working diff

        if self.timer_trigger and self.check_count:
            _: Any = snapshot
            """
                targets = list()
                try:
                    targets = snapshot(targets)
                except Error as e:
                    print_frame(e)
            """

            try:
                nginx_reload()
            except Error as _e:
                print_frame(_e)
                self.trigger_code = Error.code
                self.trigger_message = str(_e)

            else:
                self.trigger_code = 200
                self.trigger_message = "success"

            self.timer_trigger = 0
            self.check_count = 0
            self.wakeup_worker()
