"""
:author: Thomas Delaet <thomas@delaet.org>
"""
from velbus.message import Message

COMMAND_CODE = 0x0A


class BusActiveMessage(Message):
    """
    send by:
    received by: VMB1USB
    """

    def set_defaults(self, address):
        if address is not None:
            self.set_address(address)
        self.set_high_priority()
        self.set_no_rtr()

    def populate(self, priority, address, rtr, data):
        assert isinstance(data, bytes)
        self.needs_high_priority(priority)
        self.needs_no_rtr(rtr)
        self.set_attributes(priority, address, rtr)
        self.needs_no_data(data)

    def data_to_binary(self):
        """
        :return: bytes
        """
        return bytes([COMMAND_CODE])
