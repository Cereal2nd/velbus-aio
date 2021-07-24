"""
Main interface for the velbusaio lib
"""

import asyncio
import logging
import pickle
import ssl

from velbusaio.const import CACHEDIR
from velbusaio.handler import PacketHandler
from velbusaio.messages.module_type_request import ModuleTypeRequestMessage
from velbusaio.module import Module
from velbusaio.parser import VelbusParser


class Velbus:
    """
    A velbus controller
    """

    def __init__(self, ip, port, useSsl=False):
        self._log = logging.getLogger("velbus")
        self._ip = ip
        self._port = port
        self._ssl = useSsl
        self._parser = VelbusParser()
        self._handler = PacketHandler(self.send, self)
        self._writer = None
        self._reader = None
        self._modules = dict()
        self._send_queue = asyncio.Queue()

    async def add_module(self, addr, typ, data, sub_addr=None, sub_num=None):
        """
        Add a founc module to the module cache
        """
        if typ in [57]:
            # ignore signum and usbip module
            return
        if sub_addr and sub_num:
            self._modules[addr]._sub_address[sub_num] = sub_addr
            self._modules[sub_addr] = self._modules[addr]
        else:
            mod = self._load_module_from_cache(addr)
            if mod:
                self._modules[addr] = mod
            else:
                self._modules[addr] = Module(addr, typ, data, self.send)
            await self._modules[addr].load()

    def _load_module_from_cache(self, address):
        try:
            with open("{}/{}.p".format(CACHEDIR, address), "rb") as fl:
                return pickle.load(fl)
        except EnvironmentError:
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
        if self._ssl:
            ctx = ssl._create_unverified_context()
        else:
            ctx = None
        self._reader, self._writer = await asyncio.open_connection(
            self._ip, self._port, ssl=ctx
        )
        # create reader, parser and writer tasks
        asyncio.Task(self._socket_read_task())
        asyncio.Task(self._socket_send_task())
        asyncio.Task(self._parser_task())
        # scan the bus
        for addr in range(0, 256):
            msg = ModuleTypeRequestMessage(addr)
            await self.send(msg)
        # wait for 60 seconds to give the modules and the tasks the time to load all the data
        await asyncio.sleep(60)
        # create a task to wait until we have all modules loaded
        # TODO add a timeout
        tsk = asyncio.Task(self._check_if_modules_are_loaded())
        await tsk

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
                return
            print("NOT ALL MODULES LOADED YET")
            for mod in (self.get_modules()).values():
                if not mod.is_loaded():
                    print(mod)
                    print("")
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
            self._log.debug("SENDING message: {}".format(msg))
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
