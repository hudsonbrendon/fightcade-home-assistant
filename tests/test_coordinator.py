"""Tests for FightcadeDataUpdateCoordinator."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock

import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.fightcade.coordinator import (
    FightcadeData,
    FightcadeDataUpdateCoordinator,
)

FIXTURES = Path(__file__).parent / "fixtures"


def load(name: str) -> dict[str, Any]:
    return json.loads((FIXTURES / name).read_text())


@pytest.fixture
def fake_client() -> AsyncMock:
    client = AsyncMock()
    client.async_get_user.return_value = load("user_online.json")["user"]
    client.async_get_user_replays.return_value = load("user_replays.json")["results"]["results"]
    client.async_get_events.return_value = load("events_garou.json")["results"]["results"]
    return client


async def test_first_refresh_seeds_seen_events_without_firing(
    hass: HomeAssistant, fake_client: AsyncMock
) -> None:
    fired: list[Any] = []
    hass.bus.async_listen("fightcade_event", fired.append)

    entry = MockConfigEntry(domain="fightcade", data={"username": "biggs"}, entry_id="abc")
    entry.add_to_hass(hass)
    coord = FightcadeDataUpdateCoordinator(
        hass,
        client=fake_client,
        username="biggs",
        friends=[],
        poll_interval=60,
        entry_id="abc",
        config_entry=entry,
    )
    await coord.async_refresh()

    assert isinstance(coord.data, FightcadeData)
    assert coord.data.user["name"] == "biggs"
    assert coord.data.online is True
    assert coord.data.last_match is not None
    assert coord.data.last_match["opponent"] == "rival"
    assert "umk3" in coord.data.events  # favorite game
    assert fired == []  # first refresh does not fire


async def test_second_refresh_fires_event_for_new_tournament(
    hass: HomeAssistant, fake_client: AsyncMock
) -> None:
    entry = MockConfigEntry(domain="fightcade", data={"username": "biggs"}, entry_id="abc")
    entry.add_to_hass(hass)
    coord = FightcadeDataUpdateCoordinator(
        hass,
        client=fake_client,
        username="biggs",
        friends=[],
        poll_interval=60,
        entry_id="abc",
        config_entry=entry,
    )
    await coord.async_refresh()

    base_events = load("events_garou.json")["results"]["results"]
    new_event = {
        "name": "Surprise Tournament",
        "author": "x",
        "date": 1730000000000,
        "gameid": "umk3",
        "link": "https://example.com",
        "region": "EU",
    }

    async def side(gameid: str):
        return [*base_events, new_event] if gameid == "umk3" else base_events

    fake_client.async_get_events.side_effect = side

    fired: list[Any] = []
    hass.bus.async_listen("fightcade_event", fired.append)
    await coord.async_refresh()
    await hass.async_block_till_done()

    assert len(fired) == 1
    assert fired[0].data["name"] == "Surprise Tournament"
    assert fired[0].data["gameid"] == "umk3"


async def test_friend_transition_fires_event(hass: HomeAssistant, fake_client: AsyncMock) -> None:
    online_user = load("user_online.json")["user"]
    offline_user = load("user_offline.json")["user"]

    async def get_user(name: str):
        if name == "biggs":
            return online_user
        return offline_user

    fake_client.async_get_user.side_effect = get_user

    entry = MockConfigEntry(domain="fightcade", data={"username": "biggs"}, entry_id="abc")
    entry.add_to_hass(hass)
    coord = FightcadeDataUpdateCoordinator(
        hass,
        client=fake_client,
        username="biggs",
        friends=["rival"],
        poll_interval=60,
        entry_id="abc",
        config_entry=entry,
    )
    await coord.async_refresh()
    assert coord.data.friends["rival"]["online"] is False

    async def get_user_now(name: str):
        return online_user  # both online now

    fake_client.async_get_user.side_effect = get_user_now
    fired: list[Any] = []
    hass.bus.async_listen("fightcade_friend_online", fired.append)
    await coord.async_refresh()
    await hass.async_block_till_done()

    assert len(fired) == 1
    assert fired[0].data["username"] == "rival"
    assert coord.data.friends["rival"]["online"] is True
