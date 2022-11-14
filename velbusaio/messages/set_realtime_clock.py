"""
:author: Maikel Punie <maikel.punie@gmail.com>
"""
from __future__ import annotations

import time

from velbusaio.command_registry import register
from velbusaio.message import Message

COMMAND_CODE = 0xD8


@register(COMMAND_CODE)
class SetRealtimeClock(Message):
    """
    received by all modules
    """

    def __init__(self, address=0x00):
        Message.__init__(self)
        self._wday = None
        self._hour = None
        self._min = None
        self.set_defaults(address)

    def set_defaults(self, address):
        if address is not None:
            self.set_address(address)
        self.set_low_priority()
        self.set_no_rtr()
        lclt = time.localtime()
        self._wday = lclt[6]
        self._hour = lclt[3]
        self._min = lclt[4]

    def populate(self, priority, address, rtr, data):
        """
        :return: None
        """
        self.needs_low_priority(priority)
        self.needs_no_rtr(rtr)
        self.needs_data(data, 3)
        self.set_attributes(priority, address, rtr)
        self._wday = data[0]
        self._hour = data[1]
        self._min = data[2]

    def data_to_binary(self):
        """
        :return: bytes
        """
        return bytes([COMMAND_CODE, self._wday, self._hour, self._min])
