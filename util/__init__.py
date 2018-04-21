# coding=utf-8

import datetime
import os
import socket
import struct
import time
import uuid
from typing import List, Tuple, Any, Callable, Generator
from typing import no_type_check

from orderedattrdict import AttrDict

from .json import AttrJson

try:
    import fcntl
except ImportError:
    fcntl = None
from .exception import print_frame

import twisted.names.hosts
import twisted.names.common
import twisted.internet.reactor
from twisted.python.compat import nativeString
from twisted.internet.epollreactor import EPollReactor


@no_type_check
def __search_file_for_all(hosts_file: Any, name: Any):
    results = []
    try:
        lines = hosts_file.getContent().splitlines()
    except:
        return results

    name = name.lower()
    for line in lines:
        idx = line.find(b'#')
        if idx != -1:
            line = line[:idx]
        if not line:
            continue
        parts = line.split()

        if name.lower().encode() in [s.lower() for s in parts[1:]]:
            results.append(nativeString(parts[0]))
    return results


@no_type_check
def __get_host_by_name(self, name: Any, timeout: Any=None, effort: int=10):
    return self.lookupAddress(
        name, timeout
    ).addCallback(self._cbRecords, name, effort)


@no_type_check
def monkey_patch() -> None:
    twisted.names.hosts.searchFileForAll = __search_file_for_all
    twisted.names.common.ResolverBase.getHostByName = __get_host_by_name


_reactor: EPollReactor = twisted.internet.reactor


def reactor() -> EPollReactor:
    return _reactor


_uuid: str = None


def set_uuid(__uuid: str) -> None:
    global _uuid
    _uuid = __uuid


def get_uuid() -> str:
    global _uuid
    if not _uuid:
        names = [
            'system-manufacturer',
            'system-product-name',
            'system-version',
            'system-serial-number',
            'system-uuid',
        ]

        out = []
        for name in names:
            import subprocess
            p = subprocess.Popen(
                "dmidecode -s {name}".format(name=name),
                stdout=subprocess.PIPE,
                shell=True
            )
            data, _ = p.communicate()
            out.append(data.decode())

        _uuid = str(uuid.uuid5(
            uuid.NAMESPACE_URL, '.'.join(out))
        )

    return _uuid


_host_kernel: str = str()


def get_kernel() -> str:
    global _host_kernel
    if not _host_kernel:
        try:
            f = open("/proc/version")
            c = f.read()
            v = c.split()[2]
            _host_kernel = v.split("-")[0]
            f.close()
        except Exception as e:
            pass

    return _host_kernel


_host_uptime: str = str()


def get_uptime() -> str:
    global _host_uptime
    if not _host_uptime:
        try:
            f = open("/proc/uptime")
            c = f.read()
            _host_uptime = c.split()[0]
            f.close()
        except Exception as e:
            print_frame(e)

    return _host_uptime


_host_address: List[str] = list()


def get_address() -> str:
    if not _host_address:

        def get_ip_address(ifname: str) -> str:
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                return socket.inet_ntoa(
                    fcntl.ioctl(
                        s.fileno(), 0x8915,  # SIOCGIFADDR
                        struct.pack('256s', ifname[:15].encode())
                    )[20:24]
                )
            except Exception as _e:
                print_frame(_e)

            return None

        try:
            eths = os.listdir('/sys/class/net/')
            for eth in eths:
                if eth != "lo":
                    ip = get_ip_address(eth)
                    if ip is not None:
                        _host_address.append(ip)

        except Exception as e:
            print_frame(e)

    return " ".join(_host_address)


_host_hostname: str = str()


def get_hostname() -> str:
    global _host_hostname
    if not _host_hostname:
        _host = socket.gethostname()
        if _host:
            _host_hostname = _host

    return _host_hostname


def parse_hostname(hostname: str) -> Tuple:
    """
    CDN-JL-CC-CNNET2-47
    CDN-SD-LC-CNC2-132
    CDN-SD-LC-CNC2-132-OLD
    LOGSERVER-JX-NC-CMCC-6-231
    """
    isp: str = None
    idc: str = None

    hostname = hostname.strip().upper()
    hostname.replace('_', '-')
    items: List[str] = hostname.split('-')

    for _ in [0]:
        if 2 < len(items) < 5:
            isp = "unknown"
            del items[-1]
            idc = '_'.join(items)
            break

        if items[-1] == "OLD":
            del items[-1]

        del items[-1]

        if len(items[1]) > 3 or items[1] == "USA":
            break

        item = items[-1]
        if not item:
            item = "1"

        if item.isnumeric():
            replace = True
            item = items[-2]
        else:
            replace = False

        if item[-1].isnumeric():
            isp = item[:-1]
            if replace:
                items[-1] = item[-1]
        else:
            isp = item

        if not idc:
            break

        idc = '_'.join(items)

    return isp, idc


_isp: str = None
_idc: str = None


