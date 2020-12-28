#!/usr/bin/env python
# -*- coding: utf-8 -*-


def keys_exists(element, *keys):
    """
    Check if *keys (nested) exists in `element` (dict).
    """
    if not isinstance(element, dict):
        raise AttributeError("keys_exists() expects dict as first argument.")
    if len(keys) == 0:
        raise AttributeError("keys_exists() expects at least two arguments, one given.")

    _element = element
    for key in keys:
        try:
            _element = _element[key]
        except KeyError:
            return False
    return _element


def checksum(arr):
    """
    Calculate checksum of the given array.
    The checksum is calculated by summing all values in an array, then performing the two's complement.
    :param arr: The array of bytes of which the checksum has to be calculated of.
    :return: The checksum of the given array.
    """
    assert isinstance(arr, bytearray)
    crc = sum(arr)
    crc = crc ^ 255
    crc = crc + 1
    crc = crc & 255
    return crc


def h2(inp):
    return format(inp, "02x").upper()
