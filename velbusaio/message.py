"""
The velbus abstract message class
"""
from __future__ import annotations

import json

from velbusaio.const import (
    ETX,
    PRIORITY_FIRMWARE,
    PRIORITY_HIGH,
    PRIORITY_LOW,
    RTR,
    STX,
)
from velbusaio.helpers import checksum


class ParserError(Exception):
    """
    Error when invalid message is received
    """


class Message:
    """
    Base Velbus message
    """

    def __init__(self, address: int = None) -> None:
        self.priority = PRIORITY_LOW
        self.address = None
        self.rtr = False
        self.data = bytearray()
        self.set_defaults(address)

    def set_attributes(self, priority: int, address: int, rtr: int) -> None:
        """
        :return: None
        """
        self.priority = priority
        self.address = address
        self.rtr = rtr

    def populate(self, priority, address: int, rtr: int, data: int) -> None:
        """
        :return: None
        """
        raise NotImplementedError

    def set_defaults(self, address) -> None:
        """
        Set defaults

        If a message has different than low priority or NO_RTR set,
        then this method needs override in subclass

        :return: None
        """
        if address is not None:
            self.set_address(address)
        self.set_low_priority()
        self.set_no_rtr()

    def set_address(self, address: int) -> None:
        """
        :return: None
        """
        self.address = address

    def to_binary(self):
        """
        :return: bytes
        """
        data_bytes = self.data_to_binary()
        if self.rtr:
            rtr_and_size = RTR | len(data_bytes)
        else:
            rtr_and_size = len(data_bytes)
        header = bytearray([STX, self.priority, self.address, rtr_and_size])
        checksum_string = checksum(header + data_bytes)
        return (
            header
            + data_bytes
            + bytearray.fromhex(f"{checksum_string:02x}")
            + bytearray([ETX])
        )

    def data_to_binary(self):
        """
        :return: bytes
        """
        raise NotImplementedError

    def to_json_basic(self):
        """
        Create JSON structure with generic attributes

        :return: dict
        """
        return {
            "name": self.__class__.__name__,
            "priority": self.priority,
            "address": self.address,
            "rtr": self.rtr,
        }

    def to_json(self) -> str:
        """
        Dump object structure to JSON

        This method should be overridden in subclasses to include more than just generic attributes

        :return: str
        """
        return json.dumps(self.to_json_basic())

    def __str__(self) -> str:
        return self.to_json()

    def byte_to_channels(self, byte: int) -> str:
        """
        :return: list(int)
        """
        # pylint: disable-msg=R0201
        result = []
        for offset in range(0, 8):
            if byte & (1 << offset):
                result.append(offset + 1)
        return result

    def channels_to_byte(self, channels) -> int:
        """
        :return: int
        """
        # pylint: disable-msg=R0201
        result = 0
        for offset in range(0, 8):
            if offset + 1 in channels:
                result = result + (1 << offset)
        return result

    def byte_to_channel(self, byte):
        """
        :return: int
        """
        channels = self.byte_to_channels(byte)
        self.needs_one_channel(channels)
        return channels[0]

    def parser_error(self, message):
        """
        :return: None
        """
        raise ParserError(self.__class__.__name__ + " " + message)

    def needs_rtr(self, rtr):
        """
        :return: None
        """
        if not rtr:
            self.parser_error("needs rtr set")

    def set_rtr(self):
        """
        :return: None
        """
        self.rtr = True

    def needs_no_rtr(self, rtr):
        """
        :return: None
        """
        if rtr:
            self.parser_error("does not need rtr set")

    def set_no_rtr(self):
        """
        :return: None
        """
        self.rtr = False

    def needs_low_priority(self, priority):
        """
        :return: None
        """
        if priority != PRIORITY_LOW:
            self.parser_error("needs low priority set")

    def set_low_priority(self):
        """
        :return: None
        """
        self.priority = PRIORITY_LOW

    def needs_high_priority(self, priority):
        """
        :return: None
        """
        if priority != PRIORITY_HIGH:
            self.parser_error("needs high priority set")

    def set_high_priority(self):
        """
        :return: None
        """
        self.priority = PRIORITY_HIGH

    def needs_firmware_priority(self, priority):
        """
        :return: None
        """
        if priority != PRIORITY_FIRMWARE:
            self.parser_error("needs firmware priority set")

    def set_firmware_priority(self):
        """
        :return: None
        """
        self.priority = PRIORITY_FIRMWARE

    def needs_no_data(self, data):
        """
        :return: None
        """
        length = len(data)
        if length != 0:
            self.parser_error("has data included")

    def needs_data(self, data, length):
        """
        :return: None
        """
        if len(data) < length:
            self.parser_error(
                "needs " + str(length) + " bytes of data have " + str(len(data))
            )

    def needs_fixed_byte(self, byte, value):
        """
        :return: None
        """
        if byte != value:
            self.parser_error("expects " + chr(value) + " in byte " + chr(byte))

    def needs_one_channel(self, channels):
        """
        :return: None
        """
        if (
            len(channels) != 1
            or not isinstance(channels[0], int)
            or not channels[0] > 0
            or not channels[0] <= 8
        ):
            self.parser_error("needs exactly one bit set in channel byte")
