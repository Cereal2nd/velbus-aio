"""
:author: Maikel Punie <maikel.punie@gmail.com>
"""
import asyncio, logging
from collections import deque
import itertools
from velbusaio.handler import PacketHandler
from velbusaio.helpers import checksum
from velbusaio.const import (
    STX,
    ETX,
    HEADER_LENGTH,
    MIN_PACKET_LENGTH,
    MAX_DATA_AMOUNT,
    PRIORITIES,
    LENGTH_MASK,
    RTR,
)


class VelbusProtocol(asyncio.Protocol):
    """
    Transform Velbus message from wire format to Message object
    """

    __module__ = __name__
    __qualname__ = "VelbusProtocol"

    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger("velbus-protocol")
        self.modules = dict()
        self._transport = None
        self.controller = None
        self._ready = asyncio.Event()
        self._send_queue = asyncio.Queue()
        self._recv_queue = deque()
        self.buffer = deque(maxlen=10000)
        self._recv_task = None
        self._send_task = None
        self._waiter = None
        self._handler = PacketHandler(self)

    def getModules(self):
        return self.modules

    async def _send_from_queue(self):
        await self._ready.wait()
        while self._send_queue and self._ready:
            data = await self._send_queue.get()
            self.logger.debug("SENDING message: {} (qsize={})".format(data, self._send_queue.qsize()))
            self._transport.write(data)
            await asyncio.sleep(0.1)

    async def _read_from_queue(self):
        await self._ready.wait()
        while self._ready:
            self._waiter = asyncio.Future()
            await self._waiter
            while len(self._recv_queue) and self._ready:
                data = self._recv_queue.popleft()
                self.logger.debug("RECEIVING message: {} (qsize={})".format(data, len(self._recv_queue)))
                if self._transport and self._ready:
                    await self._handler.handle(data)

    async def send(self, msg):
        """
        Method to send a velbus packet
        """
        if msg.rtr:
            rtr_and_size = RTR | len(msg.data)
        else:
            rtr_and_size = len(msg.data)
        header = bytearray([STX, msg.priority, msg.address, rtr_and_size])
        _checksum = checksum(header + msg.data)
        tosend = (
            header
            + msg.data
            + bytearray.fromhex("{:02x}".format(_checksum))
            + bytearray([ETX])
        )
        await self._send_queue.put(tosend)

    def onnection_lost(self):
        """
        Overrided asyncio.Protocol
        """
        self._transport = None
        self._ready.clear()
        self._send_task.cancel()
        self._recv_task.cancel()
        self.logger.debug("Connection closed")

    def connection_made(self, transport):
        """
        Overrided asyncio.Protocol
        """
        self._transport = transport
        self._ready.set()
        self._send_task = asyncio.Task(self._send_from_queue())
        self._recv_task = asyncio.Task(self._read_from_queue())
        self.logger.debug("Connection started")

    def data_received(self, data):
        """
        Overrided asyncio.Protocol
        """
        self.buffer.extend(bytearray(data))
        self._recv_queue.append(self._next())
        if not self._waiter.done():
            self._waiter.set_result(None)

    def _next(self):
        packet = None
        has_valid_packet = self._VelbusProtocol__has_valid_packet_waiting()
        while not has_valid_packet:
            if (
                len(self.buffer) > HEADER_LENGTH
                and self._VelbusProtocol__has_packet_length_waiting()
            ):
                self._VelbusProtocol__realign_buffer()
                has_valid_packet = self._VelbusProtocol__has_valid_packet_waiting()

        if has_valid_packet:
            packet = self._VelbusProtocol__extract_packet()
        return packet

    def __has_valid_packet_waiting(self):
        """
        Checks whether or not the parser has a valid packet in its buffer.
        :return: A boolean indicating whether or not the parser has a valid packet in its buffer.
        """
        if not self._VelbusProtocol__has_valid_header_waiting():
            return False
        else:
            if len(self.buffer) < MIN_PACKET_LENGTH:
                return False
            return self._VelbusProtocol__has_packet_length_waiting() or False
        bytes_to_check = bytearray(
            itertools.islice(
                self.buffer, 0, 4 + self._VelbusProtocol__curr_packet_body_length()
            )
        )
        checksum_valid = self.buffer[
            (self._VelbusProtocol__curr_packet_length() - 2)
        ] == checksum(bytes_to_check)
        end_valid = self.buffer[(self._VelbusProtocol__curr_packet_length() - 1)] == ETX
        return checksum_valid and end_valid

    def __has_valid_header_waiting(self):
        """
        Checks whether or not the parser has a valid packet header waiting.
        :return: A boolean indicating whether or not the parser has a valid packet header waiting.
        """
        if len(self.buffer) < HEADER_LENGTH:
            return False
        start_valid = self.buffer[0] == STX
        bodysize_valid = (
            self._VelbusProtocol__curr_packet_body_length() <= MAX_DATA_AMOUNT
        )
        priority_valid = self.buffer[1] in PRIORITIES
        return start_valid and bodysize_valid and priority_valid

    def __has_packet_length_waiting(self):
        """
        Checks whether the current packet has the full length's worth of data waiting in the buffer.
        This should only be called when __has_valid_header_waiting() returns True.
        """
        return len(self.buffer) >= self._VelbusProtocol__curr_packet_length()

    def __curr_packet_length(self):
        """
        Gets the current waiting packet's total length.
        This should only be called when __has_valid_header_waiting() returns True.
        :return: The current waiting packet's total length.
        """
        return MIN_PACKET_LENGTH + self._VelbusProtocol__curr_packet_body_length()

    def __curr_packet_body_length(self):
        """
        Gets the current waiting packet's body length.
        This should only be called when __has_valid_header_waiting() returns True.
        :return: The current waiting packet's body length.
        """
        return self.buffer[3] & LENGTH_MASK

    def __extract_packet(self):
        """
        Extracts a packet from the buffer and shifts it.
        Make sure this is only called after __has_valid_packet_waiting() return True.
        :return: A bytearray with the currently waiting packet.
        """
        length = self._VelbusProtocol__curr_packet_length()
        packet = bytearray(itertools.islice(self.buffer, 0, length))
        self._VelbusProtocol__shift_buffer(length)
        return packet

    def __realign_buffer(self):
        """
        Realigns buffer by shifting the queue until the next STX or until the buffer runs out.
        """
        amount = 1
        while amount < len(self.buffer) and self.buffer[amount] != STX:
            amount += 1

        self._VelbusProtocol__shift_buffer(amount)

    def __shift_buffer(self, amount):
        """
        Shifts the buffer by the specified amount.
        :param amount: The amount of bytes that the buffer needs to be shifted.
        """
        assert isinstance(amount, int)
        for _ in itertools.repeat(None, amount):
            self.buffer.popleft()
