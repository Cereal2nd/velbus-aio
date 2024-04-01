"""
Velbus packet handler
:Author maikel punie <maikel.punie@gmail.com>
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import TYPE_CHECKING, Awaitable, Callable
import pkg_resources

from velbusaio.command_registry import commandRegistry
from velbusaio.helpers import h2, keys_exists
from velbusaio.message import Message
from velbusaio.messages.module_subtype import ModuleSubTypeMessage
from velbusaio.messages.module_type import ModuleTypeMessage
from velbusaio.raw_message import RawMessage

if TYPE_CHECKING:
    from velbusaio.controller import Velbus


class PacketHandler:
    """
    The packetHandler class
    """

    def __init__(
        self,
        writer: Callable[[Message], Awaitable[None]],
        velbus: Velbus,
    ) -> None:
        self._log = logging.getLogger("velbus-packet")
        self._writer = writer
        self._velbus = velbus
        self._active_modulescan_address = 0  # lgor
        self._moduletyperesponsemsg = None  # lgor received type response message
        self.scan_complete = False
        # lgor self._scan_complete_event = asyncio.Event()
        with open(
            pkg_resources.resource_filename(__name__, "protocol.json")
        ) as protocol_file:
            self.pdata = json.load(protocol_file)

    # lgor added for initiating single module type scan
    def set_module_type_request(self, address: int) -> None:  # lgor
        self._moduletyperesponsemsg = None  # lgor
        self._active_modulescan_address = address  # lgor

    # lgor added for test received module type message
    def is_module_typerespons_ok(self) -> bool:  # lgor
        return self._moduletyperesponsemsg is not None  # lgor

    # lgor removed: no global scan start / completion required
    # def scan_finished(self) -> None:
    #    self._scan_complete = True
    #    self._scan_complete_event.set()
    #    self._log.debug("Scan complete")

    # lgor removed: no global scan start / completion required
    # def scan_started(self) -> None:
    #    self._scan_complete = False
    #    self._scan_complete_event.clear()

    async def handle(self, rawmsg: RawMessage) -> None:
        """
        Handle a received packet
        """
        if rawmsg.address < 1 or rawmsg.address > 254:
            return
        if rawmsg.command is None:
            return

        priority = rawmsg.priority
        address = rawmsg.address
        rtr = rawmsg.rtr
        command_value = rawmsg.command
        data = rawmsg.data_only

        # lgor handle config related messages
        if command_value in (0xFF, 0xB0, 0xA7, 0xA6):  # lgor
            if (
                self.active_modulescan_address == address
            ):  # lgor only respond to requested module (VelbusLink might interfere otherwise)
                if command_value == 0xFF:  # lgor type response message
                    self._moduletyperesponsemsg = ModuleTypeMessage()  # lgor
                    self._moduletyperesponsemsg.populate(
                        priority, address, rtr, data
                    )  # lgor
            else:
                msg = ModuleSubTypeMessage()
                msg.populate(priority, address, rtr, data)

                if command_value == 0xB0:
                    msg.sub_address_offset = 0
                elif command_value == 0xA7:
                    msg.sub_address_offset = 4
                elif command_value == 0xA6:
                    msg.sub_address_offset = 8
                else:
                    raise RuntimeError("Unreachable code reached => bug here")

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
                msg.populate(priority, address, rtr, data)
                self._log.debug(f"Received {msg}")
                # send the message to the modules
                await self._velbus.get_module(msg.address).on_message(msg)
            else:
                self._log.warning(
                    "NOT FOUND IN command_registry: addr={} cmd={} packet={}".format(
                        address, command_value, ":".join(format(x, "02x") for x in data)
                    )
                )
        elif self.scan_complete:
            # this should only happen once the scan is complete, of its not complete suspended the error message
            self._log.warning(
                "UNKNOWN module, you should initialize a full new velbus scan: packet={}, address={}, modules={}".format(
                    ":".join(format(x, "02x") for x in data),
                    address,
                    self._velbus.get_modules().keys(),
                )
            )

    async def _handle_module_type(self, msg: Message) -> None:
        """
        load the module data
        """
        msg = self._moduletyperesponsemsg  # lgor
        if msg is not None:  # lgor
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
            (msg.sub_address_offset + 1): msg.sub_address_1,
            (msg.sub_address_offset + 2): msg.sub_address_2,
            (msg.sub_address_offset + 3): msg.sub_address_3,
            (msg.sub_address_offset + 4): msg.sub_address_4,
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
