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
STX: Final = 0x0F
ETX: Final = 0x04
LENGTH_MASK: Final = 0x0F
HEADER_LENGTH: Final = 4  # Header: [STX, priority, address, RTR+data length]
MAX_DATA_AMOUNT: Final = 8  # Maximum amount of data bytes in a packet
MIN_PACKET_LENGTH: Final = (
    6  # Smallest possible packet: [STX, priority, address, RTR+data length, CRC, ETC]
)
MAX_PACKET_LENGTH: Final = MIN_PACKET_LENGTH + MAX_DATA_AMOUNT
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
