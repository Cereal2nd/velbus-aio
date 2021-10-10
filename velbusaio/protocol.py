import asyncio
import binascii
from asyncio import transports
import typing as t

import backoff
from loguru import logger
from velbusaio.const import MINIMUM_MESSAGE_SIZE, MAXIMUM_MESSAGE_SIZE, SLEEP_TIME
from velbusaio.raw_message import RawMessage, create as create_message_info
from velbusaio.messages.module_type_request import ModuleTypeRequestMessage


def _on_write_backoff(details):
    logger.debug("Transport is not open, waiting {wait} seconds after {tries}", wait=details.wait, tries=details.tries)


class VelbusProtocol(asyncio.BufferedProtocol):
    """Handles the Velbus protocol

    This class is expected to be wrapped inside a VelbusConnection class object which will maintain the socket
    and handle auto-reconnects"""

    def __init__(self,loop,
                 message_received_callback: t.Callable[[RawMessage], None],
                 connection_lost_callback=None,
                 poll_devices=True) -> None:
        super().__init__()
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

        self._poll_devices = poll_devices
        self._poll_complete = False

        self._closing = False

    def connection_made(self, transport: transports.BaseTransport) -> None:
        self.transport = transport
        logger.info("Connection established to Velbus")

        self._restart_writer = True
        self.restart_writing()

        self._populate_devices()

    def _populate_devices(self):
        if not self._poll_complete and self._poll_devices:
            asyncio.ensure_future(self._send_discovery_messages(), loop=self._loop)

    async def _send_discovery_messages(self):
        pass
        # logger.info("Polling all devices on the Velbus")
        # for address in range(0x00, 0xFF):
        #     msg = ModuleTypeRequestMessage(address)
        #     await self.send_message(msg.to_raw_message())

        # self._poll_complete = True

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
            return # Connection loss was expected, nothing to do here...
        elif exc is None:
            logger.warning("EOF received from Velbus")
        else:
            logger.error(f"Velbus connection lost: {exc!r}")

        self.transport = None
        asyncio.ensure_future(self.pause_writing(), loop=self._loop)
        if self._connection_lost_callback:
            self._connection_lost_callback(exc)

    # Everything read-related

    def get_buffer(self, sizehint):
        return self._buffer_view[self._buffer_pos:]

    def buffer_updated(self, nbytes: int) -> None:
        """Receive data from the protocol.
              Called when asyncio.BufferedProtocol detects received data from network.
              """
        self._buffer_pos += nbytes

        logger.trace(
            "Received {nbytes} bytes from Velbus: {data_hex}",
            nbytes=nbytes,
            data_hex=binascii.hexlify(self._buffer[self._buffer_pos - nbytes:self._buffer_pos], ' ')
        )

        if self._buffer_pos > MINIMUM_MESSAGE_SIZE:
            # try to construct a Velbus message from the buffer
            msg, remaining_data = create_message_info(self._buffer)

            if msg:
                asyncio.ensure_future(self._process_message(msg), loop=self._loop)

            self._new_buffer(remaining_data)

    def _new_buffer(self, remaining_data=None):
        new_buffer = bytearray(MAXIMUM_MESSAGE_SIZE)
        if remaining_data:
            new_buffer[:len(remaining_data)] = remaining_data

        self._buffer = new_buffer
        self._buffer_pos = len(remaining_data) if remaining_data else 0
        self._buffer_view = memoryview(self._buffer)

    async def _process_message(self, msg: RawMessage):
        logger.debug("RX: {msg}", msg=msg)
        await self._message_received_callback(msg)

    # Everything write-related

    async def send_message(self, msg: RawMessage):
        self._send_queue.put_nowait(msg)

    async def _get_message_from_send_queue(self):
        logger.debug("Starting Velbus write message from send queue")
        logger.debug("Aquiring write lock")
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
                    logger.exception(f"Stopping Velbus writer due to {exc!r}")
                self._restart_writer = False
            except Exception as exc:
                logger.exception(f"Restarting Velbus writer due to {exc!r}")
                self._restart_writer = True
        if self._write_transport_lock.locked():
            self._write_transport_lock.release()
        logger.debug("Ending Velbus write message from send queue")

    @backoff.on_predicate(backoff.expo, lambda is_sent: not is_sent, max_tries=10, on_backoff=_on_write_backoff)
    async def _write_message(self, msg : RawMessage):
        logger.debug("TX: {msg}", msg=msg)
        if not self.transport.is_closing():
            self.transport.write(msg.to_bytes())
            return True
        else:
            return False
