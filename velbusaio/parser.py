"""
:author: Maikel Punie <maikel.punie@gmail.com>
"""
from __future__ import annotations

import asyncio
import itertools
import logging
from collections import deque

from velbusaio.const import (
    ETX,
    HEADER_LENGTH,
    LENGTH_MASK,
    MAX_DATA_AMOUNT,
    MIN_PACKET_LENGTH,
    PRIORITIES,
    STX,
)
from velbusaio.helpers import checksum


class VelbusParser:
    """
    Transform Velbus message from wire format to Message object
    """

    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger("velbus-parser")
        self.buffer = deque(maxlen=10000)

    def feed(self, data):
        """
        Feed received data in the buffer
        """
        self.buffer.extend(bytearray(data))

    # async def _next(self):
    #    packet = None
    #    has_valid_packet = self._has_valid_packet_waiting()
    #    while not has_valid_packet:
    #        if len(self.buffer) > HEADER_LENGTH and self.__has_packet_length_waiting():
    #            self.__realign_buffer()
    #            has_valid_packet = self._has_valid_packet_waiting()
    #        await asyncio.sleep(1)
    #
    #    if has_valid_packet:
    #        packet = self._extract_packet()
    #    return packet

    async def wait_for_packet(self):
        """
        Wait for a valid apcket
        """
        while not self._has_valid_packet_waiting():
            await asyncio.sleep(0.1)
        return self._extract_packet()

    def _has_valid_packet_waiting(self):
        """
        Checks whether or not the parser has a valid packet in its buffer.
        :return: A boolean indicating whether or not the parser has a valid packet in its buffer.
        TODO Fix
        """
        if not self.__has_valid_header_waiting():
            return False
        if len(self.buffer) < MIN_PACKET_LENGTH:
            return False
        return self.__has_packet_length_waiting() or False
        # bytes_to_check = bytearray(
        #    itertools.islice(self.buffer, 0, 4 + self.__curr_packet_body_length())
        # )
        # checksum_valid = self.buffer[(self.__curr_packet_length() - 2)] == checksum(
        #    bytes_to_check
        # )
        # end_valid = self.buffer[(self.__curr_packet_length() - 1)] == ETX
        # return checksum_valid and end_valid

    def __has_valid_header_waiting(self):
        """
        Checks whether or not the parser has a valid packet header waiting.
        :return: A boolean indicating whether or not the parser has a valid packet header waiting.
        """
        if len(self.buffer) < HEADER_LENGTH:
            return False
        start_valid = self.buffer[0] == STX
        bodysize_valid = self.__curr_packet_body_length() <= MAX_DATA_AMOUNT
        priority_valid = self.buffer[1] in PRIORITIES
        return start_valid and bodysize_valid and priority_valid

    def __has_packet_length_waiting(self):
        """
        Checks whether the current packet has the full length's worth of data waiting in the buffer.
        This should only be called when __has_valid_header_waiting() returns True.
        """
        return len(self.buffer) >= self.__curr_packet_length()

    def __curr_packet_length(self):
        """
        Gets the current waiting packet's total length.
        This should only be called when __has_valid_header_waiting() returns True.
        :return: The current waiting packet's total length.
        """
        return MIN_PACKET_LENGTH + self.__curr_packet_body_length()

    def __curr_packet_body_length(self):
        """
        Gets the current waiting packet's body length.
        This should only be called when __has_valid_header_waiting() returns True.
        :return: The current waiting packet's body length.
        """
        return self.buffer[3] & LENGTH_MASK

    def _extract_packet(self):
        """
        Extracts a packet from the buffer and shifts it.
        Make sure this is only called after __has_valid_packet_waiting() return True.
        :return: A bytearray with the currently waiting packet.
        """
        length = self.__curr_packet_length()
        packet = bytearray(itertools.islice(self.buffer, 0, length))
        self.__shift_buffer(length)
        return packet

    def __realign_buffer(self):
        """
        Realigns buffer by shifting the queue until the next STX or until the buffer runs out.
        """
        amount = 1
        while amount < len(self.buffer) and self.buffer[amount] != STX:
            amount += 1

        self.__shift_buffer(amount)

    def __shift_buffer(self, amount):
        """
        Shifts the buffer by the specified amount.
        :param amount: The amount of bytes that the buffer needs to be shifted.
        """
        for _ in itertools.repeat(None, amount):
            self.buffer.popleft()
