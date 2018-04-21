# coding=utf-8

import socket
import struct
from typing import no_type_check, Tuple, List, Union

from orderedattrdict import AttrDict
from twisted.internet import protocol

from util import reactor
from util.exception import print_frame
from .collector import Collector


class ClientUnix(protocol.Protocol):
    def __init__(self) -> None:
        self.metric: str = None
        self.message: str = None
        self.count_msg: int = None
        self.ts: int = None
        self.collector: 'AtsCollector' = None

    def connectionMade(self) -> None:
        message: bytes = self.message.encode('ascii')
        count_msg = len(message)
        message1: bytes = struct.pack('%sss' % count_msg, message, ''.encode('ascii'))
        message2: bytes = struct.pack('ii%sss' % count_msg, 3, len(message1), message1, ''.encode('ascii'))
        message3: bytes = struct.pack('i%ss' % len(message2), len(message2), message2)
        self.count_msg = count_msg
        self.transport.write(message3)

    def dataReceived(self, data: bytes) -> None:
        try:
            count_msg = self.count_msg
            rev_data: bytes = data
            recv_num = len(rev_data)
            (env_str, ecode, recv_type, num1, recv_name, pad_str, recv_value) = \
                struct.unpack("4siii%ss4s%ss" % (count_msg + 1, recv_num - 16 - (count_msg + 1) - 4), rev_data)

            if recv_type == 0 or recv_type == 1:
                if len(recv_value) == 8:
                    recv_value = struct.unpack("q", recv_value)[0]

            elif recv_type == 2:
                if len(recv_value) == 4:
                    recv_value = struct.unpack("f", recv_value)[0]
                elif len(recv_value) == 8:
                    recv_value = struct.unpack("d", recv_value)[0]

            elif recv_type == 3:
                recv_value = recv_value[:-1]

            if type(recv_value) == float:
                recv_value = round(recv_value, 3)

            elif type(recv_value) != int:
                print("break", 'bad value')
                self.transport.loseConnection()
                return

            message: bytes = recv_name[:-1]
            self.collector.print_ats(message.decode('ascii'), recv_value, self.ts)
            self.transport.loseConnection()

        except Exception as e:
            print_frame(e)

        self.transport.loseConnection()


class ClientUnixFactory(protocol.ClientFactory):
    protocol: type = ClientUnix

    def __init__(self, metric: str, message: str,
                 collector: 'AtsCollector', ts: int) -> None:
        self.metric: str = metric
        self.message: str = message
        self.collector: AtsCollector = collector
        self.ts: int = ts
        super().__init__()

    @no_type_check
    def buildProtocol(self, addr):
        p = protocol.ClientFactory.buildProtocol(self, addr)
        p.ts = self.ts
        p.collector = self.collector
        p.metric = self.metric
        p.message = self.message
        return p


class AtsCollector(Collector):
    def __init__(self) -> None:
        super().__init__()
        self.addr: str = None

        self.args: List[Tuple[str, str]] = [
            (
                "proxy.process.cache.bytes_used",
                "cache_bytes_used"
            ),
            (
                "proxy.process.cache.ram_cache.bytes_used",
                "ram_cache_bytes_used"
            ),
            (
                "proxy.process.cache.direntries.used",
                "direntries_used"
            ),
            (
                "proxy.node.current_client_connections",
                "client_connections"
            ),
            (
                "proxy.node.current_server_connections",
                "server_connections"
            ),
            (
                "proxy.node.user_agent_xacts_per_second",
                "user_agent_xacts_per_second"
            ),
            (
                "proxy.node.client_throughput_out",
                "client_throughput_out"
            ),
            (
                "proxy.node.bandwidth_hit_ratio",
                "bandwidth_hit_ratio"
            ),
            (
                "proxy.node.cache_hit_mem_ratio",
                "cache_hit_mem_ratio"
            ),
            (
                "proxy.node.cache_hit_ratio",
                "cache_hit_ratio"
            ),
        ]

        self.addrs: List[str] = [
            '/usr/local/var/trafficserver/mgmtapi.sock',
            '/usr/local/ats/var/trafficserver/mgmtapi.sock',
            '/var/ats/trafficserver/mgmtapi.sock',
            '/usr/local/sbin/ats/var/ats/trafficserver/mgmtapi.sock',
        ]

        for addr in self.addrs:
            sock = self.new_socket(addr)
            if sock:
                print("ATS Unix Sock Connect %s." % addr)
                self.addr = addr
                sock.close()
                break

    def name(self) -> str:
        return "AtsCollector"

    def print_ats(self, metric: str, value: Union[int, float], ts: int) -> None:
        data: AttrDict = AttrDict()
        data.metric = "ats.status.%s" % metric
        data.ts = ts
        data.value = value
        self.send_message(data)

    def new_socket(self, addr: str) -> socket.socket:
        sock: socket.socket = None
        server_address: str = addr
        try:
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            sock.connect(server_address)

        except socket.error as msg:
            if sock:
                sock.close()
            print("connecting_error:", server_address, msg)
            sock = None

        return sock

    def collect(self, ts: int) -> None:
        if self.addr:
            for arg in self.args:
                try:
                    factory: ClientUnixFactory = ClientUnixFactory(arg[1], arg[0], self, ts)
                    reactor().connectUNIX(self.addr, factory, timeout=1)
                except Exception as e:
                    print_frame(e)
