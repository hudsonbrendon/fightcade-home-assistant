"""Tests for fightcade binary sensors."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, patch

from homeassistant.const import STATE_OFF, STATE_ON
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.fightcade.const import (
    CONF_FRIENDS,
    CONF_POLL_INTERVAL,
    CONF_USERNAME,
    DOMAIN,
)

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


async def test_friend_binary_sensor_created_per_friend(hass: HomeAssistant) -> None:
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_USERNAME: "biggs"},
        options={CONF_POLL_INTERVAL: 60, CONF_FRIENDS: ["rival", "nemesis"]},
        unique_id="biggs",
    )
    entry.add_to_hass(hass)

    online_user = load("user_online.json")["user"]
    offline_user = load("user_offline.json")["user"]

    with patch("custom_components.fightcade.FightcadeClient") as ClientCls:
        c = AsyncMock()

        async def get_user(name: str):
            return online_user if name in ("biggs", "rival") else offline_user

        c.async_get_user.side_effect = get_user
        c.async_get_user_replays.return_value = []
        c.async_get_events.return_value = []
        ClientCls.return_value = c
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    rival = hass.states.get("binary_sensor.fightcade_friend_rival_online")
    nemesis = hass.states.get("binary_sensor.fightcade_friend_nemesis_online")
    assert rival is not None
    assert nemesis is not None
    assert rival.state == STATE_ON
    assert nemesis.state == STATE_OFF
