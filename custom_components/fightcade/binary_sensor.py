"""Fightcade binary sensors: user online + friend online."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import FightcadeConfigEntry
from .coordinator import FightcadeDataUpdateCoordinator
from .entity import build_device_info


async def async_setup_entry(
    hass: HomeAssistant,
    entry: FightcadeConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    entities: list[BinarySensorEntity] = [
        FightcadeOnlineBinarySensor(coordinator, entry.data["username"])
    ]
    # friend sensors added in Task 10
    async_add_entities(entities)


class FightcadeOnlineBinarySensor(
    CoordinatorEntity[FightcadeDataUpdateCoordinator], BinarySensorEntity
):
    """`on` when the user has no last_online timestamp (currently online)."""

    _attr_has_entity_name = True
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_translation_key = "user_online"

    def __init__(self, coordinator: FightcadeDataUpdateCoordinator, username: str) -> None:
        super().__init__(coordinator)
        self._username = username
        self._attr_unique_id = f"{username}_online"
        self._attr_name = "Online"
        self._attr_device_info = build_device_info(username)

    @property
    def is_on(self) -> bool:
        return self.coordinator.data.online

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        user = self.coordinator.data.user
        attrs: dict[str, Any] = {"account_created": _epoch_ms_to_iso(user["date"])}
        if (lo := user.get("last_online")) is not None:
            attrs["last_online"] = lo
            attrs["last_online_iso"] = _epoch_ms_to_iso(lo)
        return attrs


def _epoch_ms_to_iso(ms: int) -> str:
    return datetime.fromtimestamp(ms / 1000, tz=UTC).isoformat()
