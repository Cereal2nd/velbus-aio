#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import sys
import asyncio
import ssl
from velbusaio.parser import VelbusParser
from velbusaio.handler import PacketHandler
from velbusaio.module import Module
from velbusaio.messages.module_type_request import ModuleTypeRequestMessage


class Velbus:
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
        if typ in [63, 64]:
            # ignore signum and usbip module
            return
        if sub_addr and sub_num:
            self._modules[addr]._sub_address[sub_num] = sub_addr
            self._modules[sub_addr] = self._modules[addr]
        else:
            self._modules[addr] = Module(addr, typ, data, self.send)
            await self._modules[addr].load()

    def get_modules(self):
        return self._modules

    def get_module(self, addr):
        if addr in self._modules.keys():
            return self._modules[addr]
        return None

    def get_channels(self, addr):
        if addr in self._modules:
            return (self._modules).get_channels()
        return None

    async def connect(self):
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
        for addr in range(0, 15):
            msg = ModuleTypeRequestMessage(addr)
            await self.send(msg)
        # wait for 40 seconds to give the modules and the tasks the time to load all the data
        await asyncio.sleep(60)
        # create a task to wait until we have all modules loaded
        # TODO add a timeout
        tsk = asyncio.Task(self._check_if_modules_are_loaded())
        await tsk

    async def _check_if_modules_are_loaded(self):
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
                    print(mod.__dict__)
                    print("")
            await asyncio.sleep(20)

    async def send(self, msg):
        await self._send_queue.put(msg)

    async def _socket_send_task(self):
        while self._send_queue:
            msg = await self._send_queue.get()
            self._log.debug("SENDING message: {}".format(msg))
            self._writer.write(msg.to_binary())
            await asyncio.sleep(0.2)

    async def _socket_read_task(self):
        while True:
            data = await self._reader.read(10)
            self._parser.feed(data)

    async def _parser_task(self):
        while True:
            packet = await self._parser.waitForPacket()
            await self._handler.handle(packet)


async def main():
    velbus = Velbus("192.168.1.9", 27015, True)
    await velbus.connect()
    for mod in (velbus.get_modules()).values():
        print(mod.__dict__)
        print("")


logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
logging.getLogger("asyncio").setLevel(logging.DEBUG)
asyncio.run(main(), debug=False)
