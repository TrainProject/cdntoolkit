# coding: utf-8

import logging
import logging.handlers


class Logger:
    format_dict = {
        1: logging.Formatter(
            '[%(asctime)s][%(filename)s][%(name)s][%(levelname)s][threadid:%(thread)s][line:%(lineno)d]%(message)s'
        ),
        2: logging.Formatter(
            '[%(asctime)s][%(filename)s][%(name)s][%(levelname)s][threadid:%(thread)s][line:%(lineno)d]%(message)s'
        ),
        3: logging.Formatter(
            '[%(asctime)s][%(filename)s][%(name)s][%(levelname)s][threadid:%(thread)s][line:%(lineno)d]%(message)s'
        ),
        4: logging.Formatter(
            '[%(asctime)s][%(filename)s][%(name)s][%(levelname)s][threadid:%(thread)s][line:%(lineno)d]%(message)s'
        ),
        5: logging.Formatter(
            '[%(asctime)s][%(filename)s][%(name)s][%(levelname)s][threadid:%(thread)s][line:%(lineno)d]%(message)s'
        )
    }

    def __init__(self, logname, loglevel, logger) -> None:
        self.logger = logging.getLogger(logger)
        self.logger.setLevel(logging.DEBUG)

        fh = logging.handlers.TimedRotatingFileHandler(logname, when='D', interval=1, backupCount=30)
        fh.setLevel(logging.DEBUG)

        # formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        formatter = Logger.format_dict[int(loglevel)]
        fh.setFormatter(formatter)

        self.logger.addHandler(fh)

    def getlog(self):
        return self.logger
