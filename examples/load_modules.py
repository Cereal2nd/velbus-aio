#!/usr/bin/env python

import argparse
import asyncio
import logging
import sys

from velbusaio.controller import Velbus

parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument("--connect", help="Connection string", default="192.168.1.254:8445")
args = parser.parse_args()


async def main(connect_str: str):
    # SET THE connection params below
    # example via signum:
    #   velbus = Velbus("tls://192.168.1.9:27015")
    # example via plain IP
    #   velbus = Velbus("192.168.1.9:27015")
    # example via serial device
    #   velbus = Velbus("/dev/ttyAMA0")
    velbus = Velbus(connect_str)
    await velbus.connect()
    for mod in (velbus.get_modules()).values():
        print(mod)
        print("")
    await velbus.stop()


logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
logging.getLogger("asyncio").setLevel(logging.DEBUG)
asyncio.run(main(args.connect), debug=False)
