#!/usr/bin/env python


class VelbusException(Exception):
    """Velbus Exception."""

    def __init__(self, value):
        Exception.__init__(self)
        self.value = value

    def __str__(self):
        return repr(self.value)


class VelbuConnectionFailed(VelbusException):
    def __init__(self):
        super().__init__("Connection setup failed")


class VelbuConnectionTerminated(VelbusException):
    def __init__(self):
        super().__init__("Connection terminated")
