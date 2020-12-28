import asyncio
import logging
import itertools
import json
import re
from velbusaio.message import Message
from velbusaio.module import Module
from velbusaio.helpers import keys_exists, h2
from velbusaio.const import *


class PacketHandler:
    def __init__(self, protocol):
        self._log = logging.getLogger("velbus-packet")
        self.protocol = protocol
        self.modules = dict()
        with open(
            "/home/cereal/velbus-aio/velbusaio/moduleprotocol/protocol.json"
        ) as fl:
            self.pdata = json.load(fl)

    async def handle(self, data):
        self._log.info("Msg received {}".format(data))
        msg = Message()
        msg.fromData(data)

        # handle based on msgtype
        if msg.rtr:
            self._log.debug("scan")
        elif msg.msgtype == 0xFF:
            await self._handleModuleType(msg)
        del msg
        return
        if msg.address not in self.modules:
            self._log.warning(
                "Module not found (yet): {} !!!!!!!!!!!".format(msg.address)
            )
            return
        if msg.msgtype == 0xB0:
            self._handleModulesubType(msg)
        elif msg.msgtype == 0xD8:
            self._log.debug("Realtime clock status => ignore")
        elif msg.msgtype == 0xB7:
            self._log.debug("Date sync => ignore")
        elif msg.msgtype == 0xE6:
            self._handleTemperature(msg)
        elif msg.msgtype in [0xF0, 0xF1, 0xF2]:
            self._handleChannelName(msg)
        elif msg.msgtype in [0xCC, 0xFE]:
            self._log.debug("Memory data")
        else:
            self._handleModulespecifick(msg)
        del msg

    def _handleModulespecifick(self, msg):
        cmsg = keys_exists(
            self.pdata,
            "ModuleTypes",
            h2(self.modules[msg.address]["type"]),
            "Messages",
            h2(msg.msgtype),
        )
        if not cmsg:
            self._log.warning(
                "IGNORE MESSAGE: messagetype not found for module {} {}".format(
                    h2(self.modules[msg.address]["type"]), h2(msg.msgtype)
                )
            )
            return
        self._log.debug("{0} received".format(cmsg["Info"]))
        result = None
        if "Data" in cmsg and "PerByte" in cmsg["Data"]:
            result = self._perByte(cmsg["Data"]["PerByte"], msg)
        elif "Data" in cmsg and "PerMessage" in cmsg["Data"]:
            result = self._perMessage(cmsg["Data"]["PerMessage"], msg)
        if not result:
            self._log.warning("IGNORE MESSAGE: no parsing info {}".format(cmsg))
            return
        if "Channel" in result and "Value" in result:
            self.modules[msg.address]["channels"][result["Channel"]]["Value"] = result[
                "Value"
            ]
        else:
            self._log.debug("Result: {}".format(result))

    def _perMessage(self, cmsg, msg):
        print("Permessage")
        print(cmsg)

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

    async def _loadModule(self, addr, mtype):
        self._log.info("LOADING MODULE {}".format(addr))
        # request the module status (if available for this module
        if keys_exists(self.pdata, "ModuleTypes", h2(mtype), "Messages", "FA"):
            for chan in list(self.modules[addr]["channels"]):
                msg = Message()
                msg.address = addr
                msg.data = bytearray([0xFA, int(chan)])
                await self.protocol.send(msg)
        # request the module channel names
        d = keys_exists(self.pdata, "ModuleTypes", h2(mtype), "AllChannelStatus")
        if d:
            # some self.modules support FF for all channels
            msg = Message()
            msg.address = addr
            msg.data = bytearray([0xEF, 0xFF])
            await self.protocol.send(msg)
        else:
            for chan in list(self.modules[addr]["channels"]):
                msg = Message()
                msg.address = addr
                msg.data = bytearray([0xEF, int(chan)])
                await self.protocol.send(msg)

    async def _handleModuleType(self, msg):
        self._log.debug("Module type: answer to a Scan")
        # load the module data
        d = keys_exists(self.pdata, "ModuleTypes", h2(msg.data[0]))
        if not d:
            self._log.warning("Module not recognized: {}".format(msg.data[0]))
            return
        # create the module
        self.modules[msg.address] = Module(msg.address, msg.data[0], d, self.protocol)
        # load all params for the module
        await self.modules[msg.address].load()

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

    def _handleModuleSubType(self, msg):
        self._log.debug("Module subtype: answer to a Scan")
        if msg.address not in self.modules:
            return
        self.modules[msg.address]["subAddr"] = dict()
        mtype = msg.data[0]
        # remove moduletype, high serial, low serial
        del msg.data[0:3]
        # store all subaddresses
        for num, subAddr in enumerate(msg.data):
            if subAddr == 0xFF:
                continue
            self.modules[msg.address]["subAddr"][num] = subAddr
            self.modules[subAddr] = {"master": msg.address, "offset": (num * 8) + 1}

        # store thermostat
        d = keys_exists(self.pdata, "ModuleTypes", h2(mtype), "ThermostatAddr")
        if d and msg.data[int(d)] is not 0xFF:
            self.modules[msg.address]["thermostatAddr"] = msg.data[int(d)]

    def _handleChannelName(self, msg):
        channel = self._channelConvert(
            self.modules[msg.address]["type"], msg.data.pop(0), "Name"
        )
        self._log.debug(
            "Channel name part {} ({},{}) = {}".format(
                self.modules[msg.address]["typeName"],
                msg.address,
                channel,
                msg.__dict__,
            )
        )
        # clean out the channel name
        if msg.msgtype == 0xF0:
            self.modules[msg.address]["channels"]["{:0>2}".format(channel)]["Name"] = ""
        # store the chars
        for cha in msg.data:
            if cha == 0xFF:
                break
            self.modules[msg.address]["channels"]["{:0>2}".format(channel)][
                "Name"
            ] += chr(cha)

    def _handleTemperature(self, msg):
        # find the chan with "'Type': 'Temperature'" and store it
        temperature = (((msg.data[0] << 8) | msg.data[1]) / 32) * 0.0625
        for i, y in self.modules[msg.address]["channels"].items():
            if y["Type"] == "Temperature":
                self.modules[msg.address]["channels"][i]["Value"] = temperature
        self._log.debug("Temperature {0} for {1}".format(temperature, msg.address))

    def signal_channel_update(self, address, channel, valueType, value):
        print("UPDATE: {0} {1} {2} {3}".format(address, channel, valueType, value))
