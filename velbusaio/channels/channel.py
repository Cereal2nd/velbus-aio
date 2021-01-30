"""
author: Maikel Punie <maikel.punie@gmail.com>
"""

import json
import string


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
        except Exception:
            print("++++++++++++++++++++++++++++++++++++++")
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

    def __repr__(self):
        items = []
        for k, v in self.__dict__.items():
            if k not in ['_module', '_writer', '_name_parts']:
                items.append("%s = %r" % (k, v))
        return "<%s: {%s}>" % (self.__class__.__name__, ", ".join(items))

    def __str__(self):
        return self.__repr__()

    def update(self, data):
        """
        Set the attributes of this channel
        """
        for key, val in data.items():
            setattr(self, "_{}".format(key), val)

    @property
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

    @property
    def get_categories(self):
        return ["cover"]


class Button(Channel):
    """
    A Button channel
    """

    _enabled = True
    _closed = False
    _on = None

    @property
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

    @property
    def get_categories(self):
        if self._PulsePerUnits == 0:
            return ["binary_sensor"]
        return ["sensor"]


class Dimmer(Channel):
    """
    A Dimmer channel
    """

    @property
    def get_categories(self):
        return ["light"]


class EdgeLit(Channel):
    """
    An EdgeLit channel
    """

    @property
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

    @property
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

    def __str__(self):
        return "{}(name={}, loaded={}, on={})".format(
            type(self), self._name, self._is_loaded, self._on
        )


class Sensor(Channel):
    """
    A Sensor channel
    """

    @property
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

    def __str__(self):
        return "{}(name={}, loaded={}, cur={}, min={}, max={})".format(
            type(self), self._name, self._is_loaded, self._cur, self._min, self._max
        )


class LightSensor(Sensor):
    """
    A light sensor channel
    """
