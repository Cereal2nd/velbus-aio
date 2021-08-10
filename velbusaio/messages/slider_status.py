"""
:author: Frank van Breugel
"""
from __future__ import annotations

import json

from velbusaio.command_registry import register_command
from velbusaio.message import Message

COMMAND_CODE = 0x0F


class SliderStatusMessage(Message):
    """
    sent by: VMBDME
    received by:
    """

    def __init__(self, address=None):
        Message.__init__(self)
        self.channel = 0
        self.slider_state = 0
        self.slider_long_pressed = 0
        self.set_defaults(address)

    def populate(self, priority, address, rtr, data):
        """
        :return: None
        """
        self.needs_high_priority(priority)
        self.needs_no_rtr(rtr)
        self.needs_data(data, 3)
        self.set_attributes(priority, address, rtr)
        self.channel = self.byte_to_channel(data[0])
        self.slider_state = int.from_bytes([data[1]], byteorder="big")
        self.slider_long_pressed = data[2]

    def to_json(self):
        """
        :return: str
        """
        json_dict = self.to_json_basic()
        json_dict["channel"] = self.channel
        json_dict["slider_state"] = self.slider_state
        json_dict["slider_long_pressed"] = self.slider_long_pressed
        return json.dumps(json_dict)

    def cur_slider_state(self):
        """
        :return: int
        """
        return self.slider_state

    def data_to_binary(self):
        """
        :return: bytes
        """
        return bytes(
            [
                COMMAND_CODE,
                self.channels_to_byte([self.channel]),
                self.slider_state,
                self.slider_long_pressed,
            ]
        )


register_command(COMMAND_CODE, SliderStatusMessage, "VMBDME")
register_command(COMMAND_CODE, SliderStatusMessage, "VMB4DC")
register_command(COMMAND_CODE, SliderStatusMessage, "VMBDMI")
register_command(COMMAND_CODE, SliderStatusMessage, "VMBDMI-R")
register_command(COMMAND_CODE, SliderStatusMessage, "VMB1LED")
