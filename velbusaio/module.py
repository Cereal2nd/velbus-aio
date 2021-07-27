"""
This represents a velbus module
"""

import logging
import os
import pickle
import struct
import sys

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
from velbusaio.const import CACHEDIR, PRIORITY_LOW
from velbusaio.helpers import handle_match, keys_exists
from velbusaio.messages.channel_name_part1 import (
    ChannelNamePart1Message,
    ChannelNamePart1Message2,
    ChannelNamePart1Message3,
)
from velbusaio.messages.channel_name_part2 import (
    ChannelNamePart2Message,
    ChannelNamePart2Message2,
    ChannelNamePart2Message3,
)
from velbusaio.messages.channel_name_part3 import (
    ChannelNamePart3Message,
    ChannelNamePart3Message2,
    ChannelNamePart3Message3,
)
from velbusaio.messages.channel_name_request import ChannelNameRequestMessage
from velbusaio.messages.counter_status import CounterStatusMessage
from velbusaio.messages.memory_data import MemoryDataMessage
from velbusaio.messages.module_status import ModuleStatusMessage, ModuleStatusMessage2
from velbusaio.messages.module_status_request import ModuleStatusRequestMessage
from velbusaio.messages.module_subtype import ModuleSubTypeMessage
from velbusaio.messages.module_type import ModuleTypeMessage
from velbusaio.messages.push_button_status import PushButtonStatusMessage
from velbusaio.messages.read_data_from_memory import ReadDataFromMemoryMessage
from velbusaio.messages.relay_status import RelayStatusMessage
from velbusaio.messages.sensor_temperature import SensorTemperatureMessage
from velbusaio.messages.temp_sensor_status import TempSensorStatusMessage


