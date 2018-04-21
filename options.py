# coding=utf-8

from tornado.options import define, parse_command_line, options

from util.json import AttrDict


def load_options() -> None:
    define("major_version", default=0, help="major_version", type=int)
    define("minor_version", default=0, help="minor_version", type=int)
    define("release_version", default=0, help="release_version", type=int)

    define("app", default="", help="pubilsh, sync, tunnel, walker, collect, apm, web, monitor", type=str)
    define("shard", default=0, help="shard number", type=int)
    define("debug", default="", help="s:stopper,p:print log,e:print exception,d:dump,t:timeit.", type=str)
    define("log_level", default="debug", help="set debug log level", type=str)
    define("default_timeout", default=3600, help="sync and tunnel defalut timeout value", type=int)
    define("default_retry", default=3, help="sync and tunnel defalut retry value", type=int)
    define("topic_prefix", default="com.example", help="topic prefix", type=str)

    define("publish_address", default="localhost", help="publish address.", type=str)
    define("publish_port", default=9014, help="publish port.", type=int)
    define("publish_db", default="127.0.0.1:27017", help="mongodb address and port.")
    define("publish_data_name", default="publish", help="mongodb publish data name.")

    define("sync_domain", default="train.example.com", help="sync domain.", type=str)
    define("sync_address", default="localhost", help="sync address.", type=str)
    define("sync_port", default=9014, help="sync port.", type=int)
    define("sync_db", default="127.0.0.1:27017", help="mongodb address and port.")
    define("sync_data_name", default="sync", help="mongodb sync data name.")

    define("tunnel_address", default="localhost", help="tunnel address.", type=str)
    define("tunnel_port", default=9016, help="tunnel port.", type=int)
    define("tunnel_db", default="127.0.0.1:27017", help="mongodb address and port.")
    define("tunnel_data_name", default="tunnel", help="mongodb tunnel data name.")

    define("web_address", default="localhost", help="web address.", type=str)
    define("web_port", default=9005, help="web port.", type=int)

    define("monitor_address", default="", help="monitor address.", type=str)
    define("monitor_port", default=9005, help="monitor port.", type=int)

    define("router", default="ws://train.example.com/tunnel/", help="crossbar address.", type=str)
    define("router_url", default="ws://127.0.0.1/{port}/tunnel/", help="crossbar address.", type=str)
    define("router_port_start", default=48080, help="crossbar start port.", type=int)
    define("router_port_end", default=48096, help="crossbar end port.", type=int)
    define("router_port_step", default=1, help="crossbar port step.", type=int)
    define("router_domain", default="tunnel", help="crossbar tunnel", type=str)

    define("cdb_url", default="http://www.example.com/cdb/tag/search", help="cdb url.", type=str)
    define("cdb_file", default="", help="cdb file path.", type=str)
    define("cdb_uuid", default="http://www.example.com/tag/search?q=le.cdb.uuid", help="cdb uuid url.", type=str)
    define("cdb_uuid_file", default="", help="cdb uuid file path.", type=str)
    define("cdb_data", default="", help="cdb data by user.", type=str)

    define("uuid", default="", help="set fix uuid", type=str)
    define("dns_port", default=35353, help="use localhost dns port.", type=int)
    define("walker_interval", default=30, help="walker timer interval", type=int)
    define("collect_interval", default=10, help="collect timer interval", type=int)
    define("enable_collector", default="ats:if:ngx:log", help="enable collectors.", type=str)

    define("git_server", default="train.example.com", help="git server address", type=str)
    define("git_user", default="OSS-config_manager", help="for git server", type=str)
    define("git_password", default="", help="for git server", type=str)
    define("git_dir", default="/usr/local/git_repo", help="for git dir", type=str)
    define("git_work", default="/usr/local/nginx/conf", help="for git working tree", type=str)

    define("role", default="master", help="apm role.", type=str)
    define("apm_multiple", default=2, help="apm multiple.", type=int)
    define("apm_client", default="tcp:host=127.0.0.1:port=580{port:02d}", help="apm server address.", type=str)
    define("apm_server", default="tcp:port=580{port:02d}", help="apm listen address.", type=str)

    define("influx_addrs", default="127.0.0.1", help="influxdb address.", type=str)
    # define("influx_addrs", default="124.95.176.16:124.95.176.17:124.95.176.18:124.95.176.19", help="influxdb address.", type=str)
    define("influx_ports", default="5252:6262:7272:8282", help="influxdb port.", type=str)
    # define("influx_ports", default="7272:8282", help="influxdb port.", type=str)

    define("elasticsearch_online", default="127.0.0.1:9000", help="online elasticsearch address.", type=str)
    define("elasticsearch_offline", default="127.0.0.1:9201", help="offline elasticsearch address.", type=str)

    define("param", default="", help="param for private app", type=str)
    define("config", default=AttrDict(), help="internal config for app", type=AttrDict)

    parse_command_line()

    define("topic_transaction_post", default='.'.join((options.topic_prefix, "sync.transaction.post")), type=str)
    define("topic_transaction_get", default='.'.join((options.topic_prefix, "sync.transaction.get")), type=str)
    define("topic_transaction_put", default='.'.join((options.topic_prefix, "sync.transaction.put")), type=str)
    define("topic_transaction_delete", default='.'.join((options.topic_prefix, "sync.transaction.delete")), type=str)

    define("topic_transfer_post", default='.'.join((options.topic_prefix, "tunnel.transfer.post")), type=str)
    define("topic_transfer_get", default='.'.join((options.topic_prefix, "tunnel.transfer.get")), type=str)
    define("topic_transfer_put", default='.'.join((options.topic_prefix, "tunnel.transfer.put")), type=str)
    define("topic_transfer_delete", default='.'.join((options.topic_prefix, "tunnel.transfer.delete")), type=str)

    define("topic_config_get", default='.'.join((options.topic_prefix, "config.get")), type=str)
    define("topic_apm_collector", default='.'.join((options.topic_prefix, "apm.collector")), type=str)

    if options.app == "walker":
        options.config.unix_sock = "unix:/tmp/walker_collector:lockfile=1"

    elif options.app == "collect":
        options.config.unix_sock = "unix:/tmp/walker_collector:timeout=5"
        options.config.collectors = options.enable_collector.split(":")

    else:
        options.dns_port = 0

    if options.app == "config":
        hostname = list()

        context = AttrDict()
        context.path = "www_example_com_edge"
        context.version = "a36711c582fb53a5c13d1bd2b67f6e09a30c9d74"

        options.config.hostname = hostname
        options.config.context = context

    if options.app == 'web':
        options.config.METRIC_URL = {
            0: "127.0.0.1:8186",
            1: "127.0.0.1:8286",
            2: "127.0.0.1:8486",
            3: "127.0.0.1:8586",
            4: "127.0.0.1:8186",
            5: "127.0.0.1:8286",
            6: "127.0.0.1:8486",
            7: "127.0.0.1:8586"
        }

        options.config.DASHBOARD_URL = "http://127.0.0.1:3000/dashboard/db/"
        options.config.log_name = "grafana_tool_main.log"
        options.config.log_dir = "logs"
        options.config.error = ""

        options.config.SELECT = {
            "iostat.disk.read_requests": "derivative(1s)",
            "iostat.disk.read_sectors": "derivative(1s)",
            "iostat.disk.write_sectors": "derivative(1s)",
            "iostat.disk.msec_read": "derivative(1s)",
            "iostat.disk.msec_write": "derivative(1s)",
            "iostat.disk.msec_total": "derivative(1s)",
            "iostat.disk.util": "math(/100)",
            "proc.net.bytes": "derivative(1s)",
            "proc.net.packets": "derivative(1s)",
            "net.stat.tcp.abort": "derivative(1s)",
            "net.stat.tcp.receive.queue.full": "derivative(1s)",
            "net.stat.tcp.abort.failed": "derivative(1s)",
            "net.stat.tcp.retransmit": "derivative(1s)",
            "net.stat.tcp.delayedack": "derivative(1s)",
            "net.stat.tcp.congestion.recovery": "derivative(1s)",
            "net.stat.tcp.packetloss.recovery": "derivative(1s)",
            "net.stat.tcp.reording": "derivative(1s)",
            "net.stat.tcp.syncookies": "derivative(1s)",
            "ngx.status.accepts": "derivative(1s)",
            "ngx.status.handled": "derivative(1s)",
            "ngx.status.requests": "derivative(1s)"
        }

        options.config.GROUPBY = {
            "proc.net.bytes": "tag(direction)",
            "proc.net.packets": "tag(direction)",
            "net.stat.tcp.retransmit": "tag(type)",
            "net.stat.tcp.abort": "tag(type)",
            "net.stat.tcp.delayedack": "tag(type)",
            "net.stat.tcp.congestion.recovery": "tag(type)",
            "net.stat.tcp.packetloss.recovery": "tag(type)",
            "net.stat.tcp.reording": "tag(detectedby)",
            "net.stat.tcp.syncookies": "tag(type)"
        }

        options.config.UNIT = {
            "proc.net.bytes": "Bps",
            "ats.status.client_throughput_out": "Mbits"
        }

    if options.app == 'apm':
        options.config.metric_shard = {
            "ats.status.proxy.process.cache.bytes_used" : 0,
            "ats.status.proxy.process.cache.ram_cache.bytes_used" : 0,
            "ats.status.proxy.process.cache.direntries.used" : 0,
            "ats.status.proxy.node.current_client_connections" : 0,
            "ats.status.proxy.node.current_server_connections" : 0,
            "ats.status.proxy.node.user_agent_xacts_per_second" : 0,
            "ats.status.proxy.node.client_throughput_out" : 0,
            "ats.status.proxy.node.bandwidth_hit_ratio" : 0,
            "ats.status.proxy.node.cache_hit_mem_ratio" : 0,
            "ats.status.proxy.node.cache_hit_ratio" : 0,
            "ping.speed" : 0,
            "ngx.log.body_size.max" : 1,
            "ngx.log.body_size.mid" : 1,
            "ngx.log.body_size.min" : 1,
            "ngx.log.req_time.max" : 2,
            "ngx.log.req_time.mid" : 2,
            "ngx.log.req_time.min" : 2,
            "ngx.log.speed.max" : 3,
            "ngx.log.speed.mid" : 3,
            "ngx.log.speed.min" : 3,
            "ngx.log.ups_time.max" : 4,
            "ngx.log.ups_time.mid" : 4,
            "ngx.log.ups_time.min" : 4,
            "ngx.log.body_size.avg" : 5,
            "ngx.log.req_time.avg" : 5,
            "ngx.log.ups_time.avg" : 5,
            "ngx.log.body_size.sum" : 6,
            "ngx.log.qps" : 6,
            "ngx.log.speed.avg" : 6,
            "ngx.status.actives" : 7,
            "ngx.status.accepts" : 7,
            "ngx.status.handled" : 7,
            "ngx.status.requests" : 7,
            "ngx.status.reading" : 7,
            "ngx.status.writing" : 7,
            "ngx.status.waiting" : 7,
            "proc.net.stat.tcp.tcp_lost_retransmit" : 7,
            "proc.meminfo.memused" : 7,
            "proc.meminfo.memfree" : 7,
            "proc.net.packets.sum" : 7,
            "apm.master.num" : 7
        }
