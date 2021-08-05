"""
author: Maikel Punie <maikel.punie@gmail.com>
"""

import json
import string

from velbusaio.command_registry import commandRegistry
from velbusaio.const import (
    DEVICE_CLASS_TEMPERATURE,
    ENERGY_KILO_WATT_HOUR,
    ENERGY_WATT_HOUR,
    TEMP_CELSIUS,
    VOLUME_CUBIC_METER,
    VOLUME_CUBIC_METER_HOUR,
    VOLUME_LITERS,
    VOLUME_LITERS_HOUR,
)
from velbusaio.messages.switch_relay_off import SwitchRelayOffMessage
from velbusaio.messages.switch_relay_on import SwitchRelayOnMessage


class Channel:
    """
    A velbus channel
    This is the basic abstract class of a velbus channel
    """

    _on_status_update = None
    _name_parts = {}

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

    def get_module_type(self):
        return self._module.get_type()

    def get_module_type_name(self):
        return self._module.get_type_name()

    def get_module_serial(self):
        return self._module.get_serial()

    def get_module_address(self):
        return self._module._address

    def get_module_sw_version(self):
        return self._module.get_sw_version()

    def get_channel_number(self):
        return self._num

    def get_full_name(self):
        return f"{self._module.get_name()} ({self._module.get_type_name()})"

    def is_loaded(self):
        """
        Is this channel loaded

        :return: Boolean
        """
        return self._is_loaded

    def get_name(self):
        """
        :return: the channel name
        """
        return self._name

    def set_name_part(self, part, name):
        """
        Set a part of the channel name
        """
        # if int(part) not in self._name_parts:
        #    return
        self._name_parts[int(part)] = name
        if int(part) == 3:
            self._generate_name()

    def _generate_name(self):
        """
        Generate the channel name if all 3 parts are received
        """
        name = self._name_parts[1] + self._name_parts[2] + self._name_parts[3]
        self._name = "".join(filter(lambda x: x in string.printable, name))
        self._is_loaded = True
        self._name_parts = None

    def __getstate__(self):
        d = self.__dict__
        return {k: d[k] for k in d if k != "_writer" and k != "_on_status_update"}

    def __repr__(self):
        items = []
        for k, v in self.__dict__.items():
            if k not in ["_module", "_writer", "_name_parts"]:
                items.append(f"{k} = {v!r}")
        return "{}[{}]".format(type(self), ", ".join(items))

    def __str__(self):
        return self.__repr__()

    def update(self, data):
        """
        Set the attributes of this channel
        """
        for key, val in data.items():
            setattr(self, f"_{key}", val)
        if self._on_status_update:
            self._callback()

    def get_categories(self):
        """
        Get the categories (for hass)
        """
        # COMPONENT_TYPES = ["switch", "sensor", "binary_sensor", "cover", "climate", "light"]
        return []

    def on_status_update(self, meth):
        self._on_status_update = meth


class Blind(Channel):
    """
    A blind channel
    HASS OK
    """

    _state = None
    _position = None

    def get_categories(self):
        return ["cover"]

    def get_position(self):
        return self._position

    def get_state(self):
        return self._state

    def is_closed(self):
        if self._state == 0x02:
            return True
        return False

    def is_open(self):
        if self._state == 0x01:
            return True
        return False

    async def open(self):
        cls = commandRegistry.get_command(0x05, self._module.get_type())
        msg = cls(self._address)
        msg.channel = self._num
        await self._writer(msg)

    async def close(self):
        cls = commandRegistry.get_command(0x06, self._module.get_type())
        msg = cls(self._address)
        msg.channel = self._num
        await self._writer(msg)

    async def stop(self):
        cls = commandRegistry.get_command(0x04, self._module.get_type())
        msg = cls(self._address)
        msg.channel = self._num
        await self._writer(msg)

    async def set_position(self, position):
        cls = commandRegistry.get_command(0x1C, self._module.get_type())
        msg = cls(self._address)
        msg.channel = self._num
        msg.position = position
        await self._writer(msg)


class Button(Channel):
    """
    A Button channel
    HASS OK
    """

    _enabled = True
    _closed = False
    _on = None

    def get_categories(self):
        return ["binary_sensor"]

    def is_closed(self):
        """
        Return if this button is on
        """
        return self._closed

    def _callback(self):
        self._on_status_update(self.is_closed())


class ButtonCounter(Button):
    """
    A ButtonCounter channel
    This channel can act as a button and as a counter
    """

    _Unit = None
    _pulses = None
    _counter = None
    _delay = None

    def get_categories(self):
        if self._counter:
            return ["sensor"]
        return ["binary_sensor"]

    def get_class(self):
        if self._counter:
            return "counter"
        return None

    def get_counter_unit(self):
        return ENERGY_KILO_WATT_HOUR

    def get_unit(self):
        return "W"

    def get_state(self):
        val = 0
        # if we don't know the delay
        # or we don't know the unit
        # or the daly is the max value
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

    def get_counter_state(self):
        return self._counter

    def _callback(self):
        self._on_status_update(self.get_state())


class Dimmer(Channel):
    """
    A Dimmer channel
    """

    def get_categories(self):
        return ["light"]


class EdgeLit(Channel):
    """
    An EdgeLit channel
    """

    def get_categories(self):
        return ["light"]


class Memo(Channel):
    """
    A Memo text
    """


class ThermostatChannel(Channel):
    """
    A Thermostat channel
    """


class Relay(Channel):
    """
    A Relay channel
    HASS OK
    """

    _on = None

    def get_categories(self):
        return ["switch"]

    def is_on(self):
        """
        Return if this relay is on
        """
        return self._on

    async def turn_on(self):
        """
        Send the turn on message
        """
        cls = commandRegistry.get_command(0x02, self._module.get_type())
        msg = cls(self._address)
        msg.relay_channels = [self._num]
        await self._writer(msg)

    async def turn_off(self):
        """
        Send the turn off message
        """
        cls = commandRegistry.get_command(0x01, self._module.get_type())
        msg = cls(self._address)
        msg.relay_channels = [self._num]
        await self._writer(msg)

    def _callback(self):
        self._on_status_update(self.is_on())


class Sensor(Button):
    """
    A Sensor channel
    This is a bit wier, but this happens because of code sharing with openhab
    A sensor in this case is actually a Button
    """


class SensorNumber(Channel):
    """
    A Numeric Sensor channel
    """

    def get_categories(self):
        return []

    def get_state(self):
        return None

    def _callback(self):
        self._on_status_update(self.get_state())


class Temperature(Channel):
    """
    A Temperature sensor channel
    """

    _cur = None
    _max = None
    _min = None

    def get_categories(self):
        return ["sensor"]

    def get_class(self):
        return DEVICE_CLASS_TEMPERATURE

    def get_unit(self):
        return TEMP_CELSIUS

    def get_state(self):
        return self._cur

    def _callback(self):
        self._on_status_update(self.get_state())


class LightSensor(Channel):
    """
    A light sensor channel
    """

    _cur = None

    def get_categories(self):
        return ["sensor"]

    def get_class(self):
        return None

    def get_unit(self):
        return None

    def get_state(self):
        return self._cur

    def _callback(self):
        self._on_status_update(self.get_state())
