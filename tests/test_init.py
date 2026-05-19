"""Tests for setup/unload flow."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, patch

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.fightcade.api import FightcadeApiError

FIXTURES = Path(__file__).parent / "fixtures"


def load(name: str) -> dict[str, Any]:
    return json.loads((FIXTURES / name).read_text())


async def test_setup_and_unload(hass: HomeAssistant, mock_config_entry: MockConfigEntry) -> None:
    mock_config_entry.add_to_hass(hass)

    with patch("custom_components.fightcade.FightcadeClient") as ClientCls:
        client = AsyncMock()
        client.async_get_user.return_value = load("user_online.json")["user"]
        client.async_get_user_replays.return_value = load("user_replays.json")["results"]["results"]
        client.async_get_events.return_value = load("events_garou.json")["results"]["results"]
        ClientCls.return_value = client

        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()
        assert mock_config_entry.state is ConfigEntryState.LOADED

    assert await hass.config_entries.async_unload(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    assert mock_config_entry.state is ConfigEntryState.NOT_LOADED


async def test_options_change_reloads_entry(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """Changing options must trigger an entry reload (so poll/friends take effect)."""
    mock_config_entry.add_to_hass(hass)

    with patch("custom_components.fightcade.FightcadeClient") as ClientCls:
        client = AsyncMock()
        client.async_get_user.return_value = load("user_online.json")["user"]
        client.async_get_user_replays.return_value = load("user_replays.json")["results"]["results"]
        client.async_get_events.return_value = load("events_garou.json")["results"]["results"]
        ClientCls.return_value = client

        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()
        first = client.async_get_user.await_count

        hass.config_entries.async_update_entry(
            mock_config_entry, options={"poll_interval": 120, "friends": []}
        )
        await hass.async_block_till_done()

        assert client.async_get_user.await_count > first
        assert mock_config_entry.state is ConfigEntryState.LOADED


async def test_setup_retries_when_first_refresh_fails(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """API down at setup → SETUP_RETRY, not crash."""
    mock_config_entry.add_to_hass(hass)

    with patch("custom_components.fightcade.FightcadeClient") as ClientCls:
        client = AsyncMock()
        client.async_get_user.side_effect = FightcadeApiError("network down")
        ClientCls.return_value = client

        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()
        assert mock_config_entry.state in (
            ConfigEntryState.SETUP_RETRY,
            ConfigEntryState.SETUP_ERROR,
        )
