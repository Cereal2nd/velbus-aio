"""
author: Maikel Punie <maikel.punie@gmail.com>
"""

import json
import string

from velbusaio.messages.switch_relay_off import SwitchRelayOffMessage
from velbusaio.messages.switch_relay_on import SwitchRelayOnMessage


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
        self._name_parts = {}

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
        return f"{self.get_name()} ({self._module.get_name()})"

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
        try:
            self._name_parts[int(part)] = name
            if int(part) == 3:
                self._generate_name()
        except Exception as exception:
            print("++++++++++++++++++++++++++++++++++++++")
            print(exception)
            print(part)
            print(self._name_parts)

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
        return {k: d[k] for k in d if k != "_writer"}

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

    def get_categories(self):
        """
        Get the categories (for hass)
        """
        # COMPONENT_TYPES = ["switch", "sensor", "binary_sensor", "cover", "climate", "light"]
        return []


class Blind(Channel):
    """
    A blind channel
    """

    def get_categories(self):
        return ["cover"]


class Button(Channel):
    """
    A Button channel
    """

    _enabled = True
    _closed = False
    _on = None

    def get_categories(self):
        return ["binary_sensor", "light"]

    def is_on(self):
        """
        Return if this relay is on
        """
        return self._on


class ButtonCounter(Channel):
    """
    A ButtonCounter channel
    This channel can act as a button and as a counter
    """

    _Unit = None
    _PulsePerUnits = None
    _pulses = None
    _counter = None
    _delay = None

    def get_categories(self):
        if self._PulsePerUnits == 0:
            return ["binary_sensor"]
        return ["sensor"]


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
        msg = SwitchRelayOnMessage(self._address)
        msg.relay_channels = [self.num]
        await self._writer(msg)

    async def turn_off(self):
        """
        Send the turn off message
        """
        msg = SwitchRelayOffMessage(self._address)
        msg.relay_channels = [self.num]
        await self._writer(msg)


class Sensor(Channel):
    """
    A Sensor channel
    """

    def get_categories(self):
        return ["sensor"]


class SensorNumber(Sensor):
    """
    A Numeric Sensor channel
    """


class Temperature(Sensor):
    """
    A Temperature sensor channel
    """

    _cur = None
    _max = None
    _min = None


class LightSensor(Sensor):
    """
    A light sensor channel
    """
