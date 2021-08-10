"""
:author: Maikel Punie <maikel.punie@gmail.com>
"""
from __future__ import annotations

import json

from velbusaio.command_registry import register_command
from velbusaio.message import Message

COMMAND_CODE = 0xBE


class KwhStatusMessage(Message):
    """
    send by: VMB7IN
    received by:
    """

    def __init__(self, address=None):
        Message.__init__(self)
        self.channel = 0
        self.pulses = 0
        self.counter = 0
        self.kwh = 0
        self.delay = 0
        self.watt = 0

    def populate(self, priority, address, rtr, data):
        """
        -DB1    last 2 bits   = channel
        -DB1    first 6 bist  = pulses
        -DB2-5                = pulse counter
        -DB6-7                = ms/pulse
        :return: None
        """
        self.needs_no_rtr(rtr)
        self.needs_data(data, 7)
        self.set_attributes(priority, address, rtr)
        self.channel = (data[0] & 0x03) + 1
        self.pulses = (data[0] >> 2) * 100
        self.counter = (data[1] << 24) + (data[2] << 16) + (data[3] << 8) + data[4]
        self.kwh = float(float(self.counter) / self.pulses)
        self.delay = (data[5] << 8) + data[6]
        self.watt = float((1000 * 1000 * 3600) / (self.delay * self.pulses))
        if self.watt < 55:
            self.watt = 0

    def to_json(self):
        """
        :return: str
        """
        json_dict = self.to_json_basic()
        json_dict["pulses"] = self.pulses
        json_dict["counter"] = self.counter
        json_dict["kwh"] = self.kwh
        json_dict["delay"] = self.delay
        json_dict["watt"] = self.watt
        json_dict["channel"] = self.channel
        return json.dumps(json_dict)

    def get_channels(self):
        """
        :return: list
        """
        return self.channel


register_command(COMMAND_CODE, KwhStatusMessage)
