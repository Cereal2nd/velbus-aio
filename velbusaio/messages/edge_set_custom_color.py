"""
:author: Maikel Punie <maikel.punie@gmail.com>
"""
from __future__ import annotations

import json

from velbusaio.command_registry import register_command
from velbusaio.message import Message

COMMAND_CODE = 0xD4


class EdgeSetCustomColor(Message):
    """
    send by:
    received by: VMB4RYLD
    """

    def __init__(self, address=None):
        Message.__init__(self)
        self.set_defaults(address)
        self.pallet = 31
        self.rgb = False
        self.saturation = 0
        self.red = 0
        self.green = 0
        self.blue = 0

    def populate(self, priority, address, rtr, data):
        """
        :return: None
        """
        self.needs_no_rtr(rtr)
        self.set_attributes(priority, address, rtr)
        self.pallet = data[0]
        self.rgb = bool(data[1] & 0x80)
        self.saturation = data[1] & 0x7F
        self.red = data[2]
        self.green = data[3]
        self.blue = data[4]

    def to_json(self):
        """
        :return: str
        """
        json_dict = self.to_json_basic()
        json_dict["pallet"] = self.pallet
        json_dict["rgb"] = self.rgb
        json_dict["saturation"] = self.saturation
        json_dict["rgb"] = self.rgb
        json_dict["red"] = self.red
        json_dict["green"] = self.green
        json_dict["blue"] = self.blue
        return json.dumps(json_dict)

    def data_to_binary(self):
        """
        :return: bytes
        """
        return bytes(
            [
                COMMAND_CODE,
                self.pallet,
                ((self.rgb << 7) + self.saturation),
                self.red,
                self.green,
                self.blue,
            ]
        )


register_command(COMMAND_CODE, EdgeSetCustomColor)
