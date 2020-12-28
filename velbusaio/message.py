import logging
import uuid
from velbusaio.const import *


class Message(object):
    """
    Base Velbus message
    """

    priority = PRIORITY_LOW
    msgtype = None
    address = None
    sub_address = None
    chan_offset = 0
    data = bytearray([])
    rtr = False
    uuid = None

    def __init__(self):
        self.uuid = uuid.uuid4()
        pass

    def fromData(self, data):
        assert data
        assert len(data) <= MAX_PACKET_LENGTH
        self.priority = data[1]
        self.address = data[2]
        self.rtr = data[3] & RTR == RTR
        self.data_size = data[3] & 0x0F
        self.msgtype = data[4]
        self.data = data[5:-2]
        self._handleSubAddress()

    def _handleSubAddress(self):
        if self.sub_address and not self.address:
            pass
        elif self.address and not self.sub_address:
            # we have an address but do not know if its a sub or not
            # if self.address in modules \
            #    and 'master' in modules[self.address] \
            #    and 'offset' in modules[self.address]:
            #    self.sub_address = self.address
            #    self.chan_offset = modules[self.address]['offset']
            #    self.address = modules[self.address]['master']
            # else:
            self.sub_address = False
            self.sub_address = 0
