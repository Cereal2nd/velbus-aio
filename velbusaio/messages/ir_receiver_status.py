"""
:author: David Danssaert <david.danssaert@gmail.com>
"""
from __future__ import annotations

from velbusaio.command_registry import register_command
from velbusaio.messages.module_status import ModuleStatusMessage

COMMAND_CODE = 0xEB


class IRReceiverStatusMessage(ModuleStatusMessage):
    """
    send by: VMB8IR
    received by:
    """


register_command(COMMAND_CODE, IRReceiverStatusMessage, "VMB8IR")
