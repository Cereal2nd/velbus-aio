"""
This test checks if with an incoming temp_sensor_status message the thermostat operating mode and
sleep_timer values are correctly stored into the module's temperature channel.
"""
import logging
import pathlib

import pytest

from velbusaio.channels import Temperature
from velbusaio.handler import PacketHandler
from velbusaio.helpers import get_cache_dir
from velbusaio.messages import TempSensorStatusMessage
from velbusaio.messages.temp_sensor_status import DSTATUS
from velbusaio.module import Module


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "mode, sleep_timer",
    [
        (0, 0),
        (2, 0xFFFF),
        (4, 500),
        (6, 0),
    ],
)
async def test_thermostat_operating_mode(mode, sleep_timer):
    module_address = 1
    module_type = 0x28  # VMBGPOD
    cache_dir = get_cache_dir()
    pathlib.Path(cache_dir).mkdir(parents=True, exist_ok=True)

    ph = PacketHandler(None, None)
    m = Module(
        module_address,
        module_type,
        ph.pdata["ModuleTypes"][f"{module_type:02X}"],
        cache_dir=get_cache_dir(),
    )
    m._log = logging.getLogger("velbus-module")
    chan = m._translate_channel_name(m._data["TemperatureChannel"])
    m._channels[chan] = Temperature(None, None, None, False, None, None)

    msg = TempSensorStatusMessage(module_address)
    msg.status_str = DSTATUS[mode]
    msg.sleep_timer = sleep_timer
    msg.current_temp = 0
    await m.on_message(msg)

    assert m._channels[chan]._cstatus == DSTATUS[mode]
    assert m._channels[chan]._sleep_timer == sleep_timer
