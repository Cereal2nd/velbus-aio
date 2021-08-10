"""
:author: Maikel Punie <maikel.punie@gmail.com>
"""
from __future__ import annotations

import json
import logging
import time

from velbusaio.command_registry import register_command
from velbusaio.message import Message

COMMAND_CODE = 0xB7


class SetDate(Message):
    """
    received by all modules
    """

    def __init__(self, address=0x00):
        Message.__init__(self)
        self.logger = logging.getLogger("velbus")
        self._day = None
        self._mon = None
        self._year = None
        self.set_defaults(address)

    def set_defaults(self, address):
        if address is not None:
            self.set_address(address)
        self.set_low_priority()
        self.set_no_rtr()
        lclt = time.localtime()
        self._day = lclt[2]
        self._mon = lclt[1]
        self._year = lclt[0]

    def populate(self, priority, address, rtr, data):
        """
        :return: None
        """
        self.needs_low_priority(priority)
        self.needs_no_rtr(rtr)
        self.needs_data(data, 4)
        self.set_attributes(priority, address, rtr)
        self._day = data[0]
        self._mon = data[1]
        self._year = (data[2] << 8) + data[3]

    def to_json(self):
        """
        :return: str
        """
        json_dict = self.to_json_basic()
        json_dict["day"] = self._day
        json_dict["mon"] = self._mon
        json_dict["year"] = self._year
        return json.dumps(json_dict)

    def data_to_binary(self):
        """
        :return: bytes
        """
        return bytes(
            [
                COMMAND_CODE,
                self._day,
                self._mon,
                (self._year >> 8),
                (self._year & 0x00FF),
            ]
        )


register_command(COMMAND_CODE, SetDate)
