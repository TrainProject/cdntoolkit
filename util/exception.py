# coding=utf-8

import inspect
import opcode
import time
import traceback
from typing import Dict, Any, no_type_check

import beeprint
from IPython.core.ultratb import FormattedTB
from tornado.options import options


class ExceptionHook:
    instance: Any = None

    def __init__(self) -> None:
        pass

    @no_type_check
    def __call__(self, *args, **kwargs):
        if self.instance is None:
            self.instance = FormattedTB(
                mode='Plain', color_scheme='Linux', call_pdb=1
            )

        return self.instance(*args, **kwargs)


def print_frame(e: Exception=None, call_pdb: int=True) -> None:
    _ = call_pdb
    if e is not None:
        print("Excpetion:", repr(e))
    traceback.print_exc()


def print_frame_debug(e: Exception=None, call_pdb: int=True) -> None:
    if e is not None:
        print("Excpetion:", repr(e))
    traceback.print_exc()

    callerframerecord = inspect.stack()[1]
    frame = callerframerecord[0]
    info = inspect.getframeinfo(frame)
    print("{filename}:{lineno}, func: {function}".format(
        filename=info.filename, lineno=info.lineno, function=info.function)
    )

    # w(where): dump stacktrace
    # u(up): up frame
    # d(down): down frame
    # dir(): show local vars
    # locals(): show local vars value
    # l/ll(list): list source code
    # c(continue): run
    # p(print): print everything

    if call_pdb:
        print("start pdb debugger:")
        import pdb
        pdb.set_trace()

    # use w command
    # print("full stack dump:")
    # traceback.print_stack()


def print_name_from_frame(frame: Any) -> str:
    print_name = str()
    args, _, _, value_dict = inspect.getargvalues(frame)
    # print(args, _, value_dict)
    length = len(args)
    if length > 0:
        args_var = str()
        for index, value in enumerate(args):
            if index == 0 and value == 'self':
                instance = value_dict.get('self')
                if instance:
                    print_name = (
                        "{classname}::{coname}".format(
                            classname=getattr(instance, '__class__').__name__,
                            coname=frame.f_code.co_name
                        )
                    )
                    print(print_name, " call:")
                continue

            _value = value_dict.get(value)
            output = beeprint.pp(_value, output=False, max_depth=1)
            args_var += "{name}: {value}".format(name=value, value=output)

        print("arg var:\n{var}".format(var=args_var))
    return print_name


def query_name_from_frame(frame: Any) -> str:
    args, _, _, value_dict = inspect.getargvalues(frame)
    # print(args, _, value_dict)
    length = len(args)
    if length > 0:
        for index, value in enumerate(args):
            if index == 0 and value == 'self':
                instance = value_dict.get('self')
                if instance:
                    return "{classname}::{coname}".format(
                        classname=getattr(instance, '__class__').__name__,
                        coname=frame.f_code.co_name
                    )
    return None


time_record: Dict[str, float] = dict()


def trace(frame: Any, event: Any, arg: Any) -> Any:
    co = frame.f_code

    if event == 'call':
        if (co.co_filename.find("ctk") == -1 or
                co.co_filename.find("util.exception") != -1 or
                co.co_filename.find("util.json") != -1 or
                co.co_name.find("__") != -1 or
                co.co_name.find("print") != -1):
            return None

        else:
            """
            args, _, _, value_dict = inspect.getargvalues(frame)
            print("call", args, _, value_dict)
            # info = inspect.getframeinfo(frame)
            print('call %s' % co.co_name)
            """
            if 'd' in options.debug:
                print_name = print_name_from_frame(frame)
                if 't' in options.debug:
                    if print_name not in time_record:
                        time_record[print_name] = time.time()

            return trace

    elif event == 'return':
        # info = inspect.getframeinfo(frame)
        fun_name = query_name_from_frame(frame)
        if fun_name is not None:
            print(fun_name, " return:")
        else:
            print(co.co_name, " return:")

        if 't' in options.debug:
            e = time.time()
            s = time_record[fun_name]
            e -= s
            if e > 1.0:
                print(fun_name, " is running too long time %s", e)

            del time_record[fun_name]

        # arg_output = beeprint.pp(arg, output=False, max_depth=1)
        # print("arg: %s" % arg_output)

        _locals: Dict = frame.f_locals
        local_var = ""
        for name, value in _locals.items():
            if name.find("__") != -1:
                continue
            try:
                if isinstance(
                        value, (int, tuple, str, slice, set,
                                list, float, dict, complex,
                                bytes, bytearray, bool)
                    ) or str(value.__class__).split("'")[1].split('.')[0] in (
                        "util", "sync", "tunnel", "apm", "application",
                        "collect", "publish", "walker", "web"):

                    if 'd' in options.debug:
                        output = beeprint.pp(value, output=False, max_depth=1)
                        local_var += "{name}: {value}".format(
                            name=name, value=output
                        )
            except:
                pass

        if 'd' in options.debug:
            print("local var:\n{var}".format(var=local_var))

        if arg is None and \
            not opcode.opname[
                frame.f_code.co_code[frame.f_lasti]
                ] in ('RETURN_VALUE', 'YIELD_VALUE'):
            print_frame()

        if fun_name is not None:
            print(fun_name, " return!")
        else:
            print(co.co_name, " return!")

    return None
