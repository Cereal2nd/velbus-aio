"""
:author: Thomas Delaet <thomas@delaet.org>
"""
from __future__ import annotations

import json

from velbusaio.command_registry import register_command
from velbusaio.message import Message

COMMAND_CODE = 0xFE


class MemoryDataMessage(Message):
    """
    send by: VMB6IN, VMB4RYLD
    received by:
    """

    def __init__(self, address=None):
        Message.__init__(self)
        self.high_address = 0x00
        self.low_address = 0x00
        self.data = 0
        self.set_defaults(address)

    def populate(self, priority, address, rtr, data):
        """
        :return: None
        """
        self.needs_low_priority(priority)
        self.needs_no_rtr(rtr)
        self.needs_data(data, 3)
        self.set_attributes(priority, address, rtr)
        self.high_address = data[0]
        self.low_address = data[1]
        self.data = data[2]

    def data_to_binary(self):
        """
        :return: bytes
        """
        return bytes([COMMAND_CODE, self.high_address, self.low_address, self.data])

    def to_json(self):
        """
        :return: str
        """
        json_dict = self.to_json_basic()
        json_dict["high_add"] = self.high_address
        json_dict["low_addr"] = self.low_address
        json_dict["data"] = self.data
        return json.dumps(json_dict)


register_command(COMMAND_CODE, MemoryDataMessage)
