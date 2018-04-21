# coding=utf-8

# data is from /proc/diskstats
# Calculate disk statistics.  We handle 2.6 kernel output only, both
# pre-2.6.25 and post (which added back per-partition disk stats).
# (diskstats output significantly changed from 2.4).
# The fields (from iostats.txt) are mainly rate counters
# (either number of operations or number of milliseconds doing a
# particular operation), so let's just let TSD do the rate
# calculation for us.
#
# /proc/diskstats has 11 stats for a given device
# these are all rate counters except ios_in_progress
# .read_requests       Number of reads completed
# .read_merged         Number of reads merged
# .read_sectors        Number of sectors read
# .msec_read           Time in msec spent reading
# .write_requests      Number of writes completed
# .write_merged        Number of writes merged
# .write_sectors       Number of sectors written
# .msec_write          Time in msec spent writing
# .ios_in_progress     Number of I/O operations in progress
# .msec_total          Time in msec doing I/O
# .msec_weighted_total Weighted time doing I/O (multiplied by ios_in_progress)

# in 2.6.25 and later, by-partition stats are reported same as disks
# in 2.6 before 2.6.25, partitions have 4 stats per partition
# .read_issued
# .read_sectors
# .write_issued
# .write_sectors
# For partitions, these *_issued are counters collected before
# requests are merged, so aren't the same as *_requests (which is
# post-merge, which more closely represents represents the actual
# number of disk transactions).

# Given that diskstats provides both per-disk and per-partition data,
# for TSDB purposes we want to put them under different metrics (versus
# the same metric and different tags).  Otherwise, if you look at a
# given metric, the data for a given box will be double-counted, since
# a given operation will increment both the disk series and the
# partition series.  To fix this, we output by-disk data to iostat.disk.*
# and by-partition data to iostat.part.*.

# TODO: Add additional tags to map partitions/disks back to mount
# points/swap so you can (for example) plot just swap partition
# activity or /var/lib/mysql partition activity no matter which
# disk/partition this happens to be.  This is nontrivial, especially
# when you have to handle mapping of /dev/mapper to dm-N, pulling out
# swap partitions from /proc/swaps, etc.

import copy
import os
import re
from typing import Tuple, Dict

from orderedattrdict import AttrDict

from .collector import Collector


