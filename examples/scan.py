#!/usr/bin/env python
# -*- coding: utf-8 -*-

import asyncio
import logging
import sys

from velbusaio.controller import Velbus


async def main():
    velbus = Velbus("192.168.1.9", 27015, True)
    await velbus.connect()
    for mod in (velbus.get_modules()).values():
        print(mod)
        print("")
    await asyncio.sleep(60000)


logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
logging.getLogger("asyncio").setLevel(logging.DEBUG)
asyncio.run(main(), debug=False)
