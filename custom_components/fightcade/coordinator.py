"""DataUpdateCoordinator for the Fightcade integration."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import FightcadeApiError, FightcadeClient, FightcadeUserNotFound
from .const import (
    DOMAIN,
    EVENT_FRIEND_ONLINE,
    EVENT_NEW_TOURNAMENT,
    FAVORITE_GAMES_LIMIT,
)
from .models import extract_favorite_gameids, extract_last_match, is_online

_LOGGER = logging.getLogger(__name__)

STORAGE_VERSION = 1


@dataclass
class FightcadeData:
    """Single refresh snapshot consumed by all entities."""

    user: dict[str, Any]
    online: bool
    last_match: dict[str, Any] | None
    events: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    friends: dict[str, dict[str, Any]] = field(default_factory=dict)


def _event_id(event: dict[str, Any]) -> str:
    return f"{event['gameid']}:{event['name']}:{event['date']}"


class FightcadeDataUpdateCoordinator(DataUpdateCoordinator[FightcadeData]):
    """Polls Fightcade and feeds all entities for one config entry."""

    def __init__(
        self,
        hass: HomeAssistant,
        *,
        client: FightcadeClient,
        username: str,
        friends: list[str],
        poll_interval: int,
        entry_id: str,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}.{username}",
            update_interval=timedelta(seconds=poll_interval),
        )
        self._client = client
        self._username = username
        self._friends = friends
        self._first_refresh = True
        self._seen_events: dict[str, set[str]] = {}
        self._friend_online: dict[str, bool] = {}
        self._store: Store[dict[str, list[str]]] = Store(
            hass, STORAGE_VERSION, f"{DOMAIN}.{entry_id}.seen_events"
        )

    async def _async_setup(self) -> None:
        stored = await self._store.async_load() or {}
        self._seen_events = {gid: set(ids) for gid, ids in stored.items()}

    async def _async_update_data(self) -> FightcadeData:
        try:
            user = await self._client.async_get_user(self._username)
            replays = await self._client.async_get_user_replays(self._username, limit=5)

            favorites = extract_favorite_gameids(user, limit=FAVORITE_GAMES_LIMIT)
            events_by_game = await self._fetch_events(favorites)
            friends_state = await self._fetch_friends()
        except FightcadeUserNotFound as err:
            raise UpdateFailed(f"username not found: {err}") from err
        except FightcadeApiError as err:
            raise UpdateFailed(str(err)) from err

        self._detect_new_events(events_by_game)
        self._detect_friend_transitions(friends_state)
        self._first_refresh = False

        await self._store.async_save({gid: list(ids) for gid, ids in self._seen_events.items()})

        return FightcadeData(
            user=user,
            online=is_online(user),
            last_match=extract_last_match(self._username, replays),
            events=events_by_game,
            friends=friends_state,
        )

    async def _fetch_events(self, favorites: list[str]) -> dict[str, list[dict[str, Any]]]:
        if not favorites:
            return {}
        results = await asyncio.gather(
            *(self._client.async_get_events(gid) for gid in favorites),
            return_exceptions=True,
        )
        out: dict[str, list[dict[str, Any]]] = {}
        for gid, res in zip(favorites, results, strict=True):
            if isinstance(res, Exception):
                _LOGGER.warning("event fetch failed for %s: %s", gid, res)
                out[gid] = []
            else:
                out[gid] = res
        return out

    async def _fetch_friends(self) -> dict[str, dict[str, Any]]:
        if not self._friends:
            return {}
        results = await asyncio.gather(
            *(self._client.async_get_user(f) for f in self._friends),
            return_exceptions=True,
        )
        out: dict[str, dict[str, Any]] = {}
        for friend, res in zip(self._friends, results, strict=True):
            if isinstance(res, Exception):
                _LOGGER.debug("friend fetch failed for %s: %s", friend, res)
                out[friend] = {"online": False, "error": str(res), "user": None}
            else:
                out[friend] = {"online": is_online(res), "error": None, "user": res}
        return out

    def _detect_new_events(self, events_by_game: dict[str, list[dict[str, Any]]]) -> None:
        for gameid, events in events_by_game.items():
            current_ids = {_event_id(e): e for e in events}
            seen = self._seen_events.setdefault(gameid, set())
            new_ids = set(current_ids) - seen
            if not self._first_refresh:
                for nid in new_ids:
                    self.hass.bus.async_fire(EVENT_NEW_TOURNAMENT, current_ids[nid])
            self._seen_events[gameid] = set(current_ids)

    def _detect_friend_transitions(self, friends_state: dict[str, dict[str, Any]]) -> None:
        for friend, info in friends_state.items():
            was_online = self._friend_online.get(friend, False)
            now_online = info["online"]
            if not self._first_refresh and not was_online and now_online:
                self.hass.bus.async_fire(EVENT_FRIEND_ONLINE, {"username": friend})
            self._friend_online[friend] = now_online
