"""Tests for FightcadeClient."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import aiohttp
import pytest
from aiohttp import ClientSession
from aioresponses import aioresponses

from custom_components.fightcade.api import (
    FightcadeApiError,
    FightcadeClient,
    FightcadeUserNotFound,
)
from custom_components.fightcade.const import API_URL

FIXTURES = Path(__file__).parent / "fixtures"


def load_fixture(name: str) -> dict[str, Any]:
    return json.loads((FIXTURES / name).read_text())


@pytest.fixture
async def session():
    async with ClientSession() as s:
        yield s


async def test_get_user_online(session: ClientSession) -> None:
    payload = load_fixture("user_online.json")
    with aioresponses() as m:
        m.post(API_URL, payload=payload)
        client = FightcadeClient(session)
        user = await client.async_get_user("biggs")
    assert user["name"] == "biggs"
    assert "last_online" not in user
    assert user["gameinfo"]["umk3"]["rank"] == 5  # noqa: PLR2004


async def test_get_user_offline_has_last_online(session: ClientSession) -> None:
    payload = load_fixture("user_offline.json")
    with aioresponses() as m:
        m.post(API_URL, payload=payload)
        user = await FightcadeClient(session).async_get_user("biggs")
    assert user["last_online"] == 1716100000000  # noqa: PLR2004


async def test_get_user_not_found_raises(session: ClientSession) -> None:
    payload = load_fixture("user_not_found.json")
    with aioresponses() as m:
        m.post(API_URL, payload=payload)
        with pytest.raises(FightcadeUserNotFound):
            await FightcadeClient(session).async_get_user("nope")


async def test_get_user_replays(session: ClientSession) -> None:
    payload = load_fixture("user_replays.json")
    with aioresponses() as m:
        m.post(API_URL, payload=payload)
        replays = await FightcadeClient(session).async_get_user_replays("biggs")
    assert len(replays) == 2  # noqa: PLR2004
    assert replays[0]["quarkid"] == "1700000000000-1234"


async def test_get_events(session: ClientSession) -> None:
    payload = load_fixture("events_garou.json")
    with aioresponses() as m:
        m.post(API_URL, payload=payload)
        events = await FightcadeClient(session).async_get_events("garou")
    assert len(events) == 2  # noqa: PLR2004
    assert events[0]["name"] == "Weekly Garou"


async def test_http_500_raises_api_error(session: ClientSession) -> None:
    with aioresponses() as m:
        m.post(API_URL, status=500)
        with pytest.raises(FightcadeApiError):
            await FightcadeClient(session).async_get_user("biggs")


async def test_http_429_raises_api_error(session: ClientSession) -> None:
    with aioresponses() as m:
        m.post(API_URL, status=429)
        with pytest.raises(FightcadeApiError, match="rate limited"):
            await FightcadeClient(session).async_get_user("biggs")


async def test_network_error_raises_api_error(session: ClientSession) -> None:
    with aioresponses() as m:
        m.post(API_URL, exception=aiohttp.ClientError("conn refused"))
        with pytest.raises(FightcadeApiError):
            await FightcadeClient(session).async_get_user("biggs")


async def test_timeout_raises_api_error(session: ClientSession) -> None:
    with aioresponses() as m:
        m.post(API_URL, exception=TimeoutError())
        with pytest.raises(FightcadeApiError, match="timeout"):
            await FightcadeClient(session).async_get_user("biggs")
