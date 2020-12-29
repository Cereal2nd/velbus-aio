#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import sys
import asyncio
import ssl
from velbusaio.parser import VelbusParser
from velbusaio.handler import PacketHandler
from velbusaio.const import PRIORITY_LOW
from velbusaio.message import Message
from velbusaio.module import Module

writer = None


class Velbus:
    def __init__(self, ip, port, ssl=False):
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
        asyncio.Task(self.read())

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
            msg = Message()
            msg.priority = PRIORITY_LOW
            msg.address = addr
            msg.rtr = True
            await self.send(msg)

    async def send(self, msg):
        assert isinstance(msg, Message)
        self._writer.write(msg.build())
        await asyncio.sleep(0.1)

    async def read(self):
        while True:
            data = await self._reader.read(100)
            self._parser.feed(data)
            p = await self._parser._next()
            print(p)
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
asyncio.run(main(), debug=True)
