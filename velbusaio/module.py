"""
This represents a velbus module
"""
from __future__ import annotations

import logging
import os
import pathlib
import pickle
import struct
import sys

from velbusaio.channels import (
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
from velbusaio.const import CHANNEL_LIGHT_VALUE, CHANNEL_MEMO_TEXT, PRIORITY_LOW
from velbusaio.helpers import handle_match, keys_exists
from velbusaio.messages.blind_status import BlindStatusMessage, BlindStatusNgMessage
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
from velbusaio.messages.clear_led import ClearLedMessage
from velbusaio.messages.counter_status import CounterStatusMessage
from velbusaio.messages.counter_status_request import CounterStatusRequestMessage
from velbusaio.messages.dimmer_channel_status import DimmerChannelStatusMessage
from velbusaio.messages.dimmer_status import DimmerStatusMessage
from velbusaio.messages.fast_blinking_led import FastBlinkingLedMessage
from velbusaio.messages.memory_data import MemoryDataMessage
from velbusaio.messages.module_status import (
    ModuleStatusMessage,
    ModuleStatusMessage2,
    ModuleStatusPirMessage,
)
from velbusaio.messages.module_status_request import ModuleStatusRequestMessage
from velbusaio.messages.module_subtype import ModuleSubTypeMessage
from velbusaio.messages.module_type import ModuleTypeMessage
from velbusaio.messages.push_button_status import PushButtonStatusMessage
from velbusaio.messages.read_data_from_memory import ReadDataFromMemoryMessage
from velbusaio.messages.relay_status import RelayStatusMessage, RelayStatusMessage2
from velbusaio.messages.sensor_temperature import SensorTemperatureMessage
from velbusaio.messages.set_led import SetLedMessage
from velbusaio.messages.slider_status import SliderStatusMessage
from velbusaio.messages.slow_blinking_led import SlowBlinkingLedMessage
from velbusaio.messages.temp_sensor_status import TempSensorStatusMessage
from velbusaio.messages.update_led_status import UpdateLedStatusMessage


class Module:
    """
    Abstract class for Velbus hardware modules.
    """

    def __init__(
        self,
        module_address: int,
        module_type: int,
        module_data: dict,
        serial: str = "",
        memorymap=None,
        build_year=None,
        build_week=None,
        cache_dir=None,
    ) -> None:
        self._address = module_address
        self._type = module_type
        self._data = module_data

        self._name = {}
        self._sub_address = {}
        self.serial: str = serial
        self.memory_map_version = memorymap
        self.build_year = build_year
        self.build_week = build_week
        self._cache_dir = cache_dir
        self._is_loading = False
        self._channels = {}
        self.loaded = False

    def initialize(self, writer: type) -> None:
        self._log = logging.getLogger("velbus-module")
        self._writer = writer
        for chan in self._channels.values():
            chan._writer = writer

    def cleanupSubChannels(self) -> None:
        if self._sub_address == {}:
            assert "No subaddresses defined"
        for sub in range(1, 4):
            if sub not in self._sub_address:
                for i in range(((sub * 8) + 1), (((sub + 1) * 8) + 1)):
                    if i in self._channels:
                        del self._channels[i]

    def _cache(self) -> None:
        cfile = pathlib.Path(f"{self._cache_dir}/{self._address}.p")
        with cfile.open("wb") as fl:
            pickle.dump(self, fl)

    def __getstate__(self) -> dict:
        d = self.__dict__
        self_dict = {k: d[k] for k in d if k != "_writer" and k != "_log"}
        return self_dict

    def __setstate__(self, state: dict) -> None:
        self.__dict__ = state

    def __repr__(self) -> str:
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

    def __str__(self) -> str:
        return self.__repr__()

    def get_addresses(self) -> list:
        """
        Get all addresses for this module
        """
        res = []
        res.append(self._address)
        for addr in self._sub_address.values():
            res.append(addr)
        return res

    def get_type(self) -> int:
        """
        Get the module type
        """
        return self._type

    def get_type_name(self) -> str:
        return self._data["Type"]

    def get_serial(self) -> str | None:
        return self.serial

    def get_name(self) -> str:
        return self._name

    def get_sw_version(self) -> str:
        return "{}-{}.{}.{}".format(
            self.serial,
            self.memory_map_version,
            self.build_year,
            self.build_week,
        )

    def calc_channel_offset(self, address) -> int:
        _channel_offset = 0
        if self._address != address:
            for _sub_addr_key, _sub_addr_val in self._sub_address.items():
                if _sub_addr_val == address:
                    _channel_offset = 8 * _sub_addr_key
                    break
        return _channel_offset

    async def on_message(self, message) -> None:
        """
        Process received message
        """
        _channel_offset = self.calc_channel_offset(message.address)

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
            await self._process_memory_data_message(message)
        elif isinstance(message, (RelayStatusMessage, RelayStatusMessage2)):
            await self._channels[message.channel].update(
                {
                    "on": message.is_on(),
                    "inhibit": message.is_inhibited(),
                    "forced_on": message.is_forced_on(),
                    "disabled": message.is_disabled(),
                }
            )
        elif isinstance(message, SensorTemperatureMessage):
            chan = self._translate_channel_name(self._data["TemperatureChannel"])
            await self._channels[chan].update(
                {
                    "cur": message.getCurTemp(),
                    "min": message.getMinTemp(),
                    "max": message.getMaxTemp(),
                }
            )
        elif isinstance(message, TempSensorStatusMessage):
            # update the current temp
            chan = self._translate_channel_name(self._data["TemperatureChannel"])
            if chan in self._channels:
                await self._channels[chan].update(
                    {
                        "cur": message.current_temp,
                        "target": message.target_temp,
                        "cmode": message.mode_str,
                        "cstatus": message.status_str,
                    }
                )
        elif isinstance(message, PushButtonStatusMessage):
            _update_buttons = False
            for channel_types in self._data["Channels"]:
                if keys_exists(self._data, "Channels", channel_types, "Type"):
                    if self._data["Channels"][channel_types]["Type"] == "Button":
                        _update_buttons = True
                        break
            if _update_buttons:
                for channel_id in range(1, 9):
                    channel = self._translate_channel_name(channel_id + _channel_offset)
                    if channel_id in message.closed:
                        await self._channels[channel].update({"closed": True})
                    if channel_id in message.opened:
                        await self._channels[channel].update({"closed": False})
        elif isinstance(message, (ModuleStatusMessage)):
            for channel_id in range(1, 9):
                channel = self._translate_channel_name(channel_id + _channel_offset)
                if channel_id in message.closed:
                    await self._channels[channel].update({"closed": True})
                elif channel in self._channels and isinstance(
                    self._channels[channel], (Button, ButtonCounter)
                ):
                    await self._channels[channel].update({"closed": False})
        elif isinstance(message, (ModuleStatusMessage2)):
            for channel_id in range(1, 9):
                channel = self._translate_channel_name(channel_id + _channel_offset)
                if channel_id in message.closed:
                    await self._channels[channel].update({"closed": True})
                elif isinstance(self._channels[channel], (Button, ButtonCounter)):
                    await self._channels[channel].update({"closed": False})
                if channel_id in message.enabled:
                    await self._channels[channel].update({"enabled": True})
                elif channel in self._channels and isinstance(
                    self._channels[channel], (Button, ButtonCounter)
                ):
                    await self._channels[channel].update({"enabled": False})
        elif isinstance(message, CounterStatusMessage) and isinstance(
            self._channels[message.channel], ButtonCounter
        ):
            channel = self._translate_channel_name(message.channel)
            await self._channels[channel].update(
                {
                    "pulses": message.pulses,
                    "counter": message.counter,
                    "delay": message.delay,
                }
            )
        elif isinstance(message, ModuleStatusPirMessage):
            await self._channels[CHANNEL_LIGHT_VALUE].update(
                {"cur": message.light_value}
            )
        elif isinstance(message, UpdateLedStatusMessage):
            for channel_id in range(1, 9):
                channel = self._translate_channel_name(channel_id + _channel_offset)
                if channel_id in message.led_slow_blinking:
                    await self._channels[channel].update({"led_state": "slow"})
                if channel_id in message.led_fast_blinking:
                    await self._channels[channel].update({"led_state": "fast"})
                if channel_id in message.led_on:
                    await self._channels[channel].update({"led_state": "on"})
                if (
                    channel_id not in message.led_slow_blinking
                    and channel_id not in message.led_fast_blinking
                    and channel_id not in message.led_on
                ):
                    await self._channels[channel].update({"led_state": "off"})
        elif isinstance(message, SetLedMessage):
            for channel_id in range(1, 9):
                channel = self._translate_channel_name(channel_id + _channel_offset)
                if channel_id in message.leds:
                    await self._channels[channel].update({"led_state": "on"})
        elif isinstance(message, ClearLedMessage):
            for channel_id in range(1, 9):
                channel = self._translate_channel_name(channel_id + _channel_offset)
                if channel_id in message.leds:
                    await self._channels[channel].update({"led_state": "off"})
        elif isinstance(message, SlowBlinkingLedMessage):
            for channel_id in range(1, 9):
                channel = self._translate_channel_name(channel_id + _channel_offset)
                if channel_id in message.leds:
                    await self._channels[channel].update({"led_state": "slow"})
        elif isinstance(message, FastBlinkingLedMessage):
            for channel_id in range(1, 9):
                channel = self._translate_channel_name(channel_id + _channel_offset)
                if channel_id in message.leds:
                    await self._channels[channel].update({"led_state": "fast"})
        elif isinstance(message, (DimmerChannelStatusMessage, DimmerStatusMessage)):
            channel = self._translate_channel_name(message.channel)
            await self._channels[channel].update({"state": message.cur_dimmer_state()})
        elif isinstance(message, SliderStatusMessage):
            channel = self._translate_channel_name(message.channel)
            await self._channels[channel].update({"state": message.cur_slider_state()})
        elif isinstance(message, BlindStatusNgMessage):
            channel = self._translate_channel_name(message.channel)
            await self._channels[channel].update(
                {"state": message.status, "position": message.position}
            )
        elif isinstance(message, BlindStatusMessage):
            channel = self._translate_channel_name(message.channel)
            await self._channels[channel].update({"state": message.status})

        self._cache()

    def get_channels(self) -> list:
        """
        List all channels for this module
        """
        return self._channels

    async def load(self, from_cache=False) -> None:
        """
        Retrieve names of channels
        """
        # did we already start the loading?
        # this is needed for the submodules,
        # as the submodule address maps to the main module
        # this method can be called multiple times
        if self._is_loading or self.loaded:
            if from_cache:
                await self._request_module_status()
            return
        self._log.info("Load Module")
        # start the loading
        self._is_loading = True
        # load default channels
        await self.__load_default_channels()
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

    def _load(self) -> None:
        """
        Method for per module type loading
        """
        pass

    def number_of_channels(self) -> int:
        """
        Retrieve the number of available channels in this module

        :return: int
        """
        if not len(self._channels):
            return 0
        return max(self._channels.keys())

    async def set_memo_text(self, txt: str) -> None:
        if CHANNEL_MEMO_TEXT not in self._channels.keys():
            return
        await self._channels[CHANNEL_MEMO_TEXT].set(txt)

    async def _process_memory_data_message(self, message) -> None:
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
                    await self._channels[chan].update(data)
        except KeyError:
            print("KEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEY")

    def _process_channel_name_message(self, part, message) -> None:
        channel = self._translate_channel_name(message.channel)
        if channel not in self._channels:
            return
        self._channels[channel].set_name_part(part, message.name)

    def _translate_channel_name(self, channel: str) -> int:
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

    def is_loaded(self) -> bool:
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

    async def _request_module_status(self) -> None:
        """Request current state of channels."""
        if "Channels" not in self._data:
            # some modules have no channels
            return
        mod_stat_req_msg = ModuleStatusRequestMessage(self._address)
        counter_msg = None
        for chan, chan_data in self._data["Channels"].items():
            if int(chan) < 9 and chan_data["Type"] in ("Blind", "Dimmer", "Relay"):
                mod_stat_req_msg.channels.append(int(chan))
            if chan_data["Type"] == "ButtonCounter":
                if counter_msg is None:
                    counter_msg = CounterStatusRequestMessage(self._address)
                counter_msg.channels.append(int(chan))
        await self._writer(mod_stat_req_msg)
        if counter_msg is not None:
            await self._writer(counter_msg)

    async def _request_channel_name(self) -> None:
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

    async def __load_memory(self) -> None:
        """
        Request all needed memory addresses
        """
        if "Memory" not in self._data:
            self._name = None
            return

        if self._type == 0x0C:
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

    async def __load_default_channels(self) -> None:
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
            if chan_data["Type"] == "Temperature":
                if "Thermostat" in self._data or (
                    "ThermostatAddr" in self._data and self._data["ThermostatAddr"] != 0
                ):
                    await self._channels[int(chan)].update({"thermostat": True})
