"""Async client for the unofficial Fightcade public API."""

from __future__ import annotations

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
        try:
            async with self._session.post(
                API_URL,
                json=body,
                headers={"Content-Type": "application/json"},
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                if resp.status >= HTTPStatus.INTERNAL_SERVER_ERROR:
                    raise FightcadeApiError(f"server error: {resp.status}")
                if resp.status == HTTPStatus.TOO_MANY_REQUESTS:
                    raise FightcadeApiError("rate limited")
                if resp.status >= HTTPStatus.BAD_REQUEST:
                    raise FightcadeApiError(f"http {resp.status}")
                data: dict[str, Any] = await resp.json()
        except aiohttp.ClientError as err:
            _LOGGER.debug("Fightcade API client error for req=%r: %s", body.get("req"), err)
            raise FightcadeApiError(str(err)) from err
        except TimeoutError as err:
            _LOGGER.debug("Fightcade API timeout for req=%r", body.get("req"))
            raise FightcadeApiError("timeout") from err

        res = data.get("res")
        if res != "OK":
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
