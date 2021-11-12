"""
author: Maikel Punie <maikel.punie@gmail.com>
"""
from __future__ import annotations

import string
from typing import Any, Callable

from velbusaio.command_registry import commandRegistry
from velbusaio.const import (
    DEVICE_CLASS_ILLUMINANCE,
    DEVICE_CLASS_TEMPERATURE,
    ENERGY_KILO_WATT_HOUR,
    TEMP_CELSIUS,
    VOLUME_CUBIC_METER_HOUR,
    VOLUME_LITERS_HOUR,
)


class Channel:
    """
    A velbus channel
    This is the basic abstract class of a velbus channel
    """

    def __init__(self, module, num, name, nameEditable, writer, address):
        self._num = num
        self._module = module
        self._name = name
        if not nameEditable:
            self._is_loaded = True
        else:
            self._is_loaded = False
        self._writer = writer
        self._address = address
        self._on_status_update = []
        self._name_parts = {}

    def get_module_type(self) -> str:
        return self._module.get_type()

    def get_module_type_name(self) -> str:
        return self._module.get_type_name()

    def get_module_serial(self) -> str:
        return self._module.get_serial()

    def get_module_address(self, chan_type="") -> int:
        """Return (sub)module address for channel"""
        _mod_address = self._address
        if chan_type == "Button" and self._num > 8:
            _mod_address = self._module.get_addresses()[1]
            if self._num > 16:
                _mod_address = self._module.get_addresses()[2]
                if self._num > 24:
                    _mod_address = self._module.get_addresses()[3]
        return _mod_address

    def get_module_sw_version(self) -> str:
        return self._module.get_sw_version()

    def get_channel_number(self) -> int:
        return self._num

    def get_full_name(self) -> str:
        return f"{self._module.get_name()} ({self._module.get_type_name()})"

    def is_loaded(self) -> bool:
        """
        Is this channel loaded

        :return: Boolean
        """
        return self._is_loaded

    def is_counter_channel(self) -> bool:
        return False

    def is_temperature(self) -> bool:
        return False

    def get_name(self) -> str:
        """
        :return: the channel name
        """
        return self._name

    def set_name_part(self, part, name) -> None:
        """
        Set a part of the channel name
        """
        # if int(part) not in self._name_parts:
        #    return
        self._name_parts[int(part)] = name
        if len(self._name_parts) == 3:
            self._generate_name()

    def _generate_name(self) -> None:
        """
        Generate the channel name if all 3 parts are received
        """
        name = self._name_parts[1] + self._name_parts[2] + self._name_parts[3]
        self._name = "".join(filter(lambda x: x in string.printable, name))
        self._is_loaded = True
        self._name_parts = {}

    def __getstate__(self):
        d = self.__dict__
        return {
            k: d[k]
            for k in d
            if k != "_writer" and k != "_on_status_update" and k != "_name_parts"
        }

    def __setstate__(self, state):
        self.__dict__.update(state)
        self._on_status_update = []
        self._name_parts = {}

    def __repr__(self):
        items = []
        for k, v in self.__dict__.items():
            if k not in ["_module", "_writer", "_name_parts"]:
                items.append(f"{k} = {v!r}")
        return "{}[{}]".format(type(self), ", ".join(items))

    def __str__(self):
        return self.__repr__()

    async def update(self, data: dict) -> None:
        """
        Set the attributes of this channel
        """
        for key, new_val in data.items():
            cur_val = getattr(self, f"_{key}", None)
            if cur_val is None or cur_val != new_val:
                setattr(self, f"_{key}", new_val)
                for m in self._on_status_update:
                    await m()

    def get_categories(self) -> list:
        """
        Get the categories (mainly for home-assistant)
        """
        # COMPONENT_TYPES = ["switch", "sensor", "binary_sensor", "cover", "climate", "light"]
        return []

    def on_status_update(self, meth: Callable) -> None:
        self._on_status_update.append(meth)

    def get_counter_state(self):
        return None

    def get_counter_unit(self):
        return None


