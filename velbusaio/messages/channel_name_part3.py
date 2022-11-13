"""
:author: Thomas Delaet <thomas@delaet.org>
"""
from __future__ import annotations

from velbusaio.command_registry import register
from velbusaio.message import Message

COMMAND_CODE = 0xF2


@register(COMMAND_CODE)
class ChannelNamePart3Message(Message):
    """
    send by: VMB6IN, VMB4RYLD
    received by:
    """

    def __init__(self, address=None):
        Message.__init__(self)
        self.channel = 0
        self.name = ""
        self.set_defaults(address)

    def populate(self, priority, address, rtr, data):
        """
        :return: None
        """
        self.needs_low_priority(priority)
        self.needs_no_rtr(rtr)
        self.needs_data(data, 5)
        self.set_attributes(priority, address, rtr)
        channels = self.byte_to_channels(data[0])
        self.needs_one_channel(channels)
        self.channel = channels[0]
        self.name = "".join([chr(x) for x in data[1:5]])

    def data_to_binary(self):
        """
        :return: bytes
        """
        return bytes([COMMAND_CODE, self.channels_to_byte([self.channel])]) + bytes(
            self.name, "ascii", "ignore"
        )


@register(COMMAND_CODE, "VMBGP1")
@register(COMMAND_CODE, "VMBEL1")
@register(COMMAND_CODE, "VMBGP1-2")
@register(COMMAND_CODE, "VMBGP2")
@register(COMMAND_CODE, "VMBEL2")
@register(COMMAND_CODE, "VMBGP2-2")
@register(COMMAND_CODE, "VMBGP4")
@register(COMMAND_CODE, "VMBEL4")
@register(COMMAND_CODE, "VMBGP4-2")
@register(COMMAND_CODE, "VMBGPO")
@register(COMMAND_CODE, "VMBGPOD")
@register(COMMAND_CODE, "VMBGPOD-2")
@register(COMMAND_CODE, "VMBELO")
@register(COMMAND_CODE, "VMBGP4PIR")
@register(COMMAND_CODE, "VMBGP4PIR-2")
@register(COMMAND_CODE, "VMBDMI")
@register(COMMAND_CODE, "VMBDMI-R")
@register(COMMAND_CODE, "VMBIN")
@register(COMMAND_CODE, "VMBKP")
@register(COMMAND_CODE, "VMBELPIR")
@register(COMMAND_CODE, "VMBDALI")
class ChannelNamePart3Message2(ChannelNamePart3Message):
    """
    send by: VMBGP*, VMBDALI
    received by:
    """

    def populate(self, priority, address, rtr, data):
        """
        :return: None
        """
        self.needs_low_priority(priority)
        self.needs_no_rtr(rtr)
        self.needs_data(data, 5)
        self.set_attributes(priority, address, rtr)
        self.channel = data[0]
        self.name = "".join([chr(x) for x in data[1:]])


@register(COMMAND_CODE, "VMB1BL")
@register(COMMAND_CODE, "VMB2BL")
class ChannelNamePart3Message3(ChannelNamePart3Message):
    """
    send by: VMBGP*
    received by:
    """

    def populate(self, priority, address, rtr, data):
        """
        :return: None
        """
        self.needs_low_priority(priority)
        self.needs_no_rtr(rtr)
        self.needs_data(data, 5)
        self.set_attributes(priority, address, rtr)
        self.channel = (data[0] >> 1) & 0x03
        self.name = "".join([chr(x) for x in data[1:]])
