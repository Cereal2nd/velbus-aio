"""
Author: Maikel Punie <maikel.punie@gmail.com>
"""

PRIORITY_HIGH = 0xF8
PRIORITY_FIRMWARE = 0xF9
PRIORITY_LOW = 0xFB
PRIORITY_THIRDPARTY = 0xFA
PRIORITIES = [
    PRIORITY_FIRMWARE,
    PRIORITY_HIGH,
    PRIORITY_LOW,
    PRIORITY_THIRDPARTY,
]
STX = 0x0F
ETX = 0x04
LENGTH_MASK = 0x0F
HEADER_LENGTH = 4  # Header: [STX, priority, address, RTR+data length]
MAX_DATA_AMOUNT = 8  # Maximum amount of data bytes in a packet
MIN_PACKET_LENGTH = (
    6  # Smallest possible packet: [STX, priority, address, RTR+data length, CRC, ETC]
)
MAX_PACKET_LENGTH = MIN_PACKET_LENGTH + MAX_DATA_AMOUNT
RTR = 0x40
NO_RTR = 0x00
CACHEDIR = "/tmp/velbuscache"
LOAD_TIMEOUT = 600
