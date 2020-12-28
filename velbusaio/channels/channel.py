#!/usr/bin/env python
# -*- coding: utf-8 -*-

import string


class Channel:
    def __init__(self, module, num, name, nameEditable):
        self._num = num
        self._module = module
        self._name = name
        if not nameEditable:
            self._is_loaded = True
        else:
            self._is_loaded = False
        self._nameParts = {}

    def is_loaded(self):
        return self._is_loaded

    def get_name(self):
        return self._name

    def set_name_part(self, part, name):
        self._nameParts[int(part)] = name
        if int(part) == 3:
            self._generate_name()

    def _generate_name(self):
        assert len(self._nameParts) == 3
        name = self._nameParts[1] + self._nameParts[2] + self._nameParts[3]
        self._name = "".join(filter(lambda x: x in string.printable, name))
        self._is_loaded = True
        self._nameParts = None

    def __repr__(self):
        items = ("%s = %r" % (k, v) for k, v in self.__dict__.items())
        return "<%s: {%s}>" % (self.__class__.__name__, ", ".join(items))

    def __str__(self):
        return "{}(name={}, loaded={})".format(type(self), self._name, self._is_loaded)

    def update(self, data):
        for key, val in data.items():
            setattr(self, "_{}".format(key), val)

    def get_categories(self):
        # COMPONENT_TYPES = ["switch", "sensor", "binary_sensor", "cover", "climate", "light"]
        raise NotImplemented


class Blind(Channel):
    def get_categories(self):
        return ["cover"]


class Button(Channel):
    _Enabled = True
    _Closed = False

    def get_categories(self):
        return ["binary_sensor", "light"]


class ButtonCounter(Channel):
    _Unit = None
    _PulsePerUnits = None

    def get_categories(self):
        if self._PulsePerUnits == 0:
            return ["binary_sensor"]
        else:
            return ["sensor"]


class Dimmer(Channel):
    def get_categories(self):
        return ["light"]


class EdgeLit(Channel):
    def get_categories(self):
        return ["light"]


class LightSensor(Channel):
    def get_categories(self):
        return ["sensor"]


class Memo(Channel):
    pass


class Relay(Channel):
    _On = True

    def get_categories(self):
        return ["switch"]

    def is_on(self):
        return self._On

    def turn_on(self):
        pass

    def turn_off(self):
        pass


class Sensor(Channel):
    def get_categories(self):
        return ["sensor"]


class SensorNumber(Channel):
    def get_categories(self):
        return ["sensor"]


class Temperature(Channel):
    def get_categories(self):
        return ["sensor"]


class ThermostatChannel(Channel):
    pass
