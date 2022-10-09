"""
:author: Niels Laukens
"""
from __future__ import annotations

import dataclasses
import enum

from velbusaio.command_registry import register_command
from velbusaio.message import Message

COMMAND_CODE = 0xE8


class DaliDeviceSettingMsg(Message):
    """
    send by: VMBDALI
    received by:
    """

    def __init__(self, address: int | None = None):
        super().__init__()
        self.set_defaults(address)
        self.channel: int = 0

    def populate(self, priority, address: int, rtr: int, data: bytes) -> None:
        self.needs_low_priority(priority)
        self.needs_no_rtr(rtr)
        self.set_attributes(priority, address, rtr)

        self.needs_data(data, 2)
        self.channel = data[0]
        message_subtype = data[1]
        self.data: bytes | DaliDeviceSettingSubMessage = data[2:]
        try:
            decode_class = DaliDeviceSetting(message_subtype).decode_class
            if decode_class is not None:
                self.data = decode_class.from_data(self.data)
        except KeyError:
            # Unknown subtype
            pass

    def to_json_basic(self):
        me = {
            "name": str(self.__class__.__name__),
            "priority": self.priority,
            "rtr": self.rtr,
            "channel": self.channel,
        }
        if isinstance(self.data, DaliDeviceSettingSubMessage):
            me["data"] = self.data.to_json_basic()
        else:
            me["data"] = self.data.hex()
        return me


class DaliDeviceSettingSubMessage:
    """Abstract base class."""

    @classmethod
    def from_data(cls, data: bytes) -> DaliDeviceSettingSubMessage:
        raise NotImplementedError()

    def to_json_basic(self):
        raise NotImplementedError()


class DeviceType(enum.Enum):
    FluorecentLamp = 0
    EmergencyLamp = 1
    DischargeLamp = 2
    LowVoltageLamp = 3
    Dimmer = 4
    ConversionToDc = 5
    LedModule = 6
    Relay = 7
    ColorControl = 8
    Sequencer = 9
    DevicePresent = 254
    NoDevicePresent = 255


@dataclasses.dataclass
class DeviceTypeMsg(DaliDeviceSettingSubMessage):
    device_type: DeviceType

    @classmethod
    def from_data(cls, data: bytes) -> DeviceTypeMsg:
        return DeviceTypeMsg(device_type=DeviceType(data[0]))

    def to_data(self) -> bytes:
        return bytes([self.device_type.value])

    def to_json_basic(self):
        return {
            "submsg_type": self.__class__.__name__,
            "device_type": self.device_type.name,
        }


class DaliDeviceSetting(enum.Enum):
    def __new__(
        cls, value: int, decode_class: type[DaliDeviceSettingSubMessage]
    ) -> DaliDeviceSetting:
        obj = object.__new__(cls)
        obj._value_ = value
        obj.decode_class = decode_class
        return obj

    Scene0Level = (0, None)
    Scene1Level = (1, None)
    Scene2Level = (2, None)
    Scene3Level = (3, None)
    Scene4Level = (4, None)
    Scene5Level = (5, None)
    Scene6Level = (6, None)
    Scene7Level = (7, None)
    Scene8Level = (8, None)
    Scene9Level = (9, None)
    Scene10Level = (10, None)
    Scene11Level = (11, None)
    Scene12Level = (12, None)
    Scene13Level = (13, None)
    Scene14Level = (14, None)
    Scene15Level = (15, None)
    PowerOnLevel = (16, None)
    SystemFailureLevel = (17, None)
    MinimumLevel = (18, None)
    MaximumLevel = (19, None)
    FadeTimeAndRate = (20, None)
    GroupMembers = (21, None)
    # currently undefined 22
    # currently undefined 23
    # currently undefined 24
    DeviceType = (25, DeviceTypeMsg)
    ActualLevel = (26, None)


register_command(COMMAND_CODE, DaliDeviceSettingMsg, "VMBDALI")
