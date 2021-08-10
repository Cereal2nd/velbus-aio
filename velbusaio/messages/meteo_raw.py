"""
:author: Maikel Punie <maikel.punie@gmail.com>
"""
from __future__ import annotations

import json

from velbusaio.command_registry import register_command
from velbusaio.message import Message

COMMAND_CODE = 0xA9


class MeteoRawMessage(Message):
    """
    send by: VMBMETEO
    received by:
    """

    def __init__(self, address=None):
        Message.__init__(self)
        self.rain = 0
        self.light = 0
        self.wind = 0

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
        self.rain = (((data[0] << 8) | data[1]) / 32) * 0.1
        self.light = ((data[2] << 8) | data[3]) / 32
        self.wind = (((data[4] << 8) | data[5]) / 32) * 0.1

    def to_json(self):
        """
        :return: str
        """
        json_dict = self.to_json_basic()
        json_dict["rain"] = self.rain
        json_dict["light"] = self.light
        json_dict["wind"] = self.wind
        return json.dumps(json_dict)


register_command(COMMAND_CODE, MeteoRawMessage, "VMBMETEO")
