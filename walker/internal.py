# coding=utf-8

from orderedattrdict import AttrDict

from util.exception import print_frame
from util.message import WampMessage
from util.observer import signal
from .handler import WalkerHandler


class InternalHandler(WalkerHandler):
    def __init__(self, message: WampMessage) -> None:
        self.major_version = -1
        self.minor_version = -1
        self.release_version = -1
        self.thread = None
        super().__init__(message)

    def name(self) -> str:
        return "internal"

    def run(self, task: AttrDict) -> None:
        rpm_url = task.application.get("rpm_url")
        if rpm_url is not None:
            # cdntoolkit-1.1.2-0.0.0.x86_64.rpm

            file_name = rpm_url.split('/')[-1]
            version = file_name.split("-")[1]
            versions = version.split(".")
            major = int(versions[0])
            minor = int(versions[1])
            release = int(versions[2])

            if (major > self.major_version or
                    minor > self.minor_version or
                    release > self.release_version):
                try:
                    import requests
                    r = requests.get(rpm_url, stream=True)
                    with open(file_name, 'wb') as f:
                        for chunk in r.iter_content(chunk_size=1024):
                            if chunk:
                                f.write(chunk)

                    # rpm -ivh cdntoolkit-1.1.2-0.0.0.x86_64.rpm

                    import sh
                    sh.screen("-dmS", "ctk_update", "rpm", "-Uvh", rpm_url, _bg=True)

                except ImportError:
                    sh = None
                    _ = sh
                    requests = None
                    _ = requests
                except Exception as e:
                    print_frame(e)

                else:
                    message = self.config_changed(task.application)
                    task.message = message
                    task.code = 200 if not task.message else 500

                self.finish(task)

    @signal
    def config_changed(self, config: AttrDict) -> str:
        pass
