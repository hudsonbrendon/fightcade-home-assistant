"""Tests for diagnostics."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, patch

from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.fightcade.diagnostics import (
    async_get_config_entry_diagnostics,
)

FIXTURES = Path(__file__).parent / "fixtures"


def load(name: str) -> dict[str, Any]:
    return json.loads((FIXTURES / name).read_text())


async def test_diagnostics_redacts_gravatar(
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

    data = await async_get_config_entry_diagnostics(hass, mock_config_entry)
    assert data["user"]["name"] == "biggs"
    assert data["user"]["gravatar"] == "**REDACTED**"
    assert data["entry"]["data"]["username"] == "biggs"