class Module:
    """
    Abstract class for Velbus hardware modules.
    """

    def __init__(self, module_address, module_type, module_data):
        self._address = module_address
        self._type = module_type
        self._data = module_data

        self._name = {}
        self._sub_address = {}
        self.serial = 0
        self.memory_map_version = 0
        self.build_year = 0
        self.build_week = 0
        self._is_loading = False
        self._channels = {}
        self.loaded = False

    def initialize(self, writer):
        self._log = logging.getLogger("velbus-module")
        self._log.setLevel(logging.DEBUG)
        self._writer = writer
        for chan in self._channels.values():
            chan._writer = writer

    def cleanupSubChannels(self):
        if self._sub_address == {}:
            assert "No subaddresses defined"
        for sub in range(1, 4):
            if sub not in self._sub_address:
                for i in range(((sub * 8) + 1), (((sub + 1) * 8) + 1)):
                    if i in self._channels:
                        del self._channels[i]

    def _cache(self):
        if not os.path.isdir(CACHEDIR):
            os.mkdir(CACHEDIR)
        with open(f"{CACHEDIR}/{self._address}.p", "wb") as fl:
            pickle.dump(self, fl)

    def __getstate__(self):
        d = self.__dict__
        self_dict = {k: d[k] for k in d if k != "_writer" and k != "_log"}
        return self_dict

    def __setstate__(self, state):
        self.__dict__ = state

    def __repr__(self):
        return (
            "<{}: {{{}}} @ {{{}}} loaded:{{{}}} loading:{{{}}} channels{{:{}}}>".format(
                self._name,
                self._type,
                self._address,
                self.loaded,
                self._is_loading,
                self._channels,
            )
        )

    def __str__(self):
        return self.__repr__()

    def get_addresses(self):
        """
        Get all addresses for this module
        """
        res = []
        res.append(self._address)
        for addr in self._sub_address.values():
            res.append(addr)
        return res

    def get_type(self):
        """
        Get the module type
        """
        return self._type

    def get_type_name(self):
        return self._data["Type"]

    def get_serial(self):
        return self.serial

    def get_name(self):
        return self._name

    def get_sw_version(self):
        return "{}-{}.{}.{}".format(
            self.get_type_name(),
            self.memory_map_version,
            self.build_year,
            self.build_week,
        )

    def on_message(self, message):
        """
        Process received message
        """
        if isinstance(
            message,
            (
                ChannelNamePart1Message,
                ChannelNamePart1Message2,
                ChannelNamePart1Message3,
            ),
        ):
            self._process_channel_name_message(1, message)
        elif isinstance(
            message,
            (
                ChannelNamePart2Message,
                ChannelNamePart2Message2,
                ChannelNamePart2Message3,
            ),
        ):
            self._process_channel_name_message(2, message)
        elif isinstance(
            message,
            (
                ChannelNamePart3Message,
                ChannelNamePart3Message2,
                ChannelNamePart3Message3,
            ),
        ):
            self._process_channel_name_message(3, message)
        elif isinstance(message, MemoryDataMessage):
            self._process_memory_data_message(message)
        elif isinstance(message, ModuleTypeMessage):
            self._process_module_type_message(message)
        elif isinstance(message, ModuleSubTypeMessage):
            self._process_module_subtype_message(message)
        elif isinstance(message, RelayStatusMessage):
            self._channels[message.channel].update({"on": message.is_on()})
        elif isinstance(message, SensorTemperatureMessage):
            chan = self._translate_channel_name("1")
            self._channels[chan].update(
                {
                    "cur": message.getCurTemp(),
                    "min": message.getMinTemp(),
                    "max": message.getMaxTemp(),
                }
            )
        elif isinstance(message, TempSensorStatusMessage):
            chan = self._translate_channel_name("21")
            if chan in self._channels:
                self._channels[chan].update({"cur": message.current_temp})
            # self._target = message.target_temp
            # self._cmode = message.mode_str
            # self._cstatus = message.status_str
        elif isinstance(message, PushButtonStatusMessage):
            for channel in message.closed:
                self._channels[channel].update({"closed": True})
            for channel in message.opened:
                self._channels[channel].update({"closed": False})
        elif isinstance(message, ModuleStatusMessage):
            for channel in self._channels.keys():
                if channel in message.closed:
                    self._channels[channel].update({"closed": True})
                elif isinstance(self._channels[channel], (Button, ButtonCounter)):
                    self._channels[channel].update({"closed": False})
        elif isinstance(message, ModuleStatusMessage2):
            for channel in self._channels.keys():
                if channel in message.closed:
                    self._channels[channel].update({"closed": True})
                elif isinstance(self._channels[channel], (Button, ButtonCounter)):
                    self._channels[channel].update({"closed": False})
                if channel in message.enabled:
                    self._channels[channel].update({"enabled": True})
                elif isinstance(self._channels[channel], (Button, ButtonCounter)):
                    self._channels[channel].update({"enabled": False})
        elif isinstance(message, CounterStatusMessage) and isinstance(
            self._channels[message.channel], ButtonCounter
        ):
            self._channels[message.channel].update(
                {
                    "pulses": message.pulses,
                    "counter": message.counter,
                    "delay": message.delay,
                }
            )
        self._cache()

    def get_channels(self):
        """
        List all channels for this module
        """
        return self._channels

    async def load(self):
        """
        Retrieve names of channels
        """
        # did we already start the loading?
        # this is needed for the submodules,
        # as the submodule address maps to the main module
        # this method can be called multiple times
        if self._is_loading or self.loaded:
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
        # stop the loading
        self._is_loading = False

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
                for chan, chan_data in handle_match(
                    mdata["Match"], message.data
                ).items():
                    data = chan_data.copy()
                    self._channels[chan].update(data)
        except KeyError:
            print("KEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEY")

    def _process_channel_name_message(self, part, message):
        channel = self._translate_channel_name(message.channel)
        if channel not in self._channels:
            return
        self._channels[channel].set_name_part(part, message.name)

    def _translate_channel_name(self, channel):
        if keys_exists(
            self._data,
            "ChannelNumbers",
            "Name",
            "Map",
            f"{int(channel):02X}",
        ):
            return int(
                self._data["ChannelNumbers"]["Name"]["Map"][f"{int(channel):02X}"]
            )
        return int(channel)

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
        if self._is_loading:
            return False
        # the name should be loaded
        if isinstance(self._name, dict):
            return False
        # all channel names should be loaded
        for chan in self._channels.values():
            if not chan.is_loaded():
                return False
        # set that  we finished the module loading
        self.loaded = True
        self._cache()
        return True

    async def _request_module_status(self):
        # request the module status (if available for this module
        msg = ModuleStatusRequestMessage(self._address)
        msg.channels = list(range(1, 9))
        await self._writer(msg)

    async def _request_channel_name(self):
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
            self._name = None
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
            self._channels[int(chan)] = cls(
                self, int(chan), chan_data["Name"], edit, self._writer, self._address
            )
