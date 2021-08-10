"""
:author: Maikel Punie <maikel.punie@gmail.com>
"""
from __future__ import annotations

import json
import struct

from velbusaio.command_registry import register_command
from velbusaio.message import Message

COMMAND_CODE = 0x1C


class CoverPosMessage(Message):
    """
    sent by:
    received by: VMB2BLE
    """

    def __init__(self, address=None):
        Message.__init__(self)
        self.channel = 0
        self.position = 0
        self.set_defaults(address)

    def populate(self, priority, address, rtr, data):
        """
        :return: None
        """
        self.needs_high_priority(priority)
        self.needs_no_rtr(rtr)
        self.needs_data(data, 4)
        self.set_attributes(priority, address, rtr)
        self.channel = self.byte_to_channel(data[0])
        self.position = data[1]

    def to_json(self):
        """
        :return: str
        """
        json_dict = self.to_json_basic()
        json_dict["channel"] = self.channel
        json_dict["position"] = self.position
        return json.dumps(json_dict)

    def set_defaults(self, address):
        if address is not None:
            self.set_address(address)
        self.set_high_priority()
        self.set_no_rtr()

    def data_to_binary(self):
        """
        :return: bytes
        """
        return bytes(
            [
                COMMAND_CODE,
                self.channels_to_byte([self.channel]),
                self.position,
            ]
        )


register_command(COMMAND_CODE, CoverPosMessage, "VMB1BLE")
register_command(COMMAND_CODE, CoverPosMessage, "VMB2BLE")
register_command(COMMAND_CODE, CoverPosMessage, "VMB1BLS")
