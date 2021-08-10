"""
:author: Maikel Punie <maikel.punie@gmail.com> and Thomas Delaet <thomas@delaet.org>
"""
from __future__ import annotations

from velbusaio.module_registry import MODULE_DIRECTORY


class CommandRegistry:
    def __init__(self, module_directory: dict) -> None:
        self._module_directory = module_directory
        self._default_commands = {}
        self._overrides = {}

    def register_command(
        self, command_value: int, command_class: type, module_name: str = 0
    ) -> None:
        assert command_value >= 0 and command_value <= 255
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
