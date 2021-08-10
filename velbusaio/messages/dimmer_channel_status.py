"""
:author: Frank van Breugel
"""
from __future__ import annotations

import json
import struct

from velbusaio.command_registry import register_command
from velbusaio.message import Message

COMMAND_CODE = 0xB8
CHANNEL_NORMAL = 0x00
CHANNEL_INHIBITED = 0x01
CHANNEL_FORCED_ON = 0x02
CHANNEL_DISABLED = 0x03

LED_OFF = 0
LED_ON = 1 << 7
LED_SLOW_BLINKING = 1 << 6
LED_FAST_BLINKING = 1 << 5
LED_VERY_FAST_BLINKING = 1 << 4


class DimmerChannelStatusMessage(Message):
    """
    sent by: VMB4DC
    received by:
    """

    def __init__(self, address=None):
        Message.__init__(self)
        self.channel = 1
        self.disable_inhibit_forced = 0
        self.dimmer_state = 0
        self.led_status = 0
        self.delay_time = 0
        self.set_defaults(address)

    def populate(self, priority, address, rtr, data):
        """
        :return: None
        """
        self.needs_low_priority(priority)
        self.needs_no_rtr(rtr)
        self.needs_data(data, 7)
        self.set_attributes(priority, address, rtr)
        self.channel = self.byte_to_channel(data[0])
        self.disable_inhibit_forced = data[1]
        self.dimmer_state = int.from_bytes([data[2]], byteorder="big", signed=False)
        self.led_status = data[3]
        (self.delay_time,) = struct.unpack(">L", bytes([0]) + data[4:])

    def to_json(self):
        """
        :return: str
        """
        json_dict = self.to_json_basic()
        json_dict["channel"] = self.channel
        json_dict["disable_inhibit_forced"] = self.disable_inhibit_forced
        json_dict["dimmer_state"] = self.dimmer_state
        json_dict["led_status"] = self.led_status
        json_dict["delay_time"] = self.delay_time
        return json.dumps(json_dict)

    def is_normal(self):
        """
        :return: bool
        """
        return self.disable_inhibit_forced == CHANNEL_NORMAL

    def is_inhibited(self):
        """
        :return: bool
        """
        return self.disable_inhibit_forced == CHANNEL_INHIBITED

    def is_forced_on(self):
        """
        :return: bool
        """
        return self.disable_inhibit_forced == CHANNEL_FORCED_ON

    def is_disabled(self):
        """
        :return: bool
        """
        return self.disable_inhibit_forced == CHANNEL_DISABLED

    def cur_dimmer_state(self):
        """
        :return: int
        """
        return self.dimmer_state

    def data_to_binary(self):
        """
        :return: bytes
        """
        return (
            bytes(
                [
                    COMMAND_CODE,
                    self.channels_to_byte([self.channel]),
                    self.disable_inhibit_forced,
                    self.dimmer_state,
                    self.led_status,
                ]
            )
            + struct.pack(">L", self.delay_time)[-3:]
        )


register_command(COMMAND_CODE, DimmerChannelStatusMessage, "VMB4DC")
register_command(COMMAND_CODE, DimmerChannelStatusMessage, "VMBDMI")
register_command(COMMAND_CODE, DimmerChannelStatusMessage, "VMBDMI-R")