class Blind(Channel):
    """
    A blind channel
    """

    _state = None
    _position = 0

    def get_categories(self) -> list:
        return ["cover"]

    def get_position(self) -> int:
        return self._position

    def get_state(self) -> str:
        return self._state

    def is_closed(self) -> bool:
        if self._state == 0x02:
            return True
        return False

    def is_open(self) -> bool:
        if self._state == 0x01:
            return True
        return False

    def support_position(self) -> bool:
        return False

    async def open(self) -> None:
        cls = commandRegistry.get_command(0x05, self._module.get_type())
        msg = cls(self._address)
        msg.channel = self._num
        await self._writer(msg)

    async def close(self) -> None:
        cls = commandRegistry.get_command(0x06, self._module.get_type())
        msg = cls(self._address)
        msg.channel = self._num
        await self._writer(msg)

    async def stop(self) -> None:
        cls = commandRegistry.get_command(0x04, self._module.get_type())
        msg = cls(self._address)
        msg.channel = self._num
        await self._writer(msg)

    async def set_position(self, position: int) -> None:
        cls = commandRegistry.get_command(0x1C, self._module.get_type())
        msg = cls(self._address)
        msg.channel = self._num
        msg.position = position
        await self._writer(msg)


class Button(Channel):
    """
    A Button channel
    """

    _enabled = True
    _closed = False
    _led_state = None

    def get_categories(self) -> list:
        if self._enabled:
            return ["binary_sensor", "led"]
        return []

    def is_closed(self) -> bool:
        """
        Return if this button is on
        """
        return self._closed

    def is_on(self) -> bool:
        """
        Return if this relay is on
        """
        if self._led_state == "on":
            return True
        return False

    async def set_led_state(self, state: str) -> None:
        """
        Set led

        :return: None
        """
        if state == "on":
            code = 0xF6
        elif state == "slow":
            code = 0xF7
        elif state == "fast":
            code = 0xF8
        elif state == "off":
            code = 0xF5
        else:
            return

        _mod_add = self.get_module_address("Button")
        _chn_num = self._num - self._module.calc_channel_offset(_mod_add)
        cls = commandRegistry.get_command(code, self._module.get_type())
        msg = cls(_mod_add)
        msg.leds = [_chn_num]
        await self._writer(msg)
        await self.update({"led_state": state})


class ButtonCounter(Button):
    """
    A ButtonCounter channel
    This channel can act as a button and as a counter
    """

    _Unit = None
    _pulses = None
    _counter = None
    _delay = None

    def get_categories(self) -> list:
        if self._counter:
            return ["sensor"]
        return ["binary_sensor"]

    def is_counter_channel(self) -> bool:
        if self._counter:
            return True
        return False

    def get_state(self) -> int:
        val = 0
        # if we don't know the delay
        # or we don't know the unit
        # or the delay is the max value
        #   we always return 0
        if not self._delay or not self._Unit or self._delay == 0xFFFF:
            return round(0, 2)
        if self._Unit == VOLUME_LITERS_HOUR:
            val = (1000 * 3600) / (self._delay * self._pulses)
        elif self._Unit == VOLUME_CUBIC_METER_HOUR:
            val = (1000 * 3600) / (self._delay * self._pulses)
        elif self._Unit == ENERGY_KILO_WATT_HOUR:
            val = (1000 * 1000 * 3600) / (self._delay * self._pulses)
        else:
            val = 0
        return round(val, 2)

    def get_unit(self) -> str:
        if self._Unit in (
            VOLUME_LITERS_HOUR,
            VOLUME_CUBIC_METER_HOUR,
            ENERGY_KILO_WATT_HOUR,
        ):
            return self._Unit
        return None

    def get_counter_state(self) -> int:
        return round((self._counter / self._pulses), 2)

    def get_counter_unit(self) -> str:
        return self._Unit


class Sensor(Button):
    """
    A Sensor channel
    This is a bit weird, but this happens because of code sharing with openhab
    A sensor in this case is actually a Button
    """


class ThermostatChannel(Button):
    """
    A Thermostat channel
    These are the booster/heater/alarms
    """


class Dimmer(Channel):
    """
    A Dimmer channel
    """

    _state: int = 0

    def get_categories(self) -> list:
        return ["light"]

    def is_on(self) -> bool:
        """
        Check if a dimmer is turned on
        """
        if self._state == 0:
            return False
        return True

    def get_dimmer_state(self) -> int:
        """
        Return the dimmer state
        """
        return self._state

    async def set_dimmer_state(self, slider, transitiontime=0) -> None:
        """
        Set dimmer to slider
        """
        cls = commandRegistry.get_command(0x07, self._module.get_type())
        msg = cls(self._address)
        msg.dimmer_state = slider
        msg.dimmer_transitiontime = int(transitiontime)
        msg.dimmer_channels = [self._num]
        await self._writer(msg)

    async def restore_dimmer_state(self, transitiontime=0) -> None:
        """
        restore dimmer to last known state
        """
        cls = commandRegistry.get_command(0x11, self._module.get_type())
        msg = cls(self._address)
        msg.dimmer_transitiontime = int(transitiontime)
        msg.dimmer_channels = [self._num]
        await self._writer(msg)


