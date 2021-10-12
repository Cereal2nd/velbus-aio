import asyncio
import binascii
import logging
import typing as t
from asyncio import transports

import backoff

from velbusaio.const import MAXIMUM_MESSAGE_SIZE, MINIMUM_MESSAGE_SIZE, SLEEP_TIME
from velbusaio.messages.module_type_request import ModuleTypeRequestMessage
from velbusaio.raw_message import RawMessage
from velbusaio.raw_message import create as create_message_info


def _on_write_backoff(details):
    logging.debug(
        "Transport is not open, waiting {wait} seconds after {tries}",
        wait=details.wait,
        tries=details.tries,
    )


class VelbusProtocol(asyncio.BufferedProtocol):
    """Handles the Velbus protocol

    This class is expected to be wrapped inside a VelbusConnection class object which will maintain the socket
    and handle auto-reconnects"""

    def __init__(
        self,
        loop,
        message_received_callback: t.Callable[[RawMessage], None],
        connection_lost_callback=None,
    ) -> None:
        super().__init__()
        self._log = logging.getLogger("velbus-protocol")
        self._loop = loop
        self._message_received_callback = message_received_callback
        self._connection_lost_callback = connection_lost_callback

        # everything for reading from Velbus
        self._buffer = bytearray(MAXIMUM_MESSAGE_SIZE)
        self._buffer_view = memoryview(self._buffer)
        self._buffer_pos = 0

        self.transport = None

        # everything for writing to Velbus
        self._send_queue = asyncio.Queue(loop=self._loop)
        self._write_transport_lock = asyncio.Lock(loop=self._loop)
        self._writer_task = None
        self._restart_writer = False
        self.restart_writing()

        self._closing = False

    def connection_made(self, transport: transports.BaseTransport) -> None:
        self.transport = transport
        self._log.info("Connection established to Velbus")

        self._restart_writer = True
        self.restart_writing()

    async def pause_writing(self):
        """Pause writing."""
        self._restart_writer = False
        if self._writer_task:
            self._send_queue.put_nowait(None)
        await asyncio.sleep(0.1)

    def restart_writing(self):
        """Resume writing."""
        if self._restart_writer and not self._write_transport_lock.locked():
            self._writer_task = asyncio.ensure_future(
                self._get_message_from_send_queue(), loop=self._loop
            )
            self._writer_task.add_done_callback(lambda _future: self.restart_writing())

    def close(self):
        self._closing = True
        self._restart_writer = False
        if self.transport:
            self.transport.close()

    def connection_lost(self, exc: t.Optional[Exception]) -> None:
        self.transport = None

        if self._closing:
            return  # Connection loss was expected, nothing to do here...
        elif exc is None:
            self._log.warning("EOF received from Velbus")
        else:
            self._log.error(f"Velbus connection lost: {exc!r}")

        self.transport = None
        asyncio.ensure_future(self.pause_writing(), loop=self._loop)
        if self._connection_lost_callback:
            self._connection_lost_callback(exc)

    # Everything read-related

    def get_buffer(self, sizehint):
        return self._buffer_view[self._buffer_pos :]

    def data_received(self, data):
        """Receive data from the Streaming protocol.
        Called when asyncio.Protocol detects received data from serial port.
        """
        self._buffer_pos += len(data)
        _new_data = bytearray()
        for x in self._buffer:
            _new_data.append(x)

        for y in data:
            _new_data.append(int(y))
        self._check_buffer(_new_data)

    def buffer_updated(self, nbytes: int) -> None:
        """Receive data from the Buffered Streaming protocol.
        Called when asyncio.BufferedProtocol detects received data from network.
        """
        self._buffer_pos += nbytes
        self._log.debug(
            "Received {nbytes} bytes from Velbus: {data_hex}".format(
                nbytes=nbytes,
                data_hex=binascii.hexlify(
                    self._buffer[self._buffer_pos - nbytes : self._buffer_pos], " "
                ),
            )
        )
        self._check_buffer(self._buffer)

    def _check_buffer(self, buffer: bytearray):
        if self._buffer_pos > MINIMUM_MESSAGE_SIZE:
            # try to construct a Velbus message from the buffer
            msg, remaining_data = create_message_info(buffer)

            if msg:
                asyncio.ensure_future(self._process_message(msg), loop=self._loop)

            self._new_buffer(remaining_data)

    def _new_buffer(self, remaining_data=None):
        new_buffer = bytearray(MAXIMUM_MESSAGE_SIZE)
        if remaining_data:
            new_buffer[: len(remaining_data)] = remaining_data

        self._buffer = new_buffer
        self._buffer_pos = len(remaining_data) if remaining_data else 0
        self._buffer_view = memoryview(self._buffer)

    async def _process_message(self, msg: RawMessage):
        self._log.debug(f"RX: {msg}")
        await self._message_received_callback(msg)

    # Everything write-related

    async def send_message(self, msg: RawMessage):
        self._send_queue.put_nowait(msg)

    async def _get_message_from_send_queue(self):
        self._log.debug("Starting Velbus write message from send queue")
        self._log.debug("Acquiring write lock")
        await self._write_transport_lock.acquire()
        while self._restart_writer:
            # wait for an item from the queue
            msg_info = await self._send_queue.get()
            if msg_info is None:
                self._restart_writer = False
                return
            message_sent = False
            try:
                while not message_sent:
                    message_sent = await self._write_message(msg_info)
                await asyncio.sleep(SLEEP_TIME, loop=self._loop)
            except (asyncio.CancelledError, GeneratorExit) as exc:
                if not self._closing:
                    self._log.error(f"Stopping Velbus writer due to {exc!r}")
                self._restart_writer = False
            except Exception as exc:
                self._log.error(f"Restarting Velbus writer due to {exc!r}")
                self._restart_writer = True
        if self._write_transport_lock.locked():
            self._write_transport_lock.release()
        self._log.debug("Ending Velbus write message from send queue")

    @backoff.on_predicate(
        backoff.expo,
        lambda is_sent: not is_sent,
        max_tries=10,
        on_backoff=_on_write_backoff,
    )
    async def _write_message(self, msg: RawMessage):
        self._log.debug(f"TX: {msg}")
        if not self.transport.is_closing():
            self.transport.write(msg.to_bytes())
            return True
        else:
            return False
