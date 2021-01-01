#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
author: Maikel Punie <maikel.punie@gmail.com>
"""

import string

class Channel:
    """
    A velbus channel
    This is the basic abstract class of a velbus channel
    """
    def __init__(self, module, num, name, nameEditable):
        self._num = num
        self._module = module
        self._name = name
        if not nameEditable:
            self._is_loaded = True
        else:
            self._is_loaded = False
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
        assert len(self._name_parts) == 3
        name = self._name_parts[1] + self._name_parts[2] + self._name_parts[3]
        self._name = "".join(filter(lambda x: x in string.printable, name))
        self._is_loaded = True
        self._name_parts = None

    def __repr__(self):
        items = ("%s = %r" % (k, v) for k, v in self.__dict__.items())
        return "<%s: {%s}>" % (self.__class__.__name__, ", ".join(items))

    def __str__(self):
        return "{}(name={}, loaded={})".format(type(self), self._name, self._is_loaded)

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
    _Enabled = True
    _Closed = False

    @property
    def get_categories(self):
        return ["binary_sensor", "light"]


class ButtonCounter(Channel):
    """
    A ButtonCounter channel
    This channel can act as a button and as a counter
    """
    _Unit = None
    _PulsePerUnits = None

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


class LightSensor(Channel):
    """
    A light sensor channel
    """
    @property
    def get_categories(self):
        return ["sensor"]


class Memo(Channel):
    """
    A Memo text
    """


class Relay(Channel):
    """
    A Relay channel
    """
    _On = True

    @property
    def get_categories(self):
        return ["switch"]

    def is_on(self):
        """
        Return if this relay is on
        """
        return self._On

    def turn_on(self):
        """
        Send the turn on message
        """

    def turn_off(self):
        """
        Send the turn off message
        """


class Sensor(Channel):
    """
    A Sensor channel
    """
    @property
    def get_categories(self):
        return ["sensor"]


class SensorNumber(Channel):
    """
    A Numeric Sensor channel
    """
    @property
    def get_categories(self):
        return ["sensor"]


class Temperature(Channel):
    """
    A Temperature sensor channel
    """
    @property
    def get_categories(self):
        return ["sensor"]


class ThermostatChannel(Channel):
    """
    A Thermostat channel
    """
