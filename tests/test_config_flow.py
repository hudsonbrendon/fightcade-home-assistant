"""Tests for the Fightcade config flow."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, patch

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.fightcade.api import (
    FightcadeApiError,
    FightcadeUserNotFound,
)
from custom_components.fightcade.const import (
    CONF_FRIENDS,
    CONF_POLL_INTERVAL,
    CONF_USERNAME,
    DOMAIN,
)

FIXTURES = Path(__file__).parent / "fixtures"


def load(name: str) -> dict[str, Any]:
    return json.loads((FIXTURES / name).read_text())


async def test_user_flow_creates_entry(hass: HomeAssistant) -> None:
    with patch("custom_components.fightcade.config_flow.FightcadeClient") as ClientCls:
        client = AsyncMock()
        client.async_get_user.return_value = load("user_online.json")["user"]
        ClientCls.return_value = client

        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "user"

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_USERNAME: "biggs"}
        )
        assert result["type"] is FlowResultType.CREATE_ENTRY
        assert result["data"] == {CONF_USERNAME: "biggs"}
        assert result["title"] == "biggs"


async def test_user_flow_user_not_found_shows_error(hass: HomeAssistant) -> None:
    with patch("custom_components.fightcade.config_flow.FightcadeClient") as ClientCls:
        client = AsyncMock()
        client.async_get_user.side_effect = FightcadeUserNotFound("nope")
        ClientCls.return_value = client

        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_USERNAME: "nope"}
        )
        assert result["type"] is FlowResultType.FORM
        assert result["errors"] == {"base": "user_not_found"}


async def test_user_flow_api_error_shows_error(hass: HomeAssistant) -> None:
    with patch("custom_components.fightcade.config_flow.FightcadeClient") as ClientCls:
        client = AsyncMock()
        client.async_get_user.side_effect = FightcadeApiError("boom")
        ClientCls.return_value = client

        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_USERNAME: "anyone"}
        )
        assert result["errors"] == {"base": "cannot_connect"}


async def test_user_flow_rejects_duplicate(hass: HomeAssistant) -> None:
    existing = MockConfigEntry(domain=DOMAIN, data={CONF_USERNAME: "biggs"}, unique_id="biggs")
    existing.add_to_hass(hass)

    with patch("custom_components.fightcade.config_flow.FightcadeClient") as ClientCls:
        client = AsyncMock()
        client.async_get_user.return_value = load("user_online.json")["user"]
        ClientCls.return_value = client

        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_USERNAME: "biggs"}
        )
        assert result["type"] is FlowResultType.ABORT
        assert result["reason"] == "already_configured"


async def test_user_flow_rejects_empty_username(hass: HomeAssistant) -> None:
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_USERNAME: ""})
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_username"}


async def test_user_flow_rejects_whitespace_only_username(hass: HomeAssistant) -> None:
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_USERNAME: "   "}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_username"}


async def test_user_flow_unknown_exception_shows_unknown_error(
    hass: HomeAssistant,
) -> None:
    with patch("custom_components.fightcade.config_flow.FightcadeClient") as ClientCls:
        client = AsyncMock()
        client.async_get_user.side_effect = RuntimeError("boom")
        ClientCls.return_value = client

        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_USERNAME: "anyone"}
        )
        assert result["type"] is FlowResultType.FORM
        assert result["errors"] == {"base": "unknown"}


async def test_user_flow_strips_username_padding(hass: HomeAssistant) -> None:
    """Leading/trailing whitespace on username must be stripped before API + storage."""
    with patch("custom_components.fightcade.config_flow.FightcadeClient") as ClientCls:
        client = AsyncMock()
        client.async_get_user.return_value = load("user_online.json")["user"]
        ClientCls.return_value = client

        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_USERNAME: "  biggs  "}
        )
        assert result["type"] is FlowResultType.CREATE_ENTRY
        assert result["data"] == {CONF_USERNAME: "biggs"}
        client.async_get_user.assert_awaited_with("biggs")


async def test_user_flow_preserves_username_case(hass: HomeAssistant) -> None:
    """Fightcade usernames are case-sensitive — entered case must be kept."""
    with patch("custom_components.fightcade.config_flow.FightcadeClient") as ClientCls:
        client = AsyncMock()
        client.async_get_user.return_value = load("user_online.json")["user"]
        ClientCls.return_value = client

        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_USERNAME: "BiGgs"}
        )
        assert result["type"] is FlowResultType.CREATE_ENTRY
        assert result["data"] == {CONF_USERNAME: "BiGgs"}
        client.async_get_user.assert_awaited_with("BiGgs")


async def test_user_flow_duplicate_is_case_insensitive(hass: HomeAssistant) -> None:
    """Different casing of the same Fightcade account collides on unique_id."""
    existing = MockConfigEntry(domain=DOMAIN, data={CONF_USERNAME: "biggs"}, unique_id="biggs")
    existing.add_to_hass(hass)

    with patch("custom_components.fightcade.config_flow.FightcadeClient") as ClientCls:
        client = AsyncMock()
        client.async_get_user.return_value = load("user_online.json")["user"]
        ClientCls.return_value = client

        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_USERNAME: "BIGGS"}
        )
        assert result["type"] is FlowResultType.ABORT
        assert result["reason"] == "already_configured"


async def test_options_flow_strips_and_dedups_friends(
    hass, mock_config_entry: MockConfigEntry
) -> None:
    mock_config_entry.add_to_hass(hass)
    result = await hass.config_entries.options.async_init(mock_config_entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {CONF_POLL_INTERVAL: 60, CONF_FRIENDS: "rival, , nemesis,  ,rival"},
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    # blank entries dropped; duplicate "rival" kept once
    friends = result["data"][CONF_FRIENDS]
    assert friends.count("rival") == 1
    assert "nemesis" in friends
    assert "" not in friends


async def test_options_flow_updates_friends_and_interval(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    mock_config_entry.add_to_hass(hass)
    result = await hass.config_entries.options.async_init(mock_config_entry.entry_id)
    assert result["type"] is FlowResultType.FORM
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {CONF_POLL_INTERVAL: 120, CONF_FRIENDS: "rival, nemesis"},
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {
        CONF_POLL_INTERVAL: 120,
        CONF_FRIENDS: ["rival", "nemesis"],
    }
