# coding=utf-8

import re
from typing import Tuple

from orderedattrdict import AttrDict

from .collector import Collector

# /proc/net/dev has 16 fields, 8 for receive and 8 for transmit,
# defined below.
# So we can aggregate up the total bytes, packets, etc
# we tag each metric with direction=in or =out
# and iface=

# The new naming scheme of network interfaces
# Lan-On-Motherboard interfaces
# em<port number>_< virtual function instance / NPAR Index >
#
# PCI add-in interfaces
# p<slot number>p<port number>_<virtual function instance / NPAR Index>

FIELDS: Tuple[str, ...] = (
    "bytes", "packets", "errs", "dropped",
    "fifo.errs", "frame.errs", "compressed", "multicast",
    "bytes", "packets", "errs", "dropped",
    "fifo.errs", "collisions", "carrier.errs", "compressed"
)


class IfstatCollector(Collector):
    def __init__(self) -> None:
        super().__init__()
        self.f_netdev = open("/proc/net/dev", encoding='utf-8')

    def name(self) -> str:
        return "IfstatCollector"

    def collect(self, ts: int) -> None:
        # We just care about ethN and emN interfaces.  We specifically
        # want to avoid bond interfaces, because interface
        # stats are still kept on the child interfaces when
        # you bond.  By skipping bond we avoid double counting.

        self.f_netdev.seek(0)

        for line in self.f_netdev:
            m = re.match("\s+(eth?\d+|em\d+_\d+/\d+|em\d+_\d+|em\d+|"
                         "p\d+p\d+_\d+/\d+|p\d+p\d+_\d+|p\d+p\d+):(.*)", line)
            if not m:
                continue

            intf = m.group(1)
            stats = m.group(2).split(None)

            def direction(_i: int) -> str:
                if _i >= 8:
                    return "out"
                return "in"

            for i in range(16):
                data = AttrDict()
                data.metric = "proc.net.%s" % FIELDS[i]
                data.ts = ts
                data.value = int(stats[i])
                data.iface = intf
                data.direction = direction(i)
                self.send_message(data)
