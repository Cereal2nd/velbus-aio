"""
:author: Maikel Punie <maikel.punie@gmail.com>
"""
from __future__ import annotations

from velbusaio.command_registry import register_command
from velbusaio.message import Message

COMMAND_CODE = 0xBD


class CounterStatusRequestMessage(Message):
    """
    send by:
    received by: VMB7IN
    """

    def __init__(self, address=None):
        Message.__init__(self)
        self.wait_after_send = 500
        self.set_defaults(address)

    def populate(self, priority, address, rtr, data):
        """
        :return: None
        """
        self.needs_low_priority(priority)
        self.needs_no_rtr(rtr)
        self.needs_data(data, 1)
        self.set_attributes(priority, address, rtr)

    def data_to_binary(self):
        """
        :return: bytes
        """
        return bytes([COMMAND_CODE, 0x0F, 0x00])


register_command(COMMAND_CODE, CounterStatusRequestMessage, "VMB7IN")
