#!/usr/bin/env python
import pytest

import velbusaio.command_registry
from velbusaio.command_registry import CommandRegistry, register


@pytest.fixture()
def own_command_registry():
    """
    Ensure a clean, empty commandRegistry; even when modules are loaded as part of other tests
    """
    orig_command_registry = velbusaio.command_registry.commandRegistry
    velbusaio.command_registry.commandRegistry = CommandRegistry({})
    yield
    velbusaio.command_registry.commandRegistry = orig_command_registry


def test_defaults(own_command_registry):
    # insert some data
    @register(1)
    class testclass:
        pass

    @register(2)
    class testclass2:
        pass

    @register(3)
    class testclass3:
        pass

    # check if double registration is raised
    with pytest.raises(Exception, match=r"double registration in command registry"):

        @register(1)
        @register(2)
        @register(3)
        class testclassR:
            pass

    # check if invalid command id
    with pytest.raises(ValueError, match=r"Command_value should be >=0 and <=255"):

        @register(0)
        @register(256)
        class testclassV:
            pass
