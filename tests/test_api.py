"""Tests for FightcadeClient."""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import Any

import aiohttp
import pytest
from aiohttp import ClientSession
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

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
async def session(aioclient_mock: AiohttpClientMocker):
    s = aioclient_mock.create_session(asyncio.get_running_loop())
    yield s
    await s.close()


async def test_get_user_online(session: ClientSession, aioclient_mock: AiohttpClientMocker) -> None:
    payload = load_fixture("user_online.json")
    aioclient_mock.post(API_URL, json=payload)
    client = FightcadeClient(session)
    user = await client.async_get_user("biggs")
    assert user["name"] == "biggs"
    assert "last_online" not in user
    assert user["gameinfo"]["umk3"]["rank"] == 5  # noqa: PLR2004


async def test_get_user_offline_has_last_online(
    session: ClientSession, aioclient_mock: AiohttpClientMocker
) -> None:
    payload = load_fixture("user_offline.json")
    aioclient_mock.post(API_URL, json=payload)
    user = await FightcadeClient(session).async_get_user("biggs")
    assert user["last_online"] == 1716100000000  # noqa: PLR2004


async def test_get_user_not_found_raises(
    session: ClientSession, aioclient_mock: AiohttpClientMocker
) -> None:
    payload = load_fixture("user_not_found.json")
    aioclient_mock.post(API_URL, json=payload)
    with pytest.raises(FightcadeUserNotFound):
        await FightcadeClient(session).async_get_user("nope")


async def test_get_user_replays(
    session: ClientSession, aioclient_mock: AiohttpClientMocker
) -> None:
    payload = load_fixture("user_replays.json")
    aioclient_mock.post(API_URL, json=payload)
    replays = await FightcadeClient(session).async_get_user_replays("biggs")
    assert len(replays) == 2  # noqa: PLR2004
    assert replays[0]["quarkid"] == "1700000000000-1234"


async def test_get_events(session: ClientSession, aioclient_mock: AiohttpClientMocker) -> None:
    payload = load_fixture("events_garou.json")
    aioclient_mock.post(API_URL, json=payload)
    events = await FightcadeClient(session).async_get_events("garou")
    assert len(events) == 2  # noqa: PLR2004
    assert events[0]["name"] == "Weekly Garou"


async def test_http_500_raises_api_error(
    session: ClientSession, aioclient_mock: AiohttpClientMocker
) -> None:
    aioclient_mock.post(API_URL, status=500)
    with pytest.raises(FightcadeApiError):
        await FightcadeClient(session).async_get_user("biggs")


async def test_http_429_raises_api_error(
    session: ClientSession, aioclient_mock: AiohttpClientMocker
) -> None:
    aioclient_mock.post(API_URL, status=429)
    with pytest.raises(FightcadeApiError, match="rate limited"):
        await FightcadeClient(session).async_get_user("biggs")


async def test_network_error_raises_api_error(
    session: ClientSession, aioclient_mock: AiohttpClientMocker
) -> None:
    aioclient_mock.post(API_URL, exc=aiohttp.ClientError("conn refused"))
    with pytest.raises(FightcadeApiError):
        await FightcadeClient(session).async_get_user("biggs")


async def test_timeout_raises_api_error(
    session: ClientSession, aioclient_mock: AiohttpClientMocker
) -> None:
    aioclient_mock.post(API_URL, exc=TimeoutError())
    with pytest.raises(FightcadeApiError, match="timeout"):
        await FightcadeClient(session).async_get_user("biggs")


async def test_invalid_json_body_raises_api_error(
    session: ClientSession, aioclient_mock: AiohttpClientMocker
) -> None:
    """Malformed JSON body must not bubble as JSONDecodeError."""
    aioclient_mock.post(
        API_URL,
        status=200,
        text="{ not: valid, json }",
        headers={"Content-Type": "application/json"},
    )
    with pytest.raises(FightcadeApiError):
        await FightcadeClient(session).async_get_user("biggs")


async def test_non_dict_response_raises_api_error(
    session: ClientSession, aioclient_mock: AiohttpClientMocker
) -> None:
    """List/string response body must raise FightcadeApiError, not AttributeError."""
    aioclient_mock.post(API_URL, json=["not", "a", "dict"])
    with pytest.raises(FightcadeApiError):
        await FightcadeClient(session).async_get_user("biggs")


async def test_get_user_accepts_lowercase_ok(
    session: ClientSession, aioclient_mock: AiohttpClientMocker
) -> None:
    """API response with res='ok' (any case) must be treated as success."""
    payload = {"res": "ok", "user": {"name": "biggs", "gameinfo": {}}}
    aioclient_mock.post(API_URL, json=payload)
    user = await FightcadeClient(session).async_get_user("biggs")
    assert user["name"] == "biggs"


