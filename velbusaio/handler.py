import logging
import itertools
import json
import re
from velbusaio.message import Message
from velbusaio.helpers import keys_exists, h2
from velbusaio.command_registry import commandRegistry
from velbusaio.const import *
from velbusaio.messages import *


class PacketHandler:
    def __init__(self, writer, velbus):
        self._log = logging.getLogger("velbus-packet")
        self._writer = writer
        self._velbus = velbus
        self.modules = dict()
        with open(
            "/home/cereal/velbus-aio/velbusaio/moduleprotocol/protocol.json"
        ) as fl:
            self.pdata = json.load(fl)

    async def handle(self, data):
        priority = data[1]
        address = data[2]
        rtr = data[3] & RTR == RTR
        data_size = data[3] & 0x0F
        if data_size < 1:
            return
        if data[4] == 0xFF:
            msg = ModuleTypeMessage()
            msg.populate(priority, address, rtr, data[5:-2])
            await self._handleModuleType(msg)
        elif data[4] == 0xB0:
            msg = ModuleSubTypeMessage()
            msg.populate(priority, address, rtr, data[5:-2])
            await self._handleModuleSubType(msg)
        # TODO handle global messages
        elif address in self._velbus.get_modules():
            command_value = data[4]
            module_type = self._velbus.get_module(address).get_type()
            if commandRegistry.has_command(command_value, module_type):
                command = commandRegistry.get_command(command_value, module_type)
                msg = command()
                msg.populate(priority, address, rtr, data[5:-2])
                self._log.debug("Msg received {}".format(msg))
                # send the message to the modules
                (self._velbus.get_module(msg.address)).on_message(msg)

    def _perByte(self, cmsg, msg):
        result = dict()
        for num, byte in enumerate(msg.data):
            num = str(num)
            # only do something if its defined
            if num not in cmsg:
                continue
            # check if we can do a binary match
            for mat in cmsg[num]["Match"]:
                if (
                    (mat.startswith("%") and re.match(mat[1:], "{0:08b}".format(byte)))
                    or mat == "{0:08b}".format(byte)
                    or mat == "{0:02x}".format(byte)
                ):
                    result = self._perByte_handle(result, cmsg[num]["Match"][mat], byte)
        return result

    def _perByte_handle(self, result, todo, byte):
        if "Channel" in todo:
            result["Channel"] = todo["Channel"]
        if "Value" in todo:
            result["Value"] = todo["Value"]
        if "Convert" in todo:
            result["ValueList"] = []
            if todo["Convert"] == "Decimal":
                result["ValueList"].append(int(byte))
            elif todo["Convert"] == "Counter":
                result["ValueList"].append("{0:02x}".format(byte))
            elif todo["Convert"] == "Temperature":
                print("CONVERT temperature")
            elif todo["Convert"] == "Divider":
                binStr = "{0:08b}".format(byte)
                chan = binStr[6:]
                val = binStr[:5]
                print("CONVERT Divider {} {}".format(chan, val))
            elif todo["Convert"] == "Channel":
                print("CONVERT Channel")
            elif todo["Convert"] == "ChannelBit":
                print("CONVERT ChannelBit")
            elif todo["Convert"].startswith("ChannelBitStatus"):
                print("CONVERT ChannelBitStatus")
            else:
                self._log.error("UNKNOWN convert requested: {}".format(todo["Convert"]))
        return result

    async def _handleModuleType(self, msg):
        # load the module data
        d = keys_exists(self.pdata, "ModuleTypes", h2(msg.module_type))
        if not d:
            self._log.warning("Module not recognized: {}".format(msg.module_type))
            return
        # create the module
        await self._velbus.add_module(msg.address, msg.module_type, d)

    async def _handleModuleSubType(self, msg):
        if msg.address not in self._velbus.get_modules():
            return
        if msg.sub_address_1 != 0xFF:
            await self._velbus.add_module(
                msg.address, msg.module_type, None, msg.sub_address_1, 1
            )
        if msg.sub_address_2 != 0xFF:
            await self._velbus.add_module(
                msg.address, msg.module_type, None, msg.sub_address_2, 2
            )
        if msg.sub_address_3 != 0xFF:
            await self._velbus.add_module(
                msg.address, msg.module_type, None, msg.sub_address_3, 3
            )
        if msg.sub_address_4 != 0xFF:
            await self._velbus.add_module(
                msg.address, msg.module_type, None, msg.sub_address_4, 4
            )

    def _channelConvert(self, module, channel, ctype):
        d = keys_exists(self.pdata, "ModuleTypes", h2(module), "ChannelNumbers", ctype)
        if d and "Map" in d and h2(channel) in d["Map"]:
            return d["Map"][h2(channel)]
        elif d and "Convert" in d:
            return int(channel)
        else:
            for offset in range(0, 8):
                if channel & (1 << offset):
                    return offset + 1
            return None
