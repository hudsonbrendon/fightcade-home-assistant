"""Tests for fightcade sensors."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, patch

from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

FIXTURES = Path(__file__).parent / "fixtures"

RANK_A_INDEX = 5
UMK3_TIME_PLAYED_HOURS = 100.0


def load(name: str) -> dict[str, Any]:
    return json.loads((FIXTURES / name).read_text())


async def _setup(hass: HomeAssistant, entry: MockConfigEntry, **client_overrides: Any) -> None:
    entry.add_to_hass(hass)
    with patch("custom_components.fightcade.FightcadeClient") as ClientCls:
        c = AsyncMock()
        c.async_get_user.return_value = load("user_online.json")["user"]
        c.async_get_user_replays.return_value = load("user_replays.json")["results"]["results"]
        c.async_get_events.return_value = load("events_garou.json")["results"]["results"]
        for attr, value in client_overrides.items():
            getattr(c, attr).return_value = value
        ClientCls.return_value = c
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()


async def test_rank_sensor_per_game(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    await _setup(hass, mock_config_entry)
    s = hass.states.get("sensor.fightcade_biggs_umk3_rank")
    assert s is not None
    assert s.state == "A"
    assert s.attributes["rank_index"] == RANK_A_INDEX


async def test_match_count_sensor(hass: HomeAssistant, mock_config_entry: MockConfigEntry) -> None:
    await _setup(hass, mock_config_entry)
    s = hass.states.get("sensor.fightcade_biggs_umk3_matches")
    assert s.state == "120"
    assert s.attributes["unit_of_measurement"] == "matches"


async def test_time_played_sensor_in_hours(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    await _setup(hass, mock_config_entry)
    s = hass.states.get("sensor.fightcade_biggs_umk3_time_played")
    # 360_000_000 ms / 3_600_000 = 100 h
    assert float(s.state) == UMK3_TIME_PLAYED_HOURS


async def test_last_match_sensor_state_is_timestamp(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    await _setup(hass, mock_config_entry)
    s = hass.states.get("sensor.fightcade_biggs_last_match")
    assert s is not None
    # device_class=timestamp → state is ISO 8601
    assert s.state.startswith("2024-")  # 1716000000000 = May 2024
    assert s.attributes["opponent"] == "rival"
    assert s.attributes["gameid"] == "umk3"
    assert s.attributes["won"] is True
    assert s.attributes["replay_url"].endswith("/umk3/1700000000000-1234")
