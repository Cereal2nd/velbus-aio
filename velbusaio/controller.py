"""Main interface for the velbusaio lib."""

from __future__ import annotations

import asyncio
import logging
import pathlib
import re
import ssl
import time
from urllib.parse import urlparse

import serial
import serial_asyncio_fast

from velbusaio.channels import Channel
from velbusaio.exceptions import VelbusConnectionFailed
from velbusaio.handler import PacketHandler
from velbusaio.helpers import get_cache_dir
from velbusaio.message import Message
from velbusaio.messages.module_type_request import ModuleTypeRequestMessage
from velbusaio.messages.set_date import SetDate
from velbusaio.messages.set_daylight_saving import SetDaylightSaving
from velbusaio.messages.set_realtime_clock import SetRealtimeClock
from velbusaio.module import Module
from velbusaio.protocol import VelbusProtocol
from velbusaio.raw_message import RawMessage


class Velbus:
    """A velbus controller."""

    def __init__(
        self,
        dsn: str,
        cache_dir: str = get_cache_dir(),
    ) -> None:
        """Init the Velbus controller."""
        self._log = logging.getLogger("velbus")

        self._protocol = VelbusProtocol(
            message_received_callback=self._on_message_received,
            connection_lost_callback=self._on_connection_lost,
        )
        self._closing = False
        self._auto_reconnect = True

        self._dsn = dsn
        self._handler = PacketHandler(self)
        self._modules: dict[int, Module] = {}
        self._submodules: list[int] = []
        self._send_queue: asyncio.Queue = asyncio.Queue()
        self._cache_dir: str = cache_dir
        # make sure the cachedir exists
        pathlib.Path(self._cache_dir).mkdir(parents=True, exist_ok=True)

    async def _on_message_received(self, msg: RawMessage) -> None:
        """On message received function."""
        await self._handler.handle(msg)

    def _on_connection_lost(self, exc: Exception) -> None:
        """Respond to Protocol connection lost."""
        if self._auto_reconnect and not self._closing:
            self._log.debug("Reconnecting to transport")
            asyncio.ensure_future(self.connect())

    def add_module(
        self,
        addr: int,
        typ: int,
        data: dict,
        serial: int | None = None,
        memorymap: int | None = None,
        build_year: int | None = None,
        build_week: int | None = None,
    ) -> None:
        """Add a found module to the module cache."""
        module = Module.factory(
            addr,
            typ,
            data,
            serial=serial,
            build_year=build_year,
            build_week=build_week,
            memorymap=memorymap,
            cache_dir=self._cache_dir,
        )
        module.initialize(self.send)
        self._modules[addr] = module
        self._log.info(f"Found module {addr}: {module}")

    def add_submodules(self, module: Module, subList: dict[int, int]) -> None:
        """Add submodules address to module."""
        for sub_num, sub_addr in subList.items():
            if sub_addr == 0xFF:
                continue
            self._submodules.append(sub_addr)
            module._sub_address[sub_num] = sub_addr
            self._modules[sub_addr] = module
        module.cleanupSubChannels()

    def get_modules(self) -> dict:
        """Return the module cache."""
        return self._modules

    def get_module(self, addr: int) -> None | Module:
        """Get a module on an address."""
        if addr in self._modules:
            return self._modules[addr]
        return None

    def get_channels(self, addr: int) -> None | dict:
        """Get the channels for an address."""
        if addr in self._modules:
            return (self._modules[addr]).get_channels()
        return None

    async def stop(self) -> None:
        """Stop the controller."""
        self._closing = True
        self._auto_reconnect = False
        self._protocol.close()

    async def connect(self, test_connect: bool = False) -> None:
        """Connect to the bus and load all the data."""
        await self._handler.read_protocol_data()
        auth = None
        # connect to the bus
        if ":" in self._dsn:
            # tcp/ip combination
            if not re.search(r"^[A-Za-z0-9+.\-]+://", self._dsn):
                # if no scheme, then add the tcp://
                self._dsn = f"tcp://{self._dsn}"
            parts = urlparse(self._dsn)
            if parts.scheme == "tls":
                ctx = ssl._create_unverified_context()
            else:
                ctx = None
            if parts.username:
                auth = parts.username
            try:
                (
                    _transport,
                    _protocol,
                ) = await asyncio.get_event_loop().create_connection(
                    lambda: self._protocol,
                    host=parts.hostname,
                    port=parts.port,
                    ssl=ctx,
                )

            except (ConnectionRefusedError, OSError) as err:
                raise VelbusConnectionFailed from err
        else:
            # serial port
            try:
                _transport, _protocol = (
                    await serial_asyncio_fast.create_serial_connection(
                        asyncio.get_event_loop(),
                        lambda: self._protocol,
                        url=self._dsn,
                        baudrate=38400,
                        bytesize=serial.EIGHTBITS,
                        parity=serial.PARITY_NONE,
                        stopbits=serial.STOPBITS_ONE,
                        xonxoff=0,
                        rtscts=1,
                    )
                )
            except (FileNotFoundError, serial.SerialException) as err:
                raise VelbusConnectionFailed from err
        if test_connect:
            return
        # if auth is required send the auth key
        if auth:
            await self._protocol.write_auth_key(auth)

        # scan the bus
        await self._handler.scan()

    async def scan(self) -> None:
        """Service endpoint to restart the scan"""
        await self._handler.scan(True)

    async def sendTypeRequestMessage(self, address: int) -> None:
        msg = ModuleTypeRequestMessage(address)
        await self.send(msg)

    async def send(self, msg: Message) -> None:
        """Send a packet."""
        await self._protocol.send_message(
            RawMessage(
                priority=msg.priority,
                address=msg.address,
                rtr=msg.rtr,
                data=msg.data_to_binary(),
            )
        )

    def get_all(self, class_name: str) -> list[Channel]:
        """Get all channels."""
        lst = []
        for addr, mod in (self.get_modules()).items():
            if addr in self._submodules:
                continue
            for chan in (mod.get_channels()).values():
                if class_name in chan.get_categories():
                    lst.append(chan)
        return lst

    async def sync_clock(self) -> None:
        """Will send all the needed messages to sync the clock."""
        lclt = time.localtime()
        await self.send(SetRealtimeClock(wday=lclt[6], hour=lclt[3], min=lclt[4]))
        await self.send(SetDate(day=lclt[2], mon=lclt[1], year=lclt[0]))
        await self.send(SetDaylightSaving(ds=not lclt[8]))
