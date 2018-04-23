import logging.config

from op_center.basic.common import *
from op_center.basic.constant import *
from op_center.basic.exception import *
from op_center.basic.logger import DEFAULT_LOGGING

cfg = json.load(open("op_center/cfg.json"))

logging.config.dictConfig(DEFAULT_LOGGING)
