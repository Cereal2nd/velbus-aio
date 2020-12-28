#!/usr/bin/env python
# -*- coding: utf-8 -*-

import time
import logging
import sys
import asyncio
import signal
import pprint
import ssl
from velbusaio.protocol import VelbusProtocol
from velbusaio.const import PRIORITY_LOW
from velbusaio.message import Message

_protocol = None


async def domain():
    ctx = ssl._create_unverified_context()
    _transport, _protocol = await loop.create_connection(
        VelbusProtocol, "192.168.1.9", 27015, ssl=ctx
    )
    for addr in range(0, 10):
        msg = Message()
        msg.priority = PRIORITY_LOW
        msg.address = addr
        msg.rtr = True
        await _protocol.send(msg)
    await asyncio.sleep(120)
    _protocol.getModules()
    await asyncio.sleep(120)


def ask_exit():
    for task in asyncio.Task.all_tasks():
        print(task)
        task.cancel()


logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
logging.getLogger("asyncio").setLevel(logging.DEBUG)
loop = asyncio.new_event_loop()
for sig in (signal.SIGINT, signal.SIGTERM):
    loop.add_signal_handler(sig, ask_exit)
loop.run_until_complete(domain())
for sig in (signal.SIGINT, signal.SIGTERM):
    loop.remove_signal_handler(sig)
loop.close()
asyncio.set_event_loop(None)
