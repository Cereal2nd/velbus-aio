"""
Velbus packet handler
:Author maikel punie <maikel.punie@gmail.com>
"""

from __future__ import annotations

from velbusaio.const import SCAN_MODULETYPE_TIMEOUT
from velbusaio.const import SCAN_MODULEINFO_TIMEOUT
from velbusaio.const import SCAN_MODULEINFO_COMPLETION_TIME

import asyncio
import json
import logging
import threading

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
        self._typeResponseReceived = asyncio.Event()
        self._scanLock = threading.Lock()
        self._modulescan_address = 0
        self._scan_complete = False
        self._scan_delay_msec = 0
        with open(
            pkg_resources.resource_filename(__name__, "protocol.json")
        ) as protocol_file:
            self.pdata = json.load(protocol_file)

    async def scan(self) -> None:
        self._log.info("Start module scan")
        while self._modulescan_address < 254:
            address = 0
            module = None
            with self._scanLock:
                self._modulescan_address = self._modulescan_address + 1
                address = self._modulescan_address
                module = self._velbus.get_module(address)
            self._log.info(f"Starting scan {address} Module {module}")
            if module is None:
                try:
                    self._typeResponseReceived.clear()
                    await self._velbus.sendTypeRequestMessage(address)
                    await asyncio.wait_for(
                        self._typeResponseReceived.wait(),
                        SCAN_MODULETYPE_TIMEOUT / 1000.0,
                    )
                    with self._scanLock:
                        module = self._velbus.get_module(address)
                except asyncio.TimeoutError:
                    self._log.info(
                        f"Scan module {address} failed: not present or unavailable"
                    )
            if module is not None:
                if not module.is_loaded():
                    try:
                        self._log.debug(f"Module {address} detected: start loading")
                        await asyncio.wait_for(
                            module.load(from_cache=True),
                            SCAN_MODULEINFO_TIMEOUT / 1000.0,
                        )
                        self._scan_delay_msec = SCAN_MODULEINFO_COMPLETION_TIME
                        while self._scan_delay_msec > 10:
                            self._scan_delay_msec = self._scan_delay_msec - 10
                            # self._log.debug(f"\t... waiting {self._scan_delay_msec}")
                            await asyncio.sleep(0.01)
                        self._log.info(f"Scan module {address} completed")
                    except asyncio.TimeoutError:
                        self._log.error(
                            f"Module {address} did not respond to info requests after successful type request"
                        )
        self._scan_complete = True
        self._log.info("Module scan completed")

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

        # handle module type response message
        if command_value == 0xFF:
            if not self._scan_complete:
                msg = ModuleTypeMessage()
                msg.populate(priority, address, rtr, data)
                with self._scanLock:
                    await self._handle_module_type(msg)
                    if address == self._modulescan_address:
                        self._typeResponseReceived.set()
                    elif address < self._modulescan_address:
                        self._log.debug(
                            f"Resetting scan address from {self._modulescan_address} to {address}"
                        )
                        self._modulescan_address = address
                self._typeResponseReceived.set()

        # handle module subtype response message
        elif command_value in (0xB0, 0xA7, 0xA6):
            if not self._scan_complete:
                msg = ModuleSubTypeMessage()
                msg.populate(priority, address, rtr, data)
                if command_value == 0xB0:
                    msg.sub_address_offset = 0
                elif command_value == 0xA7:
                    msg.sub_address_offset = 4
                elif command_value == 0xA6:
                    msg.sub_address_offset = 8
                with self._scanLock:
                    self._scan_delay_msec = SCAN_MODULEINFO_COMPLETION_TIME
                    self._handle_module_subtype(msg)

        # ignore broadcast
        elif command_value in self.pdata["MessagesBroadCast"]:
            self._log.debug(
                "Received broadcast message {} from {}, ignoring".format(
                    self.pdata["MessageBroadCast"][command_value.upper()], address
                )
            )
        # handle other messages for modules that are already scanned
        else:
            module = None
            with self._scanLock:
                module = self._velbus.get_module(address)
            if module is not None:
                module_type = module.get_type()
                if commandRegistry.has_command(int(command_value), module_type):
                    command = commandRegistry.get_command(command_value, module_type)
                    msg = command()
                    msg.populate(priority, address, rtr, data)
                    # restart the info completion time when info message received
                    if command_value in (
                        0xF0,
                        0xF1,
                        0xF2,
                        0xFB,
                        0xFE,
                        0xCC,
                    ):  # names, memory data, memory block
                        self._scan_delay_msec = SCAN_MODULEINFO_COMPLETION_TIME
                        # self._log.debug(f"Restart timeout {msg}")
                    # send the message to the modules
                    await self._velbus.get_module(msg.address).on_message(msg)
                else:
                    self._log.warning(f"NOT FOUND IN command_registry: {rawmsg}")

    async def _handle_module_type(self, msg: Message) -> None:
        """
        load the module data
        """
        if msg is not None:
            module = self._velbus.get_module(msg.address)
            if module is None:
                data = keys_exists(self.pdata, "ModuleTypes", h2(msg.module_type))
                if not data:
                    self._log.warning(f"Module not recognized: {msg.module_type}")
                    return
                self._velbus.add_module(
                    msg.address,
                    msg.module_type,
                    data,
                    memorymap=msg.memory_map_version,
                    build_year=msg.build_year,
                    build_week=msg.build_week,
                    serial=msg.serial,
                )
            else:
                self._log.debug(
                    f"***Module already exists scanAddr={self._modulescan_address} addr={msg.address} {msg}"
                )

        # else:
        #    self._log.debug("*** handle_module_type called without response message")

    def _handle_module_subtype(self, msg: Message) -> None:
        module = self._velbus.get_module(msg.address)
        if module is not None:
            addrList = {
                (msg.sub_address_offset + 1): msg.sub_address_1,
                (msg.sub_address_offset + 2): msg.sub_address_2,
                (msg.sub_address_offset + 3): msg.sub_address_3,
                (msg.sub_address_offset + 4): msg.sub_address_4,
            }
            self._velbus.add_submodules(module, addrList)

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
