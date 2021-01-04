"""
This represents a velbus module
"""

import logging
import struct
import sys
from velbusaio.const import PRIORITY_LOW
from velbusaio.helpers import keys_exists, handle_match
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
from velbusaio.messages.module_status_request import ModuleStatusRequestMessage
from velbusaio.messages.channel_name_request import ChannelNameRequestMessage
from velbusaio.channels.channel import (
    Blind,
    Button,
    ButtonCounter,
    Dimmer,
    EdgeLit,
    LightSensor,
    Memo,
    Relay,
    Sensor,
    SensorNumber,
    Temperature,
    ThermostatChannel,
)


class Module:
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

        self._channels = {}

        self.loaded = False

        self._log.info("Found Module {} @ {} ".format(self._type, self._address))

    def get_addresses(self):
        """
        Get all addresses for this module
        """
        res = list()
        res.append(self._address)
        for addr in self._sub_address.values():
            res.append(addr)
        return res

    def get_type(self):
        """
        Get the module type
        """
        return self._type

    def on_message(self, message):
        """
        Process received message
        """
        # handle the messages
        if isinstance(message, (ChannelNamePart1Message, ChannelNamePart1Message2)):
            self._process_channel_name_message(1, message)
        elif isinstance(message, (ChannelNamePart2Message, ChannelNamePart2Message2)):
            self._process_channel_name_message(2, message)
        elif isinstance(message, (ChannelNamePart3Message, ChannelNamePart3Message2)):
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
        """
        List all channels for this module
        """
        return self._channels

    def _on_message(self, message):
        """
        Method to handle per module type messages
        """

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
        self.__load_default_channels()
        # load the data from memory ( the stuff that we need)
        await self.__load_memory()
        # load the module status
        await self._request_module_status()
        # load the channel names
        await self._request_channel_name()
        # load the module specific stuff
        self._load()

    def _load(self):
        """
        Method for per module type loading
        """

    def number_of_channels(self):
        """
        Retrieve the number of available channels in this module

        :return: int
        """
        if not len(self._channels):
            return 0
        return max(self._channels.keys())

    def light_is_buttonled(self, channel):
        """
        Is this light element a buttonled
        """
        # TODO
        return False

    def _process_memory_data_message(self, message):
        addr = "{high:02X}{low:02X}".format(
            high=message.high_address, low=message.low_address
        )
        try:
            mdata = self._data["Memory"]["1"]["Address"][addr]
            print(mdata)
            if "ModuleName" in mdata and isinstance(self._name, dict):
                # if self._name is a dict we are still loading
                # if its a string it was already complete
                if message.data == 0xFF:
                    # modulename is complete
                    self._name = "".join(str(x) for x in self._name.values())
                else:
                    char = mdata["ModuleName"].split(":")[0]
                    self._name[int(char)] = chr(message.data)
                    print("{} == {}".format(int(char), chr(message.data)))
            elif "Match" in mdata:
                for chan, chan_data in handle_match(
                    mdata["Match"], message.data
                ).items():
                    data = chan_data.copy()
                    self._channels[chan].update(data)
        except KeyError:
            print("KEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEY")

    def _process_channel_name_message(self, part, message):
        channel = int(message.channel)
        # some modules need a remap of the channel number
        if keys_exists(
            self._data, "ChannelNumbers", "Name", "Map", "{:02X}".format(channel)
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
        # if we are loaded, just return
        if self.loaded:
            return True
        # the name should be loaded
        if isinstance(self._name, dict):
            return False
        # all channel names should be loaded
        for chan in self._channels.values():
            if not chan.is_loaded():
                return False
        # set that  we finished the module loading
        self.loaded = True
        return True

    async def _request_module_status(self):
        # request the module status (if available for this module
        msg = ModuleStatusRequestMessage(self._address)
        msg.channels = list(range(1, 9))
        await self._writer(msg)

    async def _request_channel_name(self):
        self._log.debug("Requesting channel names")
        # request the module channel names
        if keys_exists(self._data, "AllChannelStatus"):
            msg = ChannelNameRequestMessage(self._address)
            msg.priority = PRIORITY_LOW
            msg.channels = 0xFF
            await self._writer(msg)
        else:
            msg = ChannelNameRequestMessage(self._address)
            msg.priority = PRIORITY_LOW
            msg.channels = list(range(1, (self.number_of_channels() + 1)))
            await self._writer(msg)

    async def __load_memory(self):
        """
        Request all needed memory addresses
        """
        if "Memory" not in self._data:
            return

        for _memory_key, memory_part in self._data["Memory"].items():
            if "Address" in memory_part:
                for addr_int in memory_part["Address"].keys():
                    addr = struct.unpack(
                        ">BB", struct.pack(">h", int("0x" + addr_int, 0))
                    )
                    msg = ReadDataFromMemoryMessage(self._address)
                    msg.priority = PRIORITY_LOW
                    msg.high_address = addr[0]
                    msg.low_address = addr[1]
                    await self._writer(msg)

    def __load_default_channels(self):
        if "Channels" not in self._data:
            return

        for chan, chan_data in self._data["Channels"].items():
            edit = True
            if "Editable" not in chan_data or chan_data["Editable"] != "yes":
                edit = False
            cls = getattr(sys.modules[__name__], chan_data["Type"])
            self._channels[int(chan)] = cls(self, chan_data["Name"], int(chan), edit)
