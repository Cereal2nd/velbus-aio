"""
Velbus packet handler
:Author maikel punie <maikel.punie@gmail.com>
"""
from __future__ import annotations

import json
import logging
import re

import pkg_resources

from velbusaio.command_registry import commandRegistry
from velbusaio.const import RTR
from velbusaio.helpers import h2, keys_exists
from velbusaio.message import Message
from velbusaio.messages.module_subtype import ModuleSubTypeMessage
from velbusaio.messages.module_type import ModuleTypeMessage


class PacketHandler:
    """
    The packetHandler class
    """

    def __init__(self, writer, velbus) -> None:
        self._log = logging.getLogger("velbus-packet")
        self._log.setLevel(logging.DEBUG)
        self._writer = writer
        self._velbus = velbus
        self._scan_complete = False
        with open(
            pkg_resources.resource_filename(__name__, "moduleprotocol/protocol.json")
        ) as protocol_file:
            self.pdata = json.load(protocol_file)

    def scan_finished(self) -> None:
        self._scan_complete = True

    def scan_started(self) -> None:
        self._scan_complete = False

    async def handle(self, data: str) -> None:
        """
        Handle a recievd packet
        """
        priority = data[1]
        address = int(data[2])
        rtr = data[3] & RTR == RTR
        data_size = data[3] & 0x0F
        command_value = data[4]
        if data_size < 1:
            return
        if address < 1 or address > 254:
            return
        if command_value == 0xFF and not self._scan_complete:
            msg = ModuleTypeMessage()
            msg.populate(priority, address, rtr, data[5:-2])
            self._log.debug(f"Received {msg}")
            await self._handle_module_type(msg)
        elif command_value == 0xB0 and not self._scan_complete:
            msg = ModuleSubTypeMessage()
            msg.populate(priority, address, rtr, data[5:-2])
            self._log.debug(f"Received {msg}")
            await self._handle_module_subtype(msg)
        elif command_value in self.pdata["MessagesBroadCast"]:
            self._log.debug(
                "Received broadcast message {} from {}, ignoring".format(
                    self.pdata["MessageBroadCast"][command_value.upper()], address
                )
            )
        elif address in self._velbus.get_modules().keys():
            module_type = self._velbus.get_module(address).get_type()
            if commandRegistry.has_command(int(command_value), module_type):
                command = commandRegistry.get_command(command_value, module_type)
                msg = command()
                msg.populate(priority, address, rtr, data[5:-2])
                self._log.debug(f"Received {msg}")
                # send the message to the modules
                await (self._velbus.get_module(msg.address)).on_message(msg)
            else:
                self._log.warning(
                    "NOT FOUND IN command_registry: addr={} cmd={} packet={}".format(
                        address, command_value, ":".join(format(x, "02x") for x in data)
                    )
                )
        elif self._scan_complete:
            # this should only happen once the scan is complete, of its not complete susppend the error message
            self._log.warning(
                "UNKNOWN module, you should iniitalize a full new velbus scan: packet={}, address={}, modules={}".format(
                    ":".join(format(x, "02x") for x in data),
                    address,
                    self._velbus.get_modules().keys(),
                )
            )

    def _per_byte(self, cmsg, msg) -> dict:
        result = {}
        for num, byte in enumerate(msg.data):
            num = str(num)
            # only do something if its defined
            if num not in cmsg:
                continue
            # check if we can do a binary match
            for mat in cmsg[num]["Match"]:
                if (
                    (mat.startswith("%") and re.match(mat[1:], f"{byte:08b}"))
                    or mat == f"{byte:08b}"
                    or mat == f"{byte:02x}"
                ):
                    result = self._per_byte_handle(
                        result, cmsg[num]["Match"][mat], byte
                    )
        return result

    def _per_byte_handle(self, result: dict, todo: dict, byte: int) -> dict:
        if "Channel" in todo:
            result["Channel"] = todo["Channel"]
        if "Value" in todo:
            result["Value"] = todo["Value"]
        if "Convert" in todo:
            result["ValueList"] = []
            if todo["Convert"] == "Decimal":
                result["ValueList"].append(int(byte))
            elif todo["Convert"] == "Counter":
                result["ValueList"].append(f"{byte:02x}")
            elif todo["Convert"] == "Temperature":
                print("CONVERT temperature")
            elif todo["Convert"] == "Divider":
                bin_str = f"{byte:08b}"
                chan = bin_str[6:]
                val = bin_str[:5]
                print(f"CONVERT Divider {chan} {val}")
            elif todo["Convert"] == "Channel":
                print("CONVERT Channel")
            elif todo["Convert"] == "ChannelBit":
                print("CONVERT ChannelBit")
            elif todo["Convert"].startswith("ChannelBitStatus"):
                print("CONVERT ChannelBitStatus")
            else:
                self._log.error("UNKNOWN convert requested: {}".format(todo["Convert"]))
        return result

    async def _handle_module_type(self, msg: Message) -> None:
        """
        load the module data
        """
        data = keys_exists(self.pdata, "ModuleTypes", h2(msg.module_type))
        if not data:
            self._log.warning(f"Module not recognized: {msg.module_type}")
            return
        # create the module
        await self._velbus.add_module(
            msg.address,
            msg.module_type,
            data,
            memorymap=msg.memory_map_version,
            build_year=msg.build_year,
            build_week=msg.build_week,
            serial=msg.serial,
        )

    async def _handle_module_subtype(self, msg: Message) -> None:
        if msg.address not in self._velbus.get_modules():
            return
        addrList = {
            1: msg.sub_address_1,
            2: msg.sub_address_2,
            3: msg.sub_address_3,
            4: msg.sub_address_4,
        }
        await self._velbus.add_submodules(msg.address, addrList)

    def _channel_convert(self, module: str, channel: str, ctype: str) -> None | int:
        data = keys_exists(
            self.pdata, "ModuleTypes", h2(module), "ChannelNumbers", ctype
        )
        if data and "Map" in data and h2(channel) in data["Map"]:
            return data["Map"][h2(channel)]
        if data and "Convert" in data:
            return int(channel)
        for offset in range(0, 8):
            if channel & (1 << offset):
                return offset + 1
        return None
