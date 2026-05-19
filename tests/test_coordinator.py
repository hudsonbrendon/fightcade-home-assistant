"""Tests for FightcadeDataUpdateCoordinator."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.fightcade.api import FightcadeApiError, FightcadeUserNotFound
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


async def test_end_to_end_new_event_fires_after_second_refresh(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    mock_config_entry.add_to_hass(hass)
    user = load("user_online.json")["user"]
    replays = load("user_replays.json")["results"]["results"]
    events_first = load("events_garou.json")["results"]["results"]

    surprise = {
        "name": "Surprise",
        "author": "x",
        "date": 1730000000000,
        "gameid": "umk3",
        "link": "https://example.com",
        "region": "EU",
    }

    with patch("custom_components.fightcade.FightcadeClient") as ClientCls:
        c = AsyncMock()
        c.async_get_user.return_value = user
        c.async_get_user_replays.return_value = replays

        # First refresh: every favorite gameid gets the base events_first.
        # Second refresh: only umk3 sees the new Surprise event added; others
        # see events_first unchanged, so we don't multiply the firing across
        # favorites.
        seen_calls = {"n": 0}
        first_refresh_count = 3  # one call per favorite gameid (limit=3)

        async def get_events(gameid: str):
            seen_calls["n"] += 1
            if seen_calls["n"] <= first_refresh_count:
                return events_first
            if gameid == "umk3":
                return [*events_first, surprise]
            return events_first

        c.async_get_events.side_effect = get_events
        ClientCls.return_value = c

        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

        fired: list[Any] = []
        hass.bus.async_listen("fightcade_event", fired.append)

        coord = mock_config_entry.runtime_data
        await coord.async_refresh()
        await hass.async_block_till_done()

    assert [ev.data["name"] for ev in fired] == ["Surprise"]


async def test_refresh_marks_failure_when_user_not_found(
    hass: HomeAssistant, fake_client: AsyncMock
) -> None:
    fake_client.async_get_user.side_effect = FightcadeUserNotFound("nope")
    entry = MockConfigEntry(domain="fightcade", data={"username": "x"}, entry_id="z")
    entry.add_to_hass(hass)
    coord = FightcadeDataUpdateCoordinator(
        hass,
        client=fake_client,
        username="x",
        friends=[],
        poll_interval=60,
        entry_id="z",
        config_entry=entry,
    )
    await coord.async_refresh()
    assert coord.last_update_success is False


async def test_refresh_marks_failure_on_api_error(
    hass: HomeAssistant, fake_client: AsyncMock
) -> None:
    fake_client.async_get_user.side_effect = FightcadeApiError("boom")
    entry = MockConfigEntry(domain="fightcade", data={"username": "x"}, entry_id="z")
    entry.add_to_hass(hass)
    coord = FightcadeDataUpdateCoordinator(
        hass,
        client=fake_client,
        username="x",
        friends=[],
        poll_interval=60,
        entry_id="z",
        config_entry=entry,
    )
    await coord.async_refresh()
    assert coord.last_update_success is False


async def test_friend_fetch_failure_marks_error_not_online(
    hass: HomeAssistant, fake_client: AsyncMock
) -> None:
    async def get_user(name: str):
        if name == "biggs":
            return load("user_online.json")["user"]
        raise FightcadeApiError("friend boom")

    fake_client.async_get_user.side_effect = get_user

    entry = MockConfigEntry(domain="fightcade", data={"username": "biggs"}, entry_id="z")
    entry.add_to_hass(hass)
    coord = FightcadeDataUpdateCoordinator(
        hass,
        client=fake_client,
        username="biggs",
        friends=["bad_friend"],
        poll_interval=60,
        entry_id="z",
        config_entry=entry,
    )
    await coord.async_refresh()
    assert coord.data is not None
    bad = coord.data.friends["bad_friend"]
    assert bad["online"] is False
    assert bad["user"] is None
    assert "boom" in bad["error"]


async def test_event_fetch_failure_logs_warning_keeps_other_games(
    hass: HomeAssistant, fake_client: AsyncMock
) -> None:
    base_events = load("events_garou.json")["results"]["results"]

    async def get_events(gameid: str):
        if gameid == "umk3":
            raise FightcadeApiError("event boom")
        return base_events

    fake_client.async_get_events.side_effect = get_events

    entry = MockConfigEntry(domain="fightcade", data={"username": "biggs"}, entry_id="z")
    entry.add_to_hass(hass)
    coord = FightcadeDataUpdateCoordinator(
        hass,
        client=fake_client,
        username="biggs",
        friends=[],
        poll_interval=60,
        entry_id="z",
        config_entry=entry,
    )
    await coord.async_refresh()
    assert coord.data is not None
    assert coord.data.events["umk3"] == []
    # other favorite gameids in the fixture have a populated events list
    other_games = [g for g in coord.data.events if g != "umk3"]
    assert other_games  # at least one other favorite
    assert all(coord.data.events[g] for g in other_games)


async def test_no_friends_returns_empty_dict(hass: HomeAssistant, fake_client: AsyncMock) -> None:
    entry = MockConfigEntry(domain="fightcade", data={"username": "biggs"}, entry_id="z")
    entry.add_to_hass(hass)
    coord = FightcadeDataUpdateCoordinator(
        hass,
        client=fake_client,
        username="biggs",
        friends=[],
        poll_interval=60,
        entry_id="z",
        config_entry=entry,
    )
    await coord.async_refresh()
    assert coord.data is not None
    assert coord.data.friends == {}


async def test_no_favorite_games_returns_empty_events(
    hass: HomeAssistant, fake_client: AsyncMock
) -> None:
    fake_client.async_get_user.return_value = {"name": "x", "gameinfo": {}}
    entry = MockConfigEntry(domain="fightcade", data={"username": "x"}, entry_id="z")
    entry.add_to_hass(hass)
    coord = FightcadeDataUpdateCoordinator(
        hass,
        client=fake_client,
        username="x",
        friends=[],
        poll_interval=60,
        entry_id="z",
        config_entry=entry,
    )
    await coord.async_refresh()
    assert coord.data is not None
    assert coord.data.events == {}
    fake_client.async_get_events.assert_not_awaited()
