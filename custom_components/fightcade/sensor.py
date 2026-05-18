"""Fightcade sensors: per-game rank/matches/time + global last match + events."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import FightcadeConfigEntry
from .const import RANK_MAP
from .coordinator import FightcadeDataUpdateCoordinator
from .entity import build_device_info


async def async_setup_entry(
    hass: HomeAssistant,
    entry: FightcadeConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    username: str = entry.data["username"]

    entities: list[SensorEntity] = [FightcadeLastMatchSensor(coordinator, username)]

    gameinfo = coordinator.data.user.get("gameinfo") or {}
    for gameid in gameinfo:
        entities.append(FightcadeRankSensor(coordinator, username, gameid))
        entities.append(FightcadeMatchesSensor(coordinator, username, gameid))
        entities.append(FightcadeTimePlayedSensor(coordinator, username, gameid))

    # events sensors added in Task 8
    async_add_entities(entities)


class _BaseFightcadeSensor(CoordinatorEntity[FightcadeDataUpdateCoordinator], SensorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator: FightcadeDataUpdateCoordinator, username: str) -> None:
        super().__init__(coordinator)
        self._username = username
        self._attr_device_info = build_device_info(username)


class _BaseFightcadePerGameSensor(_BaseFightcadeSensor):
    """Shared base for sensors tied to one game id."""

    def __init__(
        self, coordinator: FightcadeDataUpdateCoordinator, username: str, gameid: str
    ) -> None:
        super().__init__(coordinator, username)
        self._gameid = gameid

    @property
    def _gameinfo(self) -> dict[str, Any]:
        return (self.coordinator.data.user.get("gameinfo") or {}).get(self._gameid, {})


class FightcadeRankSensor(_BaseFightcadePerGameSensor):
    def __init__(
        self, coordinator: FightcadeDataUpdateCoordinator, username: str, gameid: str
    ) -> None:
        super().__init__(coordinator, username, gameid)
        self._attr_unique_id = f"{username}_{gameid}_rank"
        self._attr_name = f"{gameid} rank"
        self._attr_icon = "mdi:trophy"

    @property
    def native_value(self) -> str:
        return RANK_MAP.get(self._gameinfo.get("rank") or 0, "Unranked")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {"rank_index": self._gameinfo.get("rank") or 0}


class FightcadeMatchesSensor(_BaseFightcadePerGameSensor):
    _attr_state_class = SensorStateClass.TOTAL_INCREASING

    def __init__(
        self, coordinator: FightcadeDataUpdateCoordinator, username: str, gameid: str
    ) -> None:
        super().__init__(coordinator, username, gameid)
        self._attr_unique_id = f"{username}_{gameid}_matches"
        self._attr_name = f"{gameid} matches"
        self._attr_icon = "mdi:counter"
        self._attr_native_unit_of_measurement = "matches"

    @property
    def native_value(self) -> int:
        return int(self._gameinfo.get("num_matches") or 0)


class FightcadeTimePlayedSensor(_BaseFightcadePerGameSensor):
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_device_class = SensorDeviceClass.DURATION
    _attr_native_unit_of_measurement = UnitOfTime.HOURS
    _attr_suggested_display_precision = 1

    def __init__(
        self, coordinator: FightcadeDataUpdateCoordinator, username: str, gameid: str
    ) -> None:
        super().__init__(coordinator, username, gameid)
        self._attr_unique_id = f"{username}_{gameid}_time_played"
        self._attr_name = f"{gameid} time played"
        self._attr_icon = "mdi:clock-outline"

    @property
    def native_value(self) -> float:
        ms = int(self._gameinfo.get("time_played") or 0)
        return round(ms / 3_600_000, 1)


class FightcadeLastMatchSensor(_BaseFightcadeSensor):
    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(self, coordinator: FightcadeDataUpdateCoordinator, username: str) -> None:
        super().__init__(coordinator, username)
        self._attr_unique_id = f"{username}_last_match"
        self._attr_name = "Last match"
        self._attr_icon = "mdi:sword-cross"

    @property
    def native_value(self) -> datetime | None:
        match = self.coordinator.data.last_match
        if match is None:
            return None
        return datetime.fromtimestamp(match["date"] / 1000, tz=UTC)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        match = self.coordinator.data.last_match
        if match is None:
            return {}
        return {
            "gameid": match["gameid"],
            "channelname": match["channelname"],
            "opponent": match["opponent"],
            "opponent_country": match["opponent_country"],
            "you_score": match["you_score"],
            "opponent_score": match["opponent_score"],
            "won": match["won"],
            "duration_seconds": match["duration"],
            "ranked": match["ranked"],
            "replay_url": match["replay_url"],
            "quarkid": match["quarkid"],
        }
