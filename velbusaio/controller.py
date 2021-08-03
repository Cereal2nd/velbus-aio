"""
Main interface for the velbusaio lib
"""

import asyncio
import logging
import pickle
import ssl

import serial
import serial_asyncio

from velbusaio.const import CACHEDIR, LOAD_TIMEOUT
from velbusaio.handler import PacketHandler
from velbusaio.messages.module_type_request import ModuleTypeRequestMessage
from velbusaio.module import Module
from velbusaio.parser import VelbusParser


class Velbus:
    """
    A velbus controller
    """

    def __init__(self, dsn):
        self._log = logging.getLogger("velbus")
        self._log.setLevel(logging.DEBUG)
        self._dsn = dsn
        self._parser = VelbusParser()
        self._handler = PacketHandler(self.send, self)
        self._writer = None
        self._reader = None
        self._modules = {}
        self._submodules = []
        self._send_queue = asyncio.Queue()

    async def add_module(self, addr, typ, data, sub_addr=None, sub_num=None):
        """
        Add a founc module to the module cache
        """
        mod = self._load_module_from_cache(addr)
        if mod:
            self._log.info(f"Load module from CACHE: {addr}")
            self._modules[addr] = mod
        else:
            self._log.info(f"Load NEW module: {typ} @ {addr}")
            self._modules[addr] = Module(addr, typ, data)
        self._modules[addr].initialize(self.send)
        await self._modules[addr].load()

    async def add_submodules(self, addr, subList):
        for sub_num, sub_addr in subList.items():
            if sub_addr == 0xFF:
                continue
            self._submodules.append(sub_addr)
            self._modules[addr]._sub_address[sub_num] = sub_addr
            self._modules[sub_addr] = self._modules[addr]
        self._modules[addr].cleanupSubChannels()

    def _load_module_from_cache(self, address):
        try:
            with open(f"{CACHEDIR}/{address}.p", "rb") as fl:
                return pickle.load(fl)
        except OSError:
            pass

    def get_modules(self):
        """
        Return the module cache
        """
        return self._modules

    def get_module(self, addr):
        """
        Get a module on an address
        """
        if addr in self._modules.keys():
            return self._modules[addr]
        return None

    def get_channels(self, addr):
        """
        Get the channels for an address
        """
        if addr in self._modules:
            return (self._modules[addr]).get_channels()
        return None

    async def connect(self):
        """
        Connect to the bus and load all the data
        """
        # connect to the bus
        if ":" in self._dsn:
            # tcp/ip combination
            if self._dsn.startswith("tls://"):
                tmp = self._dsn.replace("tls://", "").split(":")
                ctx = ssl._create_unverified_context()
            else:
                tmp = self._dsn.split(":")
                ctx = None
            self._reader, self._writer = await asyncio.open_connection(
                tmp[0], tmp[1], ssl=ctx
            )
        else:
            # serial port
            self._reader, self._writer = await serial_asyncio.open_serial_connection(
                url=self._dsn,
                baudrate=38400,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                xonxoff=0,
                rtscts=1,
            )

        # create reader, parser and writer tasks
        asyncio.Task(self._socket_read_task())
        asyncio.Task(self._socket_send_task())
        asyncio.Task(self._parser_task())
        # scan the bus
        await self._scan()

    async def _scan(self):
        self._handler.scan_started()
        for addr in range(1, 255):
            msg = ModuleTypeRequestMessage(addr)
            await self.send(msg)
        await asyncio.sleep(30)
        self._handler.scan_finished()
        # create a task to wait until we have all modules loaded
        tsk = asyncio.Task(self._check_if_modules_are_loaded())
        try:
            await asyncio.wait_for(tsk, timeout=LOAD_TIMEOUT)
        except asyncio.TimeoutError:
            self._log.error(
                f"Not all modules are laoded within a timeout of {LOAD_TIMEOUT} seconds, continuing with the loaded modules"
            )

    async def _check_if_modules_are_loaded(self):
        """
        Task to wait until modules are loaded
        """
        while True:
            mods_loaded = 0
            for mod in (self.get_modules()).values():
                if mod.is_loaded():
                    mods_loaded += 1
            if mods_loaded == len(self.get_modules()):
                self._log.info("All modules loaded")
                return
            self._log.warning("Not all modules loaded yet, waiting 20 seconds")
            await asyncio.sleep(20)

    async def send(self, msg):
        """
        Send a packet
        """
        await self._send_queue.put(msg)

    async def _socket_send_task(self):
        """
        Task to send the packet from the queue to the bus
        """
        while self._send_queue:
            msg = await self._send_queue.get()
            self._log.debug(f"SENDING message: {msg}")
            # print(':'.join('{:02X}'.format(x) for x in msg.to_binary()))
            self._writer.write(msg.to_binary())
            await asyncio.sleep(0.11)

    async def _socket_read_task(self):
        """
        Task to read from a socket and push into a queue
        """
        while True:
            data = await self._reader.read(10)
            self._parser.feed(data)

    async def _parser_task(self):
        """
        Task to parser the received queue
        """
        while True:
            packet = await self._parser.wait_for_packet()
            await self._handler.handle(packet)

    def get_all(self, class_name):
        lst = []
        for addr, mod in (self.get_modules()).items():
            if addr in self._submodules:
                continue
            for chan in (mod.get_channels()).values():
                if class_name in chan.get_categories():
                    lst.append(chan)
        return lst
