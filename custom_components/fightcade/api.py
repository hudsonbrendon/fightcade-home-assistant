"""Async client for the unofficial Fightcade public API."""

from __future__ import annotations

import json
import logging
from http import HTTPStatus
from typing import Any

import aiohttp

from .const import API_URL

_LOGGER = logging.getLogger(__name__)


class FightcadeApiError(Exception):
    """Generic API failure (HTTP error, non-OK response)."""


class FightcadeUserNotFound(FightcadeApiError):
    """Raised when a username does not exist on Fightcade."""


class FightcadeClient:
    """Thin async wrapper over the Fightcade JSON-RPC-style API."""

    def __init__(self, session: aiohttp.ClientSession) -> None:
        self._session = session

    async def _request(self, body: dict[str, Any]) -> dict[str, Any]:
        req = body.get("req")
        try:
            async with self._session.post(
                API_URL,
                json=body,
                headers={"Content-Type": "application/json"},
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                if resp.status >= HTTPStatus.BAD_REQUEST:
                    snippet = (await resp.text())[:200]
                    _LOGGER.warning(
                        "Fightcade API HTTP %s for req=%r body=%r",
                        resp.status,
                        req,
                        snippet,
                    )
                    if resp.status >= HTTPStatus.INTERNAL_SERVER_ERROR:
                        raise FightcadeApiError(f"server error: {resp.status}")
                    if resp.status == HTTPStatus.TOO_MANY_REQUESTS:
                        raise FightcadeApiError("rate limited")
                    raise FightcadeApiError(f"http {resp.status}")
                try:
                    data = await resp.json(content_type=None)
                except json.JSONDecodeError as err:
                    raw = (await resp.text())[:200]
                    _LOGGER.warning(
                        "Fightcade API non-JSON body for req=%r: %s; body=%r", req, err, raw
                    )
                    raise FightcadeApiError(f"invalid json: {err}") from err
        except aiohttp.ClientError as err:
            _LOGGER.warning("Fightcade API client error for req=%r: %s", req, err)
            raise FightcadeApiError(str(err)) from err
        except TimeoutError as err:
            _LOGGER.warning("Fightcade API timeout for req=%r", req)
            raise FightcadeApiError("timeout") from err

        if not isinstance(data, dict):
            _LOGGER.warning("Fightcade API unexpected payload type %s for req=%r", type(data), req)
            raise FightcadeApiError(f"unexpected response type: {type(data).__name__}")

        res = data.get("res")
        if not isinstance(res, str) or res.upper() != "OK":
            _LOGGER.warning("Fightcade API res=%r for req=%r payload=%r", res, req, data)
            raise FightcadeApiError(f"api res: {res!r}")
        return data

    async def async_get_user(self, username: str) -> dict[str, Any]:
        """Fetch a user's profile and gameinfo."""
        try:
            data = await self._request({"req": "getuser", "username": username})
        except FightcadeApiError as err:
            if "not found" in str(err).lower():
                raise FightcadeUserNotFound(str(err)) from err
            raise
        user = data.get("user")
        if user is None:
            raise FightcadeApiError("missing 'user' key in response")
        return user

    async def async_get_user_replays(
        self, username: str, *, limit: int = 5
    ) -> list[dict[str, Any]]:
        """Fetch the user's most recent replays (newest first)."""
        data = await self._request({"req": "searchquarks", "username": username, "limit": limit})
        results = (data.get("results") or {}).get("results")
        if results is None:
            raise FightcadeApiError("missing 'results' key in response")
        return list(results)

    async def async_get_events(self, gameid: str, *, limit: int = 15) -> list[dict[str, Any]]:
        """Fetch active events for a game (newest first)."""
        data = await self._request({"req": "searchevents", "gameid": gameid, "limit": limit})
        results = (data.get("results") or {}).get("results")
        if results is None:
            raise FightcadeApiError("missing 'results' key in response")
        return list(results)
