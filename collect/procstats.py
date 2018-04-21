# coding=utf-8

import glob
import os
import re
import sys
import time
from typing import Dict, List

from orderedattrdict import AttrDict

from .collector import Collector


class ProcstatsCollector(Collector):
    def __init__(self) -> None:
        super().__init__()

        self.NUMADIR = "/sys/devices/system/node"

        self.f_uptime = open("/proc/uptime", "r", encoding='utf-8')
        self.f_meminfo = open("/proc/meminfo", "r", encoding='utf-8')
        self.f_vmstat = open("/proc/vmstat", "r", encoding='utf-8')
        self.f_stat = open("/proc/stat", "r", encoding='utf-8')
        self.f_loadavg = open("/proc/loadavg", "r", encoding='utf-8')
        self.f_entropy_avail = open("/proc/sys/kernel/random/entropy_avail", "r", encoding='utf-8')
        self.f_interrupts = open("/proc/interrupts", "r", encoding='utf-8')

        self.f_scaling = "/sys/devices/system/cpu/cpu%s/cpufreq/%s_freq"
        self.f_scaling_min: Dict = dict([])
        self.f_scaling_max: Dict = dict([])
        self.f_scaling_cur: Dict = dict([])
        self.f_softirqs = open("/proc/softirqs", "r", encoding='utf-8')

        for cpu in glob.glob("/sys/devices/system/cpu/cpu[0-9]*/cpufreq/scaling_cur_freq"):
            m = re.match("/sys/devices/system/cpu/cpu([0-9]*)/cpufreq/scaling_cur_freq", cpu)
            if not m:
                continue
            cpu_no = m.group(1)
            sys.stderr.write(self.f_scaling % (cpu_no, "min"))
            self.f_scaling_min[cpu_no] = open(self.f_scaling % (cpu_no, "cpuinfo_min"), "r", encoding='utf-8')
            self.f_scaling_max[cpu_no] = open(self.f_scaling % (cpu_no, "cpuinfo_max"), "r", encoding='utf-8')
            self.f_scaling_cur[cpu_no] = open(self.f_scaling % (cpu_no, "scaling_cur"), "r", encoding='utf-8')

        self.numastats = self.find_sysfs_numa_stats()

    def name(self) -> str:
        return "ProcstatsCollector"

    def find_sysfs_numa_stats(self) -> List:
        """Returns a possibly empty list of NUMA stat file names."""
        try:
            nodes = os.listdir(self.NUMADIR)
        except OSError as e:
            if e.errno == 2:  # No such file or directory
                return []   # We don't have NUMA stats.
            raise

        nodes = [node for node in nodes if node.startswith("node")]
        numastats = []
        for node in nodes:
            try:
                numastats.append(os.path.join(self.NUMADIR, node, "numastat"))
            except OSError as e:
                if e.errno == 2:  # No such file or directory
                    continue
                raise
        return numastats

    def print_numa_stats(self, numafiles: List) -> None:
        """From a list of files names, opens file, extracts and prints NUMA stats."""
        for numafilename in numafiles:
            numafile = open(numafilename, 'r', encoding='utf-8')
            node_id = int(numafile.name[numafile.name.find("/node/node")+10:-9])
            ts = int(time.time())
            stats = dict(line.split() for line in numafile.read().splitlines())
            for stat, tag in (# hit: process wanted memory from this node and got it
                              ("numa_hit", "hit"),
                              # miss: process wanted another node and got it from
                              # this one instead.
                              ("numa_miss", "miss")):

                data = AttrDict()
                data.metric = "sys.numa.zoneallocs"
                data.ts = ts
                data.value = int(stats[stat])
                data.node = node_id
                data.type = tag
                self.send_message(data)

            # Count this one as a separate metric because we can't sum up hit +
            # miss + foreign, this would result in double-counting of all misses.
            # See `zone_statistics' in the code of the kernel.
            # foreign: process wanted memory from this node but got it from
            # another node.  So maybe this node is out of free pages.

            data = AttrDict()
            data.metric = "sys.numa.foreign_allocs"
            data.ts = ts
            data.value = int(stats["numa_foreign"])
            data.node = node_id
            self.send_message(data)

            # When is memory allocated to a node that's local or remote to where
            # the process is running.
            for stat, tag in (("local_node", "local"),
                              ("other_node", "remote")):
                data = AttrDict()
                data.metric = "sys.numa.allocation"
                data.ts = ts
                data.value = int(stats[stat])
                data.node = node_id
                data.type = tag
                self.send_message(data)

            # Pages successfully allocated with the interleave policy.
            data = AttrDict()
            data.metric = "sys.numa.interleave"
            data.ts = ts
            data.value = int(stats["interleave_hit"])
            data.node = node_id
            self.send_message(data)

            numafile.close()

    def collect(self, ts: int) -> None:
        # proc.uptime
        self.f_uptime.seek(0)
        ts = int(time.time())
        for line in self.f_uptime:
            m = re.match("(\S+)\s+(\S+)", line)
            if m:
                data = AttrDict()
                data.metric = "proc.uptime.total"
                data.ts = ts
                data.value = m.group(1)
                self.send_message(data)

                data = AttrDict()
                data.metric = "proc.uptime.now"
                data.ts = ts
                data.value = m.group(2)
                self.send_message(data)

        # proc.meminfo
        self.f_meminfo.seek(0)
        ts = int(time.time())
        for line in self.f_meminfo:
            m = re.match("(\w+):\s+(\d+)\s+(\w+)", line)
            if m:
                if m.group(3).lower() == 'kb':
                    # convert from kB to B for easier graphing
                    value = str(int(m.group(2)) * 1024)
                else:
                    value = m.group(2)

                data = AttrDict()
                data.metric = "proc.meminfo.%s" % m.group(1).lower()
                data.ts = ts
                data.value = int(value)
                self.send_message(data)

        # proc.vmstat
        self.f_vmstat.seek(0)
        ts = int(time.time())
        for line in self.f_vmstat:
            m = re.match("(\w+)\s+(\d+)", line)
            if not m:
                continue
            if m.group(1) in ("pgpgin", "pgpgout", "pswpin",
                              "pswpout", "pgfault", "pgmajfault"):

                data = AttrDict()
                data.metric = "proc.vmstat.%s" % m.group(1)
                data.ts = ts
                data.value = int(m.group(2))
                self.send_message(data)

        # proc.stat
        self.f_stat.seek(0)
        for line in self.f_stat:
            m = re.match("(\w+)\s+(.*)", line)
            if not m:
                continue
            if m.group(1).startswith("cpu"):
                cpu_m = re.match("cpu(\d+)", m.group(1))
                if cpu_m:
                    metric_percpu = '.percpu'
                    tags = ' cpu=%s' % cpu_m.group(1)
                else:
                    metric_percpu = ''
                    tags = ''
                fields = m.group(2).split()
                cpu_types = [
                    'user', 'nice', 'system', 'idle', 'iowait',
                    'irq', 'softirq', 'guest', 'guest_nice'
                ]

                # We use zip to ignore fields that don't exist.
                for value, field_name in zip(fields, cpu_types):
                    data = AttrDict()
                    data.metric = "proc.stat.cpu%s" % metric_percpu
                    data.ts = ts
                    data.value = int(value)
                    data.type = field_name
                    if tags:
                        _tags = tags.split()
                        for tag in _tags:
                            if tag:
                                t = tag.split("=", 1)
                                data[t[0]] = t[1]
                    self.send_message(data)

            elif m.group(1) == "intr":
                data = AttrDict()
                data.metric = "proc.stat.intr"
                data.ts = ts
                data.value = int(m.group(2).split()[0])
                self.send_message(data)

            elif m.group(1) == "ctxt":
                data = AttrDict()
                data.metric = "proc.stat.ctxt"
                data.ts = ts
                data.value = int(m.group(2))
                self.send_message(data)

            elif m.group(1) == "processes":
                data = AttrDict()
                data.metric = "proc.stat.processes"
                data.ts = ts
                data.value = int(m.group(2))
                self.send_message(data)

            elif m.group(1) == "procs_blocked":
                data = AttrDict()
                data.metric = "proc.stat.procs_blocked"
                data.ts = ts
                data.value = int(m.group(2))
                self.send_message(data)

        self.f_loadavg.seek(0)

        for line in self.f_loadavg:
            m = re.match("(\S+)\s+(\S+)\s+(\S+)\s+(\d+)/(\d+)\s+", line)
            if not m:
                continue

            data = AttrDict()
            data.metric = "proc.loadavg.1min"
            data.ts = ts
            data.value = m.group(1)
            self.send_message(data)

            data = AttrDict()
            data.metric = "proc.loadavg.5min"
            data.ts = ts
            data.value = m.group(2)
            self.send_message(data)

            data = AttrDict()
            data.metric = "proc.loadavg.15min"
            data.ts = ts
            data.value = m.group(3)
            self.send_message(data)

            data = AttrDict()
            data.metric = "proc.loadavg.runnable"
            data.ts = ts
            data.value = int(m.group(4))
            self.send_message(data)

            data = AttrDict()
            data.metric = "proc.loadavg.total_threads"
            data.ts = ts
            data.value = int(m.group(5))
            self.send_message(data)

        self.f_entropy_avail.seek(0)

        for line in self.f_entropy_avail:
            data = AttrDict()
            data.metric = "proc.kernel.entropy_avail"
            data.ts = ts
            data.value = int(line.strip())
            self.send_message(data)

        self.f_interrupts.seek(0)

        # Get number of CPUs from description line.
        num_cpus = len(self.f_interrupts.readline().split())
        for line in self.f_interrupts:
            cols = line.split()

            irq_type = cols[0].rstrip(":")
            if irq_type.isalnum():
                if irq_type.isdigit():
                    if cols[-2] == "PCI-MSI-edge" and "eth" in cols[-1]:
                        irq_type = cols[-1]
                    else:
                        continue  # Interrupt type is just a number, ignore.
                for i, val in enumerate(cols[1:]):
                    if i >= num_cpus:
                        # All values read, remaining cols contain textual
                        # description
                        break
                    if not val.isdigit():
                        # something is weird, there should only be digit values
                        sys.stderr.write("Unexpected interrupts value %r in"
                                         " %r: " % (val, cols))
                        break
                    data = AttrDict()
                    data.metric = "proc.interrupts"
                    data.ts = ts
                    data.value = int(val)
                    data.type = irq_type
                    data.cpu = i
                    self.send_message(data)

        self.f_softirqs.seek(0)

        # Get number of CPUs from description line.
        num_cpus = len(self.f_softirqs.readline().split())
        for line in self.f_softirqs:
            cols = line.split()

            irq_type = cols[0].rstrip(":")
            for i, val in enumerate(cols[1:]):
                if i >= num_cpus:
                    # All values read, remaining cols contain textual
                    # description
                    break
                if not val.isdigit():
                    # something is weird, there should only be digit values
                    sys.stderr.write("Unexpected softirq value %r in"
                                     " %r: " % (val, cols))
                    break
                data = AttrDict()
                data.metric = "proc.softirqs"
                data.ts = ts
                data.value = int(val)
                data.type = irq_type
                data.cpu = i
                self.send_message(data)

        self.print_numa_stats(self.numastats)

        # Print scaling stats

        for cpu_no in self.f_scaling_min.keys():
            f = self.f_scaling_min[cpu_no]
            f.seek(0)
            for line in f:
                data = AttrDict()
                data.metric = "proc.scaling.min"
                data.ts = ts
                data.value = int(line.rstrip('\n'))
                data.cpu = cpu_no
                self.send_message(data)

        for cpu_no in self.f_scaling_max.keys():
            f = self.f_scaling_max[cpu_no]
            f.seek(0)
            for line in f:
                data = AttrDict()
                data.metric = "proc.scaling.max"
                data.ts = ts
                data.value = int(line.rstrip('\n'))
                data.cpu = cpu_no
                self.send_message(data)

        for cpu_no in self.f_scaling_cur.keys():
            f = self.f_scaling_cur[cpu_no]
            f.seek(0)
            for line in f:
                data = AttrDict()
                data.metric = "proc.scaling.cur"
                data.ts = ts
                data.value = int(line.rstrip('\n'))
                data.cpu = cpu_no
                self.send_message(data)
