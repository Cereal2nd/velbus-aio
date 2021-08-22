"""
:author: Frank van Breugel
"""
from __future__ import annotations

import json
import logging

from velbusaio.command_registry import register_command
from velbusaio.message import Message

COMMAND_CODE = 0x07


class SetDimmerMessage(Message):
    """
    send by:
    received by: VMBDME, VMB4DC
    """

    def __init__(self, address=None):
        Message.__init__(self)
        self.dimmer_channels = []
        self.logger = logging.getLogger("velbus")
        self.dimmer_state = 0
        self.dimmer_transitiontime = 0
        self.set_defaults(address)

    def set_defaults(self, address):
        if address is not None:
            self.set_address(address)
        self.set_high_priority()
        self.set_no_rtr()

    def populate(self, priority, address, rtr, data):
        """
        :return: None
        """
        self.needs_high_priority(priority)
        self.needs_no_rtr(rtr)
        self.needs_data(data, 4)
        self.set_attributes(priority, address, rtr)
        self.dimmer_channels = self.byte_to_channels(data[0])
        self.dimmer_state = data[1]
        self.dimmer_transitiontime = int.from_bytes(
            data[2:3], byteorder="big", signed=False
        )

    def to_json(self):
        """
        :return: str
        """
        json_dict = self.to_json_basic()
        json_dict["channels"] = self.dimmer_channels
        json_dict["state"] = self.dimmer_state
        json_dict["transitiontime"] = self.dimmer_transitiontime
        return json.dumps(json_dict)

    def data_to_binary(self):
        """
        :return: bytes
        """
        return (
            bytes(
                [
                    COMMAND_CODE,
                    self.channels_to_byte(self.dimmer_channels),
                    self.dimmer_state,
                ]
            )
            + self.dimmer_transitiontime.to_bytes(2, byteorder="big", signed=False)
        )


register_command(COMMAND_CODE, SetDimmerMessage, "VMBDME")
register_command(COMMAND_CODE, SetDimmerMessage, "VMB4DC")
register_command(COMMAND_CODE, SetDimmerMessage, "VMBDMI")
register_command(COMMAND_CODE, SetDimmerMessage, "VMBDMI-R")
register_command(COMMAND_CODE, SetDimmerMessage, "VMB1LED")
