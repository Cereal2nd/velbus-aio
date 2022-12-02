"""
Author: Maikel Punie <maikel.punie@gmail.com>
"""
from __future__ import annotations

from typing import Final

PRIORITY_HIGH: Final = 0xF8
PRIORITY_FIRMWARE: Final = 0xF9
PRIORITY_LOW: Final = 0xFB
PRIORITY_THIRDPARTY: Final = 0xFA
PRIORITIES: Final = [
    PRIORITY_FIRMWARE,
    PRIORITY_HIGH,
    PRIORITY_LOW,
    PRIORITY_THIRDPARTY,
]


HEADER_LENGTH: Final = 4  # Header: [Start Byte, priority, address, RTR+data length]
TAIL_LENGTH: Final = 2  # Tail: [CRC, End Byte]
MAX_BODY_SIZE: Final = 8  # Maximum amount of data bytes in a packet

MINIMUM_MESSAGE_SIZE: Final = (
    HEADER_LENGTH + TAIL_LENGTH
)  # Smallest possible packet: [Start Byte, priority, address, RTR+data length, CRC, End Byte]
MAXIMUM_MESSAGE_SIZE: Final = MINIMUM_MESSAGE_SIZE + MAX_BODY_SIZE

START_BYTE: Final = 0x0F
END_BYTE: Final = 0x04


LENGTH_MASK: Final = 0x0F

RTR: Final = 0x40
NO_RTR: Final = 0x00

CACHEDIR: Final = ".velbuscache"
LOAD_TIMEOUT: Final = 600

DEVICE_CLASS_ILLUMINANCE: Final = "illuminance"
DEVICE_CLASS_TEMPERATURE: Final = "temperature"
TEMP_CELSIUS: Final = "°C"
ENERGY_KILO_WATT_HOUR: Final = "kWh"
ENERGY_WATT_HOUR: Final = "Wh"
VOLUME_CUBIC_METER: Final = "m3"  # Not an official constant at HA yet
VOLUME_CUBIC_METER_HOUR: Final = "m3/h"  # Not an official constant at HA yet
VOLUME_LITERS: Final = "L"
VOLUME_LITERS_HOUR: Final = "L/h"  # Not an official constant at HA yet

CHANNEL_SELECTED_PROGRAM: Final = 96
CHANNEL_EDGE_LIT: Final = 97
CHANNEL_MEMO_TEXT: Final = 98
CHANNEL_LIGHT_VALUE: Final = 99

SLEEP_TIME = 60 / 1000