def get_isp_idc() -> Tuple[str, str]:
    global _isp, _idc
    if _isp is None or _idc is None:
        _isp, _idc = parse_hostname(get_hostname())
    return _isp, _idc


@no_type_check
def _timezone(utc_offset) -> str:
    # Python's division uses floor(), not round() like in other languages:
    #   -1 / 2 == -1 and not -1 / 2 == 0
    # That's why we use abs(utc_offset).
    hours = abs(utc_offset) // 3600
    minutes = abs(utc_offset) % 3600 // 60
    sign = (utc_offset < 0 and '-') or '+'
    return '%c%02d:%02d' % (sign, hours, minutes)


@no_type_check
def _timedelta_to_seconds(timedelta) -> int:
    return (timedelta.days * 86400 + timedelta.seconds +
            timedelta.microseconds // 1000)


@no_type_check
def _utc_offset(date) -> int:
    if isinstance(date, datetime.datetime) and date.tzinfo is not None:
        return _timedelta_to_seconds(date.dst() or date.utcoffset())
    else:
        return 0


@no_type_check
def _string(d, timezone) -> str:
    return ('%04d-%02d-%02dT%02d:%02d:%02d%s' %
            (d.year, d.month, d.day, d.hour, d.minute, d.second, timezone))


@no_type_check
def rfc3339_format(date) -> str:
    if not isinstance(date, datetime.datetime):
        try:
            date = datetime.datetime.utcfromtimestamp(date)
        except TypeError:
            pass

    if not isinstance(date, datetime.date):
        raise TypeError('Expected timestamp or date object. Got %r.' %
                        type(date))

    if not isinstance(date, datetime.datetime):
        date = datetime.datetime(*date.timetuple()[:3])
    utc_offset = _utc_offset(date)

    return _string(date + datetime.timedelta(seconds=utc_offset), 'Z')


@no_type_check
def polyhash(word, a=31, p=997, m=-1) -> int:
    _hash = 0
    for c in word:
        _hash = (_hash * a + ord(c)) % p

    if m == -1:
        return abs(_hash)
    else:
        return abs(_hash % m)

    # https://startupnextdoor.com/spending-a-couple-days-on-hashing-functions/
    # http://www.asmeurer.com/blog/posts/what-happens-when-you-mess-with-hashing-in-python/


def loop_timer(looper: Generator[float, None, None]) -> None:
    diff = next(looper)
    reactor().callLater(diff, loop_timer, looper)


def round_looper(interval: int, offset: int,
                 runner: Callable[[float], None]
                 ) -> Generator[float, None, None]:
    interval *= 100
    while 1:
        start = int(time.time() * 100)
        end = start - start % interval + interval
        diff = round((end - start + offset) / 100.0, 3)
        yield diff
        runner(end // 100)


@no_type_check
def perf() -> None:
    import cProfile
    import pstats
    import io

    pr = cProfile.Profile()
    pr.enable()

    def end() -> None:
        pr.disable()
        s = io.StringIO()
        sortby = 'cumulative'
        ps = pstats.Stats(pr, stream=s).sort_stats(sortby)
        ps.print_stats()
        print(s.getvalue())

    reactor().callLater(60, end)


class GeneralException(Exception):
    def __init__(self, code: int, message: str) -> None:
        self.code: int = code
        self.message: str = message
        super().__init__(message)


@no_type_check
class FrozenClass:
    _isfrozen = False

    def __init__(self) -> None:
        self._freeze()

    def __setattr__(self, key: str, value: object) -> None:
        if self._isfrozen and not hasattr(self, key):
            print_frame(TypeError("%r is a frozen class, key is %s" % (self, key)))
        object.__setattr__(self, key, value)

    def _freeze(self) -> None:
        self._isfrozen = True

    @classmethod
    def __value(cls, v: object) -> object:
        if isinstance(v, FrozenClass):
            return AttrDict(v)

        elif isinstance(v, list):
            return [
                x if not isinstance(x, FrozenClass) else AttrDict(x)
                for x in v
            ]

        elif isinstance(v, dict):
            return {
                n: x if not isinstance(x, FrozenClass) else AttrDict(x)
                for n, x in v.items()
            }

        elif isinstance(v, tuple):
            return (
                x if not isinstance(x, FrozenClass) else AttrDict(x)
                for x in v
            )

        elif isinstance(v, set):
            return {
                x if not isinstance(x, FrozenClass) else AttrDict(x)
                for x in v
            }

        else:
            return v

    def __iter__(self) -> Generator[Tuple[str, object], None, None]:
        for k, v in self.__dict__.items():
            if k.find('__') != -1:
                # yield k[2:], self.__value(v)
                yield k.split('__')[1], self.__value(v)

    def __str__(self) -> str:
        a = AttrDict(self)
        _str = AttrJson.dumps(a)
        print(_str, type(self))
        return _str
