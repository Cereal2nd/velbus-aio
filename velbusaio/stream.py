#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import sys
import asyncio
import ssl
from velbusaio.parser import VelbusParser
from velbusaio.handler import PacketHandler
from velbusaio.message import Message
from velbusaio.module import Module
from velbus.messages.module_type_request import ModuleTypeRequestMessage


class Velbus:
    def __init__(self, ip, port, ssl=False):
        self._log = logging.getLogger("velbus")
        self._ip = ip
        self._port = port
        self._ssl = ssl
        self._parser = VelbusParser()
        self._handler = PacketHandler(self.send, self)
        self._writer = None
        self._reader = None
        self._modules = dict()

    async def add_module(self, addr, typ, data, sub_addr=None, sub_num=None):
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
            return self._modules.get_channels()
        return None

    async def connect(self):
        if self._ssl:
            ctx = ssl._create_unverified_context()
        else:
            ctx = None
        self._reader, self._writer = await asyncio.open_connection(
            self._ip, self._port, ssl=ctx
        )
        asyncio.Task(self._socket_read_task())
        asyncio.Task(self._parser_task())

    async def modules_loaded(self):
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
            print(self.get_modules())
            await asyncio.sleep(20)

    async def scan(self):
        for addr in range(0, 255):
            msg = ModuleTypeRequestMessage(addr)
            await self.send(msg)

    async def send(self, msg):
        self._log.debug("SENDING message: {}".format(msg))
        self._writer.write(msg.to_binary())
        await asyncio.sleep(0.1)

    async def _socket_read_task(self):
        while True:
            data = await self._reader.read(10)
            self._parser.feed(data)

    async def _parser_task(self):
        while True:
            p = await self._parser.waitForPacket()
            await self._handler.handle(p)


async def main():
    v = Velbus("192.168.1.9", 27015, True)
    await v.connect()
    print("Connect finished")
    await v.scan()
    print("scan finished")
    await v.modules_loaded()
    print("all loaded")
    await asyncio.sleep(120)


logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
logging.getLogger("asyncio").setLevel(logging.DEBUG)
asyncio.run(main(), debug=False)
