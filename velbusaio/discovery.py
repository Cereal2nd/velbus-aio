import asyncio
import socket
import json
from typing import Tuple, Union, Text

Address = Tuple[str, int]


class VelbusDiscoveryProtocol(asyncio.DatagramProtocol):
    def __init__(self, target: Address):
        self.target = target

    def connection_made(self, transport: asyncio.transports.DatagramTransport):
        self.transport = transport
        sock = transport.get_extra_info("socket")  # type: socket.socket
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        string = "Velbus Navigation Request"
        self.transport.sendto(string.encode(), self.target)

    def datagram_received(self, data: Union[bytes, Text], addr: Address):
        # data received: b'{"message": "Velbus Navigation Guidance", "hostname": "Velbus", "model": "signum18", "id": "7b95834e", "velbus_port": 27015, "velbus_auth": false}' ('192.168.1.9', 32767)
        try:
            json_data = json.loads(data)
        except Exception:
            return
        if all(
            key in json_data
            for key in (
                "message",
                "hostname",
                "model",
                "id",
                "velbus_port",
                "velbus_auth",
            )
        ):
            res = {
                "address": addr[0],
                "hostname": json_data["hostname"],
                "model": json_data["model"],
                "id": json_data["id"],
                "port": json_data["velbus_port"],
                "auth": json_data["velbus_auth"],
            }
            print("data received:", res)


loop = asyncio.get_event_loop()
coro = loop.create_datagram_endpoint(
    lambda: VelbusDiscoveryProtocol(("192.168.1.255", 32767)),
    local_addr=("0.0.0.0", 1900),
)
loop.run_until_complete(coro)
loop.run_forever()
loop.close()
