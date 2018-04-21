# coding=utf-8

from tornado.options import define, options


def load_options() -> None:
    define("enable_auto_reset", default=-1, help="local git reset check", type=int)
    load_from_file()


def load_from_file() -> None:
    options.enable_auto_reset = 0


def save_to_file() -> None:
    pass
