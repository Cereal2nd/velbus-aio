import logging
import string
import struct
import re
import sys
from velbusaio.helpers import keys_exists
from velbusaio.message import Message
from velbusaio.messages.read_data_from_memory import ReadDataFromMemoryMessage
from velbusaio.messages.memory_data import MemoryDataMessage
from velbusaio.messages.channel_name_part1 import ChannelNamePart1Message
from velbusaio.messages.channel_name_part1 import ChannelNamePart1Message2
from velbusaio.messages.channel_name_part2 import ChannelNamePart2Message
from velbusaio.messages.channel_name_part2 import ChannelNamePart2Message2
from velbusaio.messages.channel_name_part3 import ChannelNamePart3Message
from velbusaio.messages.channel_name_part3 import ChannelNamePart3Message2
from velbusaio.messages.module_type import ModuleTypeMessage
from velbusaio.messages.module_subtype import ModuleSubTypeMessage
from velbusaio.channels.channel import *


class Module(object):
    """
    Abstract class for Velbus hardware modules.
    """

    def __init__(self, module_address, module_type, module_data, writer):
        self._address = module_address
        self._type = module_type
        self._data = module_data
        self._writer = writer
        self._log = logging.getLogger("velbus-module")
        self._log.setLevel(logging.DEBUG)

        self._name = {}
        self._sub_address = {}
        self.serial = 0
        self.memory_map_version = 0
        self.build_year = 0
        self.build_week = 0
        self._is_loading = False

        self._channel_data = {}
        self._channels = {}

        self._loaded_callbacks = []
        self.loaded = False

        self._log.info("Found Module {} @ {} ".format(self._type, self._address))

    def get_addresses(self):
        res = list()
        res.append(self._address)
        for addr in self._sub_address.values():
            res.append(addr)
        return res

    def get_type(self):
        return self._type

    def on_message(self, message):
        """
        Process received message
        """
        # handle the messages
        if message.msgtype == "F0":
            self._process_channel_name_message(1, message)
        elif message.msgtype == "F1":
            self._process_channel_name_message(2, message)
        elif message.msgtype == "F2":
            self._process_channel_name_message(3, message)
        elif isinstance(message, MemoryDataMessage):
            self._process_memory_data_message(message)
        elif isinstance(message, ModuleTypeMessage):
            self._process_module_type_message(message)
        elif isinstance(message, ModuleSubTypeMessage):
            self._process_module_subtype_message(message)
        else:
            self._on_message(message)

    def get_channels(self):
        return self._channels

    def _on_message(self, message):
        pass

    async def load(self):
        """
        Retrieve names of channels
        """
        # did we already start the loading?
        # this is needed for the submodules,
        # as the submodule address maps to the main module
        # this method can be called multiple times
        if self._is_loading:
            return
        self._log.info("Load Module")
        # start the loading
        self._is_loading = True
        # load default channels
        self._load_default_channels()
        # load the module status
        await self._request_module_status()
        # load the data from memory ( the stuff that we need)
        # await self._load_memory()
        # load the channel names
        await self._request_channel_name()
        # load the module specific stuff
        self._load()

    def _load(self):
        pass

    def number_of_channels(self):
        """
        Retrieve the number of available channels in this module

        :return: int
        """
        raise NotImplementedError

    def light_is_buttonled(self, channel):
        return False

    def _handle_match(self, matchDict, data):
        mResult = {}
        bData = "{:08b}".format(int(data))
        for _num, matchD in matchDict.items():
            tmp = {}
            for match, res in matchD.items():
                if re.fullmatch(match[1:], bData):
                    res2 = res.copy()
                    res2["Data"] = int(data)
                    tmp.update(res2)
            mResult[_num] = tmp
        result = {}
        for res in mResult.values():
            if "Channel" in res:
                result[int(res["Channel"])] = {}
                if (
                    "SubName" in res
                    and "Value" in res
                    and res["Value"] != "PulsePerUnits"
                ):
                    result[int(res["Channel"])] = {res["SubName"]: res["Value"]}
                else:
                    # Very specifick for vmb7in
                    # a = bit 0 to 5 = 0 to 63
                    # b = a * 100
                    b = (data & 0x3F) * 100
                    # c = bit 6 + 7
                    #   00 = x1
                    #   01 = x2,5
                    #   10 = x0.05
                    #   11 = x0.01
                    # d = b * c
                    if data >> 5 == 3:
                        d = b * 0.01
                    elif data >> 5 == 2:
                        d = b * 0.05
                    elif data >> 5 == 1:
                        d = b * 2.5
                    else:
                        d = b
                    result[int(res["Channel"])] = {res["Value"]: d}
        return result

    def _process_memory_data_message(self, message):
        addr = "{high:02X}{low:02X}".format(
            high=message.high_address, low=message.low_address
        )
        try:
            mdata = self._data["Memory"]["1"]["Address"][addr]
            if "ModuleName" in mdata and isinstance(self._name, dict):
                # if self._name is a dict we are still loading
                # if its a string it was already complete
                if message.data == 0xFF:
                    # modulename is complete
                    self._name = "".join(str(x) for x in self._name.values())
                else:
                    char = mdata["ModuleName"].split(":")[0]
                    self._name[int(char)] = chr(message.data)
            elif "Match" in mdata:
                for chan, cData in self._handle_match(
                    mdata["Match"], message.data
                ).items():
                    data = cData.copy()
                    self._channels[chan].update(data)
        except KeyError:
            pass

    def _process_channel_name_message(self, part, message):
        channel = int(message.channel)
        # some modules need a remap of the channel number
        if (
            channel not in self._channels
            and "ChannelNumbers" in self._data
            and "Name" in self._data["ChannelNumbers"]
            and "Map" in self._data["ChannelNumbers"]["Name"]
            and "{:02X}".format(channel) in self._data["ChannelNumbers"]["Name"]["Map"]
        ):
            channel = int(
                self._data["ChannelNumbers"]["Name"]["Map"]["{:02X}".format(channel)]
            )
        self._channels[channel].set_name_part(part, message.name)

    def _process_module_type_message(self, message):
        self.serial = message.serial
        self.memory_map_version = int(message.memory_map_version)
        self.build_year = int(message.build_year)
        self.build_week = int(message.build_week)

    def _process_module_subtype_message(self, message):
        self.serial = message.serial

    def is_loaded(self):
        """
        Check if all name messages have been received
        """
        if self.loaded:
            return True
        for chan in self._channels.values():
            if not chan.is_loaded():
                return False
        # set that  we finished the module loading
        self.loaded = True
        for callback in self._loaded_callbacks:
            callback()
        self._loaded_callbacks = []
        return True

    async def _request_module_status(self):
        # request the module status (if available for this module
        if keys_exists(self._data, "Messages", "FA"):
            msg = Message()
            msg.address = self._address
            msg.data = bytearray([0xFA, 0xFF])
            await self._writer(msg)
        else:
            self._log.info("No FA message defined")

    async def _request_channel_name(self):
        # request the module channel names
        d = keys_exists(self._data, "AllChannelStatus")
        if d:
            # some self.modules support FF for all channels
            msg = Message()
            msg.address = self._address
            msg.data = bytearray([0xEF, 0xFF])
            await self._writer(msg)
        else:
            for chan in self._channels:
                msg = Message()
                msg.address = self._address
                msg.data = bytearray([0xEF, int(chan)])
                await self._writer(msg)

    async def _load_memory(self):
        if "Memory" not in self._data:
            return

        for _memoryKey, memoryPart in self._data["Memory"].items():
            if "Address" in memoryPart:
                for addrAddr in memoryPart["Address"].keys():
                    addr = struct.unpack(
                        ">BB", struct.pack(">h", int("0x" + addrAddr, 0))
                    )
                    message = ReadDataFromMemoryMessage(self._address)
                    message.high_address = addr[0]
                    message.low_address = addr[1]
                    await self._writer(message)

    def _load_default_channels(self):
        if "Channels" not in self._data:
            return

        for chan, chanData in self._data["Channels"].items():
            edit = True
            if "Editable" not in chanData or chanData["Editable"] != "yes":
                edit = False
            cls = getattr(sys.modules[__name__], chanData["Type"])
            self._channels[int(chan)] = cls(self, chanData["Name"], int(chan), edit)
