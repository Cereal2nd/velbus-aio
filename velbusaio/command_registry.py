"""
:author: Maikel Punie <maikel.punie@gmail.com> and Thomas Delaet <thomas@delaet.org>
"""
from __future__ import annotations

MODULE_DIRECTORY = {
    0x01: "VMB8PB",
    0x02: "VMB1RY",
    0x03: "VMB1BL",
    0x05: "VMB6IN",
    0x07: "VMB1DM",
    0x08: "VMB4RY",
    0x09: "VMB2BL",
    0x0A: "VMB8IR",
    0x0B: "VMB4PD",
    0x0C: "VMB1TS",
    0x0D: "VMB1TH",
    0x0E: "VMB1TC",
    0x0F: "VMB1LED",
    0x10: "VMB4RYLD",
    0x11: "VMB4RYNO",
    0x12: "VMB4DC",
    0x13: "VMBLCDWB",
    0x14: "VMBDME",
    0x15: "VMBDMI",
    0x16: "VMB8PBU",
    0x17: "VMB6PBN",
    0x18: "VMB2PBN",
    0x19: "VMB6PBB",
    0x1A: "VMB4RF",
    0x1B: "VMB1RYNO",
    0x1C: "VMB1BLE",
    0x1D: "VMB2BLE",
    0x1E: "VMBGP1",
    0x1F: "VMBGP2",
    0x20: "VMBGP4",
    0x21: "VMBGPO",
    0x22: "VMB7IN",
    0x28: "VMBGPOD",
    0x29: "VMB1RYNOS",
    0x2A: "VMBPIRM",
    0x2B: "VMBIRC",
    0x2C: "VMBIRO",
    0x2D: "VMBGP4PIR",
    0x2E: "VMB1BLS",
    0x2F: "VMBDMI-R",
    0x31: "VMBMETEO",
    0x32: "VMB4AN",
    0x33: "VMBVP01",
    0x34: "VMBEL1",
    0x35: "VMBEL2",
    0x36: "VMBEL4",
    0x37: "VMBELO",
    0x38: "VMBELPIR",
    0x39: "VMBSIG",
    0x3A: "VMBGP1-2",
    0x3B: "VMBGP2-2",
    0x3C: "VMBGP4-2",
    0x3D: "VMBGPOD-2",
    0x3E: "VMBGP4PIR-2",
    0x3F: "VMCM3",
    0x40: "VMBUSBIP",
    0x41: "VMB1RYS",
    0x42: "VMBKP",
    0x43: "VMBIN",
    0x44: "VMB4PB",
    0x45: "VMBDALI",
}


class CommandRegistry:
    def __init__(self, module_directory: dict) -> None:
        self._module_directory = module_directory
        self._default_commands = {}
        self._overrides = {}

    def register_command(
        self, command_value: int, command_class: type, module_name: str = 0
    ) -> None:
        if command_value < 0 or command_value > 255:
            raise ValueError("Command_value should be >=0 and <=255")
        assert module_name in self._module_directory.values() or module_name == 0
        if module_name:
            module_type = next(
                (
                    mtype
                    for mtype, mname in self._module_directory.items()
                    if mname == module_name
                ),
                None,
            )
            self._register_override(command_value, command_class, module_type)
        else:
            self._register_default(command_value, command_class)

    def _register_override(
        self, command_value: int, command_class: type, module_type: str
    ) -> None:
        if module_type not in self._overrides:
            self._overrides[module_type] = {}
        if command_value not in self._overrides[module_type]:
            self._overrides[module_type][command_value] = command_class
        else:
            raise Exception("double registration in command registry")

    def _register_default(self, command_value: int, command_class: type) -> None:
        if command_value not in self._default_commands:
            self._default_commands[command_value] = command_class
        else:
            raise Exception("double registration in command registry")

    def has_command(self, command_value: int, module_type: int = 0) -> bool:
        if module_type in self._overrides:
            if command_value in self._overrides[module_type]:
                return True
        if command_value in self._default_commands:
            return True
        return False

    def get_command(self, command_value: int, module_type: int = 0) -> None | type:
        if module_type in self._overrides:
            if command_value in self._overrides[module_type]:
                return self._overrides[module_type][command_value]
        if command_value in self._default_commands:
            return self._default_commands[command_value]
        return None


commandRegistry = CommandRegistry(MODULE_DIRECTORY)


def register_command(
    command_value: int, command_class: type, module_type: str = 0
) -> None:
    """
    :return: None
    """
    commandRegistry.register_command(command_value, command_class, module_type)