async def test_get_user_missing_res_key_raises_api_error(
    session: ClientSession, aioclient_mock: AiohttpClientMocker
) -> None:
    aioclient_mock.post(API_URL, json={"user": {"name": "biggs"}})
    with pytest.raises(FightcadeApiError):
        await FightcadeClient(session).async_get_user("biggs")


async def test_get_user_ok_but_missing_user_raises_api_error(
    session: ClientSession,
    aioclient_mock: AiohttpClientMocker,
) -> None:
    aioclient_mock.post(API_URL, json={"res": "OK"})
    with pytest.raises(FightcadeApiError, match="missing 'user'"):
        await FightcadeClient(session).async_get_user("biggs")


async def test_http_403_cloudflare_raises_api_error(
    session: ClientSession, aioclient_mock: AiohttpClientMocker
) -> None:
    """Cloudflare-blocked 403 must surface as cannot_connect, never user_not_found."""
    aioclient_mock.post(API_URL, status=403, json={"error": "Forbidden", "res": "error"})
    with pytest.raises(FightcadeApiError) as excinfo:
        await FightcadeClient(session).async_get_user("biggs")
    assert "403" in str(excinfo.value)


async def test_http_401_raises_api_error(
    session: ClientSession, aioclient_mock: AiohttpClientMocker
) -> None:
    aioclient_mock.post(API_URL, status=401)
    with pytest.raises(FightcadeApiError):
        await FightcadeClient(session).async_get_user("biggs")


async def test_get_user_replays_missing_results_raises_api_error(
    session: ClientSession,
    aioclient_mock: AiohttpClientMocker,
) -> None:
    aioclient_mock.post(API_URL, json={"res": "OK"})
    with pytest.raises(FightcadeApiError):
        await FightcadeClient(session).async_get_user_replays("biggs")


async def test_get_user_replays_empty_list(
    session: ClientSession, aioclient_mock: AiohttpClientMocker
) -> None:
    aioclient_mock.post(API_URL, json={"res": "OK", "results": {"results": []}})
    replays = await FightcadeClient(session).async_get_user_replays("biggs")
    assert replays == []


async def test_get_events_missing_results_raises_api_error(
    session: ClientSession,
    aioclient_mock: AiohttpClientMocker,
) -> None:
    aioclient_mock.post(API_URL, json={"res": "OK"})
    with pytest.raises(FightcadeApiError):
        await FightcadeClient(session).async_get_events("garou")


async def test_get_events_empty_list(
    session: ClientSession, aioclient_mock: AiohttpClientMocker
) -> None:
    aioclient_mock.post(API_URL, json={"res": "OK", "results": {"results": []}})
    events = await FightcadeClient(session).async_get_events("garou")
    assert events == []


async def test_request_failure_logs_warning_with_status_and_body(
    session: ClientSession, aioclient_mock: AiohttpClientMocker, caplog: pytest.LogCaptureFixture
) -> None:
    """Cloudflare 403 with a Forbidden body must produce a visible WARNING log."""
    caplog.set_level(logging.WARNING, logger="custom_components.fightcade.api")
    aioclient_mock.post(API_URL, status=403, json={"error": "Forbidden", "res": "error"})
    with pytest.raises(FightcadeApiError):
        await FightcadeClient(session).async_get_user("biggs")
    msgs = [r.getMessage() for r in caplog.records]
    assert any("403" in m for m in msgs)
    assert any("Forbidden" in m for m in msgs)


async def test_request_timeout_logs_warning(
    session: ClientSession, aioclient_mock: AiohttpClientMocker, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.WARNING, logger="custom_components.fightcade.api")
    aioclient_mock.post(API_URL, exc=TimeoutError())
    with pytest.raises(FightcadeApiError):
        await FightcadeClient(session).async_get_user("biggs")
    assert any("timeout" in r.getMessage().lower() for r in caplog.records)


async def test_request_non_ok_res_logs_warning(
    session: ClientSession, aioclient_mock: AiohttpClientMocker, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.WARNING, logger="custom_components.fightcade.api")
    aioclient_mock.post(API_URL, json={"res": "error", "detail": "blocked"})
    with pytest.raises(FightcadeApiError):
        await FightcadeClient(session).async_get_user("biggs")
    msgs = [r.getMessage() for r in caplog.records]
    assert any("'error'" in m for m in msgs)


async def test_get_user_passes_exact_username_case(
    session: ClientSession, aioclient_mock: AiohttpClientMocker
) -> None:
    """Fightcade usernames are case-sensitive — client must not lowercase them."""
    payload = {"res": "OK", "user": {"name": "BiGgs", "gameinfo": {}}}
    aioclient_mock.post(API_URL, json=payload)
    await FightcadeClient(session).async_get_user("BiGgs")
    _method, _url, sent, _headers = aioclient_mock.mock_calls[-1]
    assert sent["username"] == "BiGgs"
