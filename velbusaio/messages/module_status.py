"""
:author: Thomas Delaet <thomas@delaet.org>
"""
from velbus.message import Message
import json

COMMAND_CODE = 0xED


class ModuleStatusMessage(Message):
    """
    send by: VMB6IN
    received by:
    """

    def __init__(self, address=None):
        Message.__init__(self)
        self.closed = []
        self.led_on = []
        self.led_slow_blinking = []
        self.led_fast_blinking = []
        self.set_defaults(address)

    def populate(self, priority, address, rtr, data):
        """
        :return: None
        """
        assert isinstance(data, bytes)
        self.needs_low_priority(priority)
        self.needs_no_rtr(rtr)
        self.needs_data(data, 4)
        self.set_attributes(priority, address, rtr)
        self.closed = self.byte_to_channels(data[0])
        self.led_on = self.byte_to_channels(data[1])
        self.led_slow_blinking = self.byte_to_channels(data[2])
        self.led_fast_blinking = self.byte_to_channels(data[3])

    def data_to_binary(self):
        """
        :return: bytes
        """
        return bytes(
            [
                COMMAND_CODE,
                self.channels_to_byte(self.closed),
                self.channels_to_byte(self.led_on),
                self.channels_to_byte(self.led_slow_blinking),
                self.channels_to_byte(self.led_fast_blinking),
            ]
        )


class ModuleStatusMessage2(Message):
    def __init__(self, address=None):
        Message.__init__(self)
        self.closed = []
        self.enabled = []
        self.normal = []
        self.locked = []
        self.programenabled = []

    def populate(self, priority, address, rtr, data):
        assert isinstance(data, bytes)
        self.needs_low_priority(priority)
        self.needs_no_rtr(rtr)
        self.needs_data(data, 6)
        self.set_attributes(priority, address, rtr)
        self.closed = self.byte_to_channels(data[0])
        self.enabled = self.byte_to_channels(data[1])
        self.normal = self.byte_to_channels(data[2])
        self.locked = self.byte_to_channels(data[3])
        self.programenabled = self.byte_to_channels(data[4])

    def data_to_binary(self):
        """
        :return: bytes
        """
        return bytes(
            [
                COMMAND_CODE,
                self.channels_to_byte(self.closed),
                self.channels_to_byte(self.enabled),
                self.channels_to_byte(self.normal),
                self.channels_to_byte(self.locked),
            ]
        )

    def to_json(self):
        """
        :return: str
        """
        json_dict = self.to_json_basic()
        json_dict["closed"] = self.closed
        json_dict["enabled"] = self.enabled
        json_dict["normal"] = self.normal
        json_dict["locked"] = self.locked
        return json.dumps(json_dict)


class ModuleStatusPirMessage(Message):
    def __init__(self, address=None):
        Message.__init__(self)
        # in data[0]
        self.dark = False  # bit 1
        self.light = False  # bit 2
        self.motion1 = False  # bit 3
        self.light_motion1 = False  # bit 4
        self.motion2 = False  # bit 5
        self.light_motion2 = False  # bit 6
        self.low_temp_alarm = False  # bit 7
        self.high_temp_alarm = False  # bit 8
        # in data[1] and data[2]
        self.light_value = 0

    def populate(self, priority, address, rtr, data):
        assert isinstance(data, bytes)
        self.needs_low_priority(priority)
        self.needs_no_rtr(rtr)
        self.needs_data(data, 7)
        self.set_attributes(priority, address, rtr)
        self.dark = 0x01 & data[0]
        self.light = 0x02 & data[0]
        self.motion1 = 0x04 & data[0]
        self.light_motion1 = 0x08 & data[0]
        self.motion2 = 0x10 & data[0]
        self.light_motion2 = 0x20 & data[0]
        self.low_temp_alarm = 0x40 & data[0]
        self.high_temp_alarm = 0x80 & data[0]
        self.light_value = (data[1] << 8) + data[2]

    def data_to_binary(self):
        """
        :return: bytes
        """
        raise NotImplementedError
