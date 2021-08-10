"""
:author: Maikel Punie <maikel.punie@gmail.com>
"""
from __future__ import annotations

import json

from velbusaio.command_registry import register_command
from velbusaio.message import Message

COMMAND_CODE = 0xE6


class SensorTemperatureMessage(Message):
    """
    send by: VMBTS, vmbg*pd, ...
    received by:
    """

    def __init__(self, address=None):
        Message.__init__(self)
        self.cur = 0
        self.min = 0
        self.max = 0

    def getCurTemp(self):
        return self.cur

    def getMaxTemp(self):
        return self.max

    def getMinTemp(self):
        return self.min

    def populate(self, priority, address, rtr, data):
        """
        data bytes (high + low)
            1 + 2   = current temp
            3 + 4   = min temp
            5 + 6   = max temp
        :return: None
        """
        self.needs_no_rtr(rtr)
        self.needs_data(data, 6)
        self.set_attributes(priority, address, rtr)
        self.cur = (((data[0] << 8) | data[1]) / 32) * 0.0625
        self.min = (((data[2] << 8) | data[3]) / 32) * 0.0625
        self.max = (((data[4] << 8) | data[5]) / 32) * 0.0625

    def to_json(self):
        """
        :return: str
        """
        json_dict = self.to_json_basic()
        json_dict["cur"] = self.cur
        json_dict["min"] = self.min
        json_dict["max"] = self.max
        return json.dumps(json_dict)


register_command(COMMAND_CODE, SensorTemperatureMessage)
