from velbusaio.const import MAXIMUM_MESSAGE_SIZE, MINIMUM_MESSAGE_SIZE


# Copyright (c) 2017 Thomas Delaet
# Copied from python-velbus (https://github.com/thomasdelaet/python-velbus)
def checksum(data) -> int:
    """
    :return: int
    """
    assert len(data) >= MINIMUM_MESSAGE_SIZE - 2
    assert len(data) <= MAXIMUM_MESSAGE_SIZE - 2
    __checksum = 0
    for data_byte in data:
        __checksum += data_byte
    __checksum = -(__checksum % 256) + 256
    return __checksum % 256


class VelbusException(Exception):
    """Velbus Exception."""

    def __init__(self, value):
        Exception.__init__(self)
        self.value = value

    def __str__(self):
        return repr(self.value)


class MessageParseException(Exception):
    pass


class BitSet:
    def __init__(self, value):
        self._value = value

    def __getitem__(self, idx):
        assert 0 <= idx < 8
        return bool((1 << idx) & self._value)

    def __setitem__(self, idx, value):
        assert 0 <= idx < 8
        assert isinstance(value, bool)
        mask = (0xFF ^ (1 << idx)) & self._value
        self._value = mask & (value << idx)

    def __len__(self):
        return 8  # a bitset represents one byte
