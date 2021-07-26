#!/usr/bin/env python

import asyncio

from velbusaio.discovery import VelbusDiscoveryProtocol

loop = asyncio.get_event_loop()
coro = loop.create_datagram_endpoint(
    lambda: VelbusDiscoveryProtocol(("192.168.1.255", 32767)),
    local_addr=("0.0.0.0", 1900),
)
loop.run_until_complete(coro)
loop.run_forever()
loop.close()