class Temperature(Channel):
    """
    A Temperature sensor channel
    """

    _cur = 0
    _max = None
    _min = None
    _target = 0
    _cmode = None
    _cstatus = None
    _thermostat = False

    def get_categories(self) -> list:
        if self._thermostat:
            return ["sensor", "climate"]
        return ["sensor"]

    def get_class(self) -> str:
        return DEVICE_CLASS_TEMPERATURE

    def get_unit(self) -> str:
        return TEMP_CELSIUS

    def get_state(self) -> int:
        return round(self._cur, 2)

    def is_temperature(self) -> bool:
        return True

    def get_max(self) -> int:
        if self._max is None:
            return None
        return round(self._max, 2)

    def get_min(self) -> int:
        if self._min is None:
            return None
        return round(self._min, 2)

    def get_climate_target(self) -> int:
        return round(self._target, 2)

    def get_climate_preset(self) -> str:
        return self._cmode

    def get_climate_mode(self) -> str:
        return self._cstatus

    async def set_temp(self, temp) -> None:
        cls = commandRegistry.get_command(0xE4, self._module.get_type())
        msg = cls(self._address)
        msg.temp = temp * 2
        await self._writer(msg)

    async def set_preset(self, mode) -> None:
        if mode == "safe":
            code = 0xDE
        elif mode == "comfort":
            code = 0xDB
        elif mode == "day":
            code = 0xDC
        elif mode == "night":
            code = 0xDD
        cls = commandRegistry.get_command(code, self._module.get_type())
        msg = cls(self._address)
        await self._writer(msg)

    async def set_mode(self, mode) -> None:
        if mode == "heat":
            code = 0xE0
        elif mode == "cool":
            code = 0xDF
        cls = commandRegistry.get_command(code, self._module.get_type())
        msg = cls(self._address)
        await self._writer(msg)


class SensorNumber(Channel):
    """
    A Numeric Sensor channel
    """

    _cur = 0

    def get_categories(self):
        return ["sensor"]

    def get_class(self):
        return None

    def get_unit(self):
        return None

    def get_state(self):
        return round(self._cur, 2)


class LightSensor(Channel):
    """
    A light sensor channel
    """

    _cur = 0

    def get_categories(self):
        return ["sensor"]

    def get_class(self):
        return DEVICE_CLASS_ILLUMINANCE

    def get_unit(self):
        return None

    def get_state(self):
        return round(self._cur, 2)


class Relay(Channel):
    """
    A Relay channel
    """

    _on = None
    _enabled = True
    _inhibit = False
    _forced_on = False
    _disabled = False

    def get_categories(self) -> list:
        if self._enabled:
            return ["switch"]
        return []

    def is_on(self) -> bool:
        """
        Return if this relay is on
        """
        return self._on

    def is_inhibit(self) -> bool:
        return self._inhibit

    def is_forced_on(self) -> bool:
        return self._forced_on

    def is_disabled(self) -> bool:
        return self._disabled

    async def turn_on(self) -> None:
        """
        Send the turn on message
        """
        cls = commandRegistry.get_command(0x02, self._module.get_type())
        msg = cls(self._address)
        msg.relay_channels = [self._num]
        await self._writer(msg)

    async def turn_off(self) -> None:
        """
        Send the turn off message
        """
        cls = commandRegistry.get_command(0x01, self._module.get_type())
        msg = cls(self._address)
        msg.relay_channels = [self._num]
        await self._writer(msg)


class EdgeLit(Channel):
    """
    An EdgeLit channel
    """

    # def get_categories(self):
    #    return ["light"]


class Memo(Channel):
    """
    A Memo text
    """

    async def set(self, txt: str) -> None:
        cls = commandRegistry.get_command(0xAC, self._module.get_type())
        msg = cls(self._address)
        msgcntr = 0
        for char in txt:
            msg.memo_text += char
            if len(msg.memo_text) >= 5:
                msgcntr += 5
                await self._writer(msg)
                msg = cls(self._address)
                msg.start = msgcntr
        await self._writer(msg)
