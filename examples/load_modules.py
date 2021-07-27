#!/usr/bin/env python

import asyncio
import logging
import sys

from velbusaio.controller import Velbus


async def main():
    # SET THE connection params below
    # example via signum:
    # velbus = Velbus("192.168.1.9", 27015, True)
    # example via plain IP
    # velbus = Velbus("192.168.1.9", 27015, False)
    velbus = Velbus("192.168.1.9", 27015, True)
    await velbus.connect()
    for mod in (velbus.get_modules()).values():
        print(mod)
        print("")
    await asyncio.sleep(60000)


logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
logging.getLogger("asyncio").setLevel(logging.DEBUG)
asyncio.run(main(), debug=False)
