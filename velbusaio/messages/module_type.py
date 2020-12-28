"""
:author: Thomas Delaet <thomas@delaet.org>
"""
import struct
from velbus.message import Message
from velbus.module_registry import MODULE_DIRECTORY

COMMAND_CODE = 0xFF
MODULES_WITHOUT_SERIAL = {
    0x01: "VMB8PB",
    0x02: "VMB1RY",
    0x03: "VMB1BL",
    0x05: "VMB6IN",
    0x07: "VMB1DM",
    0x08: "VMB4RY",
    0x09: "VMB2BL",
    0x0C: "VMB1TS",
    0x0F: "VMB1LED",
    0x14: "VMBDME",
}


class ModuleTypeMessage(Message):
    """
    send by: VMB6IN, VMB4RYLD
    received by:
    """

    # pylint: disable-msg=R0902

    def __init__(self, address=None):
        Message.__init__(self)
        self.module_type = 0x00
        self.led_on = []
        self.led_slow_blinking = []
        self.led_fast_blinking = []
        self.serial = 0
        self.memory_map_version = 0
        self.build_year = 0
        self.build_week = 0
        self.set_defaults(address)

    def module_name(self):
        """
        :return: str
        """
        if self.module_type in MODULE_DIRECTORY.keys():
            return MODULE_DIRECTORY[self.module_type]
        return "Unknown"

    def populate(self, priority, address, rtr, data):
        """
        :return: None
        """
        assert isinstance(data, bytes)
        self.needs_low_priority(priority)
        self.needs_no_rtr(rtr)
        self.needs_data(data, 4)
        self.set_attributes(priority, address, rtr)
        self.module_type = data[0]
        if data[0] not in MODULES_WITHOUT_SERIAL:
            (self.serial,) = struct.unpack(">L", bytes([0, 0, data[1], data[2]]))
            self.memory_map_version = data[3]
        self.build_year = data[-2]
        self.build_week = data[-1]

    def data_to_binary(self):
        """
        :return: bytes
        """
        return bytes(
            [
                COMMAND_CODE,
                self.module_type,
                self.channels_to_byte(self.led_on),
                self.channels_to_byte(self.led_slow_blinking),
                self.channels_to_byte(self.led_fast_blinking),
                self.build_year,
                self.build_week,
            ]
        )


