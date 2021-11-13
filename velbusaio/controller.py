"""
Main interface for the velbusaio lib
"""
from __future__ import annotations

import asyncio
import logging
import pathlib
import pickle
import ssl

import serial
import serial_asyncio

from velbusaio.const import LOAD_TIMEOUT
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
    """
    A velbus controller
    """

    def __init__(self, dsn, cache_dir=get_cache_dir()) -> None:
        self._log = logging.getLogger("velbus")
        self._loop = asyncio.get_event_loop()

        self._protocol = VelbusProtocol(
            message_received_callback=self._on_message_received,
            connection_lost_callback=self._on_connection_lost,
            end_of_scan_callback=self._on_end_of_scan,
            loop=self._loop,
        )
        self._closing = False
        self._auto_reconnect = True

        self._dsn = dsn
        self._handler = PacketHandler(self.send, self)
        self._modules = {}
        self._submodules = []
        self._send_queue = asyncio.Queue()
        self._cache_dir = cache_dir
        # make sure the cachedir exists
        pathlib.Path(self._cache_dir).mkdir(parents=True, exist_ok=True)

    async def _on_message_received(self, msg: RawMessage):
        await self._handler.handle(msg)

    def _on_connection_lost(self, exc: Exception):
        """Respond to Protocol connection lost."""
        if self._auto_reconnect and not self._closing:
            self._log.debug("Reconnecting to transport")
            asyncio.ensure_future(self.connect(), loop=self._loop)

    def _on_end_of_scan(self):
        self._handler.scan_finished()

    async def add_module(
        self,
        addr: str,
        typ: str,
        data: dict,
        serial=None,
        memorymap=None,
        build_year=None,
        build_week=None,
    ) -> None:
        """
        Add a found module to the module cache
        """
        mod = self._load_module_from_cache(self._cache_dir, addr)
        if mod is not None:
            self._log.info(f"Load module from CACHE: {addr}")
            self._modules[addr] = mod
            self._modules[addr].initialize(self.send)
            await self._modules[addr].load(True)
        else:
            self._log.info(f"Load NEW module: {typ} @ {addr}")
            self._modules[addr] = Module(
                addr,
                typ,
                data,
                serial=serial,
                build_year=build_year,
                build_week=build_week,
                memorymap=memorymap,
                cache_dir=self._cache_dir,
            )
            self._modules[addr].initialize(self.send)
            await self._modules[addr].load()

    async def add_submodules(self, addr, subList) -> None:
        for sub_num, sub_addr in subList.items():
            if sub_addr == 0xFF:
                continue
            self._submodules.append(sub_addr)
            self._modules[addr]._sub_address[sub_num] = sub_addr
            self._modules[sub_addr] = self._modules[addr]
        self._modules[addr].cleanupSubChannels()

    def _load_module_from_cache(self, cache_dir, address) -> None | str:
        try:
            cfile = pathlib.Path(f"{cache_dir}/{address}.p")
            with cfile.open("rb") as fl:
                return pickle.load(fl)
        except OSError:
            pass

    def get_modules(self) -> dict:
        """
        Return the module cache
        """
        return self._modules

    def get_module(self, addr: str) -> None | Module:
        """
        Get a module on an address
        """
        if addr in self._modules.keys():
            return self._modules[addr]
        return None

    def get_channels(self, addr: str) -> None | dict:
        """
        Get the channels for an address
        """
        if addr in self._modules:
            return (self._modules[addr]).get_channels()
        return None

    async def stop(self) -> None:
        self._closing = True
        self._auto_reconnect = False
        self._protocol.close()

    async def connect(self, test_connect: bool = False) -> None:
        """
        Connect to the bus and load all the data
        """
        # connect to the bus
        if ":" in self._dsn:
            # tcp/ip combination
            if self._dsn.startswith("tls://"):
                host, port = self._dsn.replace("tls://", "").split(":")
                ctx = ssl._create_unverified_context()
            else:
                host, port = self._dsn.split(":")
                ctx = None
            try:
                _transport, _protocol = await self._loop.create_connection(
                    lambda: self._protocol, host=host, port=port, ssl=ctx
                )

            except ConnectionRefusedError as err:
                raise VelbusConnectionFailed() from err
        else:
            # serial port
            try:
                _transport, _protocol = await serial_asyncio.create_serial_connection(
                    self._loop,
                    lambda: self._protocol,
                    url=self._dsn,
                    baudrate=38400,
                    bytesize=serial.EIGHTBITS,
                    parity=serial.PARITY_NONE,
                    stopbits=serial.STOPBITS_ONE,
                    xonxoff=0,
                    rtscts=1,
                )
            except FileNotFoundError as err:
                raise VelbusConnectionFailed() from err
        if test_connect:
            return

        # scan the bus
        await self.scan()

    async def scan(self) -> None:
        self._handler.scan_started()
        for addr in range(1, 256):
            msg = ModuleTypeRequestMessage(addr)
            await self.send(msg)
        await self._handler._scan_complete_event.wait()
        # calculate how long to wait
        calc_timeout = len(self._modules) * 30
        if calc_timeout < LOAD_TIMEOUT:
            timeout = calc_timeout
        else:
            timeout = LOAD_TIMEOUT
        # create a task to wait until we have all modules loaded
        tsk = asyncio.Task(self._check_if_modules_are_loaded())
        try:
            await asyncio.wait_for(tsk, timeout=timeout)
        except asyncio.TimeoutError:
            self._log.error(
                f"Not all modules are loaded within a timeout of {LOAD_TIMEOUT} seconds, continuing with the loaded modules"
            )

    async def _check_if_modules_are_loaded(self) -> None:
        """
        Task to wait until modules are loaded
        """
        while True:
            mods_loaded = 0
            for mod in (self.get_modules()).values():
                if mod.is_loaded():
                    mods_loaded += 1
                else:
                    self._log.warning(f"Waiting for module {mod._address}")
            if mods_loaded == len(self.get_modules()):
                self._log.info("All modules loaded")
                return
            self._log.info("Not all modules loaded yet, waiting 15 seconds")
            await asyncio.sleep(15)

    async def send(self, msg: Message) -> None:
        """
        Send a packet
        """
        await self._protocol.send_message(
            RawMessage(
                priority=msg.priority,
                address=msg.address,
                rtr=msg.rtr,
                data=msg.data_to_binary(),
            )
        )

    def get_all(self, class_name: str) -> list:
        lst = []
        for addr, mod in (self.get_modules()).items():
            if addr in self._submodules:
                continue
            for chan in (mod.get_channels()).values():
                if class_name in chan.get_categories():
                    lst.append(chan)
        return lst

    async def sync_clock(self) -> None:
        """
        This will send all the needed messages to sync the clock
        """
        await self.send(SetRealtimeClock())
        await self.send(SetDate())
        await self.send(SetDaylightSaving())
