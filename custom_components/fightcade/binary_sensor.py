"""Fightcade binary sensors: user online + friend online."""

from __future__ import annotations

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
from .models import epoch_ms_to_iso


async def async_setup_entry(
    hass: HomeAssistant,
    entry: FightcadeConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    username: str = entry.data["username"]
    entities: list[BinarySensorEntity] = [FightcadeOnlineBinarySensor(coordinator, username)]
    for friend in coordinator.data.friends:
        entities.append(FightcadeFriendOnlineBinarySensor(coordinator, username, friend))
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
        attrs: dict[str, Any] = {"account_created": epoch_ms_to_iso(user["date"])}
        if (lo := user.get("last_online")) is not None:
            attrs["last_online"] = lo
            attrs["last_online_iso"] = epoch_ms_to_iso(lo)
        return attrs


class FightcadeFriendOnlineBinarySensor(
    CoordinatorEntity[FightcadeDataUpdateCoordinator], BinarySensorEntity
):
    _attr_has_entity_name = True
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY

    def __init__(
        self,
        coordinator: FightcadeDataUpdateCoordinator,
        username: str,
        friend: str,
    ) -> None:
        super().__init__(coordinator)
        self._friend = friend
        self._attr_unique_id = f"{username}_friend_{friend}_online"
        self._attr_name = f"Friend {friend} online"
        self._attr_device_info = build_device_info(username)
        self.entity_id = f"binary_sensor.fightcade_friend_{friend}_online"

    @property
    def is_on(self) -> bool:
        info = self.coordinator.data.friends.get(self._friend)
        return bool(info and info["online"])

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        info = self.coordinator.data.friends.get(self._friend) or {}
        attrs: dict[str, Any] = {"username": self._friend}
        if info.get("error"):
            attrs["error"] = info["error"]
        user = info.get("user") or {}
        if (lo := user.get("last_online")) is not None:
            attrs["last_online"] = lo
        return attrs
