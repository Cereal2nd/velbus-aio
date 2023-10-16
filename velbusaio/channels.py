"""
author: Maikel Punie <maikel.punie@gmail.com>
"""
from __future__ import annotations

import asyncio
import math
import string
from typing import TYPE_CHECKING, Any, Awaitable, Callable

from velbusaio.command_registry import commandRegistry
from velbusaio.const import (
    DEVICE_CLASS_ILLUMINANCE,
    DEVICE_CLASS_TEMPERATURE,
    ENERGY_KILO_WATT_HOUR,
    TEMP_CELSIUS,
    VOLUME_CUBIC_METER_HOUR,
    VOLUME_LITERS_HOUR,
)
from velbusaio.message import Message
from velbusaio.messages.edge_set_color import SetEdgeColorMessage, CustomColorPriority
from velbusaio.messages.module_status import PROGRAM_SELECTION

if TYPE_CHECKING:
    from velbusaio.module import Module


class Channel:
    """
    A velbus channel
    This is the basic abstract class of a velbus channel
    """

    def __init__(
        self,
        module: Module,
        num: int,
        name: str,
        nameEditable: bool,
        writer: Callable[[Message], Awaitable[None]],
        address: int,
    ):
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

    def get_module_type(self) -> int:
        return self._module.get_type()

    def get_module_type_name(self) -> str:
        return self._module.get_type_name()

    def get_module_serial(self) -> str:
        return self._module.get_serial()

    def get_module_address(self, chan_type: str = "") -> int:
        """Return (sub)module address for channel"""
        if chan_type == "Button" and self._num > 24:
            return self._module.get_addresses()[3]
        elif chan_type == "Button" and self._num > 16:
            return self._module.get_addresses()[2]
        elif chan_type == "Button" and self._num > 8:
            return self._module.get_addresses()[1]
        else:
            return self._address

    def get_module_sw_version(self) -> str:
        return self._module.get_sw_version()

    def get_channel_number(self) -> int:
        return self._num

    def get_full_name(self) -> str:
        return f"{self._module.get_name()} ({self._module.get_type_name()})"

    def is_loaded(self) -> bool:
        """
        Is this channel loaded
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

    def set_name_char(self, pos: int, char: int) -> None:
        self._is_loaded = True
        self._name_parts = {}
        # make sure the string is long enough
        while len(self._name) < int(pos):
            self._name += " "
        # store the char on correct pos
        self._name = self._name[: int(pos)] + chr(char) + self._name[int(pos) + 1 :]

    def set_name_part(self, part: int, name: str) -> None:
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

    def __repr__(self) -> str:
        items = []
        for k, v in self.__dict__.items():
            if k not in ["_module", "_writer", "_name_parts"]:
                items.append(f"{k} = {v!r}")
        return "{}[{}]".format(type(self), ", ".join(items))

    def __str__(self) -> str:
        return self.__repr__()

    def get_channel_info(self) -> dict[str, Any]:
        data = {}
        for key, value in self.__dict__.items():
            data["type"] = self.__class__.__name__
            if key not in ["_module", "_writer", "_name_parts", "_on_status_update"]:
                data[key.replace("_", "", 1)] = value
        return data

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

    def get_categories(self) -> list[str]:
        """
        Get the categories (mainly for home-assistant)
        """
        # COMPONENT_TYPES = ["switch", "sensor", "binary_sensor", "cover", "climate", "light"]
        return []

    def on_status_update(self, meth: Callable[[], Awaitable[None]]) -> None:
        self._on_status_update.append(meth)

    def get_counter_state(self) -> int:
        raise NotImplementedError()

    def get_counter_unit(self) -> str:
        raise NotImplementedError()

    def get_max(self) -> int:
        raise NotImplementedError()

    def get_min(self) -> int:
        raise NotImplementedError()

    async def press(self) -> None:
        raise NotImplementedError()


class Blind(Channel):
    """
    A blind channel
    """

    _state = None
    # State reports the direction of *movement*: moving up, moving down or stopped
    _position = None
    # Position reporting is not supported by VMBxBL modules (only in BLE/BLS)

    def get_categories(self) -> list[str]:
        return ["cover"]

    def get_position(self) -> int | None:
        return self._position

    def get_state(self) -> str:
        return self._state

    def is_opening(self) -> bool:
        return self._state == 0x01

    def is_closing(self) -> bool:
        return self._state == 0x02

    def is_stopped(self) -> bool:
        return self._state == 0x00

    def is_closed(self) -> bool | None:
        """Report if the blind is fully closed."""
        if self._position is None:
            return None
        # else:
        return self._position == 100

    def is_open(self) -> bool | None:
        """Report if the blind is fully open."""
        if self._position is None:
            return None
        return self._position == 0

    def support_position(self) -> bool:
        # position will be populated after the first BlindStatusNgMessage (during module load)
        # For VMBxBL modules, position will remain None and not be overwritten
        return self._position is not None

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
        # may not be supported by the module
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
    _long = False

    def get_categories(self) -> list[str]:
        if self._enabled:
            return ["binary_sensor", "led", "button"]
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

    async def press(self) -> None:
        """
        Press the button
        """
        _mod_add = self.get_module_address("Button")
        _chn_num = self._num - self._module.calc_channel_offset(_mod_add)
        # send the just pressed
        cls = commandRegistry.get_command(0x00, self._module.get_type())
        msg = cls(_mod_add)
        msg.closed = [_chn_num]
        await self._writer(msg)
        # wait
        await asyncio.sleep(0.3)
        # send the just released
        msg = cls(_mod_add)
        msg.opened = [_chn_num]
        await self._writer(msg)


class ButtonCounter(Button):
    """
    A ButtonCounter channel
    This channel can act as a button and as a counter
    => standard     this is the calculated value
    => is_counter   this is the numeric value
    """

    _Unit = None
    _pulses = None
    _counter = None
    _delay = None

    def get_categories(self) -> list[str]:
        if self._counter:
            return ["sensor"]
        return ["binary_sensor", "button"]

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

    def get_unit(self) -> str | None:
        if self._Unit == VOLUME_LITERS_HOUR:
            return "L"
        if self._Unit == VOLUME_CUBIC_METER_HOUR:
            return "m3"
        if self._Unit == ENERGY_KILO_WATT_HOUR:
            return "W"
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

    def get_categories(self) -> list[str]:
        if self._enabled:
            return ["binary_sensor", "led"]
        return []


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

    def __init__(
        self,
        module: Module,
        num: int,
        name: str,
        nameEditable: bool,
        writer: Callable[[Message], Awaitable[None]],
        address: int,
        slider_scale: int = 100,
    ):
        super().__init__(module, num, name, nameEditable, writer, address)

        self.slider_scale = slider_scale
        # VMB4DC has dim values 0(off), 1-99(dimmed), 100(full on)
        # VMBDALI has dim values 0(off), 1-253(dimmed), 254(full on), 255(previous value)

    def get_categories(self) -> list[str]:
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
        return int(self._state * 100 / self.slider_scale)

    async def set_dimmer_state(self, slider: int, transitiontime: int = 0) -> None:
        """
        Set dimmer to slider
        """
        cls = commandRegistry.get_command(0x07, self._module.get_type())
        msg = cls(self._address)
        msg.dimmer_state = int(slider * self.slider_scale / 100)
        msg.dimmer_transitiontime = int(transitiontime)
        msg.dimmer_channels = [self._num]
        await self._writer(msg)

    async def restore_dimmer_state(self, transitiontime: int = 0) -> None:
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
    _cur_precision = None
    _max = None
    _min = None
    _target = 0
    _cmode = None
    _cstatus = None
    _thermostat = False
    _sleep_timer = 0

    def get_categories(self) -> list[str]:
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

    def get_max(self) -> int | None:
        if self._max is None:
            return None
        return round(self._max, 2)

    def get_min(self) -> int | None:
        if self._min is None:
            return None
        return round(self._min, 2)

    def get_climate_target(self) -> int:
        return round(self._target, 2)

    def get_climate_preset(self) -> str:
        return self._cmode

    def get_climate_mode(self) -> str:
        return self._cstatus

    async def set_temp(self, temp: float) -> None:
        cls = commandRegistry.get_command(0xE4, self._module.get_type())
        msg = cls(self._address)
        msg.temp = temp * 2  # TODO: int()
        await self._writer(msg)

    async def _switch_mode(self) -> None:
        if self._cmode == "safe":
            code = 0xDE
        elif self._cmode == "comfort":
            code = 0xDB
        elif self._cmode == "day":
            code = 0xDC
        else:  # "night"
            code = 0xDD

        if self._cstatus == "run":
            sleep = 0x0
        elif self._cstatus == "manual":
            sleep = 0xFFFF
        elif self._cstatus == "sleep":
            sleep = self._sleep_timer
        else:
            sleep = 0x0
        cls = commandRegistry.get_command(code, self._module.get_type())
        msg = cls(self._address, sleep)
        await self._writer(msg)

    async def set_preset(self, preset: str) -> None:
        self._cmode = preset
        await self._switch_mode()

    async def set_climate_mode(self, mode: str) -> None:
        self._cstatus = mode
        await self._switch_mode()

    async def set_mode(self, mode: str) -> None:
        # TODO: change function name, proposal = set_heat_cool_mode
        if mode == "heat":
            code = 0xE0
        elif mode == "cool":
            code = 0xDF
        # TODO: else case
        cls = commandRegistry.get_command(code, self._module.get_type())
        msg = cls(self._address)
        await self._writer(msg)

    async def maybe_update_temperature(self, new_temp: float, precision: float) -> None:
        # Based on experiments, Velbus modules seem to truncate (i.e. round down)
        current_temp_rounded_to_precision = (
            math.floor(self._cur / precision) * precision
        )

        if current_temp_rounded_to_precision == new_temp:
            # The newly received temperature is still in line with our current value,
            # but with reduced precision.
            # Don't update (would lose high precision)
            return

        elif (
            current_temp_rounded_to_precision - precision
            <= new_temp
            < current_temp_rounded_to_precision
            and self._cur_precision < precision
        ):
            # The newly received temperature is 1 LSb below the current value
            # and the current value was set by a better precision message
            # Modify the received temperature by "adding precision", while still keeping the same low precision value
            # e.g. (decimal digits represent precision)
            # | Actual  | Msg     | Stored  |
            # | 21.0000 | 21.0000 | 21.0000 |
            # | 20.9375 | 20.5    | 20.9375 |
            new_temp = current_temp_rounded_to_precision - self._cur_precision

        await self.update(
            {
                "cur": new_temp,
                "cur_precision": precision,
            }
        )


class SensorNumber(Channel):
    """
    A Numeric Sensor channel
    """

    _cur = 0

    def get_categories(self) -> list[str]:
        return ["sensor"]

    def get_class(self) -> None:
        return None

    def get_unit(self) -> None:
        return None

    def get_state(self) -> float:
        return round(self._cur, 2)


class LightSensor(Channel):
    """
    A light sensor channel
    """

    _cur = 0

    def get_categories(self) -> list[str]:
        return ["sensor"]

    def get_class(self) -> str:
        return DEVICE_CLASS_ILLUMINANCE

    def get_unit(self) -> None:
        return None

    def get_state(self) -> float:
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

    def get_categories(self) -> list[str]:
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

    async def reset_color(self, left=True, top=True, right=True, bottom=True):
        msg = SetEdgeColorMessage(self._address)
        msg.apply_background_color = True
        msg.color_idx = 0
        msg.apply_to_left_edge = left
        msg.apply_to_top_edge = top
        msg.apply_to_right_edge = right
        msg.apply_to_bottom_edge = bottom
        msg.apply_to_all_pages = True
        await self._writer(msg)

    async def set_color(
        self,
        color_idx: int,
        left=True,
        top=True,
        right=True,
        bottom=True,
        blinking=False,
        priority=CustomColorPriority.LOW_PRIORITY,
    ) -> None:
        """
        Send the turn off message
        """

        msg = SetEdgeColorMessage(self._address)
        msg.apply_background_color = True
        msg.background_blinking = blinking
        msg.color_idx = color_idx
        msg.apply_to_left_edge = left
        msg.apply_to_top_edge = top
        msg.apply_to_right_edge = right
        msg.apply_to_bottom_edge = bottom
        msg.apply_to_all_pages = True
        msg.custom_color_priority = priority
        await self._writer(msg)


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


class SelectedProgram(Channel):
    """
    A selected program channel
    """

    _selected_program_str = None

    def get_categories(self) -> list[str]:
        return ["select"]

    def get_class(self) -> None:
        return None

    def get_options(self) -> list:
        return list(PROGRAM_SELECTION.values())

    def get_selected_program(self) -> str:
        return self._selected_program_str

    async def set_selected_program(self, program_str: str) -> None:
        self._selected_program_str = program_str
        command_code = 0xB3
        cls = commandRegistry.get_command(command_code, self._module.get_type())
        index = list(PROGRAM_SELECTION.values()).index(program_str)
        program = list(PROGRAM_SELECTION.keys())[index]
        msg = cls(self._address, program)
        await self._writer(msg)
