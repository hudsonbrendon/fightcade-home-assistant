"""Tests for fightcade binary sensors."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, patch

from homeassistant.const import STATE_OFF, STATE_ON
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

FIXTURES = Path(__file__).parent / "fixtures"


def load(name: str) -> dict[str, Any]:
    return json.loads((FIXTURES / name).read_text())


async def test_user_online_binary_sensor_state_on(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    mock_config_entry.add_to_hass(hass)
    with patch("custom_components.fightcade.FightcadeClient") as ClientCls:
        c = AsyncMock()
        c.async_get_user.return_value = load("user_online.json")["user"]
        c.async_get_user_replays.return_value = []
        c.async_get_events.return_value = []
        ClientCls.return_value = c
        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    state = hass.states.get("binary_sensor.fightcade_biggs_online")
    assert state is not None
    assert state.state == STATE_ON
    assert state.attributes["device_class"] == "connectivity"


async def test_user_online_binary_sensor_state_off(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    mock_config_entry.add_to_hass(hass)
    with patch("custom_components.fightcade.FightcadeClient") as ClientCls:
        c = AsyncMock()
        c.async_get_user.return_value = load("user_offline.json")["user"]
        c.async_get_user_replays.return_value = []
        c.async_get_events.return_value = []
        ClientCls.return_value = c
        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    state = hass.states.get("binary_sensor.fightcade_biggs_online")
    assert state.state == STATE_OFF
    assert state.attributes["last_online"] == 1716100000000  # noqa: PLR2004