class IostatCollector(Collector):
    def __init__(self) -> None:
        super().__init__()

        # Docs come from the Linux kernel's Documentation/iostats.txt
        self.FIELDS_DISK: Tuple[str, ...] = (
            "read_requests",        # Total number of reads completed successfully.
            "read_merged",          # Adjacent read requests merged in a single req.
            "read_sectors",         # Total number of sectors read successfully.
            "msec_read",            # Total number of ms spent by all reads.
            "write_requests",       # total number of writes completed successfully.
            "write_merged",         # Adjacent write requests merged in a single req.
            "write_sectors",        # total number of sectors written successfully.
            "msec_write",           # Total number of ms spent by all writes.
            "ios_in_progress",      # Number of actual I/O requests currently in flight.
            "msec_total",           # Amount of time during which ios_in_progress >= 1.
            "msec_weighted_total",  # Measure of recent I/O completion time and backlog.
        )

        self.FIELDS_PART: Tuple[str, ...] = (
            "read_issued",
            "read_sectors",
            "write_issued",
            "write_sectors",
        )

        self.prev_times = (0, 0)

    def name(self) -> str:
        return "IostatCollector"

    def read_uptime(self) -> Tuple[float, float]:
        try:
            f_uptime = open("/proc/uptime", encoding='utf-8')
            line = f_uptime.readline()

            curr_times = line.split(None)
            delta_times = (float(curr_times[0]) - float(self.prev_times[0]),  float(curr_times[1]) - float(self.prev_times[1]))
            self.prev_times = curr_times
            return delta_times

        finally:
            f_uptime.close()

    @staticmethod
    def get_system_hz() -> int:
        """Return system hz use SC_CLK_TCK."""
        ticks = os.sysconf(os.sysconf_names['SC_CLK_TCK'])

        if ticks == -1:
            return 100
        else:
            return ticks

    @staticmethod
    def is_device(device_name: str, allow_virtual: int) -> bool:
        """Test whether given name is a device or a partition, using sysfs."""
        device_name = re.sub('/', '!', device_name)

        if allow_virtual:
            devicename = "/sys/block/" + device_name + "/device"
        else:
            devicename = "/sys/block/" + device_name

        return os.access(devicename, os.F_OK)

    def collect(self, ts: int) -> None:
        init_stats = {
            "read_requests": 0,
            "read_merged": 0,
            "read_sectors": 0,
            "msec_read": 0,
            "write_requests": 0,
            "write_merged": 0,
            "write_sectors": 0,
            "msec_write": 0,
            "ios_in_progress": 0,
            "msec_total": 0,
            "msec_weighted_total": 0,
        }

        prev_stats: Dict = dict()
        f_diskstats = open("/proc/diskstats", encoding='utf-8')
        HZ = self.get_system_hz()
        itv = 1.0

        f_diskstats.seek(0)
        itv = self.read_uptime()[0]

        for line in f_diskstats:
            # maj, min, devicename, [list of stats, see above]
            values = line.split(None)
            # shortcut the deduper and just skip disks that
            # haven't done a single read.  This eliminates a bunch
            # of loopback, ramdisk, and cdrom devices but still
            # lets us report on the rare case that we actually use
            # a ramdisk.
            if values[3] == "0":
                continue

            if int(values[1]) % 16 == 0 and int(values[0]) > 1:
                metric = "iostat.disk."
            else:
                continue
                # metric = "iostat.part."

            device = values[2]
            if len(values) == 14:
                # full stats line
                for i in range(11):
                    data = AttrDict()
                    data.metric = "%s%s" % (metric, self.FIELDS_DISK[i])
                    data.ts = ts
                    data.value = int(values[i+3])
                    data.dev = device
                    self.send_message(data)

                ret = self.is_device(device, 0)
                # if a device or a partition, calculate the svctm/await/util
                if not ret:
                    continue

                stats = dict(zip(self.FIELDS_DISK, values[3:]))
                if device not in prev_stats:
                    prev_stats[device] = init_stats

                rd_ios = float(stats.get(b"read_requests".decode('ascii')))
                wr_ios = float(stats.get(b"write_requests".decode('ascii')))
                nr_ios = rd_ios + wr_ios
                prev_rd_ios = float(prev_stats[device].get(b"read_requests".decode('ascii')))
                prev_wr_ios = float(prev_stats[device].get(b"write_requests".decode('ascii')))
                prev_nr_ios = prev_rd_ios + prev_wr_ios
                tput = ((nr_ios - prev_nr_ios) * float(HZ) / float(itv))
                util = ((float(stats.get(b"msec_total".decode('ascii'))) - float(prev_stats[device].get(b"msec_total".decode('ascii')))) * float(HZ) / float(itv))
                svctm = 0.0
                await = 0.0
                r_await = 0.0
                w_await = 0.0

                if tput:
                    svctm = util / tput

                rd_ticks = stats.get(b"msec_read".decode('ascii'))
                wr_ticks = stats.get(b"msec_write".decode('ascii'))

                prev_rd_ticks = prev_stats[device].get(b"msec_read".decode('ascii'))
                prev_wr_ticks = prev_stats[device].get(b"msec_write".decode("ascii"))

                if rd_ios != prev_rd_ios:
                    r_await = (float(rd_ticks) - float(prev_rd_ticks) ) / float(rd_ios - prev_rd_ios)
                if wr_ios != prev_wr_ios:
                    w_await = (float(wr_ticks) - float(prev_wr_ticks) ) / float(wr_ios - prev_wr_ios)
                if nr_ios != prev_nr_ios:
                    await = (float(rd_ticks) + float(wr_ticks) - float(prev_rd_ticks) - float(prev_wr_ticks)) / float(nr_ios - prev_nr_ios)

                data = AttrDict()
                data.metric = "%s%s" % (metric, "svctm")
                data.ts = ts
                data.value = round(svctm, 2)
                data.dev = device
                self.send_message(data)

                data = AttrDict()
                data.metric = "%s%s" % (metric, "r_await")
                data.ts = ts
                data.value = round(r_await, 2)
                data.dev = device
                self.send_message(data)

                data = AttrDict()
                data.metric = "%s%s" % (metric, "w_await")
                data.ts = ts
                data.value = round(w_await, 2)
                data.dev = device
                self.send_message(data)

                data = AttrDict()
                data.metric = "%s%s" % (metric, "await")
                data.ts = ts
                data.value = round(await, 2)
                data.dev = device
                self.send_message(data)

                data = AttrDict()
                data.metric = "%s%s" % (metric, "util")
                data.ts = ts
                data.value = round(util/1000.0, 2)
                data.dev = device
                self.send_message(data)

                prev_stats[device] = copy.deepcopy(stats)

            elif len(values) == 7:
                # partial stats line
                for i in range(4):
                    data = AttrDict()
                    data.metric = "%s%s" % (metric, self.FIELDS_PART[i])
                    data.ts = ts
                    data.value = int(values[i+3])
                    data.dev = device
                    self.send_message(data)

            else:
                pass
                # print >> sys.stderr, "Cannot parse /proc/diskstats line: ", line
